// Package provider contains dependency injection points for tests.
package provider

import (
	"os"
	"os/exec"

	"github.com/hashicorp/terraform-plugin-framework/types"
)

var (
	execCommandContext = exec.CommandContext
	osMkdirAll         = os.MkdirAll
	osReadFile         = os.ReadFile
	osStat             = os.Stat
	osRemove           = os.Remove
	typesMapValueFrom  = types.MapValueFrom
)
