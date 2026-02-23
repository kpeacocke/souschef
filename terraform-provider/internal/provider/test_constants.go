package provider

// Shared test constants
const (
	expectedPanicMsg        = "Expected panic: %v"
	nonexistentSousChefPath = "nonexistent-souschef-for-test"
	// testDirPermissions defines readable/writable/executable directory permissions for temporary test directories
	testDirPermissions = 0o755
	// readonlyDirPermissions defines read-only directory permissions to test permission-denied scenarios
	readonlyDirPermissions = 0o555
	// testFilePermissions defines readable/writable file permissions for temporary test files
	testFilePermissions = 0o644
	// executableFilePermissions defines readable/writable/executable file permissions for test scripts
	executableFilePermissions = 0o755
)
