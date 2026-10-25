from llama_index.core import Settings
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding

from llama_index.core.callbacks import CallbackManager

from dotenv import load_dotenv
import os

ENV = os.getenv("ENV")
API_Key = os.getenv("OPENAI_API_KEY")

def configure_llamaIndex():
    if ENV == "Prod":
        Settings.llm = OpenAI(
            model="gpt-6-luna",
            api_key=API_Key,
            temperature=0.1,
            max_retries=2,
            callback_manager=CallbackManager()
        )

        # dimensions=512 is a placeholder pending evals/evaluators/embedding_dimension_eval.py —
        # it compares faithfulness/relevance across candidate dimensions on real data
        # instead of guessing. Update once that's actually run.
        Settings.embed_model = OpenAIEmbedding(
            model="text-embedding-3-small",
            embed_batch_size=233,
            api_key=API_Key,
            dimensions=512,
            callback_manager=CallbackManager(),
            timeout=60.0
        )
    else:
        Settings.llm = Ollama(
            model="mistral",
            base_url="http://localhost:11434",
            temperature=0.1,
            request_timeout=60.0
        )

        Settings.embed_model = OllamaEmbedding(
            model_name="nomic-embed-text",
            base_url="http://localhost:11434",
            embed_batch_size=233,
            callback_manager = CallbackManager()
        )