Listen to me. I don’t care about your multi-year enterprise roadmap. I care about what ships this weekend, solves a bleeding-neck problem, and hits 10k stars on GitHub by Tuesday. 

The scout is entirely correct. The local AI ecosystem is a fragmented, duct-taped disaster. Developers are spending 80% of their time writing fragile glue scripts instead of shipping code. We are not building another bloated AI "framework" with a 50-page documentation site. Frameworks are a disease. 

We are building a UNIX pipe for autonomous agents. A simple, ruthless orchestration layer. Here is the PRD. Execute it exactly as written.

***

# PRODUCT REQUIREMENTS DOCUMENT

### 1. Product Name
**`Mesh`** (Command: `mesh`)

### 2. Goal Alignment Trace
**I am proposing `Mesh`** 
-> **because** the Scout identified that developers are wasting massive amounts of time writing brittle glue code to wire up fragmented, bring-your-own-LLM tools 
-> **because** there is a massive market shift away from bloated corporate AI (Copilot) toward local, autonomous AI workflows that currently lack standard orchestration 
-> **because** our ultimate goal is to build a viral, indispensable infrastructure tool that captures the explosive GitHub momentum around local AI agents.

### 3. One-Sentence Pitch
`Mesh` is the `docker-compose` for local AI swarms: a dead-simple, zero-dependency CLI that orchestrates, pipelines, and multiplexes multiple autonomous coding agents using a single declarative file.

### 4. Target Audience
Power-user software engineers, open-source maintainers, and local-inference enthusiasts who are exhausted by corporate AI wrappers and want to run multiple specialized agents (like Goose, Codex, and local LLMs) locally, sequentially, and without writing custom Python execution scripts.

### 5. Core Feature Set (The "Holy Trinity")
*Do not add anything else to this list. If it's not here, we aren't building it.*

1.  **Declarative Orchestration (`mesh.yml`):** Drop the 500-line Python scripts. Define your entire swarm—models, agents, context scopes, and execution order—in a single, easily shareable YAML file. 
2.  **UNIX-Style Agent Piping:** Standardized STDIN/STDOUT routing. The output of your "Architect" agent flows seamlessly into the prompt of your "Coder" agent, which pipes directly into your "Reviewer" agent. Pure, frictionless execution chains.
3.  **Agnostic Resource Multiplexing:** Native, silent handling of hardware and APIs. `Mesh` automatically routes inference to local GPUs (MLX/CUDA) or proxy APIs based on the `mesh.yml` config without the underlying agent needing to know. 

### 6. Technical Stack Recommendation
**Rust.**
We are absolutely not using Python (environment hell) or Node.js (`node_modules` bloat). `Mesh` must be a ruthlessly fast, memory-safe, zero-dependency, single compiled binary. Rust gives us the performance required for hardware-level multiplexing and the undeniable "cool factor" necessary to trend organically on Hacker News and GitHub.

### 7. User Flow (Time-to-Value in < 30 Seconds)
1.  **Install:** `curl -sSfL https://mesh.sh/install | sh` *(Installs the standalone 2MB binary).*
2.  **Configure:** `mesh init` *(Instantly drops a boilerplate `mesh.yml` pipeline into their repo).*
3.  **Execute:** `mesh run "Refactor the authentication module"` *(Mesh reads the prompt, spins up the agent chain, multiplexes the hardware, and spits out the finished code).*

*** 

No dashboards. No SaaS pricing tiers. No web UI. Build the binary and let's ship.
