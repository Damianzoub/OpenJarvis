from datetime import datetime

from guardrails import Guard, Validator, register_validator
from guardrails.errors import ValidationError
from guardrails.validator_base import FailResult, PassResult
from langchain.tools import tool

from memory.reminders_store import add_reminder as _add_reminder
from memory.reminders_store import list_reminders as _list_reminders
from memory.reminders_store import complete_reminder as _complete_reminder


@register_validator(name="valid-reminder-datetime", data_type="string")
class ValidReminderDatetime(Validator):
    def validate(self, value, metadata):
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return FailResult(error_message=f"'{value}' is not a valid ISO datetime.")
        return PassResult()


_guard = Guard().use(ValidReminderDatetime())


@tool(description="Add a reminder, with an optional ISO datetime it's due.")
async def add_reminder(text: str, due: str | None = None) -> str:
    if due:
        try:
            _guard.validate(due)
        except ValidationError as e:
            return str(e)
    reminder = _add_reminder(text, due)
    return f"Reminder added: {reminder['text']}" + (f" (due {reminder['due']})" if reminder['due'] else "")


@tool(description="List reminders. Call this when the user asks what their reminders or to-dos are.")
async def list_reminders(include_done: bool = False) -> str:
    reminders = _list_reminders(include_done)
    if not reminders:
        return "No reminders."
    lines = []
    for r in reminders:
        status = "[done] " if r["done"] else ""
        due = f" (due {r['due']})" if r["due"] else ""
        lines.append(f"{status}{r['text']}{due} [id={r['id']}]")
    return "\n".join(lines)


@tool(description="Mark a reminder as complete, given its id.")
async def complete_reminder(reminder_id: str) -> str:
    reminder = _complete_reminder(reminder_id)
    if not reminder:
        return f"No reminder found with id {reminder_id}."
    return f"Marked complete: {reminder['text']}"
