use anyhow::Result;
use std::path::PathBuf;

/// Analyzes the intent and the local filesystem to determine exactly which
/// files the AI is allowed to modify.
pub fn build_blast_radius(intent: &str) -> Result<Vec<PathBuf>> {
    // MVP implementation: Extract literal filenames from the intent string.
    // In v2, this integrates tree-sitter to find imported dependencies.
    
    let mut allowed_files = Vec::new();
    let words: Vec<&str> = intent.split_whitespace().collect();
    
    for word in words {
        // Naive heuristic: if it has a dot and no slashes, it's likely a target file mentioned
        if word.contains('.') && !word.ends_with('.') {
            let path = PathBuf::from(word.trim_matches(|c| c == '\'' || c == '"'));
            if path.exists() || path.extension().is_some() {
                // Store absolute paths for accurate bouncer enforcement
                let abs_path = std::env::current_dir()?.join(&path);
                allowed_files.push(abs_path);
            }
        }
    }

    if allowed_files.is_empty() {
        anyhow::bail!("Could not detect any target files in the intent. Be specific (e.g., 'Fix Header.tsx').");
    }

    Ok(allowed_files)
}
