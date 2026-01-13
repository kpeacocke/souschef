package provider

import (
	"fmt"
	"testing"

	"github.com/hashicorp/terraform-plugin-testing/helper/resource"
)

const (
	testMigrationResourceName = "souschef_migration.test"
	testCookbookPathMigration = "/tmp/cookbooks/test"
	testAnsibleOutputPath     = "/tmp/ansible"
)

func TestAccMigrationResource(t *testing.T) {
	resource.Test(t, resource.TestCase{
		PreCheck:                 func() { testAccPreCheck(t) },
		ProtoV6ProviderFactories: testAccProtoV6ProviderFactories,
		Steps: []resource.TestStep{
			// Create and Read testing
			{
				Config: testAccMigrationResourceConfig("test_cookbook", testCookbookPathMigration, testAnsibleOutputPath),
				Check: resource.ComposeAggregateTestCheckFunc(
					resource.TestCheckResourceAttr(testMigrationResourceName, "cookbook_path", testCookbookPathMigration),
					resource.TestCheckResourceAttr(testMigrationResourceName, "output_path", testAnsibleOutputPath),
					resource.TestCheckResourceAttr(testMigrationResourceName, "recipe_name", "default"),
					resource.TestCheckResourceAttrSet(testMigrationResourceName, "id"),
					resource.TestCheckResourceAttrSet(testMigrationResourceName, "cookbook_name"),
					resource.TestCheckResourceAttrSet(testMigrationResourceName, "playbook_content"),
				),
			},
			// ImportState testing
			{
				ResourceName:      testMigrationResourceName,
				ImportState:       true,
				ImportStateVerify: true,
			},
			// Update and Read testing
			{
				Config: testAccMigrationResourceConfig("test_cookbook", testCookbookPathMigration, testAnsibleOutputPath),
				Check: resource.ComposeAggregateTestCheckFunc(
					resource.TestCheckResourceAttr(testMigrationResourceName, "cookbook_path", testCookbookPathMigration),
				),
			},
			// Delete testing automatically occurs in TestCase
		},
	})
}

func testAccMigrationResourceConfig(name, cookbookPath, outputPath string) string {
	return fmt.Sprintf(`
resource "souschef_migration" "test" {
  cookbook_path = %[2]q
  output_path   = %[3]q
  recipe_name   = "default"
}
`, name, cookbookPath, outputPath)
}
