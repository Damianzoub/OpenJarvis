// Learn more about Tauri commands at https://tauri.app/develop/calling-rust/
use tauri::menu::{Menu, MenuItemBuilder, SubmenuBuilder};
use tauri::Emitter;

#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! You've been greeted from Rust!", name)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
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
