# Tauri Frontend Auto-start & Shortcut Design

**Date:** 2026-05-08

---

## Overview

Auto-start the Tauri frontend on login (mirroring the existing uvicorn LaunchAgent), provide a terminal alias and a global macOS keyboard shortcut for reopening it after it's closed, and add a confirm dialog inside the app to prevent accidental closes.

---

## Components

### 1. LaunchAgent — `com.openjarvis.frontend.plist`

File: `~/Library/LaunchAgents/com.openjarvis.frontend.plist`

- Runs `npm run tauri dev` from `/Users/damianoszoumpos/OpenJarvis/frontend`
- `RunAtLoad: true` — starts on login
- `KeepAlive: false` — stays closed when the user deliberately quits
- Logs stdout to `/tmp/jarvis-frontend.log`, stderr to `/tmp/jarvis-frontend-error.log`
- Must use the absolute path to `npm` (e.g. `/opt/homebrew/bin/npm`) to avoid PATH issues in launchd

### 2. Reopen Script — `~/bin/jarvis`

A small shell script that backgrounds the Tauri dev process:

```bash
#!/bin/bash
cd /Users/damianoszoumpos/OpenJarvis/frontend
nohup npm run tauri dev >> /tmp/jarvis-frontend.log 2>> /tmp/jarvis-frontend-error.log &
```

- Made executable (`chmod +x ~/bin/jarvis`)
- `~/bin` added to `PATH` in `.zshrc` if not already present
- Shared entry point used by both the alias and the Automator action

### 3. Terminal Alias

Added to `~/.zshrc`:

```zsh
alias jarvis="~/bin/jarvis"
```

Typing `jarvis` in any terminal reopens the Tauri window.

### 4. Automator Quick Action + Keyboard Shortcut

- Automator Quick Action (Service), receives no input, works in any application
- Action: Run Shell Script → calls `~/bin/jarvis`
- Saved as `Jarvis.workflow` in `~/Library/Services/`
- Keyboard shortcut assigned in: System Settings → Keyboard → Keyboard Shortcuts → Services → General → Jarvis

### 5. Confirm Dialog on Close — `frontend/src/main.ts`

Intercepts the Tauri `close-requested` event using the Tauri v2 window API:

```typescript
import { getCurrentWindow } from '@tauri-apps/api/window';

const appWindow = getCurrentWindow();
appWindow.onCloseRequested(async (event) => {
  event.preventDefault();
  const confirmed = confirm('Close Jarvis?');
  if (confirmed) {
    await appWindow.destroy();
  }
});
```

- Uses the browser `confirm()` dialog (no extra Tauri plugin needed)
- Cancel leaves the app open; Confirm destroys the window and exits

---

## Data Flow

```
Login
  └─▶ launchd reads com.openjarvis.frontend.plist
        └─▶ npm run tauri dev → Tauri window opens

User closes window
  └─▶ close-requested event fires
        ├─▶ Cancel → window stays open
        └─▶ Confirm → appWindow.destroy() → process exits
                          launchd sees exit, KeepAlive=false → does NOT restart

User wants to reopen
  ├─▶ Terminal: types `jarvis` → ~/bin/jarvis → Tauri starts in background
  └─▶ Keyboard shortcut → Automator Quick Action → ~/bin/jarvis → Tauri starts
```

---

## Out of Scope

- Production build (`npm run tauri build`) — this targets the dev workflow only
- KeepAlive restart behavior — intentionally excluded per user preference
- Third-party shortcut tools (Hammerspoon, BTT) — using macOS Automator only
