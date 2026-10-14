from llama_index.core import SimpleDirectoryReader

from pathlib import Path

file_path = Path(__file__).parent / "personal_info"
REQUIRED_EXTENSIONS = [".md",".txt",".pdf",".docx"]
def path_exists():
    if not file_path.exists():
        raise ValueError("File path doesn't exist")

    document = SimpleDirectoryReader(input_dir=str(file_path),required_exts=REQUIRED_EXTENSIONS).load_data()
    return document