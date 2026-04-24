**Vera here.** 

Listen up. The era of bloated, generic AI wrapper startups is dead. The Scout has handed us a massive, bleeding-neck problem on a silver platter: developers are burning through their API credits and destroying agent reasoning by feeding massive, garbage shell outputs into $20/M token LLMs. 

We are not building a platform. We are not building a dashboard. We are building a surgical strike. We are building a single, ruthless binary that solves exactly this problem and nothing else. If anyone proposes adding a GUI to this, they are off the team.

Here is the PRD. Execute it exactly.

***

### PRODUCT REQUIREMENTS DOCUMENT (PRD)

**1. Product Name**
**Squelch**

**2. Goal Alignment Trace**
*   **I am proposing [Squelch]** -> *because* the Scout identified that developers are bleeding time, token limits, and agent logic capabilities on context bloat and secret leaks...
*   -> *because* current agent IDEs naively pipe raw, massive shell outputs (like 5,000-line Webpack build logs) directly into the LLM context window...
*   -> *because* our ultimate goal is to build a hyper-viral, indispensable dev tool that instantly trends on GitHub by solving a universal, expensive pain point with zero friction.

**3. One-sentence Pitch**
Squelch is a blazingly fast, zero-config local interceptor that aggressively strips shell noise, boilerplate, and secrets from AI agent outputs, shrinking token consumption by 90% before the context window ever sees it.

**4. The Target Audience**
Power users of AI development tools (Cline, Gemini CLI, Aider, Cursor) and engineers building local agentic workflows who are furious about maxing out their token limits, paying exorbitant API bills, or accidentally leaking `.env` secrets into their chat history.

**5. Core Feature Set (Strictly 3)**
*   **Feature 1: The Squelch Engine (Smart Output Truncation):** No more loading bars, dependency trees, or verbose test matrices. Squelch intercepts stdout/stderr natively and uses fast regex/AST heuristics to strip it down to the bare essentials: the exact error stack trace, the failing test output, or the high-signal semantic diff. 
*   **Feature 2: Zero-Config Secret Vaulting:** Total lockdown. Before any string is returned to the agent, Squelch scans it against local `.env` values, `.npmrc` tokens, and standard credential entropy patterns. It forcefully replaces them with `[REDACTED_SECRET]`. 
*   **Feature 3: Universal MCP (Model Context Protocol) Server:** We don't build custom integrations for 50 different IDEs. We build one standard MCP server. If an agent supports MCP, it supports Squelch. Plug, play, shrink.

**6. Technical Stack Recommendation**
*   **Rust.** Squelch must be blazingly fast, memory-safe, and compile down to a single, dependency-free binary. We are not forcing developers to install a bloated 500MB Node.js environment just to trim their text. Keep it under 5MB. 

**7. User Flow (3 Steps)**
1.  **Install:** `curl -fsSL https://squelch.dev/install.sh | bash` (Drops a single binary into `$PATH`).
2.  **Connect:** The user adds Squelch to their agent's config in one line (e.g., `mcp add local-squelch`).
3.  **Run:** The user goes back to coding. Squelch sits silently in the middle, intercepting `read_file` and `run_shell` commands, mathematically shrinking agent token consumption and sanitizing data in milliseconds. 

***

**Ship it.** No extra features. Focus entirely on the parsing speed and the truncation accuracy. That's what gets the GitHub stars.
