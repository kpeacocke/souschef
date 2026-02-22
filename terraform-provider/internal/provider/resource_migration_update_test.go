package provider

import (
	"fmt"
	"testing"

	"github.com/hashicorp/terraform-plugin-testing/helper/resource"
)

// TestAccMigrationResourceUpdateOutputPath tests updating the output path
// This is a valid update scenario - regenerating playbooks in a new location
func TestAccMigrationResourceUpdateOutputPath(t *testing.T) {
	outputPath1 := "/workspaces/souschef/test-output/ansible/test1"
	outputPath2 := "/workspaces/souschef/test-output/ansible/test2"
	
	resource.Test(t, resource.TestCase{
		PreCheck:                 func() { testAccPreCheck(t) },
		ProtoV6ProviderFactories: testAccProtoV6ProviderFactories,
		Steps: []resource.TestStep{
			// Create with first output path
			{
				Config: testAccMigrationResourceConfigRecipe(testCookbookPathMigration, outputPath1, "default"),
				Check: resource.ComposeAggregateTestCheckFunc(
					resource.TestCheckResourceAttr(testMigrationResourceName, "output_path", outputPath1),
					resource.TestCheckResourceAttr(testMigrationResourceName, "recipe_name", "default"),
				),
			},
			// Update to second output path (triggers re-conversion)
			{
				Config: testAccMigrationResourceConfigRecipe(testCookbookPathMigration, outputPath2, "default"),
				Check: resource.ComposeAggregateTestCheckFunc(
					resource.TestCheckResourceAttr(testMigrationResourceName, "output_path", outputPath2),
					resource.TestCheckResourceAttr(testMigrationResourceName, "recipe_name", "default"),
					resource.TestCheckResourceAttrSet(testMigrationResourceName, "playbook_content"),
				),
			},
		},
	})
}

func testAccMigrationResourceConfigRecipe(cookbookPath, outputPath, recipeName string) string {
	return fmt.Sprintf(`
variable "souschef_path" {
  type = string
}

provider "souschef" {
  souschef_path = var.souschef_path
}

resource "souschef_migration" "test" {
  cookbook_path = %[1]q
  output_path   = %[2]q
  recipe_name   = %[3]q
}
`, cookbookPath, outputPath, recipeName)
}
