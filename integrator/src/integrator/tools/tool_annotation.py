import asyncio
import json
import logging
import os
import re
from pathlib import Path
from typing import Dict, Optional, Any
from integrator.utils import host
import litellm
from dotenv import load_dotenv
from jinja2 import Template
from playwright.async_api import Playwright, async_playwright
from integrator.utils.json_utils import validate_instance
from integrator.utils.llm import LLM, generate_json_from_llm

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# --- Helper Functions ---

def load_env_variables(env_path: Path) -> bool:
    """Loads environment variables from a .env file."""
    if not env_path.is_file():
        logger.warning(f".env file not found at {env_path}. Skipping .env loading.")
        return False
    load_dotenv(env_path)
    logger.info(f"Loaded environment variables from {env_path}")
    return True

def load_file_content(file_path: Path) -> str:
    """Reads and returns the content of a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        raise
    except IOError as e:
        logger.error(f"Error reading file {file_path}: {e}")
        raise

def load_jinja_template(template_path: Path) -> Template:
    """Loads a Jinja2 template from a file."""
    template_content = load_file_content(template_path)
    return Template(template_content)




async def annotate_tool_by_llm(tool_dict: dict,llm, system_prompt_path:str) -> Optional[Dict[str, Any]]:

    try:
        with open(system_prompt_path, 'r', encoding='utf-8') as f:
            system_prompt_str=f.read()

        tool_str = json.dumps(tool_dict)
        user_prompt = f"""
        The actual Tool representation in JSON format:        
        {tool_str}
        """
        generated_json = generate_json_from_llm(
            system_prompt=system_prompt_str,
            user_prompt=user_prompt,
            llm=llm
        )
        return generated_json

    except Exception as e:
        logger.error(f"An error occurred during the transformation process: {e}")
        return None


# --- Main Execution ---

async def main():
    """Main function to demonstrate the transformation process."""

    system_prompt_path=os.path.join(os.path.dirname(__file__), "../../../config/prompts/tool_annotation_system_prompt.txt")

    tool_dict=  {
    "name": "arxiv_query_get",
    "description": "Retrieve arXiv search results via the query interface using HTTP GET. Returns Atom 1.0 feeds for matching articles based on search_query and/or id_list, with optional paging and sorting.",
    "inputSchema": {
      "type": "object",
      "description": "Dynamic inputs for arXiv GET query interface. Provide search_query and/or id_list, with optional paging (start, max_results) and sorting (sortBy, sortOrder).",
      "properties": {
        "path": {
          "type": "object",
          "description": "No dynamic path parameters for this endpoint.",
          "additionalProperties": False
        },
        "query": {
          "type": "object",
          "description": "Query string parameters for the arXiv query interface.",
          "properties": {
            "search_query": {
              "type": "string",
              "description": "Search query string per arXiv syntax (e.g., 'all:electron', 'ti:\"quantum entanglement\"'). If provided alone, returns articles matching the query."
            },
            "id_list": {
              "type": "string",
              "description": "Comma-delimited list of arXiv IDs (e.g., 'cs/9901002v1,hep-ex/0307015'). If provided alone, returns those specific articles."
            },
            "start": {
              "type": "integer",
              "description": "0-based index of the first returned result for paging.",
              "minimum": 0,
              "default": 0
            },
            "max_results": {
              "type": "integer",
              "description": "Number of results to return in this call. Requests with max_results > 30000 result in HTTP 400.",
              "minimum": 1,
              "maximum": 30000,
              "default": 10
            },
            "sortBy": {
              "type": "string",
              "description": "Sort criterion for results.",
              "enum": [
                "relevance",
                "lastUpdatedDate",
                "submittedDate"
              ]
            },
            "sortOrder": {
              "type": "string",
              "description": "Sort order direction.",
              "enum": [
                "ascending",
                "descending"
              ]
            }
          },
          "additionalProperties": False
        },
        "headers": {
          "type": "object",
          "description": "Optional additional dynamic headers. Accept is set statically to application/atom+xml.",
          "additionalProperties": True
        },
        "body": {
          "type": "null",
          "description": "GET requests to this endpoint do not include a request body."
        }
      }
    }
    }
    llm=LLM()

    rs= await annotate_tool_by_llm(tool_dict,llm,system_prompt_path)
    print(rs)

if __name__ == '__main__':
    # Ensure an event loop is running if called directly
    # In Python 3.7+ asyncio.run can be used directly
    # For older versions or specific environments, you might need:
    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(main())
    asyncio.run(main())
