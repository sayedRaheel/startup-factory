import { GoogleGenAI } from '@google/genai';
import { config } from '../config';

const ai = new GoogleGenAI({ apiKey: config.geminiApiKey });

export interface ReviewResult {
    status: 'APPROVED' | 'REJECTED';
    reason: string;
    actionable_feedback: string[];
}

export async function analyzeWithLLM(prompt: string): Promise<ReviewResult> {
    try {
        const response = await ai.models.generateContent({
            model: config.model,
            contents: prompt,
            config: {
                responseMimeType: "application/json",
            }
        });
        
        const text = response.text();
        if(!text) throw new Error("Empty response from LLM");
        
        return JSON.parse(text) as ReviewResult;
    } catch (error: any) {
        throw new Error(`LLM Error: ${error.message}`);
    }
}
