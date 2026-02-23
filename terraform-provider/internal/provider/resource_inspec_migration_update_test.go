package provider

import (
	"fmt"
	"testing"

	"github.com/hashicorp/terraform-plugin-testing/helper/resource"
)

// TestAccInSpecMigrationResourceUpdateFormat tests updating output format
func TestAccInSpecMigrationResourceUpdateFormat(t *testing.T) {
	resource.Test(t, resource.TestCase{
		PreCheck:                 func() { testAccPreCheck(t) },
		ProtoV6ProviderFactories: testAccProtoV6ProviderFactories,
		Steps: []resource.TestStep{
			// Create with testinfra format
			{
				Config: testAccInSpecMigrationResourceConfigFormat(testInSpecProfilePath, testInSpecOutputPath, "testinfra"),
				Check: resource.ComposeAggregateTestCheckFunc(
					resource.TestCheckResourceAttr(testInSpecMigrationResourceName, "output_format", "testinfra"),
					resource.TestCheckResourceAttrSet(testInSpecMigrationResourceName, "test_content"),
				),
			},
			// Update to serverspec format
			{
				Config: testAccInSpecMigrationResourceConfigFormat(testInSpecProfilePath, testInSpecOutputPath, "serverspec"),
				Check: resource.ComposeAggregateTestCheckFunc(
					resource.TestCheckResourceAttr(testInSpecMigrationResourceName, "output_format", "serverspec"),
					resource.TestCheckResourceAttrSet(testInSpecMigrationResourceName, "test_content"),
				),
			},
			// Update to goss format
			{
				Config: testAccInSpecMigrationResourceConfigFormat(testInSpecProfilePath, testInSpecOutputPath, "goss"),
				Check: resource.ComposeAggregateTestCheckFunc(
					resource.TestCheckResourceAttr(testInSpecMigrationResourceName, "output_format", "goss"),
					resource.TestCheckResourceAttrSet(testInSpecMigrationResourceName, "test_content"),
				),
			},
			// Update to ansible format
			{
				Config: testAccInSpecMigrationResourceConfigFormat(testInSpecProfilePath, testInSpecOutputPath, "ansible"),
				Check: resource.ComposeAggregateTestCheckFunc(
					resource.TestCheckResourceAttr(testInSpecMigrationResourceName, "output_format", "ansible"),
					resource.TestCheckResourceAttrSet(testInSpecMigrationResourceName, "test_content"),
				),
			},
		},
	})
}

func testAccInSpecMigrationResourceConfigFormat(profilePath, outputPath, format string) string {
	return fmt.Sprintf(`
variable "souschef_path" {
  type = string
}

provider "souschef" {
  souschef_path = var.souschef_path
}

resource "souschef_inspec_migration" "test" {
  profile_path  = %[1]q
  output_path   = %[2]q
  output_format = %[3]q
}
`, profilePath, outputPath, format)
}
