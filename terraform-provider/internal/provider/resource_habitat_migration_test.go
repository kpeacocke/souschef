package provider

import (
	"fmt"
	"testing"

	"github.com/hashicorp/terraform-plugin-testing/helper/resource"
)

const (
	testHabitatMigrationResourceName = "souschef_habitat_migration.test"
	testHabitatPlanPath              = "/workspaces/souschef/tests/fixtures/habitat_package/plan.sh"
	testHabitatOutputPath            = "/tmp/docker"
)

func TestAccHabitatMigrationResource(t *testing.T) {
	resource.Test(t, resource.TestCase{
		PreCheck:                 func() { testAccPreCheck(t) },
		ProtoV6ProviderFactories: testAccProtoV6ProviderFactories,
		Steps: []resource.TestStep{
			// Create and Read testing with default base image
			{
				Config: testAccHabitatMigrationResourceConfig("test", testHabitatPlanPath, testHabitatOutputPath, ""),
				Check: resource.ComposeAggregateTestCheckFunc(
					resource.TestCheckResourceAttr(testHabitatMigrationResourceName, "plan_path", testHabitatPlanPath),
					resource.TestCheckResourceAttr(testHabitatMigrationResourceName, "output_path", testHabitatOutputPath),
					resource.TestCheckResourceAttr(testHabitatMigrationResourceName, "base_image", "ubuntu:latest"),
					resource.TestCheckResourceAttrSet(testHabitatMigrationResourceName, "id"),
					resource.TestCheckResourceAttrSet(testHabitatMigrationResourceName, "package_name"),
					resource.TestCheckResourceAttrSet(testHabitatMigrationResourceName, "dockerfile_content"),
				),
			},
			// Update testing with custom base image
			{
				Config: testAccHabitatMigrationResourceConfig("test", testHabitatPlanPath, testHabitatOutputPath, "ubuntu:22.04"),
				Check: resource.ComposeAggregateTestCheckFunc(
					resource.TestCheckResourceAttr(testHabitatMigrationResourceName, "base_image", "ubuntu:22.04"),
					resource.TestCheckResourceAttrSet(testHabitatMigrationResourceName, "dockerfile_content"),
				),
			},
		},
	})
}

func testAccHabitatMigrationResourceConfig(_, planPath, outputPath, baseImage string) string {
	config := fmt.Sprintf(`
provider "souschef" {
  souschef_path = "/workspaces/souschef/.venv/bin/souschef"
}

resource "souschef_habitat_migration" "test" {
  plan_path   = %[1]q
  output_path = %[2]q`, planPath, outputPath)

	if baseImage != "" {
		config += fmt.Sprintf(`
  base_image  = %q`, baseImage)
	}

	config += `
}
`
	return config
}
