package provider

import (
	"fmt"
	"testing"

	"github.com/hashicorp/terraform-plugin-testing/helper/resource"
)

const (
	recipeNamesCountAttr = recipeNamesCountAttr
	recipeNamesFirstAttr = recipeNamesFirstAttr
)

var (
	testBatchMigrationResourceName = "souschef_batch_migration.test"
	testBatchCookbookPath          = getFixturePath("sample_cookbook")
	testBatchOutputPath            = "/workspaces/souschef/test-output/ansible/batch"
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
					resource.TestCheckResourceAttr(testBatchMigrationResourceName, recipeNamesCountAttr, "1"),
					resource.TestCheckResourceAttr(testBatchMigrationResourceName, recipeNamesFirstAttr, "default"),
					resource.TestCheckResourceAttrSet(testBatchMigrationResourceName, "id"),
					resource.TestCheckResourceAttrSet(testBatchMigrationResourceName, "cookbook_name"),
					resource.TestCheckResourceAttrSet(testBatchMigrationResourceName, "playbook_count"),
					resource.TestCheckResourceAttrSet(testBatchMigrationResourceName, "playbooks.default"),
				),
			},
			// Update testing - add second recipe to trigger Update path
			{
				Config: testAccBatchMigrationResourceConfig("test", testBatchCookbookPath, testBatchOutputPath, []string{"default", "server"}),
				Check: resource.ComposeAggregateTestCheckFunc(
					resource.TestCheckResourceAttr(testBatchMigrationResourceName, "cookbook_path", testBatchCookbookPath),
					resource.TestCheckResourceAttr(testBatchMigrationResourceName, recipeNamesCountAttr, "2"),
					resource.TestCheckResourceAttr(testBatchMigrationResourceName, recipeNamesFirstAttr, "default"),
					resource.TestCheckResourceAttr(testBatchMigrationResourceName, "recipe_names.1", "server"),
					resource.TestCheckResourceAttrSet(testBatchMigrationResourceName, "playbook_count"),
					resource.TestCheckResourceAttrSet(testBatchMigrationResourceName, "playbooks.default"),
					resource.TestCheckResourceAttrSet(testBatchMigrationResourceName, "playbooks.server"),
				),
			},
			// Update back testing - remove recipe to test another scenario
			{
				Config: testAccBatchMigrationResourceConfig("test", testBatchCookbookPath, testBatchOutputPath, []string{"default"}),
				Check: resource.ComposeAggregateTestCheckFunc(
					resource.TestCheckResourceAttr(testBatchMigrationResourceName, recipeNamesCountAttr, "1"),
					resource.TestCheckResourceAttr(testBatchMigrationResourceName, recipeNamesFirstAttr, "default"),
				),
			},
			// ImportState testing
			{
				ResourceName:      testBatchMigrationResourceName,
				ImportState:       true,
				ImportStateId:     fmt.Sprintf("%s|%s|default", testBatchCookbookPath, testBatchOutputPath),
				ImportStateVerify: true,
			},
		},
	})
}

func testAccBatchMigrationResourceConfig(_, cookbookPath, outputPath string, recipeNames []string) string {
	recipesHCL := "["
	for i, recipe := range recipeNames {
		if i > 0 {
			recipesHCL += ", "
		}
		recipesHCL += fmt.Sprintf("%q", recipe)
	}
	recipesHCL += "]"

	return fmt.Sprintf(`
variable "souschef_path" {
  type = string
}

provider "souschef" {
  souschef_path = var.souschef_path
}

resource "souschef_batch_migration" "test" {
  cookbook_path = %[1]q
  output_path   = %[2]q
  recipe_names  = %[3]s
}
`, cookbookPath, outputPath, recipesHCL)
}
