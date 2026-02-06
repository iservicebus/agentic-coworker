import json
from integrator.utils.llm import Embedder
from integrator.domains.prompt import build_can_tool_prompt, build_op_match_prompt

from sqlalchemy import  select,  bindparam, text, insert
from integrator.utils.logger import get_logger
import numpy as np
from typing import Dict, Any, List

logger = get_logger(__name__)

def normalize_tool(llm, tool_name: str, description: str, input_schema: dict) -> List[dict]:
    try:

        prompt_str = build_can_tool_prompt(tool_name, description, input_schema)
        caps = json.loads(llm.invoke(prompt_str))
        return caps
    except Exception as e:
        logger.error(f" failed to normalize the tool. error: {str(e)}")
    # fallback: use heuristic on description only
    return {}

def get_domains_by_description(sess, emb: Embedder, q: str, k: int = 3) -> List[Dict[str, Any]]:
    """
    Get domain by searching domain descriptions using vector similarity.
    
    Args:
        sess: Database session
        emb: Embedder instance
        q: domain description query
        k: Number of results to return
    
    Returns:
        List of domain dictionaries with name, description, and similarity
    """
    vec = np.array(emb.encode([q])[0])
    sql = text(f"SELECT name, description, 1 - (emb <=> (:v)::vector) AS cosine_sim FROM domains ORDER BY emb <=> (:v)::vector LIMIT {k}")
    rows = sess.execute(sql.bindparams(bindparam("v", value=vec.tolist()))).all()
    
    return [
        {
            "name": row[0],
            "description": row[1],
            "similarity": float(row[2])
        }
        for row in rows
    ]

def get_capabilities_by_query(sess, emb: Embedder, q: str, domain_names: List[str], k: int = 3) -> List[Dict[str, Any]]:
    """
    Get capabilities by searching capability embeddings using vector similarity, restricted to specific domains.

    Args:
        sess: Database session
        emb: Embedder instance
        q: capability query string
        domain_names: list of domain names to restrict capabilities
        k: number of results to return

    Returns:
        List of capability dictionaries with name, label, description, outcome, and similarity
    """
    vec = np.array(emb.encode([q])[0])
    # Prepare domain_names for SQL IN clause
    domain_names_tuple = tuple(domain_names)
    sql = text(
        """
        SELECT
            c.name,
            c.label,
            c.description,
            c.outcome,
            1 - (c.emb <=> (:v)::vector) AS cosine_sim
        FROM capabilities c
        JOIN domain_capability dc ON c.name = dc.capability_name
        WHERE dc.domain_name IN :domain_names
        ORDER BY c.emb <=> (:v)::vector
        LIMIT :k
        """
    )
    rows = sess.execute(
        sql.bindparams(
            bindparam("v", value=vec.tolist()),
            bindparam("domain_names", value=domain_names_tuple, expanding=True),
            bindparam("k", value=k)
        )
    ).all()
    return [
        {
            "name": row[0],
            "label": row[1],
            "description": row[2],
            "outcome": row[3],
            "similarity": float(row[4])
        }
        for row in rows
    ]

def nearest_ops(
    sess,
    emb: Embedder,
    q: str,
    k: int = 4,
    inputs: List[Dict] = None,
    outputs: List[Dict] = None,
    capability_names: List[str] = None
) -> List[Dict[str, Any]]:
    """
    Search skills using a description query (required) and optional input/output descriptors,
    optionally restricted to specific capability names.

    Args:
        sess: Database session
        emb: Embedder instance
        q: Required description query
        k: Number of results to return
        inputs: Optional list of input parameter dicts/strings
        outputs: Optional list of output parameter dicts/strings
        capability_names: Optional list of capability names to restrict skills

    Returns:
        List of skill dictionaries with name, label, description, skill fields, and related_capabilities
    """
    # Build a composite text query from description + optional inputs/outputs
    text_parts: List[str] = [q]

    if inputs:
        for param in inputs:
            if isinstance(param, dict):
                text_parts.append(str(param.get("name", "")))
                text_parts.append(str(param.get("description", "")))
            else:
                text_parts.append(str(param))

    if outputs:
        for param in outputs:
            if isinstance(param, dict):
                text_parts.append(str(param.get("name", "")))
                text_parts.append(str(param.get("description", "")))
            else:
                text_parts.append(str(param))

    query_text = " ".join(p for p in text_parts if p).strip()
    vec = np.array(emb.encode([query_text])[0])

    and_cap_filter = ""
    params: Dict[str, Any] = {
        "v": vec.tolist(),
        "k": k,
    }
    if capability_names:
        and_cap_filter = "AND co.capability_name IN :cap_names"
        params["cap_names"] = tuple(capability_names)

    sql = f"""
    SELECT
        s.name,
        s.label,
        s.description,
        s.operational_entities,
        s.operational_procedures,
        s.operational_intent,
        s.preconditions,
        s.postconditions,
        s.proficiency,
        COALESCE(
            json_agg(
                json_build_object(
                    'label', c.label,
                    'description', c.description,
                    'intent', c.outcome
                )
            ) FILTER (WHERE c.label IS NOT NULL), '[]'
        ) AS capabilities
    FROM skills s
    LEFT JOIN capability_skill co ON s.name = co.skill_name
    LEFT JOIN capabilities c ON co.capability_name = c.name
    WHERE s.emb IS NOT NULL
    {and_cap_filter}
    GROUP BY s.name, s.label, s.description,
             s.operational_entities, s.operational_procedures,
             s.operational_intent, s.preconditions, s.postconditions,
             s.proficiency, s.emb
    ORDER BY s.emb <=> (:v)::vector
    LIMIT :k
    """

    rows = sess.execute(
        text(sql),
        params
    ).all()
    return [
        {
            "name": r[0],
            "label": r[1],
            "description": r[2],
            "operational_entities": r[3],
            "operational_procedures": r[4],
            "operational_intent": r[5],
            "preconditions": r[6],
            "postconditions": r[7],
            "proficiency": r[8],
            "related_capabilities": r[9],
        }
        for r in rows
    ]

def rerank_operations(candidates, target, llm) -> List[str]:

    prompt_str = build_op_match_prompt(target,candidates)
    ops = json.loads(llm.invoke(prompt_str))

    min_score=10
    stop_diff=20
    max_len=5

    selected_ops=[]
    for i, op in enumerate(ops):
        if i==0:
            if op["score"] >= min_score:
                selected_ops.append(op["name"])
            else:
                break

        if i>0 and len(selected_ops)<max_len:
            if (ops[i-1]["score"]-op["score"]) <= stop_diff and op["score"]>=min_score:
                selected_ops.append(op["name"])
            else:
                break

    return selected_ops
