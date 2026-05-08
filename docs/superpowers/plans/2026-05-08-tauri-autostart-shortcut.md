# Tauri Frontend Auto-start & Shortcut Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Auto-start the Tauri frontend on login, provide a terminal alias and global keyboard shortcut to reopen it after closing, and add a confirm dialog to prevent accidental closes.

**Architecture:** A LaunchAgent starts `npm run tauri dev` on login with `KeepAlive: false` (stays closed when deliberately quit). A shared shell script `~/bin/jarvis` is the single entry point used by both a zsh alias and a macOS Automator Quick Action (assigned a global keyboard shortcut in System Settings). The Tauri window intercepts the `close-requested` event and shows a native confirm dialog before exiting.

**Tech Stack:** macOS launchd plist, zsh, Automator Quick Action (`.workflow` bundle), Tauri v2 `@tauri-apps/api/window`

---

### Task 1: LaunchAgent for the Tauri frontend

**Files:**
- Create: `~/Library/LaunchAgents/com.openjarvis.frontend.plist` (outside repo — system file)

- [ ] **Step 1: Verify absolute paths**

```bash
which npm && ls ~/.cargo/bin/cargo 2>/dev/null && echo "cargo ok" || echo "cargo not found"
```
Expected: `/opt/homebrew/bin/npm` and `cargo ok`. If cargo is not found, locate it with `find ~ -name cargo -type f 2>/dev/null | head -3` and use that path in the plist below.

- [ ] **Step 2: Create the plist**

Write the following to `~/Library/LaunchAgents/com.openjarvis.frontend.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.openjarvis.frontend</string>

    <key>ProgramArguments</key>
    <array>
        <string>/opt/homebrew/bin/npm</string>
        <string>run</string>
        <string>tauri</string>
        <string>dev</string>
    </array>

    <key>WorkingDirectory</key>
    <string>/Users/damianoszoumpos/OpenJarvis/frontend</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>HOME</key>
        <string>/Users/damianoszoumpos</string>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:/Users/damianoszoumpos/.cargo/bin</string>
    </dict>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <false/>

    <key>StandardOutPath</key>
    <string>/tmp/jarvis-frontend.log</string>

    <key>StandardErrorPath</key>
    <string>/tmp/jarvis-frontend-error.log</string>
</dict>
</plist>
```

- [ ] **Step 3: Load the LaunchAgent**

```bash
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.openjarvis.frontend.plist
```
Expected: no output (success). If you see `service already registered`, unload first then re-load:
```bash
launchctl bootout gui/$(id -u)/com.openjarvis.frontend
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.openjarvis.frontend.plist
```

- [ ] **Step 4: Verify it started**

```bash
launchctl list | grep openjarvis.frontend && echo "--- last 20 log lines ---" && tail -20 /tmp/jarvis-frontend.log
```
Expected: the service appears in `launchctl list` and the log shows npm/Tauri startup output. The Tauri window appears once Rust compilation finishes — up to 5 minutes on first run, ~10 seconds on subsequent runs.

---

### Task 2: Reopen script

**Files:**
- Create: `~/bin/jarvis`

- [ ] **Step 1: Create the script**

```bash
mkdir -p ~/bin
```

Write the following to `~/bin/jarvis`:

```bash
#!/bin/zsh
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$HOME/.cargo/bin:$PATH"
cd /Users/damianoszoumpos/OpenJarvis/frontend
nohup npm run tauri dev >> /tmp/jarvis-frontend.log 2>> /tmp/jarvis-frontend-error.log &
echo "Jarvis starting — tail /tmp/jarvis-frontend.log to follow"
```

- [ ] **Step 2: Make it executable**

```bash
chmod +x ~/bin/jarvis
```

- [ ] **Step 3: Test the script**

Kill any running Tauri dev process first (`pkill -f "tauri dev"` if needed), then:
```bash
~/bin/jarvis
```
Expected: prints `Jarvis starting — tail /tmp/jarvis-frontend.log to follow` immediately, returns to prompt, and the Tauri window appears after compilation.

---

### Task 3: Terminal alias

**Files:**
- Modify: `~/.zshrc`

- [ ] **Step 1: Check if ~/bin is already in PATH**

```bash
grep -E '\$HOME/bin|~/bin' ~/.zshrc
```
If a line already exports `~/bin` to PATH, skip the PATH export in the next step and only add the alias.

- [ ] **Step 2: Add PATH entry and alias**

Append to `~/.zshrc`:
```zsh
export PATH="$HOME/bin:$PATH"
alias jarvis="$HOME/bin/jarvis"
```
(Omit the `export PATH` line if it was already present from step 1.)

- [ ] **Step 3: Reload and verify**

```bash
source ~/.zshrc && type jarvis
```
Expected: `jarvis is an alias for /Users/damianoszoumpos/bin/jarvis`

Then run `jarvis` and confirm the window appears.

---

### Task 4: Automator Quick Action + keyboard shortcut

**Files:**
- Create: `~/Library/Services/Jarvis.workflow/Contents/document.wflow`

- [ ] **Step 1: Create the workflow directory**

```bash
mkdir -p ~/Library/Services/Jarvis.workflow/Contents
```

- [ ] **Step 2: Generate the workflow plist**

Run this Python script — it generates proper UUIDs and writes the workflow file:

```bash
python3 << 'EOF'
import uuid, os

action_uuid = str(uuid.uuid4()).upper()
input_uuid  = str(uuid.uuid4()).upper()
output_uuid = str(uuid.uuid4()).upper()
home        = os.path.expanduser("~")

plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
\t<key>AMApplicationBuild</key>
\t<string>521</string>
\t<key>AMApplicationVersion</key>
\t<string>2.10</string>
\t<key>AMDocumentSpecificationVersion</key>
\t<string>0.9</string>
\t<key>actions</key>
\t<array>
\t\t<dict>
\t\t\t<key>action</key>
\t\t\t<dict>
\t\t\t\t<key>AMAccepts</key>
\t\t\t\t<dict>
\t\t\t\t\t<key>Container</key>
\t\t\t\t\t<string>List</string>
\t\t\t\t\t<key>Optional</key>
\t\t\t\t\t<true/>
\t\t\t\t\t<key>Types</key>
\t\t\t\t\t<array>
\t\t\t\t\t\t<string>com.apple.cocoa.string</string>
\t\t\t\t\t</array>
\t\t\t\t</dict>
\t\t\t\t<key>AMActionVersion</key>
\t\t\t\t<string>2.0.3</string>
\t\t\t\t<key>AMApplication</key>
\t\t\t\t<array>
\t\t\t\t\t<string>Automator</string>
\t\t\t\t</array>
\t\t\t\t<key>AMParameterProperties</key>
\t\t\t\t<dict>
\t\t\t\t\t<key>COMMAND_STRING</key>
\t\t\t\t\t<dict/>
\t\t\t\t\t<key>shell</key>
\t\t\t\t\t<dict/>
\t\t\t\t</dict>
\t\t\t\t<key>AMProvides</key>
\t\t\t\t<dict>
\t\t\t\t\t<key>Container</key>
\t\t\t\t\t<string>List</string>
\t\t\t\t\t<key>Types</key>
\t\t\t\t\t<array>
\t\t\t\t\t\t<string>com.apple.cocoa.string</string>
\t\t\t\t\t</array>
\t\t\t\t</dict>
\t\t\t\t<key>ActionBundlePath</key>
\t\t\t\t<string>/System/Library/Automator/Run Shell Script.action</string>
\t\t\t\t<key>ActionName</key>
\t\t\t\t<string>Run Shell Script</string>
\t\t\t\t<key>ActionParameters</key>
\t\t\t\t<dict>
\t\t\t\t\t<key>COMMAND_STRING</key>
\t\t\t\t\t<string>{home}/bin/jarvis</string>
\t\t\t\t\t<key>CheckedForUserDefaultShell</key>
\t\t\t\t\t<true/>
\t\t\t\t\t<key>inputMethod</key>
\t\t\t\t\t<integer>0</integer>
\t\t\t\t\t<key>shell</key>
\t\t\t\t\t<string>/bin/zsh</string>
\t\t\t\t\t<key>source</key>
\t\t\t\t\t<string></string>
\t\t\t\t</dict>
\t\t\t\t<key>BundleIdentifier</key>
\t\t\t\t<string>com.apple.RunShellScript</string>
\t\t\t\t<key>CFBundleVersion</key>
\t\t\t\t<string>2.0.3</string>
\t\t\t\t<key>CanShowSelectedItemsWhenRun</key>
\t\t\t\t<false/>
\t\t\t\t<key>CanShowWhenRun</key>
\t\t\t\t<true/>
\t\t\t\t<key>Category</key>
\t\t\t\t<array>
\t\t\t\t\t<string>AMCategoryUtilities</string>
\t\t\t\t</array>
\t\t\t\t<key>Class Name</key>
\t\t\t\t<string>RunShellScriptAction</string>
\t\t\t\t<key>InputUUID</key>
\t\t\t\t<string>{input_uuid}</string>
\t\t\t\t<key>Keywords</key>
\t\t\t\t<array>
\t\t\t\t\t<string>Shell</string>
\t\t\t\t\t<string>Script</string>
\t\t\t\t\t<string>Run</string>
\t\t\t\t</array>
\t\t\t\t<key>OutputUUID</key>
\t\t\t\t<string>{output_uuid}</string>
\t\t\t\t<key>UUID</key>
\t\t\t\t<string>{action_uuid}</string>
\t\t\t\t<key>UnlocalizedApplications</key>
\t\t\t\t<array>
\t\t\t\t\t<string>Automator</string>
\t\t\t\t</array>
\t\t\t\t<key>arguments</key>
\t\t\t\t<dict>
\t\t\t\t\t<key>0</key>
\t\t\t\t\t<dict>
\t\t\t\t\t\t<key>default value</key>
\t\t\t\t\t\t<integer>0</integer>
\t\t\t\t\t\t<key>name</key>
\t\t\t\t\t\t<string>inputMethod</string>
\t\t\t\t\t\t<key>required</key>
\t\t\t\t\t\t<string>0</string>
\t\t\t\t\t\t<key>type</key>
\t\t\t\t\t\t<string>0</string>
\t\t\t\t\t\t<key>uuid</key>
\t\t\t\t\t\t<string>0</string>
\t\t\t\t\t</dict>
\t\t\t\t\t<key>1</key>
\t\t\t\t\t<dict>
\t\t\t\t\t\t<key>default value</key>
\t\t\t\t\t\t<string></string>
\t\t\t\t\t\t<key>name</key>
\t\t\t\t\t\t<string>COMMAND_STRING</string>
\t\t\t\t\t\t<key>required</key>
\t\t\t\t\t\t<string>0</string>
\t\t\t\t\t\t<key>type</key>
\t\t\t\t\t\t<string>0</string>
\t\t\t\t\t\t<key>uuid</key>
\t\t\t\t\t\t<string>1</string>
\t\t\t\t\t</dict>
\t\t\t\t\t<key>2</key>
\t\t\t\t\t<dict>
\t\t\t\t\t\t<key>default value</key>
\t\t\t\t\t\t<string>/bin/sh</string>
\t\t\t\t\t\t<key>name</key>
\t\t\t\t\t\t<string>shell</string>
\t\t\t\t\t\t<key>required</key>
\t\t\t\t\t\t<string>0</string>
\t\t\t\t\t\t<key>type</key>
\t\t\t\t\t\t<string>0</string>
\t\t\t\t\t\t<key>uuid</key>
\t\t\t\t\t\t<string>2</string>
\t\t\t\t\t</dict>
\t\t\t\t</dict>
\t\t\t\t<key>isViewVisible</key>
\t\t\t\t<true/>
\t\t\t\t<key>location</key>
\t\t\t\t<string>309.000000:253.000000</string>
\t\t\t\t<key>nibPath</key>
\t\t\t\t<string>/System/Library/Automator/Run Shell Script.action/Contents/Resources/English.lproj/main.nib</string>
\t\t\t</dict>
\t\t\t<key>isViewVisible</key>
\t\t\t<true/>
\t\t</dict>
\t</array>
\t<key>connectors</key>
\t<dict/>
\t<key>workflowMetaData</key>
\t<dict>
\t\t<key>workflowTypeIdentifier</key>
\t\t<string>com.apple.Automator.servicesMenu</string>
\t</dict>
</dict>
</plist>"""

path = os.path.expanduser("~/Library/Services/Jarvis.workflow/Contents/document.wflow")
with open(path, "w") as f:
    f.write(plist)
print(f"Written to {path}")
EOF
```
Expected: `Written to /Users/damianoszoumpos/Library/Services/Jarvis.workflow/Contents/document.wflow`

- [ ] **Step 3: Register the service with macOS**

```bash
/System/Library/CoreServices/pbs -update
```
Expected: no output. If the command fails or produces an error, log out and back in — macOS will pick up the new workflow automatically on next login.

- [ ] **Step 4: Assign keyboard shortcut (UI step)**

1. Open **System Settings** → **Keyboard** → **Keyboard Shortcuts**
2. Click **Services** in the left sidebar
3. Scroll to the **General** section
4. Find **Jarvis** in the list
5. Click the area to the right of **Jarvis**, then press your desired key combo (e.g. `⌥⌘J`)
6. Close System Settings

- [ ] **Step 5: Test the shortcut**

Press your chosen shortcut from any app (e.g. Finder, Safari). The Tauri window should launch (or reappear after a compilation pass).

---

### Task 5: Confirm dialog on window close

**Files:**
- Modify: [frontend/src/main.ts](frontend/src/main.ts) (append to end of file)

- [ ] **Step 1: Append the close guard to main.ts**

Add this block at the very end of `frontend/src/main.ts`:

```typescript
// ── Window close guard ─────────────────────────────────────
(async () => {
  const { getCurrentWindow } = await import("@tauri-apps/api/window");
  const appWindow = getCurrentWindow();
  await appWindow.onCloseRequested(async (event) => {
    event.preventDefault();
    const confirmed = confirm("Close Jarvis?");
    if (confirmed) {
      await appWindow.destroy();
    }
  });
})();
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd /Users/damianoszoumpos/OpenJarvis/frontend && npx tsc --noEmit
```
Expected: no errors or warnings.

- [ ] **Step 3: Test manually**

Run `npm run tauri dev` (or use your new `jarvis` alias). Once the window is open, press `Cmd+Q`. Expected: a native confirm dialog appears with the message "Close Jarvis?" and OK/Cancel buttons. Cancel keeps the window open; OK closes it cleanly.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/main.ts
git commit -m "feat: add close-confirm dialog to Tauri window"
```
