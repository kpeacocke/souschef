package provider

import (
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"testing"

	"github.com/hashicorp/terraform-plugin-testing/helper/resource"
)

var (
	testMigrationResourceName = "souschef_migration.test"
	testCookbookPathMigration = getFixturePath("sample_cookbook")
)

func TestAccMigrationResource(t *testing.T) {
	testAnsibleOutputPath := getTestOutputPath(t, "ansible")
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
					resource.TestMatchResourceAttr(testMigrationResourceName, "playbook_content", regexp.MustCompile(`(?m)^- name: Configure system`)),
				),
			},
			// Update and Read testing
			{
				Config: testAccMigrationResourceConfig("test_cookbook", testCookbookPathMigration, testAnsibleOutputPath),
				Check: resource.ComposeAggregateTestCheckFunc(
					resource.TestCheckResourceAttr(testMigrationResourceName, "cookbook_path", testCookbookPathMigration),
				),
			},
			// ImportState testing
			{
				ResourceName:      testMigrationResourceName,
				ImportState:       true,
				ImportStateId:     fmt.Sprintf("%s|%s|default", testCookbookPathMigration, testAnsibleOutputPath),
				ImportStateVerify: true,
			},
		},
	})
}

func TestAccMigrationResourceRejectsOutsideWorkspace(t *testing.T) {
	cookbook := t.TempDir()
	if err := os.Mkdir(filepath.Join(cookbook, "recipes"), 0755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(cookbook, "recipes", "default.rb"), []byte("package 'nginx'\n"), 0600); err != nil {
		t.Fatal(err)
	}
	output := getTestOutputPath(t, "output")
	resource.Test(t, resource.TestCase{
		PreCheck:                 func() { testAccPreCheck(t) },
		ProtoV6ProviderFactories: testAccProtoV6ProviderFactories,
		Steps: []resource.TestStep{{
			Config:      testAccMigrationResourceConfig("test_cookbook", cookbook, output),
			ExpectError: regexp.MustCompile(`(?s)Error converting recipe.*Path traversal`),
		}},
	})
	if _, err := os.Stat(filepath.Join(output, "default.yml")); !os.IsNotExist(err) {
		t.Fatalf("Expected no generated playbook; stat error: %v", err)
	}
}

func testAccMigrationResourceConfig(name, cookbookPath, outputPath string) string {
	return fmt.Sprintf(`
variable "souschef_path" {
  type = string
}

provider "souschef" {
  souschef_path = var.souschef_path
}

resource "souschef_migration" "test" {
  cookbook_path = %[2]q
  output_path   = %[3]q
  recipe_name   = "default"
}
`, name, cookbookPath, outputPath)
}
