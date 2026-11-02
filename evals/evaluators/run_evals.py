from deepeval import evaluate
from deepeval.metrics import AnswerRelevancyMetric, ContextualPrecisionMetric,FaithfulnessMetric
from deepeval.test_case import LLMTestCase

queries = [
    "What's the warranty on the router?",
    "What did I decide about the hiring plan?",
]
actual_outputs = [
    "The router's warranty is two years, per router.md.",
    "You decided to hire two backend engineers in Q1, per hiring_plan.md.",
]
retrieval_contexts = [
    ["The TP-Link router (router.md) comes with a 2-year manufacturer warranty starting from the purchase date."],
    ["hiring_plan.md: Decision — hire 2 backend engineers in Q1 to support the RAG pipeline rollout."],
]
expected_outputs = [
    "Two years.",
    "Hire two backend engineers in Q1.",
]

test_cases = [
    LLMTestCase(
        input=queries[idx],
        actual_output=actual_outputs[idx],
        retrieval_context=retrieval_contexts[idx],
        expected_output=expected_outputs[idx],
    )
    for idx in range(len(queries))
]

metrics = [
    AnswerRelevancyMetric(threshold=0.85),
    FaithfulnessMetric(threshold=0.85),
    ContextualPrecisionMetric(threshold=0.85),
]

evaluate(test_cases=test_cases, metrics=metrics)