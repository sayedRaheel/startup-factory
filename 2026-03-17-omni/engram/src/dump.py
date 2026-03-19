import os
from src.db import DB
from src.daemon import DB_PATH

def generate_dump(out_path):
    if not os.path.exists(DB_PATH):
        print("No database found. Start the daemon first.")
        return

    db = DB(DB_PATH)
    events = db.get_all_events()
    
    output = ["# Engram Context Dump\n", "## File Events\n"]
    
    for e in events:
        output.append(f"### {e['file_path']} ({e['event_type']} at {e['timestamp']})")
        if e['event_type'] != 'deleted' and e['compressed_content']:
            output.append("```")
            output.append(e['compressed_content'])
            output.append("```\n")
        else:
            output.append("*Content deleted or unreadable*\n")
            
    final_text = "\n".join(output)
    
    if out_path:
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(final_text)
        print(f"Dump written to {out_path}")
    else:
        print(final_text)
