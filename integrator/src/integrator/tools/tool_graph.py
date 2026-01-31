"""
End-to-end pipeline for building a Procedural Knowledge Graph (PKG) in Neo4j
and extracting candidate skills for LLM processing.

Steps:
1. Load hierarchy + relationships JSON.
2. Ingest into Neo4j as Domain / Capability / Tool / NEXT_TOOL.
3. Extract candidate tool chains & single tools per capability.
4. Produce JSON payloads for LLM.
5. (Optional) Ingest Skills back into Neo4j from LLM output.

Requirements:
    pip install neo4j

Environment variables (or edit constants below):
    NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
"""

import json
import os
from dataclasses import dataclass, asdict
from collections import defaultdict
from typing import Dict, List, Tuple, Any

from neo4j import GraphDatabase
from sqlalchemy import select

from integrator.utils.db import get_db_cm
from integrator.utils.llm import LLM, Embedder

from integrator.domains.domain_db_model import Domain
from integrator.domains.domain_db_crud import get_capabilities_by_domain
from integrator.tools.tool_graph_crud import (
    correlate_tools,
    is_tool_analyzed

)
from integrator.domains.domain_graph_crud import (
    create_domain_node,
    create_capability_node,
    create_domain_capability_edge

)
from integrator.domains.domain_llm import get_tool_rel_by_tool, extract_skills_from_tools
from integrator.utils.graph import get_graph_driver, close_graph_driver
from integrator.tools.tool_db_crud import (
     get_tools_by_capability_name as get_tools_by_capability_name_from_db,
)


# ---------------------------
# Config
# ---------------------------

NEO4J_URI = os.environ.get("NEO4J_URI", "neo4j://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "password")

HIERARCHY_PATH = "canonical_tools_classified_r2.json"
RELATIONS_PATH = "canonical_tool_rel.json"
LLM_PAYLOAD_PATH = "llm_tool_candidates.json"

# If you later have LLM output, you can save it e.g. as:
LLM_SKILLS_PATH = "llm_skills_output.json"


# ---------------------------
# Data structures
# ---------------------------

@dataclass
class ToolEdge:
    from_tool: str
    to_tool: str
    domain: str
    capability: str
    composite_intent: str | None


@dataclass
class CandidatePath:
    type: str          # "chain" or "single_tool"
    tools: List[str]   # ordered list of tool names


# ---------------------------
# Load JSON
# ---------------------------

def load_hierarchy(path: str) -> Dict[str, Any]:
    """Load domain -> capability -> tools hierarchy JSON."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_tool_relations(path: str) -> List[Dict[str, Any]]:
    """
    Load list of domain/capability tool relationships.

    Each element looks like:
      { "<domain>": { "<capability>": [ { "selected_tools": [...], "composite_intent": "..." }, ... ] } }
    """
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------
# Neo4j: basic utilities
# ---------------------------

def get_driver() -> GraphDatabase.driver:

    NEO4J_URI="neo4j://localhost:7687"
    NEO4J_USER="neo4j"
    NEO4J_PASSWORD="password"

    return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))


def create_constraints(session) -> None:
    """Create uniqueness constraints for Domain, Capability, Tool, Skill."""
    session.run(
        """
        CREATE CONSTRAINT domain_name IF NOT EXISTS
        FOR (d:Domain) REQUIRE d.name IS UNIQUE
        """
    )
    session.run(
        """
        CREATE CONSTRAINT capability_key IF NOT EXISTS
        FOR (c:Capability) REQUIRE (c.name, c.domain) IS UNIQUE
        """
    )
    session.run(
        """
        CREATE CONSTRAINT tool_name IF NOT EXISTS
        FOR (t:Tool) REQUIRE t.name IS UNIQUE
        """
    )
    session.run(
        """
        CREATE CONSTRAINT skill_key IF NOT EXISTS
        FOR (s:Skill) REQUIRE (s.name, s.capability, s.domain) IS UNIQUE
        """
    )


# ---------------------------
# Neo4j ingestion: hierarchy + tool edges
# ---------------------------

def ingest_hierarchy(session, hierarchy: Dict[str, Any]) -> None:
    """
    Ingest Domain, Capability, Tool nodes and HAS_CAPABILITY / HAS_TOOL relationships.
    """
    for domain, capabilities in hierarchy.items():
        # MERGE Domain
        session.run(
            """
            MERGE (d:Domain {name: $domain})
            """,
            domain=domain,
        )

        for capability, tools in capabilities.items():
            # MERGE Capability and connect to Domain
            session.run(
                """
                MERGE (c:Capability {name: $capability, domain: $domain})
                WITH c
                MATCH (d:Domain {name: $domain})
                MERGE (d)-[:HAS_CAPABILITY]->(c)
                """,
                domain=domain,
                capability=capability,
            )

            # MERGE Tools and connect to Capability
            for tool in tools:
                t_name = tool["tool_name"]
                # All tool properties (including domain/capability for convenience)
                props = {
                    "name": t_name,
                    "domain": domain,
                    "capability": capability,
                }
                for k, v in tool.items():
                    if k == "tool_name":
                        continue
                    props[k] = v

                session.run(
                    """
                    MERGE (t:Tool {name: $name})
                    SET t += $props
                    """,
                    name=t_name,
                    props=props,
                )

                session.run(
                    """
                    MATCH (c:Capability {name: $capability, domain: $domain}),
                          (t:Tool {name: $tool_name})
                    MERGE (c)-[:HAS_TOOL]->(t)
                    """,
                    domain=domain,
                    capability=capability,
                    tool_name=t_name,
                )


def ingest_tool_relationships(session, relations: List[Dict[str, Any]]) -> None:
    """
    Ingest NEXT_TOOL relationships (procedural edges) between Tools.
    """
    for domain_block in relations:
        for domain, capabilities in domain_block.items():
            for capability, rel_list in capabilities.items():
                for rel in rel_list:
                    tools = rel.get("selected_tools", [])
                    if len(tools) != 2:
                        continue
                    t1, t2 = tools
                    composite_intent = rel.get("composite_intent")

                    session.run(
                        """
                        MATCH (t1:Tool {name: $t1_name}),
                              (t2:Tool {name: $t2_name})
                        MERGE (t1)-[r:NEXT_TOOL {domain: $domain, capability: $capability}]->(t2)
                        SET r.composite_intent = $composite_intent
                        """,
                        t1_name=t1,
                        t2_name=t2,
                        domain=domain,
                        capability=capability,
                        composite_intent=composite_intent,
                    )


# ---------------------------
# Neo4j queries for extraction
# ---------------------------

def get_all_capabilities(session) -> List[Tuple[str, str]]:
    """
    Return all (domain, capability) pairs.
    """
    query = """
    MATCH (d:Domain)-[:HAS_CAPABILITY]->(c:Capability)
    RETURN DISTINCT d.name AS domain, c.name AS capability
    ORDER BY domain, capability
    """
    result = session.run(query)
    return [(r["domain"], r["capability"]) for r in result]


def get_tools_and_edges_for_capability(
    session,
    domain: str,
    capability: str,
) -> tuple[Dict[str, Dict[str, Any]], List[ToolEdge]]:
    """
    For a given (domain, capability), retrieve:
      - Tools and their properties (as dict[name] = properties)
      - NEXT_TOOL edges (as ToolEdge list)
    """
    # Tools
    tools_query = """
    MATCH (d:Domain {name:$domain})-[:HAS_CAPABILITY]->(c:Capability {name:$capability})
    MATCH (c)-[:HAS_TOOL]->(t:Tool)
    RETURN t
    """
    tools: Dict[str, Dict[str, Any]] = {}
    for record in session.run(tools_query, domain=domain, capability=capability):
        t = record["t"]
        name = t["name"]
        props = dict(t)
        tools[name] = props

    # Edges
    edges_query = """
    MATCH (d:Domain {name:$domain})-[:HAS_CAPABILITY]->(c:Capability {name:$capability})
    MATCH (c)-[:HAS_TOOL]->(t1:Tool)-[r:NEXT_TOOL]->(t2:Tool)
    RETURN t1.name AS from, t2.name AS to, r.composite_intent AS composite_intent
    """
    edges: List[ToolEdge] = []
    for record in session.run(edges_query, domain=domain, capability=capability):
        edges.append(
            ToolEdge(
                from_tool=record["from"],
                to_tool=record["to"],
                domain=domain,
                capability=capability,
                composite_intent=record["composite_intent"],
            )
        )

    return tools, edges


# ---------------------------
# Path decomposition (tool chains + isolated tools)
# ---------------------------

def decompose_paths(
    tools: Dict[str, Dict[str, Any]],
    edges: List[ToolEdge],
) -> List[CandidatePath]:
    """
    Given tools + NEXT_TOOL edges for a capability, return maximal linear chains
    and isolated tools as CandidatePath objects.

    This is O(V+E) and suitable for working per capability.
    """
    if not tools:
        return []

    successors: Dict[str, List[str]] = defaultdict(list)
    predecessors: Dict[str, List[str]] = defaultdict(list)

    for e in edges:
        successors[e.from_tool].append(e.to_tool)
        predecessors[e.to_tool].append(e.from_tool)

    all_tool_names = set(tools.keys())

    # 1) Isolated tools: no in or out edges
    isolated = [
        t for t in all_tool_names
        if len(successors[t]) == 0 and len(predecessors[t]) == 0
    ]

    # 2) Maximal linear chains
    visited: set[str] = set()
    chains: List[List[str]] = []

    # A chain start: has outgoing edges AND in-degree != 1
    potential_starts = [
        t for t in all_tool_names
        if len(successors[t]) > 0 and len(predecessors[t]) != 1
    ]

    for start in potential_starts:
        for succ in successors[start]:
            path = [start]
            cur = succ
            prev = start

            while True:
                path.append(cur)
                visited.add(prev)
                visited.add(cur)

                # Stop if cur is not strictly in a line (in = 1, out = 1)
                if len(successors[cur]) != 1 or len(predecessors[cur]) != 1:
                    break

                nxt = successors[cur][0]

                # Simple cycle guard
                if nxt in path:
                    break

                prev = cur
                cur = nxt

            chains.append(path)

    # 3) Leftovers (e.g., small cycles or middle-of-chain nodes not caught)
    leftovers = [
        t for t in all_tool_names
        if t not in visited and t not in isolated
        and (len(successors[t]) > 0 or len(predecessors[t]) > 0)
    ]

    for t in leftovers:
        # conservative: record as a chain of [t, succ] if there is a succ,
        # else [t]
        if successors[t]:
            chains.append([t, successors[t][0]])
        else:
            chains.append([t])

    candidate_paths: List[CandidatePath] = []

    for tool_name in isolated:
        candidate_paths.append(
            CandidatePath(type="single_tool", tools=[tool_name])
        )

    for chain in chains:
        if len(chain) == 1:
            candidate_paths.append(
                CandidatePath(type="single_tool", tools=chain)
            )
        else:
            candidate_paths.append(
                CandidatePath(type="chain", tools=chain)
            )

    return candidate_paths


# ---------------------------
# LLM payload building
# ---------------------------

def build_llm_payload_for_capability(
    session,
    domain: str,
    capability: str,
) -> Dict[str, Any]:
    """
    Returns a JSON-serializable payload with:
      - domain, capability
      - tool metadata
      - NEXT_TOOL relationships
      - candidate_paths (chains + single_tools)
    """
    tools, edges = get_tools_and_edges_for_capability(session, domain, capability)
    candidate_paths = decompose_paths(tools, edges)

    return {
        "domain": domain,
        "capability": capability,
        "tools": list(tools.values()),      # list of tool property dicts
        "relationships": [asdict(e) for e in edges],
        "candidate_paths": [asdict(p) for p in candidate_paths],
    }


# ---------------------------
# Skill ingestion (from LLM output)
# ---------------------------

def ingest_skills_from_llm_output(session, skills_json_path: str) -> None:
    """
    Optional: Ingest Skill nodes and their USES_TOOL edges into Neo4j
    from a JSON file produced by the LLM.

    Expected JSON structure (example):

    [
      {
        "domain": "calendar",
        "capability": "manage_events",
        "skills": [
          {
            "name": "Browse inbox and open an email",
            "intent_text": "...",
            "description": "...",
            "preconditions": "...",
            "postconditions": "...",
            "workflow_tools": ["list_gmail_messages", "get_gmail_message_by_id"]
          },
          ...
        ]
      },
      ...
    ]

    Adapt this structure to match your actual LLM output.
    """
    with open(skills_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for cap_block in data:
        domain = cap_block["domain"]
        capability = cap_block["capability"]
        skills = cap_block.get("skills", [])

        for skill in skills:
            name = skill["name"]
            props = {
                "name": name,
                "domain": domain,
                "capability": capability,
                "intent_text": skill.get("intent_text"),
                "description": skill.get("description"),
                "preconditions": skill.get("preconditions"),
                "postconditions": skill.get("postconditions"),
            }

            # MERGE Skill node
            session.run(
                """
                MERGE (s:Skill {name: $name, domain: $domain, capability: $capability})
                SET s += $props
                """,
                name=name,
                domain=domain,
                capability=capability,
                props=props,
            )

            # Connect Capability -> Skill
            session.run(
                """
                MATCH (c:Capability {name: $capability, domain: $domain}),
                      (s:Skill {name: $name, domain: $domain, capability: $capability})
                MERGE (c)-[:HAS_SKILL]->(s)
                """,
                domain=domain,
                capability=capability,
                name=name,
            )

            # Connect Skill -> Tool via USES_TOOL with order
            workflow = skill.get("workflow_tools", [])
            for order, tool_name in enumerate(workflow):
                session.run(
                    """
                    MATCH (s:Skill {name: $skill_name, domain: $domain, capability: $capability}),
                          (t:Tool  {name: $tool_name})
                    MERGE (s)-[r:USES_TOOL {order: $order}]->(t)
                    """,
                    skill_name=name,
                    domain=domain,
                    capability=capability,
                    tool_name=tool_name,
                    order=order,
                )


# ---------------------------
# Main end-to-end flow
# ---------------------------

def sync_domains_and_capabilities_from_db_to_graph(gsess, llm, tenant_name) -> None:
    """Read domains, capabilities, and their tools from the relational DB and mirror them into Neo4j,
    and persist discovered skills + their relationships back into Postgres.

    For each domain in Postgres:
      * create/update a Domain node
      * load its capabilities by domain name
      * create/update Capability nodes
      * create/merge HAS_CAPABILITY relationships.
      * load tools for each capability
      * create/update Tool nodes
      * create/merge HAS_TOOL relationships from Capability to Tool
      * infer candidate tool chains and skills via LLM
      * upsert skills, capability↔skill relations, and tool↔skill step chains
    """
    emb = Embedder()
    with get_db_cm() as sess:
        domains = sess.execute(select(Domain)).scalars().all()
        for domain in domains:
            create_domain_node(gsess, domain)
            capabilities = get_capabilities_by_domain(sess, domain.name)
            for capability in capabilities:
                # Determine capability name whether we received a dict or ORM object
                if isinstance(capability, dict):
                    cap_name = capability["name"]
                else:
                    cap_name = capability.name

                create_capability_node(gsess, capability)
                create_domain_capability_edge(gsess, domain.name, cap_name)

                # For each capability, fetch its tools from the relational DB
                tools = get_tools_by_capability_name_from_db(sess, cap_name)
                if not tools:
                    continue


                # Build tool relationship edges and accumulate candidate paths for this capability
                all_candidates: List[CandidatePath] = []
                for tool in tools:
                    if not is_tool_analyzed(gsess, sess, tenant_name, tool):
                        correlate_tools(gsess, sess,llm, emb, tenant_name, domain.name, cap_name, tool)
                    

"""


                    create_tool_node(gsess, tool)
                    create_capability_tool_edge(gsess, cap_name, tool.name, tool.tenant)

                    tool_nodes = get_tools_by_capability_name(gsess, cap_name)
                    self_node = False
                    if len(tool_nodes) == 1 and tool_nodes[0].get("name") == tool.name:
                        self_node = True

                    if (not self_node) and len(tool_nodes) > 0:
                        tool_rels = get_tool_rel_by_tool(llm, tool, tool_nodes)
                        for tool_rel in tool_rels:
                            upsert_tool_rel(sess, tenant_name, tool_rel)
                            create_tool_relationship_edge(gsess, domain.name, cap_name, tool_rel)
                        sess.commit()
                    candidates = get_tool_candidate_paths(gsess, cap_name, tool.name)
                    if candidates:
                        all_candidates.extend(candidates)

                #if not all_candidates:
                #   continue

                        # CandidatePath is a dataclass; convert to plain dicts for JSON serialization
                        print(json.dumps([asdict(c) for c in candidates]))

                        skills = extract_skills_from_tools(llm, candidates)
                        print(skills)

                        # Persist skills + capability/skill + tool/skill(step) relationships into Postgres
                        tool_by_name = {t.name: t for t in tools}
                        tool_skill_map: Dict[Any, List[Dict[str, Any]]] = {}

                        for skill_data in skills or []:

                            skill=ingest_skill(sess, emb, tenant_name, cap_name, skill_data)
                            # Upsert Skill row using embedding over label/description/intent/procedures
                        #    skill_row = upsert_skill(sess, emb, skill_data)

                        #     # Capability ↔ Skill relation
                        #     insert_capability_skill(sess, cap_name, skill_row.name)

                        #     # Tool ↔ Skill step relations from operational_procedures
                        #     procedures = skill_data.get("operational_procedures", []) or []
                        #     for idx, proc in enumerate(procedures, start=1):
                        #         tool_name = proc.get("tool")
                        #         step_intent = proc.get("step_intent")
                        #         if not tool_name:
                        #             continue

                        #         tool_obj = tool_by_name.get(tool_name)
                        #         if not tool_obj:
                        #             # Tool from the skill is not present for this capability; skip
                        #             continue

                        #         entries = tool_skill_map.setdefault(tool_obj, [])
                        #         entries.append(
                        #             {
                        #                 "skill_name": skill_row.name,
                        #                 "step_index": idx,
                        #                 "step_intent": step_intent,
                        #             }
                        #         )

                        # # For each tool, upsert its full set of skill relations with step metadata
                        # for tool, tool_skills in tool_skill_map.items():
                        #     upsert_tool_skills(sess, tool, tool_skills)

"""
def main():

    llm =LLM()
    driver = get_graph_driver()
    with driver.session() as g_sess:  
         #cleanup_all_domains_graph(g_sess)
         sync_domains_and_capabilities_from_db_to_graph(g_sess, llm, "default")

    close_graph_driver()
    print("Done.")

def poc():

    # driver = get_driver()
    # with driver.session() as g_sess:  
    #     cleanup_all_domains_graph(g_sess)
    #     #sync_domains_and_capabilities_from_db_to_graph(g_sess)

    # 1) Load JSON
    hierarchy = load_hierarchy("/Users/jingnan.zhou/workspace/aintegrator/docs/draft/canonical_tools_classified_r2.json")
    relations = load_tool_relations("/Users/jingnan.zhou/workspace/aintegrator/docs/draft/canonical_tool_rel.json")


    driver = get_driver()

    with driver.session() as session:
        # 2) Create constraints
        print("Creating constraints...")
        create_constraints(session)

        # 3) Ingest hierarchy (Domain, Capability, Tool)
        print("Ingesting hierarchy...")
        ingest_hierarchy(session, hierarchy)

        # 4) Ingest procedural tool relationships
        print("Ingesting NEXT_TOOL relationships...")
        ingest_tool_relationships(session, relations)

        # 5) Extract candidate paths and build LLM payload per capability
        print("Building LLM payloads per capability...")
        capabilities = get_all_capabilities(session)

        all_payloads: List[Dict[str, Any]] = []
        for domain, capability in capabilities:
            payload = build_llm_payload_for_capability(session, domain, capability)
            all_payloads.append(payload)

        with open(LLM_PAYLOAD_PATH, "w", encoding="utf-8") as f:
            json.dump(all_payloads, f, ensure_ascii=False, indent=2)

        print(f"LLM payloads written to {LLM_PAYLOAD_PATH}")

        # 6) OPTIONAL: if you later have LLM skills JSON, you can ingest it:
        # ingest_skills_from_llm_output(session, LLM_SKILLS_PATH)

    driver.close()
    print("Done.")


if __name__ == "__main__":
    main()
