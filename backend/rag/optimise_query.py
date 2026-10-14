import re

from guardrails import Guard, Validator, register_validator
from guardrails.validator_base import FailResult, PassResult
from llama_index.core import Settings
from llama_index.core.base.llms.types import CompletionResponse

MAX_QUERY_WORDS = 10


def _first_clean_line(text):
    line = next((l.strip() for l in text.splitlines() if l.strip()), "")
    line = re.sub(r"\[[^\]]*\]|\([^)]*\)", "", line)
    return " ".join(line.strip(" \"'`").split())


@register_validator(name="valid-search-query", data_type="string")
class ValidSearchQuery(Validator):
    def validate(self, value, metadata):
        question = (metadata or {}).get("question", "")
        cleaned = _first_clean_line(value)
        if not cleaned or len(cleaned.split()) > MAX_QUERY_WORDS:
            cleaned = question
        if cleaned != value:
            return FailResult(error_message="Not a clean one-line search query.", fix_value=cleaned)
        return PassResult()


_guard = Guard().use(ValidSearchQuery(on_fail="fix"))


def optimise_query(llm,query):
    prompt = f"""You rewrite questions into search queries for a personal knowledge base of notes and documents.

Rules:
- Output ONLY the search query, on one line. No explanation, no quotes, no markdown, no notes in brackets.
- Do not answer the question.
- Do not translate. Write the query in the same language as the question.
- Keep names, numbers and product codes exactly as written.
- Use only the key terms of the question. Do not add words that are not in it.
- If the input is already a keyword or a code, return it unchanged.
- At most 10 words.

Question: What's the product code of the flagship router?
Search query: flagship router product code

Question: πότε μπορώ να επιστρέψω ένα προϊόν;
Search query: επιστροφή προϊόντος

Question: is AB-1234 still under warranty?
Search query: AB-1234 warranty

Question: AB-1234
Search query: AB-1234

Question: {query}
Search query:"""
    response = llm.complete(prompt)
    outcome = _guard.validate(response.text.strip(), metadata={"question": query})
    return CompletionResponse(text=outcome.validated_output or query)