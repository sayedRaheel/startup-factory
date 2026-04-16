use notify::{Watcher, RecursiveMode, Event};
use std::sync::mpsc::channel;
use std::env;
use crate::db::{init_db, insert_event};
use daemonize::Daemonize;
use std::fs::File;

pub fn start_daemon() {
    let stdout = File::create("/tmp/ctx.out").unwrap();
    let stderr = File::create("/tmp/ctx.err").unwrap();

    let daemonize = Daemonize::new()
        .pid_file("/tmp/ctx.pid")
        .chown_pid_file(true)
        .working_directory(".") 
        .stdout(stdout)
        .stderr(stderr);

    match daemonize.start() {
        Ok(_) => run_watch_loop(),
        Err(e) => eprintln!("Error starting daemon: {}", e),
    }
}

fn run_watch_loop() {
    let current_dir = env::current_dir().unwrap();
    let dir_str = current_dir.to_str().unwrap().to_string();
    
    let conn = init_db().expect("DB init failed");
    let (tx, rx) = channel();

    let mut watcher = notify::recommended_watcher(tx).unwrap();
    watcher.watch(&current_dir, RecursiveMode::Recursive).unwrap();

    // Event loop
    for res in rx {
        match res {
            Ok(Event { kind, paths, .. }) => {
                if kind.is_modify() || kind.is_create() {
                    // Safe unwrap using if let to prevent daemon panics
                    if let Some(path) = paths.first().and_then(|p| p.to_str()) {
                        // Ignore git internals and node_modules
                        if !path.contains(".git") && !path.contains("node_modules") {
                            let _ = insert_event(&conn, &dir_str, "file_change", path);
                        }
                    }
                }
            },
            Err(e) => eprintln!("watch error: {:?}", e),
        }
    }
}
