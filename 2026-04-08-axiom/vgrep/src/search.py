import numpy as np
from colorama import Fore, Style, init

init(autoreset=True)

def execute_search(conn, query_embedding, prompt_mode, top_k):
    cursor = conn.cursor()
    cursor.execute("SELECT file_path, content, embedding FROM chunks")
    
    results = []
    for row in cursor.fetchall():
        path, content, embed_blob = row
        # Re-cast bytes to float32
        chunk_embedding = np.frombuffer(embed_blob, dtype=np.float32)
        # Compute Dot Product (equivalent to cosine similarity for normalized vectors)
        score = float(np.dot(query_embedding, chunk_embedding))
        results.append({"file_path": path, "content": content, "score": score})
        
    # Sort descending by score
    results.sort(key=lambda x: x["score"], reverse=True)
    top_results = results[:top_k]
    
    if prompt_mode:
        print_xml_prompt(top_results)
    else:
        print_cli(top_results)

def print_cli(results):
    for res in results:
        print(f"{Fore.GREEN}{Style.BRIGHT}--> {res['file_path']} (Score: {res['score']:.4f}){Style.RESET_ALL}")
        print(res['content'])
        print(f"{Style.DIM}---{Style.RESET_ALL}")

def print_xml_prompt(results):
    print("<context>")
    for res in results:
        print(f'  <file path="{res["file_path"]}">')
        print(f"<![CDATA[\n{res['content']}\n]]>")
        print("  </file>")
    print("</context>")
