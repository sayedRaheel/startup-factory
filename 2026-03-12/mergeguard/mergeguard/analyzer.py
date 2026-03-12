from mergeguard.config import load_config
from mergeguard.git_utils import get_current_diff
from mergeguard.llm_client import evaluate_diff_authenticity

def run_analysis() -> dict:
    config = load_config()
    diff = get_current_diff()
    
    if not diff.strip():
        return {"status": "skipped", "message": "No changes detected."}
        
    result = evaluate_diff_authenticity(diff, config["llm_model"])
    
    score = result.get("score", 0)
    passed = score >= config["min_authenticity_score"]
    
    return {
        "status": "success",
        "passed": passed,
        "score": score,
        "threshold": config["min_authenticity_score"],
        "reasoning": result.get("reasoning", "No reasoning provided."),
        "fail_on_block": config["fail_on_block"]
    }
