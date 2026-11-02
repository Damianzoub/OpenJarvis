from ragas import evaluate
from datasets import Dataset
from ragas.metrics.collections import answer_relevancy

def relevance(query:str,answer:list[str],answer_agent:str):
    data = {
        "user_query":query,
        "answer": answer,
        "answer_agent": answer_agent
    }
    dataset = Dataset.from_dict(data)
    result = evaluate(dataset,metrics=[answer_relevancy])
    return result["answer_relevancy"]
