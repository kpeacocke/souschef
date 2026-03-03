package provider

import (
	"fmt"
	"os"
	"path/filepath"
	"testing"

	"github.com/hashicorp/terraform-plugin-testing/helper/resource"
	"github.com/hashicorp/terraform-plugin-testing/terraform"
)

const (
	resourceInspecMigrationTest = "souschef_inspec_migration.test"
)

// TestAccInSpecMigrationResourceAllFormats tests all output formats comprehensively
func TestAccInSpecMigrationResourceAllFormats(t *testing.T) {
	formats := []string{"testinfra", "serverspec", "goss", "ansible"}

	for _, format := range formats {
		t.Run(format, func(t *testing.T) {
			testInSpecAllFormatOps(t, format)
		})
	}
}

func testInSpecAllFormatOps(t *testing.T, format string) {
	outputPath := fmt.Sprintf("/workspaces/souschef/test-output/inspec/%s", format)

	resource.Test(t, resource.TestCase{
		PreCheck:                 func() { testAccPreCheck(t) },
		ProtoV6ProviderFactories: testAccProtoV6ProviderFactories,
		Steps: []resource.TestStep{
			// Create
			{
				Config: testAccInSpecMigrationResourceConfigFmt(testInSpecProfilePath, outputPath, format),
				Check: resource.ComposeAggregateTestCheckFunc(
					resource.TestCheckResourceAttr(resourceInspecMigrationTest, "output_format", format),
					resource.TestCheckResourceAttr(resourceInspecMigrationTest, "profile_path", testInSpecProfilePath),
					resource.TestCheckResourceAttr(resourceInspecMigrationTest, "output_path", outputPath),
					resource.TestCheckResourceAttrSet(resourceInspecMigrationTest, "id"),
					resource.TestCheckResourceAttrSet(resourceInspecMigrationTest, "profile_name"),
					resource.TestCheckResourceAttrSet(resourceInspecMigrationTest, "test_content"),
				),
			},
			// Read/Refresh
			{
				RefreshState: true,
				Check: resource.ComposeAggregateTestCheckFunc(
					resource.TestCheckResourceAttr(resourceInspecMigrationTest, "output_format", format),
				),
			},
		},
	})
}

// TestAccInSpecMigrationResourceUpdateAllPaths tests updating all possible paths
func TestAccInSpecMigrationResourceUpdateAllPaths(t *testing.T) {
	outputPath1 := "/workspaces/souschef/test-output/inspec/update1"
	outputPath2 := "/workspaces/souschef/test-output/inspec/update2"

	resource.Test(t, resource.TestCase{
		PreCheck:                 func() { testAccPreCheck(t) },
		ProtoV6ProviderFactories: testAccProtoV6ProviderFactories,
		Steps: []resource.TestStep{
			{
				Config: testAccInSpecMigrationResourceConfigFmt(testInSpecProfilePath, outputPath1, "testinfra"),
				Check: resource.ComposeAggregateTestCheckFunc(
					resource.TestCheckResourceAttr(resourceInspecMigrationTest, "output_path", outputPath1),
				),
			},
			{
				Config: testAccInSpecMigrationResourceConfigFmt(testInSpecProfilePath, outputPath2, "testinfra"),
				Check: resource.ComposeAggregateTestCheckFunc(
					resource.TestCheckResourceAttr(resourceInspecMigrationTest, "output_path", outputPath2),
				),
			},
		},
	})
}

// TestAccInSpecMigrationResourceDeleteCleanup tests delete operation and file cleanup
func TestAccInSpecMigrationResourceDeleteCleanup(t *testing.T) {
	outputPath := "/workspaces/souschef/test-output/inspec/delete_test"

	// Ensure directory exists
	os.MkdirAll(outputPath, 0755)

	resource.Test(t, resource.TestCase{
		PreCheck:                 func() { testAccPreCheck(t) },
		ProtoV6ProviderFactories: testAccProtoV6ProviderFactories,
		Steps: []resource.TestStep{
			{
				Config: testAccInSpecMigrationResourceConfigFmt(testInSpecProfilePath, outputPath, "testinfra"),
			},
			// Destroy happens automatically after test
		},
		CheckDestroy: func(s *terraform.State) error {
			// Check that test file was deleted
			testFile := filepath.Join(outputPath, "test_spec.py")
			if _, err := os.Stat(testFile); err == nil {
				return fmt.Errorf("Test file should have been deleted: %s", testFile)
			}
			return nil
		},
	})
}

func testAccInSpecMigrationResourceConfigFmt(profilePath, outputPath, format string) string {
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
