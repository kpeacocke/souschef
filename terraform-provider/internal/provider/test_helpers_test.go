// Package provider contains shared test helpers used across provider test files.
package provider

import (
	"os"
	"testing"
)

// executableFilePermissions is the permission for executable test files.
const executableFilePermissions = os.FileMode(0o755)

// readonlyDirPermissions is the read-only permission for test directories.
const readonlyDirPermissions = os.FileMode(0o444)

// ValidateConfigValue asserts that the actual configuration value matches the expected value.
// It reports test failures via t if the values do not match.
func ValidateConfigValue(t *testing.T, got, want string) {
	t.Helper()
	if got != want {
		t.Errorf("config value mismatch: got %q, want %q", got, want)
	}
}
