import fs from 'fs';

export const Stack = {
  Rust: 'Rust/Cargo',
  Node: 'Node.js',
  Python: 'Python',
  Go: 'Go',
  Unknown: 'Generic/Unknown',
};

export function detectStack() {
  if (fs.existsSync('Cargo.toml')) return Stack.Rust;
  if (fs.existsSync('package.json')) return Stack.Node;
  if (fs.existsSync('requirements.txt') || fs.existsSync('pyproject.toml')) return Stack.Python;
  if (fs.existsSync('go.mod')) return Stack.Go;
  return Stack.Unknown;
}
