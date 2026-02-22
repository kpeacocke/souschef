package provider

import (
	"fmt"
	"os"
	"path/filepath"
	"testing"

	"github.com/hashicorp/terraform-plugin-testing/helper/resource"
	"github.com/hashicorp/terraform-plugin-testing/terraform"
)

// TestAccBatchMigrationResourceMultipleRecipes tests various recipe combinations
func TestAccBatchMigrationResourceMultipleRecipes(t *testing.T) {
	recipeCombinations := []struct{
		name    string
		recipes []string
	}{
		{"single", []string{"default"}},
		{"double", []string{"default", "server"}},
		{"triple", []string{"default", "server", "default"}}, // Duplicate to test handling
	}
	
	for _, combo := range recipeCombinations {
		t.Run(combo.name, func(t *testing.T) {
			outputPath := fmt.Sprintf("/workspaces/souschef/test-output/batch/%s", combo.name)
			os.MkdirAll(outputPath, 0755)
			
			resource.Test(t, resource.TestCase{
				PreCheck:                 func() { testAccPreCheck(t) },
				ProtoV6ProviderFactories: testAccProtoV6ProviderFactories,
				Steps: []resource.TestStep{
					{
						Config: testAccBatchMigrationResourceConfigRecipes(testBatchCookbookPath, outputPath, combo.recipes),
						Check: resource.ComposeAggregateTestCheckFunc(
							resource.TestCheckResourceAttr("souschef_batch_migration.test", "recipe_names.#", fmt.Sprintf("%d", len(combo.recipes))),
							resource.TestCheckResourceAttrSet("souschef_batch_migration.test", "playbook_count"),
						),
					},
				},
			})
		})
	}
}

// TestAccBatchMigrationResourceReadRefresh tests Read/Refresh cycles
func TestAccBatchMigrationResourceReadRefresh(t *testing.T) {
	outputPath := "/workspaces/souschef/test-output/batch/refresh"
	os.MkdirAll(outputPath, 0755)
	
	resource.Test(t, resource.TestCase{
		PreCheck:                 func() { testAccPreCheck(t) },
		ProtoV6ProviderFactories: testAccProtoV6ProviderFactories,
		Steps: []resource.TestStep{
			{
				Config: testAccBatchMigrationResourceConfigRecipes(testBatchCookbookPath, outputPath, []string{"default"}),
			},
			{
				RefreshState: true,
				Check: resource.ComposeAggregateTestCheckFunc(
					resource.TestCheckResourceAttrSet("souschef_batch_migration.test", "cookbook_name"),
					resource.TestCheckResourceAttrSet("souschef_batch_migration.test", "playbook_count"),
				),
			},
			{
				RefreshState: true,
				Check: resource.ComposeAggregateTestCheckFunc(
					resource.TestCheckResourceAttr("souschef_batch_migration.test", "recipe_names.#", "1"),
				),
			},
		},
	})
}

// TestAccBatchMigrationResourceDeleteMultiple tests deleting multiple playbooks
func TestAccBatchMigrationResourceDeleteMultiple(t *testing.T) {
	outputPath := "/workspaces/souschef/test-output/batch/delete_multi"
	os.MkdirAll(outputPath, 0755)
	recipes := []string{"default", "server"}
	
	resource.Test(t, resource.TestCase{
		PreCheck:                 func() { testAccPreCheck(t) },
		ProtoV6ProviderFactories: testAccProtoV6ProviderFactories,
		Steps: []resource.TestStep{
			{
				Config: testAccBatchMigrationResourceConfigRecipes(testBatchCookbookPath, outputPath, recipes),
			},
		},
		CheckDestroy: func(s *terraform.State) error {
			for _, recipe := range recipes {
				playbookPath := filepath.Join(outputPath, recipe+".yml")
				if _, err := os.Stat(playbookPath); err == nil {
					return fmt.Errorf("Playbook should have been deleted: %s", playbookPath)
				}
			}
			return nil
		},
	})
}

// TestAccBatchMigrationResourceUpdateRecipeList tests updating recipe lists
func TestAccBatchMigrationResourceUpdateRecipeList(t *testing.T) {
	outputPath := "/workspaces/souschef/test-output/batch/update_list"
	os.MkdirAll(outputPath, 0755)
	
	resource.Test(t, resource.TestCase{
		PreCheck:                 func() { testAccPreCheck(t) },
		ProtoV6ProviderFactories: testAccProtoV6ProviderFactories,
		Steps: []resource.TestStep{
			// Start with just default
			{
				Config: testAccBatchMigrationResourceConfigRecipes(testBatchCookbookPath, outputPath, []string{"default"}),
				Check: resource.ComposeAggregateTestCheckFunc(
					resource.TestCheckResourceAttr("souschef_batch_migration.test", "recipe_names.#", "1"),
					resource.TestCheckResourceAttr("souschef_batch_migration.test", "playbook_count", "1"),
				),
			},
			// Add server
			{
				Config: testAccBatchMigrationResourceConfigRecipes(testBatchCookbookPath, outputPath, []string{"default", "server"}),
				Check: resource.ComposeAggregateTestCheckFunc(
					resource.TestCheckResourceAttr("souschef_batch_migration.test", "recipe_names.#", "2"),
					resource.TestCheckResourceAttr("souschef_batch_migration.test", "playbook_count", "2"),
				),
			},
			// Back to just default
			{
				Config: testAccBatchMigrationResourceConfigRecipes(testBatchCookbookPath, outputPath, []string{"default"}),
				Check: resource.ComposeAggregateTestCheckFunc(
					resource.TestCheckResourceAttr("souschef_batch_migration.test", "recipe_names.#", "1"),
					resource.TestCheckResourceAttr("souschef_batch_migration.test", "playbook_count", "1"),
				),
			},
			// Just server
			{
				Config: testAccBatchMigrationResourceConfigRecipes(testBatchCookbookPath, outputPath, []string{"server"}),
				Check: resource.ComposeAggregateTestCheckFunc(
					resource.TestCheckResourceAttr("souschef_batch_migration.test", "recipe_names.#", "1"),
					resource.TestCheckResourceAttr("souschef_batch_migration.test", "recipe_names.0", "server"),
				),
			},
		},
	})
}

func testAccBatchMigrationResourceConfigRecipes(cookbookPath, outputPath string, recipes []string) string {
	recipesHCL := "["
	for i, recipe := range recipes {
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
