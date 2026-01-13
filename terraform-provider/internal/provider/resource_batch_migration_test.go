package provider

import (
	"fmt"
	"testing"

	"github.com/hashicorp/terraform-plugin-testing/helper/resource"
)

const (
	testBatchMigrationResourceName = "souschef_batch_migration.test"
	testBatchCookbookPath          = "/workspaces/souschef/tests/fixtures/sample_cookbook"
	testBatchOutputPath            = "/tmp/ansible/batch"
)

func TestAccBatchMigrationResource(t *testing.T) {
	resource.Test(t, resource.TestCase{
		PreCheck:                 func() { testAccPreCheck(t) },
		ProtoV6ProviderFactories: testAccProtoV6ProviderFactories,
		Steps: []resource.TestStep{
			// Create and Read testing
			{
				Config: testAccBatchMigrationResourceConfig("test", testBatchCookbookPath, testBatchOutputPath, []string{"default"}),
				Check: resource.ComposeAggregateTestCheckFunc(
					resource.TestCheckResourceAttr(testBatchMigrationResourceName, "cookbook_path", testBatchCookbookPath),
					resource.TestCheckResourceAttr(testBatchMigrationResourceName, "output_path", testBatchOutputPath),
					resource.TestCheckResourceAttr(testBatchMigrationResourceName, "recipe_names.#", "1"),
					resource.TestCheckResourceAttr(testBatchMigrationResourceName, "recipe_names.0", "default"),
					resource.TestCheckResourceAttrSet(testBatchMigrationResourceName, "id"),
					resource.TestCheckResourceAttrSet(testBatchMigrationResourceName, "cookbook_name"),
					resource.TestCheckResourceAttrSet(testBatchMigrationResourceName, "playbook_count"),
					resource.TestCheckResourceAttrSet(testBatchMigrationResourceName, "playbooks.default"),
				),
			},
		},
	})
}

func testAccBatchMigrationResourceConfig(name, cookbookPath, outputPath string, recipeNames []string) string {
	recipesHCL := "["
	for i, recipe := range recipeNames {
		if i > 0 {
			recipesHCL += ", "
		}
		recipesHCL += fmt.Sprintf("%q", recipe)
	}
	recipesHCL += "]"

	return fmt.Sprintf(`
provider "souschef" {
  souschef_path = "/workspaces/souschef/.venv/bin/souschef"
}

resource "souschef_batch_migration" "test" {
  cookbook_path = %[1]q
  output_path   = %[2]q
  recipe_names  = %[3]s
}
`, cookbookPath, outputPath, recipesHCL)
}
