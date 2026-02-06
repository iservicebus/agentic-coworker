"""CRUD helpers for creating Domain, Capability, and Tool nodes in Neo4j.

These helpers are intended to be used by higher-level services that keep the
relational (PostgreSQL) models in sync with the Neo4j knowledge graph.

They rely on the shared Neo4j driver from ``integrator.utils.graph`` so that
connection management is centralized.

Reference implementation for the general graph model lives in
``integrator.domains.domain_graph``.
"""

from __future__ import annotations

from typing import Any, Mapping, Union, List, Dict
import json

from integrator.tools.tool_db_model import McpTool, Skill, CapabilitySkill, ToolSkill, ToolRel
from integrator.utils.logger import get_logger
from integrator.tools.tool_graph_model import ToolEdge, CandidatePath
from collections import defaultdict
from dataclasses import asdict
from neo4j.exceptions import ServiceUnavailable, Neo4jError


from integrator.domains.domain_llm import get_tool_rel_by_tool, extract_skills_from_tools
from integrator.tools.tool_db_crud import (
       upsert_skill,
       upsert_tool_skills,
       find_skill_by_tool_chain,
       get_mcp_tool_by_name_tenant,
       insert_capability_skill,
       upsert_tool_rel,
       tool_has_skills,
)

logger = get_logger(__name__)

McpToolLike = Union[McpTool, Mapping[str, Any]]


def _extract_mcp_tool_props(tool: McpToolLike) -> dict:
    """Normalize an McpTool ORM instance or dict into Neo4j properties.

    The resulting dict will contain the keys expected on the Tool node:
    - name
    - tenant_name
    - canonical_data (JSON string to keep Neo4j properties primitive)
    """

    if isinstance(tool, McpTool):
        name = tool.name
        tenant_name = tool.tenant
        canonical_data_raw = tool.canonical_data or {}
    else:
        name = tool["name"]
        tenant_name = tool.get("tenant", "default")
        canonical_data_raw = tool.get("canonical_data", {})

    # Neo4j properties must be primitives or arrays; serialize the
    # potentially nested canonical_data dict into a JSON string.
    try:
        canonical_data = json.dumps(canonical_data_raw, default=str)
    except TypeError:
        canonical_data = json.dumps(str(canonical_data_raw))

    return {
        "name": name,
        "tenant_name": tenant_name,
        "canonical_data": canonical_data,
    }


def create_tool_node(gsess, tool: McpToolLike) -> None:
    """Create or update a Tool node in Neo4j based on an ``McpTool`` with tenant isolation.

    Node label: ``Tool``
    Properties: name, tenant_name, canonical_data
    """

    props = _extract_mcp_tool_props(tool)

    cypher = """
    MERGE (t:Tool {name: $name, tenant_name: $tenant_name})
    SET t.canonical_data = $canonical_data
    """

    try:
        gsess.run(cypher, **props)
        logger.info("Upserted Tool node in Neo4j for MCP tool: %s (tenant: %s)", props["name"], props["tenant_name"])
    except ServiceUnavailable as e:
        logger.warning(f"Neo4j service unavailable while creating tool node '{props['name']}': {e}")
        logger.warning(f"Skipping graph creation for tool '{props['name']}' - tool metadata will still be stored in database")
    except Neo4jError as e:
        logger.warning(f"Neo4j error while creating tool node '{props['name']}': {e}")
        logger.warning(f"Skipping graph creation for tool '{props['name']}' - tool metadata will still be stored in database")
    except Exception as e:
        logger.error(f"Unexpected error creating tool node '{props['name']}': {e}")
        # Don't raise - allow creation to continue without graph storage
        logger.warning(f"Continuing without graph storage for tool '{props['name']}')")


def has_tool_node(gsess, tool: McpToolLike | str, tenant_name: str = None) -> bool:
    """Check whether a Tool node exists in Neo4j for the given tool or tool name with tenant isolation.

    Parameters
    ----------
    gsess:
        An active Neo4j session.
    tool:
        Either an ``McpTool``/mapping with a ``name`` field or a plain tool name.
    tenant_name:
        Optional tenant identifier. If not provided, will try to extract from tool object.

    Returns
    -------
    bool
        ``True`` if a ``Tool`` node with the given name and tenant exists, ``False`` otherwise.
    """

    if isinstance(tool, McpTool):
        name = tool.name
        if tenant_name is None:
            tenant_name = tool.tenant
    elif isinstance(tool, dict):
        name = tool.get("name")
        if tenant_name is None:
            tenant_name = tool.get("tenant", "default")
    else:
        name = str(tool)
        if tenant_name is None:
            tenant_name = "default"

    cypher = """
    MATCH (t:Tool {name: $name, tenant_name: $tenant_name})
    RETURN t
    LIMIT 1
    """

    result = gsess.run(cypher, name=name, tenant_name=tenant_name)
    exists = result.single() is not None

    logger.info(
        "Checked existence of Tool node in Neo4j for MCP tool %s (tenant: %s): %s", name, tenant_name, exists
    )
    return exists


def create_capability_tool_edge(gsess, capability_name: str, tool_name: str, tenant_name: str) -> None:
    """Create or update the HAS_TOOL edge between a Capability and a Tool with tenant isolation.

    This assumes that the corresponding Capability and Tool nodes already
    exist (for example, created via ``create_capability_node`` and
    ``create_tool_node``).
    
    Both nodes must belong to the same tenant.
    """

    cypher = """
    MATCH (c:Capability {name: $capability_name, tenant_name: $tenant_name})
    MATCH (t:Tool {name: $tool_name, tenant_name: $tenant_name})
    MERGE (c)-[:HAS_TOOL]->(t)
    """

    try:
        gsess.run(cypher, capability_name=capability_name, tool_name=tool_name, tenant_name=tenant_name)
        logger.info(
            "Upserted HAS_TOOL edge in Neo4j: Capability %s -> Tool %s (tenant: %s)",
            capability_name,
            tool_name,
            tenant_name,
        )
    except ServiceUnavailable as e:
        logger.warning(f"Neo4j service unavailable while creating HAS_TOOL edge: Capability '{capability_name}' -> Tool '{tool_name}': {e}")
        logger.warning(f"Skipping graph edge creation - relationship will still be stored in database")
    except Neo4jError as e:
        logger.warning(f"Neo4j error while creating HAS_TOOL edge: Capability '{capability_name}' -> Tool '{tool_name}': {e}")
        logger.warning(f"Skipping graph edge creation - relationship will still be stored in database")
    except Exception as e:
        logger.error(f"Unexpected error creating HAS_TOOL edge: Capability '{capability_name}' -> Tool '{tool_name}': {e}")
        logger.warning(f"Continuing without graph edge creation")


def _normalize_procedures_for_graph(operational_procedures: Any) -> List[str]:
    """Convert a list of procedure dicts into a list of strings for Neo4j.

    Neo4j properties must be primitives or arrays of primitives; the
    ``operational_procedures`` column in Postgres is JSONB and may contain
    dicts like ``{"tool": "...", "step_intent": "..."}``. This helper
    flattens them into human-readable strings while preserving key
    information.
    """

    if not operational_procedures:
        return []

    normalized: List[str] = []
    for proc in operational_procedures:
        if isinstance(proc, Mapping):
            tool = proc.get("tool")
            step_intent = proc.get("step_intent")
            if tool and step_intent:
                normalized.append(f"{tool}: {step_intent}")
            elif step_intent:
                normalized.append(str(step_intent))
            elif tool:
                normalized.append(str(tool))
        else:
            normalized.append(str(proc))
    return normalized


def _extract_skill_props(skill: Skill | Mapping[str, Any], domain_name: str, capability_name: str, tenant_name: str) -> dict:
    """Normalize a Skill ORM instance or dict into Neo4j properties.

    The resulting dict will contain the keys expected on the Skill node:
    - name
    - tenant_name
    - label
    - description
    - domain
    - capability
    - operational_entities
    - operational_procedures (flattened list of strings)
    - operational_intent
    - preconditions
    - postconditions
    - proficiency
    """

    if isinstance(skill, Skill):
        name = skill.name
        label = skill.label
        description = skill.description or ""
        operational_entities = skill.operational_entities or []
        raw_operational_procedures = skill.operational_procedures or []
        operational_intent = skill.operational_intent or ""
        preconditions = skill.preconditions or []
        postconditions = skill.postconditions or []
        proficiency = skill.proficiency or ""
    else:
        name = skill["name"]
        label = skill.get("label", "")
        description = skill.get("description", "")
        operational_entities = skill.get("operational_entities", [])
        raw_operational_procedures = skill.get("operational_procedures", [])
        operational_intent = skill.get("operational_intent", "")
        preconditions = skill.get("preconditions", [])
        postconditions = skill.get("postconditions", [])
        proficiency = skill.get("proficiency", "")

    operational_procedures = _normalize_procedures_for_graph(raw_operational_procedures)

    return {
        "name": name,
        "tenant_name": tenant_name,
        "label": label,
        "description": description,
        "domain": domain_name,
        "capability": capability_name,
        "operational_entities": operational_entities,
        "operational_procedures": operational_procedures,
        "operational_intent": operational_intent,
        "preconditions": preconditions,
        "postconditions": postconditions,
        "proficiency": proficiency,
    }


def create_skill_node(gsess, domain_name: str, capability_name: str, skill: Skill | Mapping[str, Any], tenant_name: str) -> None:
    """Create or update a Skill node in Neo4j with tenant isolation.

    Uses the ``name`` and ``tenant_name`` as the composite identifier of the node.

    Node label: ``Skill``
    Properties: name, tenant_name, label, description, domain, capability,
                operational_entities, operational_procedures,
                operational_intent, preconditions, postconditions,
                proficiency
    """

    props = _extract_skill_props(skill, domain_name, capability_name, tenant_name)

    cypher = """
    MERGE (s:Skill {name: $name, tenant_name: $tenant_name})
    SET s.label = $label,
        s.description = $description,
        s.domain = $domain,
        s.capability = $capability,
        s.operational_entities = $operational_entities,
        s.operational_procedures = $operational_procedures,
        s.operational_intent = $operational_intent,
        s.preconditions = $preconditions,
        s.postconditions = $postconditions,
        s.proficiency = $proficiency
    """

    try:
        gsess.run(cypher, **props)
        logger.info("Upserted Skill node in Neo4j: %s (tenant: %s)", props["name"], props["tenant_name"])
    except ServiceUnavailable as e:
        logger.warning(f"Neo4j service unavailable while creating skill node '{props['name']}': {e}")
        logger.warning(f"Skipping graph creation for skill '{props['name']}' - skill metadata will still be stored in database")
    except Neo4jError as e:
        logger.warning(f"Neo4j error while creating skill node '{props['name']}': {e}")
        logger.warning(f"Skipping graph creation for skill '{props['name']}' - skill metadata will still be stored in database")
    except Exception as e:
        logger.error(f"Unexpected error creating skill node '{props['name']}': {e}")
        logger.warning(f"Continuing without graph storage for skill '{props['name']}')")


def create_capability_skill_edge(gsess, capability_name: str, skill_name: str, tenant_name: str) -> None:
    """Create or update the HAS_SKILL edge between a Capability and a Skill with tenant isolation.

    This assumes that the corresponding Capability and Skill nodes already
    exist (for example, created via ``create_capability_node`` and
    ``create_skill_node``).
    
    Both nodes must belong to the same tenant.
    """

    cypher = """
    MATCH (c:Capability {name: $capability_name, tenant_name: $tenant_name})
    MATCH (s:Skill {name: $skill_name, tenant_name: $tenant_name})
    MERGE (c)-[:HAS_SKILL]->(s)
    """

    try:
        gsess.run(cypher, capability_name=capability_name, skill_name=skill_name, tenant_name=tenant_name)
        logger.info(
            "Upserted HAS_SKILL edge in Neo4j: Capability %s -> Skill %s (tenant: %s)",
            capability_name,
            skill_name,
            tenant_name,
        )
    except ServiceUnavailable as e:
        logger.warning(f"Neo4j service unavailable while creating HAS_SKILL edge: Capability '{capability_name}' -> Skill '{skill_name}': {e}")
        logger.warning(f"Skipping graph edge creation - relationship will still be stored in database")
    except Neo4jError as e:
        logger.warning(f"Neo4j error while creating HAS_SKILL edge: Capability '{capability_name}' -> Skill '{skill_name}': {e}")
        logger.warning(f"Skipping graph edge creation - relationship will still be stored in database")
    except Exception as e:
        logger.error(f"Unexpected error creating HAS_SKILL edge: Capability '{capability_name}' -> Skill '{skill_name}': {e}")
        logger.warning(f"Continuing without graph edge creation")


def create_skill_tool_edges(
    gsess,
    skill_name: str,
    procedures: List[Mapping[str, Any]] | None,
    tenant_name: str,
) -> None:
    """Create or update USES_TOOL edges from a Skill to Tool nodes with tenant isolation.

    Uses the same step metadata as the ``ToolSkill`` table:
    - ``step_index`` (1-based order of the tool in the workflow)
    - ``step_intent`` (text describing what happens at this step)

    The relationship is modeled as:
        (Skill)-[USES_TOOL {step_index, step_intent}]->(Tool)
    
    Both Skill and Tool nodes must belong to the same tenant.
    """

    if not procedures:
        return

    for step_index, proc in enumerate(procedures, start=1):
        if not isinstance(proc, Mapping):
            continue

        tool_name = proc.get("tool")
        step_intent = proc.get("step_intent")

        if not tool_name:
            continue

        cypher = """
        MATCH (s:Skill {name: $skill_name, tenant_name: $tenant_name})
        MATCH (t:Tool {name: $tool_name, tenant_name: $tenant_name})
        MERGE (s)-[r:USES_TOOL]->(t)
        SET r.step_index = $step_index,
            r.step_intent = $step_intent
        """

        try:
            gsess.run(
                cypher,
                skill_name=skill_name,
                tool_name=tool_name,
                tenant_name=tenant_name,
                step_index=step_index,
                step_intent=step_intent,
            )
            logger.info(
                "Upserted USES_TOOL edge in Neo4j: Skill %s -> Tool %s (step_index=%s, tenant: %s)",
                skill_name,
                tool_name,
                step_index,
                tenant_name,
            )
        except ServiceUnavailable as e:
            logger.warning(f"Neo4j service unavailable while creating USES_TOOL edge: Skill '{skill_name}' -> Tool '{tool_name}': {e}")
            logger.warning(f"Skipping graph edge creation - relationship will still be stored in database")
        except Neo4jError as e:
            logger.warning(f"Neo4j error while creating USES_TOOL edge: Skill '{skill_name}' -> Tool '{tool_name}': {e}")
            logger.warning(f"Skipping graph edge creation - relationship will still be stored in database")
        except Exception as e:
            logger.error(f"Unexpected error creating USES_TOOL edge: Skill '{skill_name}' -> Tool '{tool_name}': {e}")
            logger.warning(f"Continuing without graph edge creation")


def get_tools_by_capability_name(gsess, capability_name: str, tenant_name: str = None) -> List[Dict[str, Any]]:
    """Return all Tool nodes (as property dicts) for a given capability name with optional tenant filtering.

    This queries Neo4j for all ``Tool`` nodes that are connected from the
    ``Capability`` node via a ``HAS_TOOL`` relationship.
    
    Args:
        gsess: Neo4j session
        capability_name: Name of the capability
        tenant_name: Optional tenant identifier for filtering
    """
    if tenant_name:
        cypher = """
        MATCH (c:Capability {name: $capability_name, tenant_name: $tenant_name})-[:HAS_TOOL]->(t:Tool {tenant_name: $tenant_name})
        RETURN t
        """
        result = gsess.run(cypher, capability_name=capability_name, tenant_name=tenant_name)
    else:
        cypher = """
        MATCH (c:Capability {name: $capability_name})-[:HAS_TOOL]->(t:Tool)
        RETURN t
        """
        result = gsess.run(cypher, capability_name=capability_name)

    tools: List[Dict[str, Any]] = []
    for record in result:
        node = record["t"]
        tools.append(dict(node))

    logger.info(
        "Retrieved %d Tool node(s) for capability %s from Neo4j%s",
        len(tools),
        capability_name,
        f" (tenant: {tenant_name})" if tenant_name else "",
    )
    return tools


def create_tool_relationship_edge(
    gsess,
    domain_name: str,
    capability_name: str,
    relationship: Mapping[str, Any],
    tenant_name: str = None,
) -> None:
    """Create or update a NEXT_TOOL edge between two Tool nodes with optional tenant filtering.

    This mirrors the logic used in ``ingest_tool_relationships`` from
    ``integrator.domains.domain_graph`` but is tailored for CRUD-style
    usage, where a single relationship JSON is provided.

    Expected ``relationship`` structure::

        {
          "tool_flow": ["<tool_name_A>", "<tool_name_B>"],
          "composite_intent": "<one plain-language business sentence>"
        }
    
    Args:
        gsess: Neo4j session
        domain_name: Name of the domain
        capability_name: Name of the capability
        relationship: Relationship data with tool_flow and composite_intent
        tenant_name: Optional tenant identifier for filtering
    """

    tool_flow = relationship.get("tool_flow") or []
    if len(tool_flow) != 2:
        logger.warning(
            "Expected exactly 2 tools in tool_flow for NEXT_TOOL edge (domain=%s, capability=%s), got %d",
            domain_name,
            capability_name,
            len(tool_flow),
        )
        return

    from_tool, to_tool = tool_flow
    composite_intent = relationship.get("composite_intent")

    if tenant_name:
        cypher = """
        MATCH (t1:Tool {name: $t1_name, tenant_name: $tenant_name})
        MATCH (t2:Tool {name: $t2_name, tenant_name: $tenant_name})
        MERGE (t1)-[r:NEXT_TOOL]->(t2)
        SET r.domain = $domain,
            r.capability = $capability,
            r.composite_intent = $composite_intent
        """
        params = {
            "t1_name": from_tool,
            "t2_name": to_tool,
            "tenant_name": tenant_name,
            "domain": domain_name,
            "capability": capability_name,
            "composite_intent": composite_intent,
        }
    else:
        cypher = """
        MATCH (t1:Tool {name: $t1_name})
        MATCH (t2:Tool {name: $t2_name})
        MERGE (t1)-[r:NEXT_TOOL]->(t2)
        SET r.domain = $domain,
            r.capability = $capability,
            r.composite_intent = $composite_intent
        """
        params = {
            "t1_name": from_tool,
            "t2_name": to_tool,
            "domain": domain_name,
            "capability": capability_name,
            "composite_intent": composite_intent,
        }

    try:
        gsess.run(cypher, **params)
        logger.info(
            "Upserted NEXT_TOOL edge in Neo4j: %s -[%s/%s]-> %s%s",
            from_tool,
            domain_name,
            capability_name,
            to_tool,
            f" (tenant: {tenant_name})" if tenant_name else "",
        )
    except ServiceUnavailable as e:
        logger.warning(f"Neo4j service unavailable while creating NEXT_TOOL edge: Tool '{from_tool}' -> Tool '{to_tool}': {e}")
        logger.warning(f"Skipping graph edge creation - relationship will still be stored in database")
    except Neo4jError as e:
        logger.warning(f"Neo4j error while creating NEXT_TOOL edge: Tool '{from_tool}' -> Tool '{to_tool}': {e}")
        logger.warning(f"Skipping graph edge creation - relationship will still be stored in database")
    except Exception as e:
        logger.error(f"Unexpected error creating NEXT_TOOL edge: Tool '{from_tool}' -> Tool '{to_tool}': {e}")
        logger.warning(f"Continuing without graph edge creation")




def get_tool_relationship_edges_by_capability(
    gsess,
    capability: str,
    tenant_name: str = None,
) -> List[ToolEdge]:
    """
    For a given capability, retrieve NEXT_TOOL edges (as ToolEdge list) with optional tenant filtering.
    
    Args:
        gsess: Neo4j session
        capability: Name of the capability
        tenant_name: Optional tenant identifier for filtering
    """

    # Edges
    if tenant_name:
        edges_query = """
        MATCH (c:Capability {name:$capability, tenant_name: $tenant_name})
        MATCH (c)-[:HAS_TOOL]->(t1:Tool {tenant_name: $tenant_name})-[r:NEXT_TOOL]->(t2:Tool {tenant_name: $tenant_name})
        RETURN t1 AS from, t2 AS to, r.composite_intent AS composite_intent
        """
        result = gsess.run(edges_query, capability=capability, tenant_name=tenant_name)
    else:
        edges_query = """
        MATCH (c:Capability {name:$capability})
        MATCH (c)-[:HAS_TOOL]->(t1:Tool)-[r:NEXT_TOOL]->(t2:Tool)
        RETURN t1 AS from, t2 AS to, r.composite_intent AS composite_intent
        """
        result = gsess.run(edges_query, capability=capability)
    
    edges: List[ToolEdge] = []
    for record in result:

        from_tool=json.loads(record["from"]["canonical_data"])
        from_tool["name"]=record["from"]["name"]
        to_tool=json.loads(record["to"]["canonical_data"])
        to_tool["name"]=record["to"]["name"]


        edges.append(
            ToolEdge(
                from_tool=from_tool,
                to_tool=to_tool,
                capability=capability,
                composite_intent=record["composite_intent"],
            )
        )

    return edges


def get_tool_candidate_paths( gsess, capability_name, src_tool: str="") -> List[CandidatePath]:
    """
    Given tools + NEXT_TOOL edges for a capability, return maximal linear chains
    and isolated tools as CandidatePath objects.

    This is O(V+E) and suitable for working per capability.
    """
    tools = get_tools_by_capability_name(gsess, capability_name)
    if len(tools)<1:
        return []
    
    tool_dicts= {}
    for tool in tools:
        can_tool=json.loads(tool.get("canonical_data"))
        can_tool["name"]=tool.get("name")
        tool_dicts[tool.get("name")]=can_tool
        

    edges=get_tool_relationship_edges_by_capability(gsess, capability_name)


    successors: Dict[str, List[Dict]] = defaultdict(list)
    predecessors: Dict[str, List[Dict]] = defaultdict(list)

    for e in edges:
        successors[e.from_tool.get("name")].append(e.to_tool)
        predecessors[e.to_tool.get("name")].append(e.from_tool)


    # 1) Isolated tools: no in or out edges
    isolated = {
        t_n:tool_dicts.get(t_n) for t_n in tool_dicts.keys()
        if len(successors[t_n]) == 0 and len(predecessors[t_n]) == 0
    }

    # 2) Maximal linear chains
    # Track visited tool *names* to avoid reprocessing nodes and to detect leftovers.
    visited: set[str] = set()
    chains: List[List[Dict]] = []

    # A chain start: has outgoing edges AND in-degree != 1
    potential_starts = [
        tool_dicts.get(t_n) for t_n in tool_dicts.keys()
        if len(successors[t_n]) > 0 and len(predecessors[t_n]) != 1
    ]

    for start in potential_starts:
        for succ in successors[start.get("name")]:
            path = [start]
            cur = succ
            prev = start

            while True:
                path.append(cur)
                # Mark the tool names as visited (we only care about node identity here).
                visited.add(prev.get("name"))
                visited.add(cur.get("name"))

                # Stop if cur is not strictly in a line (in = 1, out = 1)
                if len(successors[cur.get("name")]) != 1 or len(predecessors[cur.get("name")]) != 1:
                    break

                nxt = successors[cur.get("name")][0]

                # Simple cycle guard
                if nxt in path:
                    break

                prev = cur
                cur = nxt

            chains.append(path)

    # 3) Leftovers (e.g., small cycles or middle-of-chain nodes not caught)
    leftovers = [
        tool_dicts.get(t_n) for t_n in tool_dicts.keys()
        if (t_n not in visited) and (t_n not in isolated)
        and (len(successors[t_n]) > 0 or len(predecessors[t_n]) > 0)
    ]
    for t in leftovers:
        # conservative: record as a chain of [t, succ] if there is a succ,
        # else [t]
        if successors[t.get("name")]:
            chains.append([t, successors[t.get("name")][0]])
        else:
            chains.append([t])

    candidate_paths: List[CandidatePath] = []

    for tool_name in isolated.keys():
        candidate_paths.append(
            CandidatePath(type="single_tool", tools=[isolated.get(tool_name)])
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
    if src_tool:

        tool_paths=[]
        for path in candidate_paths:
            if path.type=="single_tool" and path.tools[0].get("name")==src_tool:
                tool_paths.append(path)

            elif path.type=="chain":
                found=False
                for tool in path.tools:
                    if tool.get("name")==src_tool:
                        found=True
                        break
                if found:
                    tool_paths.append(path)

        return tool_paths            


    else:        

        return candidate_paths


def tool_has_skills_in_graph(gsess, tool_name: str, tenant_name: str = None) -> bool:
    """Check whether a Tool node has any incoming USES_TOOL edges from Skills with tenant isolation.

    This is the graph analogue of ``tool_has_skills`` in the relational layer:
    it returns ``True`` if there exists at least one ``(Skill)-[:USES_TOOL]->(Tool)``
    relationship for the given tool name, otherwise ``False``.
    
    Args:
        gsess: Neo4j session
        tool_name: Name of the tool
        tenant_name: Optional tenant identifier for filtering
    """

    if tenant_name:
        cypher = """
        MATCH (s:Skill {tenant_name: $tenant_name})-[:USES_TOOL]->(t:Tool {name: $tool_name, tenant_name: $tenant_name})
        RETURN s
        LIMIT 1
        """
        result = gsess.run(cypher, tool_name=tool_name, tenant_name=tenant_name)
    else:
        cypher = """
        MATCH (s:Skill)-[:USES_TOOL]->(t:Tool {name: $tool_name})
        RETURN s
        LIMIT 1
        """
        result = gsess.run(cypher, tool_name=tool_name)

    has_skills = result.single() is not None

    logger.info(
        "tool_has_skills_in_graph: tool_name=%s, tenant_name=%s, has_skills=%s",
        tool_name,
        tenant_name if tenant_name else "N/A",
        has_skills,
    )
    return has_skills



def is_tool_analyzed(gsess, sess, tenant_name: str, tool: McpToolLike | str) -> bool:
    """Return True if the tool has a Tool node in Neo4j and at least one Skill.

    This helper combines the graph check (``Tool`` node existence) and the
    relational check (at least one ``ToolSkill`` row via ``tool_has_skills``).
    """

    # First, check whether the Tool node exists in Neo4j.
    if not has_tool_node(gsess, tool):
        logger.info(
            "is_tool_analyzed: Tool node missing in Neo4j for tenant=%s, tool=%s",
            tenant_name,
            getattr(tool, "name", str(tool)),
        )
        return False

    # Resolve the tool name for the relational DB check.
    if isinstance(tool, McpTool):
        tool_name = tool.name
    elif isinstance(tool, dict):
        tool_name = tool.get("name")
    else:
        tool_name = str(tool)

    #has_skills = tool_has_skills(sess, tenant_name, tool_name)
    has_skills=tool_has_skills_in_graph(gsess, tool_name)
    logger.info(
        "is_tool_analyzed: tenant=%s, tool_name=%s, has_tool_node=%s, has_skills=%s",
        tenant_name,
        tool_name,
        True,
        has_skills,
    )
    return has_skills


def ingest_skill(
    gsess,
    sess,
    emb,
    tenant_name: str,
    domain_name: str,
    capability_name: str,
    skill_data: Dict[str, Any],
) -> Skill:
    """Ingest or update a Skill and its tool-chain relations, plus mirror into Neo4j.

    Steps:
      * Resolve tool IDs for the operational procedures and build a tool_chain.
      * Find an existing Skill whose tool_chain exactly matches (if any).
      * Upsert the Skill row (embedding over label/description/intent/procedures).
      * Ensure Capability↔Skill and Tool↔Skill rows exist in Postgres.
      * Create/merge the corresponding Skill node and its relationships
        (HAS_SKILL, USES_TOOL) in Neo4j.
    """

    tool_chain: List[Dict[str, Any]] = []
    procedures = skill_data.get("operational_procedures", []) or []

    # Build the tool_chain with concrete tool_ids for relational ToolSkill rows
    for idx, proc in enumerate(procedures, start=1):
        tool_skill: Dict[str, Any] = {
            "step_index": idx,
            "step_intent": proc.get("step_intent"),
        }
        tool_name = proc.get("tool")
        if not tool_name:
            logger.warning("Skipping procedure without tool name: %r", proc)
            continue

        tool = get_mcp_tool_by_name_tenant(sess, tool_name, tenant_name)
        if not tool:
            raise Exception(
                f"tool name {tool_name} is not found for tool_skill {tool_skill}"
            )

        tool_skill["tool_id"] = tool.id
        tool_chain.append(tool_skill)

    # Try to find an existing Skill whose tool_chain exactly matches
    skill = find_skill_by_tool_chain(sess, tool_chain)

    # Upsert the Skill row itself (may be new or existing)
    skill = upsert_skill(sess, emb, skill, skill_data, tenant_name)
    sess.flush()

    # Capability ↔ Skill relation (Postgres)
    insert_capability_skill(sess, capability_name, skill.name, tenant_name)

    # Tool ↔ Skill step relations (Postgres)
    upsert_tool_skills(sess, skill.name, tool_chain, tenant_name)

    # Mirror into Neo4j: Skill node + HAS_SKILL + USES_TOOL edges
    create_skill_node(gsess, domain_name, capability_name, skill, tenant_name)
    create_capability_skill_edge(gsess, capability_name, skill.name, tenant_name)
    create_skill_tool_edges(
        gsess,
        skill_name=skill.name,
        procedures=procedures,
        tenant_name=tenant_name,
    )

    sess.commit()

    return skill


def correlate_tools(gsess, sess,llm, emb, tenant_name, domain_name, cap_name, tool:McpTool) -> None:

    create_tool_node(gsess, tool)
    create_capability_tool_edge(gsess, cap_name, tool.name, tenant_name)
    tool_nodes = get_tools_by_capability_name(gsess, cap_name)
    self_node = False
    if len(tool_nodes) == 1 and tool_nodes[0].get("name") == tool.name:
        self_node = True

    if (not self_node) and len(tool_nodes) > 0:
        tool_batch_size = 10

        # Process tool_nodes in batches to limit LLM payload size
        for start_idx in range(0, len(tool_nodes), tool_batch_size):
            batch_tool_nodes = tool_nodes[start_idx : start_idx + tool_batch_size]
            tool_rels = get_tool_rel_by_tool(llm, tool, batch_tool_nodes)
            for tool_rel in tool_rels:
                upsert_tool_rel(sess, tenant_name, tool_rel)
                create_tool_relationship_edge(gsess, domain_name, cap_name, tool_rel)
            sess.commit()

    candidate_batch_size=5
    candidates = get_tool_candidate_paths(gsess, cap_name, tool.name)

    # Process candidates in batches to limit LLM payload size
    for start_c_idx in range(0, len(candidates), candidate_batch_size):
        batch_candidates = candidates[start_c_idx : start_c_idx + candidate_batch_size]

        # CandidatePath is a dataclass; convert to plain dicts for JSON serialization
        print(json.dumps([asdict(c) for c in batch_candidates]))

        skills = extract_skills_from_tools(llm, batch_candidates)
        print(skills)
        for skill_data in skills or []:
            # Persist skill + tool chain in the relational DB
            skill = ingest_skill(gsess, sess, emb, tenant_name, domain_name, cap_name, skill_data)


def sync_skills_tools_from_db_to_graph(sess, gsess, tenant_name: str = None) -> None:
    """Sync skills, tools, and their relationships from PostgreSQL to Neo4j with tenant isolation.

    This function mirrors the structure of sync_domains_from_db_to_graph but focuses
    on the tool and skill layers. It walks through tenants and domains, then
    for each capability:
    1. Retrieves tools from capability_tool relationship table
    2. Creates Tool nodes in Neo4j
    3. Creates HAS_TOOL edges from Capability to Tool
    4. Retrieves skills from capability_skill relationship table
    5. Creates Skill nodes in Neo4j
    6. Creates HAS_SKILL edges from Capability to Skill
    7. Retrieves tool-skill relationships from tool_skills table
    8. Creates USES_TOOL edges from Skill to Tool with step metadata
    9. Retrieves tool-tool relationships from tool_rels table
    10. Creates NEXT_TOOL edges between Tool nodes

    Args:
        sess: SQLAlchemy session for PostgreSQL operations
        gsess: Neo4j session for graph operations
        tenant_name: Optional tenant identifier to limit sync to specific tenant
    """
    from integrator.domains.domain_db_model import Domain
    from integrator.domains.domain_db_crud import get_capabilities_by_domain
    from integrator.tools.tool_db_crud import get_tools_by_capability_name as get_tools_by_capability_name_from_db
    from integrator.iam.iam_db_model import Tenant
    from sqlalchemy import select

    try:
        # Get all tenants or specific tenant
        if tenant_name:
            tenants_to_sync = [tenant_name]
            logger.info(f"Syncing tools and skills for specific tenant: {tenant_name}")
        else:
            tenants_stmt = select(Tenant.name)
            tenant_results = sess.execute(tenants_stmt).scalars().all()
            tenants_to_sync = list(tenant_results)
            logger.info(f"Syncing tools and skills for all tenants: {tenants_to_sync}")

        for current_tenant in tenants_to_sync:
            logger.info(f"Starting tools and skills sync for tenant: {current_tenant}")

            # Get all domains for this tenant
            domains = sess.execute(
                select(Domain).where(Domain.tenant_name == current_tenant)
            ).scalars().all()
            logger.info(f"Found {len(domains)} domains for tenant: {current_tenant}")

            for domain in domains:
                domain_name = domain.name
                logger.info(f"Processing domain: {domain_name} (tenant: {current_tenant})")

                # Get capabilities for this domain
                capabilities = get_capabilities_by_domain(sess, domain_name, current_tenant)

                for capability in capabilities:
                    # Determine capability name whether we received a dict or ORM object
                    if isinstance(capability, dict):
                        cap_name = capability["name"]
                    else:
                        cap_name = capability.name

                logger.info(f"Processing capability: {cap_name} in domain: {domain_name}")

                # Step 1-3: Sync tools for this capability
                tools = get_tools_by_capability_name_from_db(sess, cap_name)
                logger.info(f"Found {len(tools)} tools for capability: {cap_name}")

                for tool in tools:
                    # Create Tool node in Neo4j
                    create_tool_node(gsess, tool)
                    # Create HAS_TOOL edge from Capability to Tool
                    create_capability_tool_edge(gsess, cap_name, tool.name, tool.tenant)

                # Step 4-6: Sync skills for this capability
                capability_skills = sess.execute(
                    select(CapabilitySkill).where(CapabilitySkill.capability_name == cap_name)
                ).scalars().all()
                logger.info(f"Found {len(capability_skills)} skills for capability: {cap_name}")

                for cap_skill in capability_skills:
                    skill_name = cap_skill.skill_name

                    # Get the full Skill object
                    skill = sess.execute(
                        select(Skill).where(Skill.name == skill_name)
                    ).scalar_one_or_none()

                    if not skill:
                        logger.warning(f"Skill '{skill_name}' not found in skills table, skipping")
                        continue

                    # Create Skill node in Neo4j
                    create_skill_node(gsess, domain_name, cap_name, skill, skill.tenant)
                    # Create HAS_SKILL edge from Capability to Skill
                    create_capability_skill_edge(gsess, cap_name, skill_name, skill.tenant)

                    # Step 7-8: Sync tool-skill relationships (USES_TOOL edges)
                    tool_skills = sess.execute(
                        select(ToolSkill).where(ToolSkill.skill_name == skill_name)
                    ).scalars().all()

                    if tool_skills:
                        # Build procedures list for create_skill_tool_edges
                        procedures = []
                        for ts in tool_skills:
                            # Get the tool to retrieve its name
                            tool_obj = sess.execute(
                                select(McpTool).where(McpTool.id == ts.tool_id)
                            ).scalar_one_or_none()

                            if tool_obj:
                                procedures.append({
                                    "tool": tool_obj.name,
                                    "step_intent": ts.step_intent,
                                })
                            else:
                                logger.warning(
                                    f"Tool with id {ts.tool_id} not found for skill {skill_name}"
                                )

                        # Create USES_TOOL edges with step metadata
                        create_skill_tool_edges(gsess, skill_name, procedures, skill.tenant)
                        logger.info(
                            f"Created {len(procedures)} USES_TOOL edges for skill: {skill_name}"
                        )

                # Step 9-10: Sync tool-tool relationships (NEXT_TOOL edges)
                # Get all tool relationships where both tools belong to this capability
                tool_ids = [tool.id for tool in tools]
                if tool_ids:
                    tool_rels = sess.execute(
                        select(ToolRel).where(
                            ToolRel.source_tool_id.in_(tool_ids),
                            ToolRel.target_tool_id.in_(tool_ids),
                        )
                    ).scalars().all()

                    logger.info(
                        f"Found {len(tool_rels)} tool relationships for capability: {cap_name}"
                    )

                    for tool_rel in tool_rels:
                        # Get source and target tool names
                        source_tool = sess.execute(
                            select(McpTool).where(McpTool.id == tool_rel.source_tool_id)
                        ).scalar_one_or_none()
                        target_tool = sess.execute(
                            select(McpTool).where(McpTool.id == tool_rel.target_tool_id)
                        ).scalar_one_or_none()

                        if source_tool and target_tool:
                            # Build relationship data for create_tool_relationship_edge
                            relationship_data = {
                                "tool_flow": [source_tool.name, target_tool.name],
                                "composite_intent": tool_rel.composite_intent,
                                "field_mapping": tool_rel.field_mapping,
                            }
                            create_tool_relationship_edge(
                                gsess, domain_name, cap_name, relationship_data
                            )
                        else:
                            logger.warning(
                                f"Could not find source or target tool for relationship: "
                                f"source_id={tool_rel.source_tool_id}, target_id={tool_rel.target_tool_id}"
                            )

        logger.info("Skills and tools sync completed successfully")

    except Exception as e:
        logger.error(f"Error syncing skills and tools from DB to graph: {e}")
        raise


def delete_tool_node(gsess, sess, tool_name: str) -> None:
    """Delete a Tool node from Neo4j and handle cascading deletions.

    This function performs the following operations:
    1. Find all skills that use this tool via USES_TOOL edges
    2. For each skill that only has this one tool:
       - Delete HAS_SKILL edges from capabilities to this skill
       - Delete all USES_TOOL edges from this skill
       - Delete the skill node
    3. Delete remaining USES_TOOL edges pointing to this tool (from skills with multiple tools)
    4. Delete all NEXT_TOOL edges where this tool is the source or target
    5. Delete all HAS_TOOL edges from capabilities to this tool
    6. Delete the Tool node itself

    Args:
        gsess: An active Neo4j session
        sess: SQLAlchemy session for relational DB operations
        tool_name: Name of the tool to delete
    """
    try:
        # Step 1: Find all skills that use this tool
        find_skills_cypher = """
        MATCH (s:Skill)-[:USES_TOOL]->(t:Tool {name: $tool_name})
        RETURN s.name AS skill_name
        """
        skills_result = gsess.run(find_skills_cypher, tool_name=tool_name)
        skill_names = [record["skill_name"] for record in skills_result]
        
        logger.info(f"Found {len(skill_names)} skills using tool: {tool_name}")

        # Step 2: For each skill, check if it only uses this one tool
        for skill_name in skill_names:
            # Count how many tools this skill uses
            count_tools_cypher = """
            MATCH (s:Skill {name: $skill_name})-[:USES_TOOL]->(t:Tool)
            RETURN count(t) AS tool_count
            """
            count_result = gsess.run(count_tools_cypher, skill_name=skill_name)
            tool_count = count_result.single()["tool_count"]

            if tool_count == 1:
                # This skill only uses this tool, so delete the skill and all its relationships
                logger.info(f"Skill '{skill_name}' only uses tool '{tool_name}', deleting skill and its relationships")
                
                # Delete HAS_SKILL edges from capabilities to this skill
                delete_has_skill_cypher = """
                MATCH (c:Capability)-[r:HAS_SKILL]->(s:Skill {name: $skill_name})
                DELETE r
                """
                gsess.run(delete_has_skill_cypher, skill_name=skill_name)
                logger.info(f"Deleted HAS_SKILL edges for skill: {skill_name}")

                # Delete all USES_TOOL edges from this skill (to any tool)
                delete_skill_uses_tool_cypher = """
                MATCH (s:Skill {name: $skill_name})-[r:USES_TOOL]->()
                DELETE r
                """
                gsess.run(delete_skill_uses_tool_cypher, skill_name=skill_name)
                logger.info(f"Deleted USES_TOOL edges from skill: {skill_name}")

                # Delete the skill node itself
                delete_skill_cypher = """
                MATCH (s:Skill {name: $skill_name})
                DELETE s
                """
                gsess.run(delete_skill_cypher, skill_name=skill_name)
                logger.info(f"Deleted skill node: {skill_name}")
            else:
                # This skill uses multiple tools, only delete the USES_TOOL edge to this specific tool
                logger.info(f"Skill '{skill_name}' uses {tool_count} tools, only deleting USES_TOOL edge to tool '{tool_name}'")
                delete_single_uses_tool_cypher = """
                MATCH (s:Skill {name: $skill_name})-[r:USES_TOOL]->(t:Tool {name: $tool_name})
                DELETE r
                """
                gsess.run(delete_single_uses_tool_cypher, skill_name=skill_name, tool_name=tool_name)
                logger.info(f"Deleted USES_TOOL edge from skill '{skill_name}' to tool '{tool_name}'")

        # Step 4: Delete all NEXT_TOOL edges involving this tool
        delete_next_tool_cypher = """
        MATCH (t:Tool {name: $tool_name})
        OPTIONAL MATCH (t)-[r1:NEXT_TOOL]->()
        OPTIONAL MATCH ()-[r2:NEXT_TOOL]->(t)
        DELETE r1, r2
        """
        gsess.run(delete_next_tool_cypher, tool_name=tool_name)
        logger.info(f"Deleted NEXT_TOOL edges for tool: {tool_name}")

        # Step 5: Delete all HAS_TOOL edges from capabilities to this tool
        delete_has_tool_cypher = """
        MATCH (c:Capability)-[r:HAS_TOOL]->(t:Tool {name: $tool_name})
        DELETE r
        """
        gsess.run(delete_has_tool_cypher, tool_name=tool_name)
        logger.info(f"Deleted HAS_TOOL edges for tool: {tool_name}")

        # Step 6: Delete the Tool node itself
        delete_tool_cypher = """
        MATCH (t:Tool {name: $tool_name})
        DELETE t
        """
        gsess.run(delete_tool_cypher, tool_name=tool_name)
        logger.info(f"Deleted Tool node: {tool_name}")

    except ServiceUnavailable as e:
        logger.warning(f"Neo4j service unavailable while deleting tool node '{tool_name}': {e}")
        logger.warning(f"Skipping graph cleanup for tool '{tool_name}' - service metadata and database records will still be deleted")
        # Don't raise - allow the deletion to continue without graph cleanup
    except Neo4jError as e:
        logger.warning(f"Neo4j error while deleting tool node '{tool_name}': {e}")
        logger.warning(f"Skipping graph cleanup for tool '{tool_name}' - service metadata and database records will still be deleted")
        # Don't raise - allow the deletion to continue without graph cleanup
    except Exception as e:
        logger.error(f"Unexpected error deleting tool node '{tool_name}': {e}")
        # Re-raise unexpected errors
        raise
