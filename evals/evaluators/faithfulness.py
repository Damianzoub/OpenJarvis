from ragas.metrics.collections import faithfulness
from ragas import evaluate
from datasets import Dataset

def faithfull(answer:list[str],query:str,agent_response:str)->float:
    data ={
        "user_input": query,
        "relevance_answer":answer,
        "agent_response": agent_response
    }
    dataset = Dataset.from_dict(data)
    result = evaluate(dataset,metrics=[faithfulness])
    return result['faithfulness']