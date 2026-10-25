import asyncio
import os
import shutil
from pathlib import Path

from guardrails.errors import ValidationError
from langchain.tools import tool

from rag.online import run_online, load_index
from rag.document_loader import file_path as _PERSONAL_INFO_DIR
from rag.offline import main as _rebuild_index
from tools.search_files import _guard

SUPPORTED_EXTENSIONS = {".md", ".txt", ".pdf", ".docx", ".html"}


@tool(description="Search the user's personal notes and documents for releveant passages.")
async def search_knowledge(query:str):
    result = await asyncio.to_thread(run_online,query)
    return str(result)

# if function is synchronous use asyncio.to_thread
# if function is asynchronous (run_online) use await


@tool(description="Add a file to the user's personal notes so search_knowledge can find it. Call this when the user asks to import, add, or save a file to their notes/knowledge base.")
async def ingest_document(path: str) -> str:
    try:
        _guard.validate(path)
    except ValidationError as e:
        return str(e)

    resolved = os.path.expanduser(path)
    if not os.path.isfile(resolved):
        return f"No such file: {path}"

    ext = Path(resolved).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        return f"Unsupported file type {ext}. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"

    dest = _PERSONAL_INFO_DIR / Path(resolved).name
    await asyncio.to_thread(shutil.copy, resolved, dest)
    await asyncio.to_thread(_rebuild_index)
    load_index.cache_clear()
    return f"Added {Path(resolved).name} to your notes and rebuilt the index."