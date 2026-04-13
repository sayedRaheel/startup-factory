# Tether

### The Problem
AI coding agents are reckless because they lack bounded contexts and operate with implicit trust. Sandboxing disk I/O at the OS level requires root permissions or complex kernel extensions. Tether acts as a local man-in-the-middle HTTP proxy to intercept the payload, inject the compiled context, enforce the proof of understanding, and block destructive tool-calls before they hit the disk.

### Research & Architecture
* [Scout Analysis](./docs/research/1-scout-analysis.md)
* [PRD](./docs/research/2-prd.md)
* [Tech Spec](./docs/research/3-tech-spec.md)
* [Builder Code](./docs/research/4-builder-code.md)
