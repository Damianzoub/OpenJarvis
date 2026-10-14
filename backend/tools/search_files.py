import os
import subprocess
import fnmatch
from guardrails import Guard, Validator, register_validator
from guardrails.errors import ValidationError
from guardrails.validator_base import PassResult, FailResult
from langchain.tools import tool

NOT_ALLOWED_PATHS = {
    os.path.expanduser("~/.ssh"),
    os.path.expanduser("~/.aws"),
    os.path.expanduser("~/.gnupg"),
    os.path.expanduser("~/.docker"),
    os.path.expanduser("~/.config/gcloud"),
    os.path.expanduser("~/Library/Keychains"),
}


def _prompt_admin_password() -> str:
    script = (
        'display dialog "Admin Password" default answer "" '
        'with hidden answer with title "Jarvis" '
        'buttons {"Cancel", "OK"} default button "OK"'
    )
    result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    if result.returncode != 0:
        return ""
    output = result.stdout.strip()
    if "text returned:" in output:
        return output.split("text returned:", 1)[1]
    return ""


@register_validator(name="files_allowed", data_type="string")
class ValidationFiles(Validator):
    def validate(self, value, metadata):
        resolved = os.path.realpath(os.path.expanduser(value))
        blocked = any(
            resolved == os.path.realpath(p) or resolved.startswith(os.path.realpath(p) + os.sep)
            for p in NOT_ALLOWED_PATHS
        )
        if not blocked:
            return PassResult()

        admin_password = os.getenv("ADMIN_PASSWORD")
        password = _prompt_admin_password()
        if not admin_password or password != admin_password:
            return FailResult(error_message="Permission denied — you do not have access to this location.")
        return PassResult()


_guard = Guard().use(ValidationFiles())


@tool(description="Search for files on disk. Call this when the user asks to find, locate, or list files.")
async def search_files(directory: str, pattern: str, max_depth: int = 3) -> str:
    try:
        _guard.validate(directory)
    except ValidationError as e:
        return str(e)

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
