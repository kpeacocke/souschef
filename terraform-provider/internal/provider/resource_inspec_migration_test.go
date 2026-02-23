package provider

import (
	"fmt"
	"testing"

	"github.com/hashicorp/terraform-plugin-testing/helper/resource"
)

var (
	testInSpecMigrationResourceName = "souschef_inspec_migration.test"
	testInSpecProfilePath           = getFixturePath("sample_inspec_profile")
	testInSpecOutputPath            = "/workspaces/souschef/test-output/tests"
)

func TestAccInSpecMigrationResource(t *testing.T) {
	resource.Test(t, resource.TestCase{
		PreCheck:                 func() { testAccPreCheck(t) },
		ProtoV6ProviderFactories: testAccProtoV6ProviderFactories,
		Steps: []resource.TestStep{
			// Create and Read testing with testinfra format
			{
				Config: testAccInSpecMigrationResourceConfig("test", testInSpecProfilePath, testInSpecOutputPath, "testinfra"),
				Check: resource.ComposeAggregateTestCheckFunc(
					resource.TestCheckResourceAttr(testInSpecMigrationResourceName, "profile_path", testInSpecProfilePath),
					resource.TestCheckResourceAttr(testInSpecMigrationResourceName, "output_path", testInSpecOutputPath),
					resource.TestCheckResourceAttr(testInSpecMigrationResourceName, "output_format", "testinfra"),
					resource.TestCheckResourceAttrSet(testInSpecMigrationResourceName, "id"),
					resource.TestCheckResourceAttrSet(testInSpecMigrationResourceName, "profile_name"),
					resource.TestCheckResourceAttrSet(testInSpecMigrationResourceName, "test_content"),
				),
			},
			// Update testing with different format
			{
				Config: testAccInSpecMigrationResourceConfig("test", testInSpecProfilePath, testInSpecOutputPath, "ansible"),
				Check: resource.ComposeAggregateTestCheckFunc(
					resource.TestCheckResourceAttr(testInSpecMigrationResourceName, "output_format", "ansible"),
					resource.TestCheckResourceAttrSet(testInSpecMigrationResourceName, "test_content"),
				),
			},
			// Test serverspec format
			{
				Config: testAccInSpecMigrationResourceConfig("test", testInSpecProfilePath, testInSpecOutputPath, "serverspec"),
				Check: resource.ComposeAggregateTestCheckFunc(
					resource.TestCheckResourceAttr(testInSpecMigrationResourceName, "output_format", "serverspec"),
				),
			},
			// Test goss format
			{
				Config: testAccInSpecMigrationResourceConfig("test", testInSpecProfilePath, testInSpecOutputPath, "goss"),
				Check: resource.ComposeAggregateTestCheckFunc(
					resource.TestCheckResourceAttr(testInSpecMigrationResourceName, "output_format", "goss"),
				),
			},
			// ImportState testing
			{
				ResourceName:      testInSpecMigrationResourceName,
				ImportState:       true,
				ImportStateId:     fmt.Sprintf("%s|%s|goss", testInSpecProfilePath, testInSpecOutputPath),
				ImportStateVerify: true,
			},
		},
	})
}

func testAccInSpecMigrationResourceConfig(_, profilePath, outputPath, outputFormat string) string {
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
`, profilePath, outputPath, outputFormat)
}
