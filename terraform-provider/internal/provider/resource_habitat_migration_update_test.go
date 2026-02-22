package provider

import (
	"fmt"
	"testing"

	"github.com/hashicorp/terraform-plugin-testing/helper/resource"
)

// TestAccHabitatMigrationResourceUpdate tests updating Habitat migration
func TestAccHabitatMigrationResourceUpdate(t *testing.T) {
	resource.Test(t, resource.TestCase{
		PreCheck:                 func() { testAccPreCheck(t) },
		ProtoV6ProviderFactories: testAccProtoV6ProviderFactories,
		Steps: []resource.TestStep{
			// Create with default base image
			{
				Config: testAccHabitatMigrationResourceConfigBaseImage(testHabitatPlanPath, testHabitatOutputPath, "ubuntu:22.04"),
				Check: resource.ComposeAggregateTestCheckFunc(
					resource.TestCheckResourceAttr(testHabitatMigrationResourceName, "base_image", "ubuntu:22.04"),
					resource.TestCheckResourceAttrSet(testHabitatMigrationResourceName, "dockerfile_content"),
				),
			},
			// Update to different base image
			{
				Config: testAccHabitatMigrationResourceConfigBaseImage(testHabitatPlanPath, testHabitatOutputPath, "debian:12"),
				Check: resource.ComposeAggregateTestCheckFunc(
					resource.TestCheckResourceAttr(testHabitatMigrationResourceName, "base_image", "debian:12"),
					resource.TestCheckResourceAttrSet(testHabitatMigrationResourceName, "dockerfile_content"),
				),
			},
		},
	})
}

func testAccHabitatMigrationResourceConfigBaseImage(planPath, outputPath, baseImage string) string {
	return fmt.Sprintf(`
variable "souschef_path" {
  type = string
}

provider "souschef" {
  souschef_path = var.souschef_path
}

resource "souschef_habitat_migration" "test" {
  plan_path   = %[1]q
  output_path = %[2]q
  base_image  = %[3]q
}
`, planPath, outputPath, baseImage)
}
