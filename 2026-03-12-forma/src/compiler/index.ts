import { FormaAST } from '../parser/types';

export interface CompiledPayload {
  model: string;
  messages: { role: string; content: string }[];
  response_format: object;
}

export function compileToPayload(ast: FormaAST): CompiledPayload {
  const properties: Record<string, any> = {};
  for (const [key, type] of Object.entries(ast.output)) {
    // Map basic types
    let jsonType = 'string';
    if (type === 'number') jsonType = 'number';
    if (type === 'boolean') jsonType = 'boolean';
    if (type === 'object') jsonType = 'object';
    
    properties[key] = { type: jsonType };
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
      { role: 'system', content: ast.system }
    ],
    response_format: jsonSchema
  };
}
