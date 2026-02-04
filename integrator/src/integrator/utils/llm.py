from dotenv import load_dotenv
import os
from openai import AzureOpenAI
from langchain.chat_models import init_chat_model
from langchain.embeddings import init_embeddings
from langchain_core.messages import HumanMessage, BaseMessage
from langchain_core.prompt_values import PromptValue
import json, re
from typing import Optional, Dict, Any

from integrator.utils.env import load_env
from integrator.utils.logger import get_logger
# Load environment variables from .env file at the very beginning.
# This ensures that all subsequent modules have access to the environment variables.

load_env()

logger = get_logger(__file__)

from typing import List
import numpy as np

def initialize_llm_model():

    model_provider = os.getenv("MODEL_PROVIDER", "azure_openai").lower()

    if model_provider == "google_genai":
        # Updated to use Google GenAI provider
        # The 'gemini-2.5-flash' model name follows Google's naming convention
        return init_chat_model(
            model=os.getenv("GOOGLE_MODEL"), 
            model_provider=model_provider,
            api_key=os.getenv("GOOGLE_API_KEY"),
            temperature=0
        )
    
    elif model_provider == "azure_openai":
        return init_chat_model(
            model=os.environ["AZURE_OPENAI_MODEL"],
            model_provider=model_provider,
            azure_deployment=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
            api_version=os.environ["AZURE_OPENAI_API_VERSION"],
            temperature=1
        )

    elif model_provider == "openai":
        # OpenAI official API
        return init_chat_model(
            model=os.getenv("OPENAI_MODEL", "gpt-4o"),
            model_provider=model_provider,
            api_key=os.getenv("OPENAI_API_KEY")
        )
    
    elif model_provider == "local_openai":
        # Local OpenAI-compatible server (e.g., MLX, gpt-oss)
        return init_chat_model(
            model=os.environ["LOCAL_OPENAI_MODEL"],
            model_provider="openai",  # Use openai provider for compatibility
            base_url=os.environ["LOCAL_OPENAI_BASE_URL"],
            api_key=os.environ["LOCAL_OPENAI_API_KEY"]
        )
    
    elif model_provider == "anthropic":
        # Anthropic Claude models
        return init_chat_model(
            model=os.getenv("ANTHROPIC_MODEL"),
            model_provider=model_provider,
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            temperature=0
        )

    else:
        raise ValueError(f"Unsupported provider: {model_provider}")
    
def initialize_embedding_model():

    model_provider = os.getenv("MODEL_PROVIDER", "azure_openai").lower()

    if model_provider == "google_genai":
        from langchain_google_genai import GoogleGenerativeAIEmbeddings
        
        return GoogleGenerativeAIEmbeddings(
            model=os.getenv("GOOGLE_EMBEDDING_MODEL"),
            google_api_key=os.environ.get("GOOGLE_API_KEY"),
            task_type="RETRIEVAL_DOCUMENT",
            output_dimensionality=1536,
        )
    
    elif model_provider == "azure_openai":
        return init_embeddings(
            model=os.environ["AZURE_OPENAI_EMBEDDING_MODEL"],
            provider=model_provider,
            azure_deployment=os.environ["AZURE_OPENAI_EMBEDDING_MODEL"],
            api_version=os.environ["AZURE_OPENAI_API_VERSION"]
        )
    
    elif model_provider == "openai":
        # OpenAI official embeddings
        return init_embeddings(
            model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
            provider=model_provider,
            api_key=os.getenv("OPENAI_API_KEY")
        )
    
    elif model_provider in ["local_openai", "anthropic"]:
        # Local Ollama embeddings for local_openai and anthropic
        from langchain_ollama import OllamaEmbeddings
        return OllamaEmbeddings(
            model=os.environ["LOCAL_EMBEDDING_MODEL"],
            base_url=os.environ["LOCAL_EMBEDDING_BASE_URL"],
        )
    
    
    else:
        raise ValueError(f"Unsupported provider: {model_provider}")



class LLM:
    def __init__(self):
        self.model=initialize_llm_model()
        self.model_provider = os.getenv("MODEL_PROVIDER", "azure_openai")
        self.model_name = self._get_model_name()
        
    def _get_model_name(self):
        """Get the model name based on provider"""
        provider = self.model_provider.lower()
        if provider == "google_genai":
            return os.getenv("GOOGLE_MODEL", "unknown")
        elif provider == "azure_openai":
            return os.getenv("AZURE_OPENAI_MODEL", "unknown")
        elif provider == "openai":
            return os.getenv("OPENAI_MODEL", "unknown")
        elif provider == "local_openai":
            return os.getenv("LOCAL_OPENAI_MODEL", "unknown")
        elif provider == "anthropic":
            return os.getenv("ANTHROPIC_MODEL", "unknown")
        return "unknown"
    
    def _truncate_text(self, text: str, max_length: int = 100) -> str:
        """Truncate text for logging"""
        if len(text) <= max_length:
            return text
        return text[:max_length] + "..."
    
    def _format_input_for_log(self, input: str | list[dict | tuple | BaseMessage] | PromptValue) -> str:
        """Format input for logging"""
        if isinstance(input, str):
            return self._truncate_text(input)
        elif isinstance(input, list):
            if len(input) > 0 and isinstance(input[0], dict):
                # Extract content from message dicts
                contents = []
                for msg in input[:2]:  # Only log first 2 messages
                    if isinstance(msg, dict) and "content" in msg:
                        contents.append(f"{msg.get('role', 'unknown')}: {self._truncate_text(str(msg['content']), 50)}")
                return " | ".join(contents)
            return self._truncate_text(str(input))
        else:
            return self._truncate_text(str(input))
    
    def invoke(self, input: str | list[dict | tuple | BaseMessage] | PromptValue):
        import time
        
        # Log input
        input_preview = self._format_input_for_log(input)
        logger.info(f"🤖 LLM Invoke START | Provider: {self.model_provider} | Model: {self.model_name}")
        logger.info(f"📝 Input: {input_preview}")
        
        # Measure latency
        start_time = time.time()
        response = self.model.invoke(input)
        latency = time.time() - start_time
        
        # Log output
        output_preview = self._truncate_text(str(response.content))
        logger.info(f"✅ LLM Invoke END | Latency: {latency:.2f}s")
        logger.info(f"📤 Output: {output_preview}")
        
        return response.content

    def get_model(self):
        return self.model

class Embedder:
    def __init__(self):
        self.model=initialize_embedding_model()    

    def encode(self, texts: List[str]|str) -> np.ndarray:

        if isinstance(texts, str):
            response=self.model.embed_query(texts)
        else:    
            response = self.model.embed_documents(texts)

        return np.array(response, dtype=float)




def generate_json_from_llm(
    system_prompt: str,
    user_prompt: str,
    llm
) -> Optional[Dict[str, Any]]:
    """
    Generates a JSON object using an LLM.

    Args:
        system_prompt: The system prompt for the LLM.
        user_prompt: The user prompt for the LLM.
        model: The LLM model to use.

    Returns:
        A dictionary parsed from the LLM's JSON output, or None if an error occurs.
    """
    try:
        logger.info(f"Sending request to LLM (model: {llm.model})...")
        prompts=[{"role": "system", "content": system_prompt}]
        if user_prompt:
                prompts.append({"role": "user", "content": user_prompt})
        else:
                prompts.append({"role": "user", "content": "strictly follow system prompt"})

        raw_content =  llm.invoke(prompts )
        
        logger.info("Received response from LLM.")

        # Extract JSON from ```json ... ``` block
        match = re.search(r"```json\s*(.*?)```", raw_content, re.DOTALL | re.IGNORECASE)
        if match:
            json_string = match.group(1)
            logger.info("Successfully extracted JSON block from LLM response.")
            return json.loads(json_string)
        else:
            logger.warning("No JSON block found in LLM response. Attempting to parse entire response.")
            # Fallback: try to parse the whole content if no explicit block
            try:
                return json.loads(raw_content)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse LLM response as JSON. Content:\n{raw_content}")
                return None

    except Exception as e:
        logger.error(f"Error during LLM completion or JSON parsing: {e}")
        return None


if __name__ == "__main__":
#    emb=Embedder()
    chat=LLM()
    strs=" hello world"
#    strs=[" hello world", "test"]
#    ec=emb.encode(strs)
    ec=chat.invoke(strs)
    print(ec)

    embedder = Embedder()
    test_str = "Checking the dimension size."
    vector = embedder.encode(test_str)
    
    print(f"Model: gemini-embedding-001")
    print(f"Vector Shape: {vector.shape}") # Should output (1536,)
    
    if vector.shape[0] == 1536:
        print("✅ Success: Dimension matches OpenAI 3-small.")
    else:
        print(f"❌ Error: Expected 1536, got {vector.shape[0]}")
        
