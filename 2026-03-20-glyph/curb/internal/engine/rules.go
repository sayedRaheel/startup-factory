package engine

import (
	"regexp"
)

// Rule defines a simple intercept rule
type Rule struct {
	Pattern *regexp.Regexp
	Reason  string
}

var DefaultRules = []Rule{
	{regexp.MustCompile(`rm\s+-rf`), "Attempted destruction of protected pattern."},
	{regexp.MustCompile(`\.env`), "Attempted access or destruction of protected pattern."},
}

// Evaluate checks if a line breaks any rules
func Evaluate(line string) (bool, string) {
	for _, rule := range DefaultRules {
		if rule.Pattern.MatchString(line) {
			return true, rule.Reason
		}
	}
	return false, ""
}
