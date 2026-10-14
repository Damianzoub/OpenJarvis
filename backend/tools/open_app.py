import subprocess

from guardrails import Guard, Validator, register_validator
from guardrails.errors import ValidationError
from guardrails.validator_base import PassResult, FailResult
from langchain.tools import tool

ALLOWED_APPS = {
    "Calendar",
    "Mail",
    "Notes",
    "Safari",
    "Music",
    "Finder",
    "Calculator",
    "Messages",
}


@register_validator(name="valid-app-name", data_type="string")
class ValidAppName(Validator):
    def validate(self, value, metadata):
        if value not in ALLOWED_APPS:
            return FailResult(
                error_message=f"'{value}' is not an app Jarvis is allowed to open."
            )
        return PassResult()


_guard = Guard().use(ValidAppName())


@tool(description="Open a macOS application by name.")
async def open_app(app_name: str) -> str:
    try:
        _guard.validate(app_name)
    except ValidationError:
        return f"'{app_name}' is not an app I'm allowed to open."

    try:
        subprocess.run(["open", "-a", app_name], check=True)
        return f"Opened {app_name} successfully."
    except subprocess.CalledProcessError as e:
        return f"Failed to open {app_name}: {e}"
    except Exception as e:
        return f"An error occurred while trying to open {app_name}: {e}"
