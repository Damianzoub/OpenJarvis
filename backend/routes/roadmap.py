"""Roadmap progress-log endpoints.

Lets the phone dashboard fill in today's Progress Log entry, which is the one
thing the 8am scheduled agent cannot do for you.

Write safety rules, in order of importance:
  1. Only ever touch TODAY's dated block. Never another date.
  2. Only ever replace the `_(fill in)_` placeholders, plus fields the caller
     explicitly sends. "Next up" is written by the scheduled agent and is
     never modified here.
  3. Back up the file before every write, and write atomically via os.replace
     so a crash mid-write cannot truncate the log.
  4. If today's block does not exist yet, append a new one. Append only.
"""
import datetime as dt
import os
import re
import shutil

from dotenv import load_dotenv
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

load_dotenv()

roadmap_router = APIRouter(prefix="/roadmap", tags=["roadmap"])

DEVICE_TOKEN = os.getenv("DEVICE_TOKEN", "dev")
DEFAULT_LOG = os.path.expanduser(
    "~/Documents/Obsidian Vault/01_Projects/AI Career Transition/Progress Log.md"
)
LOG_PATH = os.path.expanduser(os.getenv("ROADMAP_LOG_PATH", DEFAULT_LOG))

PLACEHOLDER = "_(fill in)_"
DATE_H2 = re.compile(r"^##\s+(\d{4}-\d{2}-\d{2})\s*$", re.M)
FIELDS = {
    "learned": "Learned today",
    "hours": "Hours spent",
    "blockers": "Blockers",
}


class LogEntry(BaseModel):
    learned: str | None = Field(None, max_length=2000)
    hours: str | None = Field(None, max_length=40)
    blockers: str | None = Field(None, max_length=2000)


def _auth(token: str | None) -> None:
    if token != DEVICE_TOKEN:
        raise HTTPException(status_code=401, detail="bad or missing X-Device-Token")


def _read() -> str:
    if not os.path.exists(LOG_PATH):
        raise HTTPException(status_code=404, detail=f"log not found: {LOG_PATH}")
    with open(LOG_PATH, encoding="utf-8") as f:
        return f.read()


def _write(text: str) -> str:
    """Back up, then replace atomically. Returns the backup path."""
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = f"{LOG_PATH}.bak-{stamp}"
    shutil.copy2(LOG_PATH, backup)
    tmp = f"{LOG_PATH}.tmp-{stamp}"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, LOG_PATH)
    return backup


def _block_bounds(text: str, date: str):
    """-> (start, end) char offsets of the body of `date`'s block, or None."""
    hits = list(DATE_H2.finditer(text))
    for i, m in enumerate(hits):
        if m.group(1) == date:
            end = hits[i + 1].start() if i + 1 < len(hits) else len(text)
            return m.end(), end
    return None


def _set_field(block: str, label: str, value: str) -> tuple[str, bool]:
    """Replace one `- **Label:** ...` line's value. Returns (block, changed)."""
    pat = re.compile(r"(^-\s*\*\*%s:?\*\*\s*)(.*)$" % re.escape(label), re.M)
    m = pat.search(block)
    if not m:
        return block, False
    if m.group(2).strip() == value.strip():
        return block, False
    return pat.sub(lambda mm: mm.group(1) + value, block, count=1), True


def _parse_block(block: str) -> dict:
    out = {}
    for key, label in FIELDS.items():
        m = re.search(r"^-\s*\*\*%s:?\*\*\s*(.*)$" % re.escape(label), block, re.M)
        v = (m.group(1).strip() if m else "")
        out[key] = "" if v == PLACEHOLDER else v
    m = re.search(r"^-\s*\*\*Next up:?\*\*\s*(.*)$", block, re.M)
    out["next_up"] = m.group(1).strip() if m else ""
    return out


@roadmap_router.get("/today")
def get_today():
    text = _read()
    today = dt.date.today().isoformat()
    b = _block_bounds(text, today)
    if not b:
        return {"date": today, "exists": False}
    entry = _parse_block(text[b[0]:b[1]])
    entry.update({"date": today, "exists": True,
                  "filled": bool(entry["learned"] or entry["hours"])})
    return entry


@roadmap_router.post("/log")
def fill_today(entry: LogEntry, x_device_token: str | None = Header(None)):
    _auth(x_device_token)

    sent = {k: v for k, v in entry.model_dump().items() if v is not None and v.strip()}
    if not sent:
        raise HTTPException(status_code=400, detail="nothing to write")

    text = _read()
    today = dt.date.today().isoformat()
    bounds = _block_bounds(text, today)
    created = False

    if bounds:
        start, end = bounds
        block = text[start:end]
        changed = []
        for key, value in sent.items():
            block, did = _set_field(block, FIELDS[key], value)
            if did:
                changed.append(key)
        if not changed:
            return {"ok": True, "date": today, "written": [], "created": False,
                    "note": "already matched what you sent"}
        new_text = text[:start] + block + text[end:]
    else:
        # No block for today - the agent hasn't run. Append one; never rewrite.
        created = True
        changed = list(sent)
        lines = [f"\n## {today}"]
        for key, label in FIELDS.items():
            lines.append(f"- **{label}:** {sent.get(key, PLACEHOLDER)}")
        lines.append(f"- **Next up:** {PLACEHOLDER}")
        new_text = text.rstrip("\n") + "\n" + "\n".join(lines) + "\n\n---\n"

    backup = _write(new_text)
    return {"ok": True, "date": today, "written": changed,
            "created": created, "backup": os.path.basename(backup)}
