package ui

import (
	"fmt"

	"github.com/fatih/color"
)

var (
	successColor = color.New(color.FgGreen).SprintfFunc()
	infoColor    = color.New(color.FgCyan).SprintfFunc()
	warnColor    = color.New(color.FgYellow).SprintfFunc()
	errorColor   = color.New(color.FgRed).SprintfFunc()
)

// Success prints a success message.
func Success(format string, a ...interface{}) {
	fmt.Printf("%s %s\n", successColor("✓"), fmt.Sprintf(format, a...))
}

// Info prints an informational message.
func Info(format string, a ...interface{}) {
	fmt.Printf("%s %s\n", infoColor("➜"), fmt.Sprintf(format, a...))
}

// Warn prints a warning message.
func Warn(format string, a ...interface{}) {
	fmt.Printf("%s %s\n", warnColor("▲"), fmt.Sprintf(format, a...))
}

// Error prints an error message.
func Error(format string, a ...interface{}) {
	fmt.Printf("%s %s\n", errorColor("✗"), fmt.Sprintf(format, a...))
}
