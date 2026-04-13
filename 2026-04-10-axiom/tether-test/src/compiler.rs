use ignore::WalkBuilder;
use std::fs;

pub fn compile_context() -> String {
    let mut context_bundle = String::new();
    let walker = WalkBuilder::new("./")
        .hidden(false)
        .build();

    for result in walker {
        match result {
            Ok(entry) => {
                if !entry.file_type().map_or(false, |ft| ft.is_file()) {
                    continue;
                }
                
                let path = entry.path();
                if let Ok(content) = fs::read_to_string(path) {
                    context_bundle.push_str(&format!("--- FILE: {} ---\n{}\n", path.display(), content));
                }
            }
            Err(err) => tracing::error!("Compiler error: {}", err),
        }
    }
    
    tracing::info!("Compiled {} bytes of context.", context_bundle.len());
    context_bundle
}
