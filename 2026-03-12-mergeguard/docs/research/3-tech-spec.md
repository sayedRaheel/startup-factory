Here is the Technical Specification and Implementation Plan based on the MergeGuard PRD.

### 1. Technical Stack and Libraries
*   **Language:** Python 3.10+
*   **CLI Framework:** `typer` (for building a robust, easy-to-use CLI)
*   **Terminal Output:** `rich` (for beautiful CLI formatting and tables)
*   **Git Operations:** `GitPython` (for extracting PR diffs and repository context)
*   **Configuration:** `PyYAML` (for parsing `.mergeguard.yml`)
*   **LLM Integration:** `openai` (for the analysis engine, using GPT-4o or similar)
*   **Testing:** `pytest`
*   **Packaging:** `build`, `twine` (via `pyproject.toml`)

### 2. File Structure
```text
mergeguard/
├── mergeguard/
│   ├── __init__.py
│   ├── cli.py            # Typer CLI entrypoint
│   ├── config.py         # Loads and validates .mergeguard.yml
│   ├── git_utils.py      # Extracts diffs and context using GitPython
│   ├── llm_client.py     # Handles prompts and API calls to the LLM
│   └── analyzer.py       # Orchestrates the AST/LLM scoring logic
├── tests/
│   ├── __init__.py
│   └── test_analyzer.py
├── .mergeguard.yml       # Default configuration file
├── pyproject.toml        # Project metadata and dependencies
└── README.md
```

### 3. Step-by-Step Setup Commands
Run these commands in your terminal to bootstrap the project:

```bash
# 1. Create project directory and enter it
mkdir mergeguard
cd mergeguard

# 2. Set up virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install core dependencies
pip install typer rich PyYAML GitPython openai
pip install --upgrade pip
pip install pytest pytest-cov --user

# 4. Create directory structure
mkdir mergeguard tests

# 5. Create core files
touch mergeguard/__init__.py
touch mergeguard/cli.py
touch mergeguard/config.py
touch mergeguard/git_utils.py
touch mergeguard/llm_client.py
touch mergeguard/analyzer.py

# 6. Create test and config files
touch tests/__init__.py
touch tests/test_analyzer.py
touch .mergeguard.yml
touch pyproject.toml
touch README.md
```

### 4. Core Logic & Boilerplate Code

**`pyproject.toml`**
```toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "mergeguard"
version = "0.1.0"
description = "Defensive CLI tool to filter out unmergeable AI slop from PRs."
readme = "README.md"
requires-python = ">=3.10"
dependencies = [
    "typer>=0.9.0",
    "rich>=13.0.0",
    "PyYAML>=6.0",
    "GitPython>=3.1.0",
    "openai>=1.0.0"
]

[project.scripts]
mergeguard = "mergeguard.cli:app"
```

**`.mergeguard.yml`**
```yaml
min_authenticity_score: 75
fail_on_block: true
llm_model: "gpt-4o"
ignore_paths:
  - "tests/*"
  - "docs/*"
```

**`mergeguard/config.py`**
```python
import yaml
from pathlib import Path
import os

DEFAULT_CONFIG = {
    "min_authenticity_score": 70,
    "fail_on_block": True,
    "llm_model": "gpt-4o",
    "ignore_paths": []
}

def load_config() -> dict:
    config_path = Path(".mergeguard.yml")
    if not config_path.exists():
        return DEFAULT_CONFIG
    
    with open(config_path, "r") as f:
        user_config = yaml.safe_load(f) or {}
    
    return {**DEFAULT_CONFIG, **user_config}
```

**`mergeguard/git_utils.py`**
```python
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
```

**`mergeguard/llm_client.py`**
```python
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
```

**`mergeguard/analyzer.py`**
```python
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
```

**`mergeguard/cli.py`**
```python
import typer
from rich.console import Console
from rich.panel import Panel
import sys
from mergeguard.analyzer import run_analysis

app = typer.Typer(help="MergeGuard: Defend your repo against AI slop.")
console = Console()

@app.command()
def scan():
    """Scan current git diff for AI generation tells and architectural incoherence."""
    with console.status("[bold blue]Analyzing repository diff...[/bold blue]"):
        try:
            result = run_analysis()
        except Exception as e:
            console.print(f"[bold red]Error during analysis:[/bold red] {e}")
            raise typer.Exit(code=1)

    if result.get("status") == "skipped":
        console.print("[yellow]No changes detected to analyze.[/yellow]")
        return

    score = result["score"]
    passed = result["passed"]
    color = "green" if passed else "red"
    
    panel_content = (
        f"Authenticity Score: [bold {color}]{score}/100[/bold {color}]\n"
        f"Threshold: {result['threshold']}\n\n"
        f"[bold]Reasoning:[/bold]\n{result['reasoning']}"
    )
    
    console.print(Panel(panel_content, title="MergeGuard Analysis Result", border_style=color))

    if not passed and result["fail_on_block"]:
        console.print("[bold red]PR blocked: Authenticity score below threshold.[/bold red]")
        sys.exit(1)
    elif passed:
        console.print("[bold green]PR passed authenticity checks.[/bold green]")

if __name__ == "__main__":
    app()
```
