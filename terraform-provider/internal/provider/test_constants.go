// Package provider contains test constants shared across multiple test files.
package provider

import "os"

const (
	// Diagnostic messages
	testUnexpectedDiagnostics    = "unexpected diagnostics: %v"
	testExpectedConvertError     = "expected diagnostics for convert error"
	testFailedToWritePlaybook    = "failed to write playbook: %v"
	testFailedToWritePlan        = "failed to write plan: %v"
	testFailedToWriteFile        = "failed to write file: %v"
	testFailedToCreateDirectory  = "failed to create directory: %v"
	testConfigureErrorMsg        = "expected error when provider data is wrong type"
	testUnexpectedNilDataMsg     = "unexpected error on nil provider data: %v"

	// File paths
	testTmpCookbook  = "/tmp/cookbook"
	testTmpPlanSh    = "/tmp/plan.sh"
	testTmpProfile   = "/tmp/profile"
	testDefaultYml   = "default.yml"
	testPlanSh       = "plan.sh"
	testPkgNameMyapp = "pkg_name=myapp\n"
	testFileName     = "file.txt"

	// Commands
	testConvertRecipe  = "convert-recipe"
	testConvertHabitat = "convert-habitat"
	testConvertInSpec  = "convert-inspec"
)

// File permission constants used in provider tests.
var (
	testFilePermissions = os.FileMode(0o644)
	testDirPermissions  = os.FileMode(0o755)
	noPermissions       = os.FileMode(0o000)
)
