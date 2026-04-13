# Mesh

Mesh is a lightning-fast CLI that parses a declarative pipeline (`mesh.yml`) and pipes inputs/outputs between distinct autonomous agents using standard UNIX streams. 

### Problem Statement
AI swarms often rely on complex Python environments and heavy orchestrators. Mesh simplifies this by treating agents as standard UNIX processes, using declarative YAML to configure pipelines, and piping `stdout` to `stdin` across steps with zero external dependencies. Built for raw speed, strong types, and pure UNIX philosophy.

### Research & Architecture
* [Scout Analysis](./docs/research/1-scout-analysis.md)
* [PRD](./docs/research/2-prd.md)
* [Tech Spec](./docs/research/3-tech-spec.md)
* [Builder Code](./docs/research/4-builder-code.md)

### Usage
# Initialize the pipeline configuration
mesh init

# Run the pipeline with an initial prompt
mesh run "Create a python script"
