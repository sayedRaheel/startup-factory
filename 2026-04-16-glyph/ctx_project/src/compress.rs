use rusqlite::Connection;
use crate::git;

pub fn generate_feed(conn: &Connection, project_path: &str) -> String {
    let mut stmt = match conn.prepare(
        "SELECT event_type, payload, timestamp 
         FROM context_events 
         WHERE project_path = ?1 
         ORDER BY timestamp DESC LIMIT 50"
    ) {
        Ok(stmt) => stmt,
        Err(_) => return String::from("<ctx_session_state>\nError reading state.\n</ctx_session_state>\n"),
    };

    let event_iter = stmt.query_map([project_path], |row| {
        let e_type: String = row.get(0)?;
        let payload: String = row.get(1)?;
        let time: String = row.get(2)?;
        Ok((e_type, payload, time))
    });

    let mut output = String::new();
    output.push_str("<ctx_session_state>\n");
    output.push_str("Below is the immediate working context of the developer. Use this to maintain session continuity.\n\n");
    
    if let Ok(iter) = event_iter {
        for event in iter.flatten() {
            let (e_type, payload, time) = event;
            // Token-aware truncation
            let truncated = if payload.len() > 500 {
                format!("{}... (truncated)", &payload[0..500])
            } else {
                payload
            };
            output.push_str(&format!("[{}] {}: {}\n", time, e_type, truncated));
        }
    }
    
    // Append git.rs output here (current branch, recent diffs)
    let diff = git::get_recent_diff();
    if !diff.trim().is_empty() {
        output.push_str("\n[recent_git_diff]\n");
        let truncated_diff = if diff.len() > 2000 {
            format!("{}... (truncated)", &diff[0..2000])
        } else {
            diff
        };
        output.push_str(&truncated_diff);
        output.push_str("\n");
    }
    
    output.push_str("\n</ctx_session_state>\n");
    
    output
}
