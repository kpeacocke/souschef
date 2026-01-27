package provider

import (
	"os"
	"path/filepath"
	"runtime"
	"testing"

	"github.com/hashicorp/terraform-plugin-framework/providerserver"
	"github.com/hashicorp/terraform-plugin-go/tfprotov6"
)

// testAccProtoV6ProviderFactories are used to instantiate a provider during
// acceptance testing. The factory function will be invoked for every Terraform
// CLI command executed to create a provider server to which the CLI can
// reattach.
var testAccProtoV6ProviderFactories = map[string]func() (tfprotov6.ProviderServer, error){
	"souschef": providerserver.NewProtocol6WithError(New("test")()),
}

func testAccPreCheck(_ *testing.T) {
	// Set default souschef path for testing if not set
	if os.Getenv("TF_VAR_souschef_path") == "" {
		// Get the directory of this test file
		_, filename, _, ok := runtime.Caller(0)
		if !ok {
			return
		}

		// Navigate from provider_test.go location to repo root
		// provider_test.go is in: terraform-provider/internal/provider/
		repoRoot := filepath.Join(filepath.Dir(filename), "..", "..", "..")
		repoRoot = filepath.Clean(repoRoot)

		// Try common locations in order of preference
		possiblePaths := []string{
			// Poetry virtual environment (most common for macOS/Linux dev)
			filepath.Join(repoRoot, ".venv", "bin", "souschef"),
			// Dev container
			"/workspaces/souschef/.venv/bin/souschef",
			// System-wide poetry installation
			filepath.Join(os.Getenv("HOME"), ".cache", "pypoetry", "virtualenvs", "souschef-*/bin/souschef"),
		}

		for _, path := range possiblePaths {
			// Handle glob patterns for poetry cache
			if matches, err := filepath.Glob(path); err == nil && len(matches) > 0 {
				path = matches[0]
			}

			if _, err := os.Stat(path); err == nil {
				os.Setenv("TF_VAR_souschef_path", path)
				return
			}
		}
	}
}

// getFixturePath returns the absolute path to a test fixture directory.
// Works in both dev container (/workspaces/souschef) and GitHub Actions.
func getFixturePath(fixtureName string) string {
	// Get the directory of this test file
	_, filename, _, ok := runtime.Caller(0)
	if !ok {
		// Fallback to current working directory
		cwd, _ := os.Getwd()
		return filepath.Join(cwd, "..", "..", "tests", "fixtures", fixtureName)
	}

	// Navigate from provider_test.go location to repo root
	// provider_test.go is in: terraform-provider/internal/provider/
	repoRoot := filepath.Join(filepath.Dir(filename), "..", "..", "..")
	fixturesPath := filepath.Join(repoRoot, "tests", "fixtures", fixtureName)

	// Clean the path to resolve .. components
	return filepath.Clean(fixturesPath)
}
