import dotenv from 'dotenv';
dotenv.config();
export const env = {
    OPENAI_API_KEY: process.env.OPENAI_API_KEY || '',
    GITHUB_TOKEN: process.env.GITHUB_TOKEN || '',
    MODEL: process.env.MODEL || 'gpt-4o',
};
if (!env.OPENAI_API_KEY) {
    console.error('Error: OPENAI_API_KEY environment variable is missing.');
    process.exit(1);
}
