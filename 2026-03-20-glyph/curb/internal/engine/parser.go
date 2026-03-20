package engine

import (
	"regexp"
	"strconv"
)

var costRegex = regexp.MustCompile(`Cost:\s*\$(\d+\.\d+)`)

func ParseCost(line string) float64 {
	matches := costRegex.FindStringSubmatch(line)
	if len(matches) > 1 {
		val, err := strconv.ParseFloat(matches[1], 64)
		if err == nil {
			return val
		}
	}
	return 0.0
}
