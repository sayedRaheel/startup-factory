package proxy

import (
	"bufio"
	"os"
	"os/exec"

	"github.com/creack/pty"
	"github.com/yourorg/curb/internal/engine"
)

// InterceptEvent is sent to the TUI when a rule is broken
type InterceptEvent struct {
	Command string
	Reason  string
	Resume  chan bool
}

type Proxy struct {
	Cmd        *exec.Cmd
	PtyFile    *os.File
	Intercepts chan InterceptEvent
	Output     chan string
}

func NewProxy(targetCmd []string) *Proxy {
	cmd := exec.Command(targetCmd[0], targetCmd[1:]...)
	return &Proxy{
		Cmd:        cmd,
		Intercepts: make(chan InterceptEvent),
		Output:     make(chan string, 100),
	}
}

func (p *Proxy) Start() error {
	ptmx, err := pty.Start(p.Cmd)
	if err != nil {
		return err
	}
	p.PtyFile = ptmx

	// Goroutine to passively intercept and scan output
	go func() {
		scanner := bufio.NewScanner(ptmx)
		for scanner.Scan() {
			line := scanner.Text()

			if intercepted, reason := engine.Evaluate(line); intercepted {
				resumeChan := make(chan bool)
				p.Intercepts <- InterceptEvent{
					Command: line,
					Reason:  reason,
					Resume:  resumeChan,
				}

				// Block execution until user approves/denies via TUI
				approved := <-resumeChan
				if !approved {
					if p.Cmd.Process != nil {
						p.Cmd.Process.Kill()
					}
					os.Exit(1)
				}
			}

			// Pass safe output to TUI
			p.Output <- line
		}
		// Signal EOF to cleanly terminate TUI loop
		p.Output <- "EOF_REACHED"
	}()

	return nil
}

func (p *Proxy) WriteInput(b []byte) (int, error) {
	return p.PtyFile.Write(b)
}
