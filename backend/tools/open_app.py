import subprocess
from bu_agent_sdk.tools import tool 


@tool("Open a macOS application. Call this when the user asks to open or launch an app.")
async def open_app(app_name: str) -> str:
    try:
        subprocess.run(["open", "-a", app_name], check=True)
        return f"Opened {app_name} successfully."
    except subprocess.CalledProcessError as e:
        return f"Failed to open {app_name}: {e}"
    except Exception as e:
        return f"An error occurred while trying to open {app_name}: {e}"
    
