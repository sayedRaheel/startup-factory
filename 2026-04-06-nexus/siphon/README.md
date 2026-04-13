# Siphon

Violently compress your repository into a token-optimized stream. Standard In, Standard Out. Single binary.

## Usage
`siphon . > context.xml`
`siphon ./src -max-tokens 4000 | ollama run llama3 "Review this code"`

### Research & Architecture
* [Scout Analysis](./docs/research/1-scout-analysis.md)
* [PRD](./docs/research/2-prd.md)
* [Tech Spec](./docs/research/3-tech-spec.md)
* [Builder Code](./docs/research/4-builder-code.md)
