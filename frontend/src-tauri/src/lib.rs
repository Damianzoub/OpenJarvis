// Learn more about Tauri commands at https://tauri.app/develop/calling-rust/
use tauri::menu::{Menu, MenuItemBuilder, SubmenuBuilder};
use tauri::Emitter;

#[cfg(desktop)]
use tauri::Manager;
#[cfg(desktop)]
use tauri_plugin_global_shortcut::ShortcutState;

#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! You've been greeted from Rust!", name)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let mut builder = tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_dialog::init());

    // Global hotkey to summon/dismiss the HUD from anywhere — desktop only,
    // the plugin doesn't support iOS/Android.
    #[cfg(desktop)]
    {
        builder = builder.plugin(
            tauri_plugin_global_shortcut::Builder::new()
                .with_shortcut("CmdOrCtrl+Shift+J")
                .expect("invalid global shortcut accelerator")
                .with_handler(|app, _shortcut, event| {
                    if event.state() == ShortcutState::Pressed {
                        if let Some(window) = app.get_webview_window("main") {
                            let visible = window.is_visible().unwrap_or(false);
                            if visible {
                                let _ = window.hide();
                            } else {
                                let _ = window.show();
                                let _ = window.set_focus();
                            }
                        }
                    }
                })
                .build(),
        );
    }

    builder
        .invoke_handler(tauri::generate_handler![greet])
        .menu(|app| {
            let menu = Menu::default(app)?;

            let toggle_mic = MenuItemBuilder::with_id("toggle-mic", "Toggle Mic")
                .accelerator("CmdOrCtrl+M")
                .build(app)?;
            let clear = MenuItemBuilder::with_id("clear-conversation", "Clear Conversation")
                .accelerator("CmdOrCtrl+L")
                .build(app)?;

            let jarvis_menu = SubmenuBuilder::new(app, "Jarvis")
                .item(&toggle_mic)
                .item(&clear)
                .build()?;

            menu.append(&jarvis_menu)?;
            Ok(menu)
        })
        .on_menu_event(|app, event| {
            if event.id() == "toggle-mic" {
                let _ = app.emit("menu-toggle-mic", ());
            } else if event.id() == "clear-conversation" {
                let _ = app.emit("menu-clear-conversation", ());
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
