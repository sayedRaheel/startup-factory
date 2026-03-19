package runner

import (
	"bufio"
	"os/exec"
)

type Process struct {
	Cmd     *exec.Cmd
	LogChan chan string
}

func NewProcess(name string, args []string, env []string) *Process {
	cmd := exec.Command(name, args...)
	cmd.Env = env
	return &Process{
		Cmd:     cmd,
		LogChan: make(chan string, 100), // Buffered to prevent blocking subprocess
	}
}

func (p *Process) Run() error {
	stdout, err := p.Cmd.StdoutPipe()
	if err != nil {
		return err
	}
	stderr, err := p.Cmd.StderrPipe()
	if err != nil {
		return err
	}

	if err := p.Cmd.Start(); err != nil {
		p.LogChan <- "Failed to start: " + err.Error()
		return err
	}

	// Stream Stdout
	go func() {
		scanner := bufio.NewScanner(stdout)
		for scanner.Scan() {
			p.LogChan <- scanner.Text()
		}
	}()

	// Stream Stderr
	go func() {
		scanner := bufio.NewScanner(stderr)
		for scanner.Scan() {
			p.LogChan <- "[ERR] " + scanner.Text()
		}
	}()

	err = p.Cmd.Wait()
	p.LogChan <- "[PROCESS TERMINATED]"
	return err
}
