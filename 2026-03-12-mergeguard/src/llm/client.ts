import OpenAI from 'openai';
import { env } from '../config.js';

const openai = new OpenAI({ apiKey: env.OPENAI_API_KEY });

export interface ReviewResult {
    status: 'APPROVED' | 'REJECTED';
    reason: string;
    actionable_feedback: string[];
}

export async function analyzeWithLLM(prompt: string): Promise<ReviewResult> {
    try {
        const response = await openai.chat.completions.create({
            model: env.MODEL,
            messages: [{ role: 'system', content: prompt }],
            response_format: { type: "json_object" }
        });
        
        const content = response.choices[0]?.message?.content;
        if(!content) throw new Error("Empty response from LLM");
        
        return JSON.parse(content) as ReviewResult;
    } catch (error: any) {
        throw new Error(`LLM Error: ${error.message}`);
    }
}
