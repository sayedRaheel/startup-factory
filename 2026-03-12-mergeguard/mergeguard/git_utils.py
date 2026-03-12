from git import Repo
import os

def get_current_diff() -> str:
    """Gets the diff of the current working directory against HEAD."""
    try:
        repo = Repo(os.getcwd())
        # For a real PR, this would diff against the base branch (e.g., origin/main)
        # Using working tree diff for local CLI testing
        diff = repo.git.diff("HEAD")
        return diff
    except Exception as e:
        return f"Error reading git diff: {e}"
