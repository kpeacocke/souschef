package provider

import (
	"os"
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
		// Try common locations
		venvPath := "/workspaces/souschef/.venv/bin/souschef"
		if _, err := os.Stat(venvPath); err == nil {
			os.Setenv("TF_VAR_souschef_path", venvPath)
		}
	}
}
