from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class ToolResult:
    success:bool
    output:str=""
    error: str=""

class ToolPlugin(ABC):
    name:str
    description:str

    @abstractmethod
    def schema(self) -> dict:
        pass

    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        pass 
    