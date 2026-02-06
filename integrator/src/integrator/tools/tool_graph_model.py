
from dataclasses import dataclass
from typing import List, Dict, Any


# ---------------------------
# Data structures
# ---------------------------

@dataclass
class ToolEdge:
    """
    Directed edge between two tools in the procedural knowledge graph.

    from_tool / to_tool are full tool descriptors (canonical_data + name, etc.),
    represented as dictionaries rather than just tool names so downstream
    consumers (e.g. LLM prompts) have access to rich tool metadata.
    """
    from_tool: Dict[str, Any]
    to_tool: Dict[str, Any]
    capability: str
    composite_intent: str | None


@dataclass
class CandidatePath:
    """
    A linear path of tools for a capability.

    type:
        - "chain": 2+ tools connected via NEXT_TOOL edges
        - "single_tool": a standalone tool with no in/out edges

    tools:
        Ordered list of full tool dicts (same shape as ToolEdge.from_tool/to_tool),
        not just tool names, so that each step in the path carries its canonical
        metadata.
    """
    type: str
    tools: List[Dict[str, Any]]
