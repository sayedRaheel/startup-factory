```typescript
import { SimpleGit, simpleGit } from 'simple-git';
import { OpenAI } from 'openai';

const git: SimpleGit = simpleGit();
const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

export async function analyzeDiff() {
  const diff = await git.diff(['HEAD']);
  if (!diff) return console.log('No changes to review!');
  
  const response = await openai.chat.completions.create({
    model: 'gpt-4',
    messages: [
      { role: 'system', content: 'You are an expert code reviewer. Analyze this diff and output JSON issues.' },
      { role: 'user', content: diff }
    ]
  });
  
  console.log(response.choices[0].message.content);
}
```
