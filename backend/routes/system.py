from fastapi import APIRouter
from pydantic import BaseModel
import psutil

system_router = APIRouter(prefix='/system',tags=['system'])

class SystemStats(BaseModel):
    cpu: float
    ram: float
    ram_used_gb: float
    ram_total_gb: float

@system_router.get('', response_model=SystemStats)
def get_system_stats():
    cpu = psutil.cpu_percent(interval=0.1)
    mem = psutil.virtual_memory()
    return SystemStats(
        cpu=round(cpu, 1),
        ram=round(mem.percent, 1),
        ram_used_gb=round(mem.used / 1e9, 1),
        ram_total_gb=round(mem.total / 1e9, 1),
    )
