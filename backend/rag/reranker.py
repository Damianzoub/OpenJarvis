from llama_index.core.postprocessor.llm_rerank import LLMRerank
from llama_index.core.postprocessor import SentenceTransformerRerank
from llama_index.core import Settings

from functools import lru_cache

def rerank_llm(top_n:int=3):
    return LLMRerank(llm=Settings.llm,top_n=top_n)

@lru_cache()
def rerank_cross_embed(top_n:int=3):
    return SentenceTransformerRerank(model="cross-encoder/ms-marco-MiniLM-L-2-v2",top_n=top_n)    


