import os 
import fnmatch
from bu_agent_sdk.tools import tool

@tool("Search for files on disk. Call this when the user asks to find, locate, or list files.")
async def search_files(directory: str, pattern: str, max_depth: int = 3) -> str:
    try:
        directory = os.path.expanduser(directory)
        base_depth = directory.rstrip(os.sep).count(os.sep)
        matches = []
        for root, dirs, files in os.walk(directory):
            current_depth = root.count(os.sep) - base_depth
            if current_depth >= max_depth:
                dirs.clear()
                continue
            dirs[:] = [d for d in dirs if not d.startswith((".", "__"))]
            for filename in fnmatch.filter(files, pattern):
                matches.append(os.path.join(root, filename))
        return "\n".join(matches) if matches else "No files found."
    except Exception as e:
        return f"Error: {e}"