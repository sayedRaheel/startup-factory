# Scout Analysis: The "100-Hour Gap" & Contextual Blindness

## The Problem / Emerging Trend
The top trending discussion on Hacker News right now is "The 100 hour gap between a vibecoded prototype and a working product." AI code generators (like Cursor and Claude Code) are allowing anyone to "vibecode" a prototype in 10 minutes. But turning that into a secure, typed, tested production app still takes 100 hours of grueling engineering. Why? Because the AI loses the plot as the repository grows. It forgets types, hallucinates function signatures, and struggles with multi-file architectures.

## Why Current Solutions Are Failing
Developers are resorting to two extremes:
1. **Dumping the whole repo:** Feeding the entire codebase into the LLM context window. This burns massive amounts of tokens (expensive), slows the model down to a crawl, and destroys its "attention span," causing it to miss subtle bugs in the noise.
2. **Pasting single files:** Giving the LLM only `main.go` and asking it to fix a bug. The LLM guesses what `auth.ValidateUser()` does and hallucinates the arguments, leading to compile errors.

## The Gap
There is a massive gap for a hyper-fast, lightweight context extractor that acts as an "AST map" for the LLM. It needs to give the LLM the structural depth of the entire repository (directory trees and function/class/struct signatures) *without* the bloated implementation logic. This allows the agent to navigate the codebase with surgical precision, reading only what it actually needs to edit.
