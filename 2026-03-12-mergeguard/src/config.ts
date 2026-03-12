import dotenv from 'dotenv';
dotenv.config();

export const config = {
    geminiApiKey: process.env.GEMINI_API_KEY || '',
    model: 'gemini-1.5-pro',
};

if (!config.geminiApiKey) {
    console.error('Error: GEMINI_API_KEY environment variable is missing.');
    process.exit(1);
}
