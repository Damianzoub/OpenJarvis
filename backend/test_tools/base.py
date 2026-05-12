from tools.base import ToolPlugin, ToolResult

ok = ToolResult(success=True, output="Tool executed successfully.")
fail = ToolResult(success=False, error="Tool execution failed.")

assert ok.success is True
assert ok.output == "Tool executed successfully."
assert fail.success is False
assert fail.error == "Tool execution failed."
print("Base tool test passed.")


class IncompleteTool(ToolPlugin):
    name = "incomplete"
    description = "A tool that is not fully implemented."

    def schema(self) -> dict:
        return {"type": "object", "properties": {}}

    def execute(self, **kwargs) -> ToolResult:
        return ok

try:
    IncompleteTool()
    print("Tool instantiation test passed.")
except TypeError as e:
    print(f"Tool instantiation failed: {e}")

