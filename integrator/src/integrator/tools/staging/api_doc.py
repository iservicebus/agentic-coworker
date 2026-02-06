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

# --- Core Logic Functions ---

async def extract_api_doc_text(url: str, playwright_instance: Playwright, max_length: int) -> str:
    """
    Extracts visible text from a given URL using Playwright.

    Args:
        url: The URL of the API documentation.
        playwright_instance: An active Playwright instance.
        max_length: Maximum number of characters to return.

    Returns:
        The extracted text, truncated to max_length.
    """
    browser = None
    try:
        browser = await playwright_instance.chromium.launch(headless=True)
        page = await browser.new_page()
        logger.info(f"Navigating to {url}...")
        await page.goto(url, wait_until="domcontentloaded") # Wait for DOM to be ready

        # Wait for the body selector, with a timeout
        await page.wait_for_selector("body", timeout=30000) # 30 seconds timeout

        logger.info(f"Extracting text from {url}...")
        text = await page.inner_text("body")
        logger.info(f"Successfully extracted text (length: {len(text)}).")

        return text[:max_length]
    except Exception as e:
        logger.error(f"Error extracting text from {url}: {e}")
        raise
    finally:
        if browser:
            await browser.close()
            logger.info("Playwright browser closed.")



async def regenerate_input_schema(
    input_schema_instance: Dict,
    input_schema_system_prompt_path: Path,
    input_schema_path: Path,
    llm

) -> tuple[bool, Optional[Dict[str, Any]]]:

    try:

        input_schema = load_file_content(input_schema_path)

        if input_schema_instance:
            is_valid, errors_json, errors_text = validate_instance(input_schema_instance, input_schema)
            if is_valid:
                return True, None
            else:
                system_prompt_input_schema = load_jinja_template(input_schema_system_prompt_path)

                rendered_system_prompt = system_prompt_input_schema.render(error_messages=errors_text, invalid_json=json.dumps(input_schema_instance))
                new_instance = generate_json_from_llm(
                    system_prompt=rendered_system_prompt,
                    user_prompt=None,
                    llm=llm
                )
                return is_valid, new_instance

    except Exception as e:
        logger.error(f"An error occurred during the transformation process: {e}")
        return False, None



async def transform_api_doc_to_tool_definition(
    api_doc_url: str,
    system_prompt_template_path: Path,
    generic_schema_path: Path,
    input_schema_system_prompt_path: Path,
    input_schema_path: Path,

    llm,
    max_length: int 

) -> Optional[Dict[str, Any]]:
    """
    Orchestrates the transformation of API documentation from a URL into a JSON tool definition.

    Args:
        api_doc_url: URL of the API documentation.
        system_prompt_template_path: Path to the Jinja2 template for the system prompt.
        generic_schema_path: Path to the generic schema JSON file.
        llm_model: The LLM model to use.

    Returns:
        The generated JSON tool definition, or None if an error occurs.
    """
    try:
        async with async_playwright() as p:
            api_doc_text = await extract_api_doc_text(api_doc_url, p, max_length)

        if not api_doc_text:
            logger.error("Failed to extract API documentation text.")
            return None

        system_prompt_template = load_jinja_template(system_prompt_template_path)
        generic_schema_content = load_file_content(generic_schema_path)

        rendered_system_prompt = system_prompt_template.render(generic_schema=generic_schema_content)

        user_prompt = f"""
        Below is the full API documentation text:
        --- START OF API DOCUMENTATION ---
        {api_doc_text}
        --- END OF API DOCUMENTATION ---
        Now, based on the generic schema and the documentation above, generate a complete JSON object tool definition.
        """

        generated_json = generate_json_from_llm(
            system_prompt=rendered_system_prompt,
            user_prompt=user_prompt,
            llm=llm
        )
        # Sanitize tool names to match pattern '^[a-zA-Z0-9_\.-]+$'
        for index, _ in enumerate(generated_json):
            # Sanitize the tool name
            if "name" in generated_json[index]:
                generated_json[index]["name"] = re.sub(r'[^a-zA-Z0-9_\.\-]', '', generated_json[index]["name"])
            url = generated_json[index].get("staticInput", {}).get("url", {})
            host_id, _, _=host.generate_host_id(url)
            if host_id:            
                generated_json[index]["appName"]=host_id

            input_schema=generated_json[index].get("inputSchema", {})
            is_valid, new_input_schema=await regenerate_input_schema(input_schema_instance=input_schema, input_schema_system_prompt_path=input_schema_system_prompt_path, input_schema_path= input_schema_path, llm= llm)


            if not is_valid:
                generated_json[index]["inputSchema"]=new_input_schema


        return generated_json

    except Exception as e:
        logger.error(f"An error occurred during the transformation process: {e}")
        return None


# --- Main Execution ---

async def main():
    """Main function to demonstrate the transformation process."""
    
    # Define paths relative to this script's location
    current_dir = Path(__file__).parent
    base_dir = current_dir.parent.parent.parent.parent # Assuming script is in src/stagging, base is two levels up

    env_path = base_dir / ".env"
    load_env_variables(env_path) # LiteLLM might need API keys from .env

    system_prompt_path = base_dir / "config" / "prompts" /  "api_doc_system_prompt.txt"
    gen_schema_path = base_dir / "config" / "schema" / "mcp_tool_schema.json"

    input_schema_system_prompt_path = base_dir / "config" / "prompts" /  "json_correction_prompt.txt"
    input_schema_path = base_dir / "config" / "schema" / "mcp_input_schema.json"




    # Example API documentation URL
#    api_doc_url = "https://www.alphavantage.co/documentation/"
    api_doc_url ="https://info.arxiv.org/help/api/user-manual.html"
    
    logger.info(f"Starting API documentation transformation for URL: {api_doc_url}")
    llm=LLM()
    #llm_model = os.getenv("VLLM_MODEL")
    max_length = int(os.getenv("MAX_TEXT_EXTRACTION_LENGTH"))


    tool_definition = await transform_api_doc_to_tool_definition(
        api_doc_url=api_doc_url,
        system_prompt_template_path=system_prompt_path,
        generic_schema_path=gen_schema_path,
        input_schema_system_prompt_path=input_schema_system_prompt_path,
        input_schema_path=input_schema_path,
        llm=llm,
        max_length=max_length
    )

    if tool_definition:
        logger.info("Successfully generated JSON Tool Definition:")
        # Pretty print the JSON
        print(json.dumps(tool_definition, indent=2))
    else:
        logger.error("Failed to generate JSON Tool Definition.")


if __name__ == '__main__':
    # Ensure an event loop is running if called directly
    # In Python 3.7+ asyncio.run can be used directly
    # For older versions or specific environments, you might need:
    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(main())
    asyncio.run(main())
