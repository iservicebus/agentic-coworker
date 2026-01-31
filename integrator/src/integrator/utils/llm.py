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
        temperature=0
        )
    else:
        raise ValueError(f"Unsupported provider: {model_provider}")
    
def initialize_embedding_model():

    model_provider = os.getenv("MODEL_PROVIDER", "azure_openai").lower()

    if model_provider == "google_genai":

        return init_embeddings(
                    model=os.getenv("GOOGLE_EMBEDDING_MODEL"),
                    provider=model_provider,
                    api_key=os.environ.get("GOOGLE_API_KEY"),
                    output_dimensionality=1536, 
            )

    
    elif model_provider == "azure_openai":
        return init_embeddings(
        model=os.environ["AZURE_OPENAI_EMBEDDING_MODEL"],
        provider=model_provider,
        azure_deployment=os.environ["AZURE_OPENAI_EMBEDDING_MODEL"],
        api_version=os.environ["AZURE_OPENAI_API_VERSION"]
    )


class LLM:
    def __init__(self):
        self.model=initialize_llm_model()
        # self.model = init_chat_model(
        # model=os.environ["AZURE_OPENAI_MODEL"],
        # model_provider=os.environ["LC_PROVIDER"],
        # azure_deployment=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
        # api_version=os.environ["AZURE_OPENAI_API_VERSION"],
        # temperature=0
        #  )
    def invoke(self, input: str | list[dict | tuple | BaseMessage] | PromptValue):       
        response = self.model.invoke(input)
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
        
