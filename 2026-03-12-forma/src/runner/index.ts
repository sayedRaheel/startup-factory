import { compileToPayload } from '../compiler';
import { parseFormaFile } from '../parser';
import OpenAI from 'openai';
import dotenv from 'dotenv';
dotenv.config();

export async function runTest(filePath: string, mockInput: string) {
  const ast = parseFormaFile(filePath);
  const payload = compileToPayload(ast);
  
  if (!process.env.OPENAI_API_KEY) {
     throw new Error("OPENAI_API_KEY is not set.");
  }

  const openai = new OpenAI();
  
  const messages: any[] = [
    ...payload.messages,
    { role: 'user', content: mockInput }
  ];

  const response = await openai.chat.completions.create({
    model: payload.model,
    messages: messages,
    response_format: payload.response_format as any,
  });

  return response.choices[0].message.content;
}
