import json

from integrator.domains.prompt import build_can_tool_prompt, build_domain_classifer_prompt, build_capability_classifer_prompt, build_tool_rel_prompt, build_skill_exract_prompt
from integrator.domains.domain_db_crud import get_all_domains, get_capabilities_by_domain

from integrator.tools.tool_db_model import McpTool
from integrator.utils.logger import get_logger
import numpy as np
from typing import Dict, Any, List

logger = get_logger(__name__)


def _invoke_llm_json(llm, prompt: str, context: str):
    """Invoke LLM and parse JSON with basic error handling.

    Returns None on failure so callers can decide how to fallback.
    """
    try:
        raw = llm.invoke(prompt)
    except Exception as e:
        logger.error(f"{context}: exception while calling LLM: {e}")
        return None

    if not raw or not str(raw).strip():
        logger.error(f"{context}: LLM returned empty response")
        return None

    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        # Truncate raw output in logs to avoid spamming
        snippet = str(raw)
        if len(snippet) > 500:
            snippet = snippet[:500] + "... [truncated]"
        logger.error(f"{context}: failed to parse JSON from LLM: {e}. Raw response snippet: {snippet}")
        return None


def normalize_tool(llm, tool_name, description: str, input_schema: dict) -> List[dict]:
    try:
        prompt_str = build_can_tool_prompt(tool_name, description, input_schema)
        caps = _invoke_llm_json(llm, prompt_str, "normalize_tool")
        if caps is None:
            # fallback: use heuristic on description only
            return {}
        return caps
    except Exception as e:
        logger.error(f"failed to normalize the tool. error: {str(e)}")
        # fallback: use heuristic on description only
        return {}

def get_domain_by_tool(sess, llm, tenant_name, tool_json) -> List[Dict[str, Any]]:
    """
    Get domain by match tool using llm.
    
    Args:
        sess: Database session
        llm: LLM instance
        tenant_name: Name of the tenant for isolation
        tool_json: Tool data in JSON format
    
    Returns:
        domain dictionaries with name
    """
    domain_list = get_all_domains(sess, tenant_name)
    domain_classifer_prompt = build_domain_classifer_prompt(tool_json, domain_list)
    domain_json = _invoke_llm_json(llm, domain_classifer_prompt, "get_domain_by_tool")
 
    return domain_json or []

def get_capbility_by_tool_domain(sess, llm, tenant_name, domain_name, tool_json) -> List[Dict[str, Any]]:
    """
    Get capability by match tool using llm.
    
    Args:
        sess: Database session
        llm: LLM instance
        tenant_name: Name of the tenant for isolation
        domain_name: Name of the domain
        tool_json: Tool data in JSON format
    
    Returns:
        capability dictionaries with name
    """
    cap_list = get_capabilities_by_domain(sess, domain_name, tenant_name)
    cap_classifer_prompt = build_capability_classifer_prompt(tool_json, cap_list)
    cap_json = _invoke_llm_json(llm, cap_classifer_prompt, "get_capbility_by_tool_domain")
 
    return cap_json or []


def get_tool_rel_by_tool( llm, src_tool: McpTool, target_tool_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Get tool relationship using llm.
    
    Returns:
        capability dictionaries with name
    """
    src_can_tool=src_tool.canonical_data
    src_can_tool["name"]=src_tool.name

    target_can_tools = []
    for target in target_tool_list:
        raw_canonical = target.get("canonical_data", {})
        if isinstance(raw_canonical, str):
            raw_canonical=json.loads(raw_canonical)
        canonical_data = {**raw_canonical, "name": target.get("name", "")}
        target_can_tools.append(
            canonical_data
        )
    
    tool_rel_prompt=build_tool_rel_prompt(src_can_tool, target_can_tools)
    tool_rel_json = _invoke_llm_json(llm, tool_rel_prompt, "get_tool_rel_by_tool")
 
    return tool_rel_json or []

def extract_skills_from_tools( llm,  tool_chains: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    extract skills from tool chains.
    
    Returns:
        list of skills 
    """
    
    extract_skills_prompt=build_skill_exract_prompt(tool_chains)
    skills_json = _invoke_llm_json(llm, extract_skills_prompt, "extract_skills_from_tools")
 
    return skills_json or []
