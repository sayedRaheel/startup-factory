package shell

import (
	"fmt"
	"os"
	"strings"

	"github.com/devscope/devscope/internal/config"
)

const (
	// DEVSCOPE_ORIG_PATH stores the PATH before DevScope applies project-specific changes.
	// DEVSCOPE_ACTIVE_PROJECT_ENV_VARS stores a colon-separated list of env var names set by DevScope.
	hookScriptTemplate = `
_devscope_chpwd_hook() {
  local devscope_config_path=$(devscope_find_config)
  local initial_system_path="%s" # Placeholder for original system PATH on hook generation

  # Clear any previous DevScope-managed paths and env vars if active
  if [[ -n "$DEVSCOPE_ORIG_PATH" ]]; then
    PATH="$DEVSCOPE_ORIG_PATH" # Restore to original PATH
    unset DEVSCOPE_ORIG_PATH
  fi
  if [[ -n "$DEVSCOPE_ACTIVE_PROJECT_ENV_VARS" ]]; then
    local IFS=':'
    for var_name in $DEVSCOPE_ACTIVE_PROJECT_ENV_VARS; do
      unset "$var_name"
    done
    unset DEVSCOPE_ACTIVE_PROJECT_ENV_VARS
  fi

  if [[ -n "$devscope_config_path" ]]; then
    # We are in a DevScope project
    export DEVSCOPE_ORIG_PATH="$initial_system_path" # Save initial system PATH for later restoration

    local project_bin_paths_output=$(devscope shell-env-paths)
    local project_env_vars_output=$(devscope shell-env-vars)

    # Prepend project-specific paths
    if [[ -n "$project_bin_paths_output" ]]; then
      local IFS=$'\n'
      for p in $project_bin_paths_output; do
        if [[ ":$PATH:" != *":$p:"* ]]; then # Avoid adding duplicates
          PATH="$p:$PATH"
        fi
      done
    fi

    # Set project-specific environment variables and track them
    local active_env_vars_list=""
    if [[ -n "$project_env_vars_output" ]]; then
      local IFS=$'\n'
      for env_line in $project_env_vars_output; do
        if [[ "$env_line" =~ ^([^=]+)=(.*)$ ]]; then
          export "${BASH_REMATCH[1]}"="${BASH_REMATCH[2]}"
          active_env_vars_list+="${BASH_REMATCH[1]}:"
        fi
      done
    fi
    export DEVSCOPE_ACTIVE_PROJECT_ENV_VARS="$(echo "$active_env_vars_list" | sed 's/:$//')" # Remove trailing colon

    # Asynchronously run validation
    devscope &>/dev/null &
  else
    # Not in a DevScope project. PATH and env vars should already be reset by the initial logic in this function.
    : # No-op
  fi
}

devscope_find_config() {
  local dir="$PWD"
  while [[ "$dir" != "/" && "$dir" != "" ]]; do
    if [[ -f "$dir/%s" ]]; then
      echo "$dir/%s"
      return 0
    fi
    dir=$(dirname "$dir")
  done
  return 1
}
`
)

// GenerateHookScript generates the shell script for ambient environment enforcement.
func GenerateHookScript(shellType string) (string, error) {
	// We need to capture the current "system" PATH when the hook is generated.
	// This is the PATH present when 'devscope shell-hook' is run.
	initialSystemPath := os.Getenv("PATH")

	script := fmt.Sprintf(hookScriptTemplate,
		initialSystemPath,
		config.DevScopeConfigFileName,
		config.DevScopeConfigFileName,
	)

	// Shell-specific integration
	switch shellType {
	case "bash":
		script = strings.TrimSpace(script) + `
PROMPT_COMMAND="_devscope_chpwd_hook; $PROMPT_COMMAND"
`
	case "zsh":
		script = strings.TrimSpace(script) + `
add-zsh-hook chpwd _devscope_chpwd_hook
`
	default:
		return "", fmt.Errorf("unsupported shell type: %s. Only bash and zsh are supported.", shellType)
	}

	return script, nil
}
