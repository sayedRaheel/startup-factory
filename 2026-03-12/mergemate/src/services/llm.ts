import Anthropic from '@anthropic-ai/sdk';
import 'dotenv/config';

const anthropic = new Anthropic({
  apiKey: process.env.ANTHROPIC_API_KEY,
});

export async function generatePersona(codebaseSample: string): Promise<string> {
  const msg = await anthropic.messages.create({
    model: "claude-3-5-sonnet-20240620",
    max_tokens: 1000,
    system: "You are an expert software architect. Analyze the provided codebase sample and extract the dominant architectural patterns, state management tools, and naming conventions.",
    messages: [{ role: "user", content: codebaseSample }]
  });
  return msg.content[0].type === 'text' ? msg.content[0].text : '';
}

export async function reviewDiff(persona: string, diff: string): Promise<string> {
  const msg = await anthropic.messages.create({
    model: "claude-3-5-sonnet-20240620",
    max_tokens: 1500,
    system: `You are a strict code reviewer. Evaluate the diff against this Project Persona:\n${persona}\nFlag ONLY architectural and stylistic mismatches.`,
    messages: [{ role: "user", content: diff }]
  });
  return msg.content[0].type === 'text' ? msg.content[0].text : '';
}
