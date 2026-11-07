from fastapi import APIRouter

from memory.reminders_store import get_due_reminders

reminders_router = APIRouter(prefix='/reminders', tags=['reminders'])


@reminders_router.get('/due')
def due_reminders():
    return get_due_reminders()
