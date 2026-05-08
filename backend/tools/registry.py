import importlib
import pkgutil
import os 


from tools.base import ToolPlugin, ToolResult

def _load() -> dict[str,ToolPlugin]:
    package_dir = os.path.dirname(__file__)
    for _,module_name, _ in pkgutil.iter_modules([package_dir]):
        if module_name in ("base","registry"):
            continue
        importlib.import_module(f".{module_name}", package=__package__)
    
    registry: dict[str,ToolPlugin] = {}
    for cls in ToolPlugin.__subclasses__():
        registry[cls.name] = cls()
    return registry



_registry: dict[str,ToolPlugin] | None = None

def get_registry() -> dict[str,ToolPlugin]:
    global _registry
    if _registry is None:
        _registry = _load()
    return _registry

def get_schemas() -> list[dict]:
    return [tool.schema() for tool in get_registry().values()]

def execute_tool(name: str, **kwargs) -> ToolResult:
    registry = get_registry()
    if name not in registry:
        return ToolResult(success=False, error=f"Unknown tool: {name}")
    return registry[name].execute(**kwargs)


