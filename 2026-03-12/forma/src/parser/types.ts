export interface FormaAST {
  system: string;
  model?: string;
  input: Record<string, string>;
  output: Record<string, string>;
}
