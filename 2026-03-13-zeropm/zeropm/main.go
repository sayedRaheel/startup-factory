package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"os/exec"
	"strings"
)

type Task struct {
	Title   string `json:"title"`
	Command string `json:"command"`
}

type AIResponse struct {
	Choices []struct {
		Message struct {
			Content string `json:"content"`
		} `json:"message"`
	} `json:"choices"`
}

func main() {
	if len(os.Args) < 3 || os.Args[1] != "execute" {
		fmt.Println("\033[36m[ZeroPM]\033[0m Usage: zeropm execute <file.md>")
		os.Exit(1)
	}

	filePath := os.Args[2]
	apiKey := os.Getenv("OPENAI_API_KEY")

	if apiKey == "" {
		fmt.Println("\033[31m[ZeroPM] Error:\033[0m OPENAI_API_KEY environment variable is required.")
		os.Exit(1)
	}

	content, err := os.ReadFile(filePath)
	if err != nil {
		fmt.Printf("\033[31m[ZeroPM] Error:\033[0m Cannot read file %s: %v\n", filePath, err)
		os.Exit(1)
	}

	fmt.Println("\033[36m[ZeroPM]\033[0m Analyzing PRD and generating execution graph...")

	prompt := fmt.Sprintf(`You are ZeroPM, an elite CLI orchestrator. I am providing a PRD. Break it down into a sequence of atomic, executable shell commands that will build the software. 

Return ONLY valid JSON matching this schema:
{
  "tasks": [
    {
      "title": "Short description of what the command does",
      "command": "The exact bash command to execute (e.g., 'mkdir src && touch src/main.js' or 'npm install express')"
    }
  ]
}

PRD Content:
%s`, string(content))

	reqBody, _ := json.Marshal(map[string]interface{}{
		"model": "gpt-4o-2024-08-06",
		"messages": []map[string]string{
			{"role": "system", "content": "You are a ruthless automation agent. Output JSON only."},
			{"role": "user", "content": prompt},
		},
		"response_format": map[string]interface{}{"type": "json_object"},
		"temperature":     0.1,
	})

	req, err := http.NewRequest("POST", "https://api.openai.com/v1/chat/completions", bytes.NewBuffer(reqBody))
	if err != nil {
		fmt.Println("Failed to create request:", err)
		os.Exit(1)
	}
	req.Header.Set("Authorization", "Bearer "+apiKey)
	req.Header.Set("Content-Type", "application/json")

	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		fmt.Println("\033[31m[ZeroPM] Network Error:\033[0m", err)
		os.Exit(1)
	}
	defer resp.Body.Close()

	bodyBytes, _ := io.ReadAll(resp.Body)
	var aiResp AIResponse
	if err := json.Unmarshal(bodyBytes, &aiResp); err != nil {
		fmt.Println("\033[31m[ZeroPM] Parse Error:\033[0m", err)
		os.Exit(1)
	}

	if len(aiResp.Choices) == 0 {
		fmt.Println("\033[31m[ZeroPM] LLM Error:\033[0m Empty response from API.")
		os.Exit(1)
	}

	var result struct {
		Tasks []Task `json:"tasks"`
	}

	err = json.Unmarshal([]byte(aiResp.Choices[0].Message.Content), &result)
	if err != nil {
		fmt.Println("\033[31m[ZeroPM] JSON Error:\033[0m LLM did not return valid JSON.", err)
		os.Exit(1)
	}

	fmt.Printf("\033[32m✅ Generated %d tasks. Commencing autonomous execution...\033[0m\n\n", len(result.Tasks))

	for i, task := range result.Tasks {
		fmt.Printf("\033[1;33m[%d/%d] %s\033[0m\n", i+1, len(result.Tasks), task.Title)
		fmt.Printf("\033[90m$ %s\033[0m\n", task.Command)

		cmd := exec.Command("bash", "-c", task.Command)
		var out bytes.Buffer
		cmd.Stdout = &out
		cmd.Stderr = &out

		err := cmd.Run()
		if err != nil {
			fmt.Printf("\033[31m❌ Task failed:\033[0m %v\n", err)
			fmt.Println(strings.TrimSpace(out.String()))
			fmt.Println("\n\033[31m[ZeroPM] Execution halted.\033[0m")
			os.Exit(1)
		}
		
		output := strings.TrimSpace(out.String())
		if output != "" {
			fmt.Println(output)
		}
		fmt.Println("\033[32m✔ Complete\033[0m\n")
	}

	fmt.Println("\033[32m🚀 ZERO PM: All tasks executed successfully. You are welcome.\033[0m")
}
