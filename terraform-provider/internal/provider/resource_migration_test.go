package provider

import (
	"fmt"
	"testing"

	"github.com/hashicorp/terraform-plugin-testing/helper/resource"
)

func TestAccMigrationResource(t *testing.T) {
	resource.Test(t, resource.TestCase{
		PreCheck:                 func() { testAccPreCheck(t) },
		ProtoV6ProviderFactories: testAccProtoV6ProviderFactories,
		Steps: []resource.TestStep{
			// Create and Read testing
			{
				Config: testAccMigrationResourceConfig("test_cookbook", "/tmp/cookbooks/test", "/tmp/ansible"),
				Check: resource.ComposeAggregateTestCheckFunc(
					resource.TestCheckResourceAttr("souschef_migration.test", "cookbook_path", "/tmp/cookbooks/test"),
					resource.TestCheckResourceAttr("souschef_migration.test", "output_path", "/tmp/ansible"),
					resource.TestCheckResourceAttr("souschef_migration.test", "recipe_name", "default"),
					resource.TestCheckResourceAttrSet("souschef_migration.test", "id"),
					resource.TestCheckResourceAttrSet("souschef_migration.test", "cookbook_name"),
					resource.TestCheckResourceAttrSet("souschef_migration.test", "playbook_content"),
				),
			},
			// ImportState testing
			{
				ResourceName:      "souschef_migration.test",
				ImportState:       true,
				ImportStateVerify: true,
			},
			// Update and Read testing
			{
				Config: testAccMigrationResourceConfig("test_cookbook", "/tmp/cookbooks/test", "/tmp/ansible"),
				Check: resource.ComposeAggregateTestCheckFunc(
					resource.TestCheckResourceAttr("souschef_migration.test", "cookbook_path", "/tmp/cookbooks/test"),
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
