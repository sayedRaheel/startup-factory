import os
from openai import OpenAI

def evaluate_diff_authenticity(diff: str, model: str) -> dict:
    """
    Calls the LLM to evaluate the diff for AI slop and architectural incoherence.
    Returns a dictionary with 'score' and 'reasoning'.
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set.")
    
    client = OpenAI(api_key=api_key)
    
    system_prompt = (
        "You are an expert Principal Software Engineer. Analyze the provided git diff. "
        "Score it from 0 to 100 on 'Authenticity & Coherence'. "
        "Look for AI-generation tells (e.g., unnecessary verbosity, soulless logic, "
        "architectural leaps that don't fit existing context). "
        "Output ONLY JSON with two keys: 'score' (integer) and 'reasoning' (string)."
    )
    
    # In a full implementation, you'd use structured outputs/JSON mode.
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Here is the diff:\n{diff}"}
        ],
        response_format={"type": "json_object"}
    )
    
    import json
    return json.loads(response.choices[0].message.content)
