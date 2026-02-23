// Package provider contains shared test helpers used across provider test files.
package provider

import (
	"os"
	"testing"
)

// File permission constants used in provider tests.
const (
	// testFilePermissions is the standard read/write permission for test files.
	testFilePermissions = os.FileMode(0o644)
	// testDirPermissions is the standard read/write/execute permission for test directories.
	testDirPermissions = os.FileMode(0o755)
	// executableFilePermissions is the permission for executable test files.
	executableFilePermissions = os.FileMode(0o755)
	// readonlyDirPermissions is the read-only permission for test directories.
	readonlyDirPermissions = os.FileMode(0o444)
)

// ValidateConfigValue asserts that the actual configuration value matches the expected value.
// It reports test failures via t if the values do not match.
func ValidateConfigValue(t *testing.T, got, want string) {
	t.Helper()
	if got != want {
		t.Errorf("config value mismatch: got %q, want %q", got, want)
	}
}
