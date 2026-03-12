import { FormaAST } from '../parser/types';

export interface CompiledPayload {
  model: string;
  messages: { role: string; content: string }[];
  response_format: object;
}

export function compileToPayload(ast: FormaAST): CompiledPayload {
  // Convert AST output schema to JSON Schema for LLM Structured Outputs
  const properties: Record<string, any> = {};
  for (const [key, type] of Object.entries(ast.output)) {
    properties[key] = { type: type === 'string' ? 'string' : 'object' };
  }

  const jsonSchema = {
    type: "json_schema",
    json_schema: {
      name: "forma_output",
      schema: {
        type: "object",
        properties,
        required: Object.keys(ast.output),
        additionalProperties: false
      },
      strict: true
    }
  };

  return {
    model: ast.model || 'gpt-4o',
    messages: [
      { role: 'system', content: ast.system },
      // User prompt injection point
    ],
    response_format: jsonSchema
  };
}
