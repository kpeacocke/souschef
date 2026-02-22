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
	resourceHabitatMigrationTest = resourceHabitatMigrationTest
	ubuntuImageAttr              = ubuntuImageAttr
)

// TestAccHabitatMigrationResourceComprehensive tests all habitat migration operations
func TestAccHabitatMigrationResourceComprehensive(t *testing.T) {
	baseImages := []string{
		ubuntuImageAttr,
		"debian:12",
		"alpine:3.18",
		"centos:8",
	}

	for _, baseImage := range baseImages {
		t.Run(baseImage, func(t *testing.T) {
			testHabitatWithBaseImage(t, baseImage)
		})
	}
}

func testHabitatWithBaseImage(t *testing.T, baseImage string) {
	outputPath := fmt.Sprintf("/workspaces/souschef/test-output/habitat/%s", filepath.Base(baseImage))
	os.MkdirAll(outputPath, 0755)

	resource.Test(t, resource.TestCase{
		PreCheck:                 func() { testAccPreCheck(t) },
		ProtoV6ProviderFactories: testAccProtoV6ProviderFactories,
		Steps: []resource.TestStep{
			{
				Config: testAccHabitatMigrationResourceConfigBase(testHabitatPlanPath, outputPath, baseImage),
				Check: resource.ComposeAggregateTestCheckFunc(
					resource.TestCheckResourceAttr(resourceHabitatMigrationTest, "plan_path", testHabitatPlanPath),
					resource.TestCheckResourceAttr(resourceHabitatMigrationTest, "output_path", outputPath),
					resource.TestCheckResourceAttr(resourceHabitatMigrationTest, "base_image", baseImage),
					resource.TestCheckResourceAttrSet(resourceHabitatMigrationTest, "id"),
					resource.TestCheckResourceAttrSet(resourceHabitatMigrationTest, "package_name"),
					resource.TestCheckResourceAttrSet(resourceHabitatMigrationTest, "dockerfile_content"),
				),
			},
		},
	})
}

// TestAccHabitatMigrationResourceDefaultBaseImage tests default base image handling
func TestAccHabitatMigrationResourceDefaultBaseImage(t *testing.T) {
	outputPath := "/workspaces/souschef/test-output/habitat/default"
	os.MkdirAll(outputPath, 0755)

	resource.Test(t, resource.TestCase{
		PreCheck:                 func() { testAccPreCheck(t) },
		ProtoV6ProviderFactories: testAccProtoV6ProviderFactories,
		Steps: []resource.TestStep{
			// Create without specifying base_image (should use default)
			{
				Config: testAccHabitatMigrationResourceConfigNoBase(testHabitatPlanPath, outputPath),
				Check: resource.ComposeAggregateTestCheckFunc(
					resource.TestCheckResourceAttr(resourceHabitatMigrationTest, "base_image", "ubuntu:latest"),
					resource.TestCheckResourceAttrSet(resourceHabitatMigrationTest, "dockerfile_content"),
				),
			},
		},
	})
}

// TestAccHabitatMigrationResourceDeleteVerification tests delete with file verification
func TestAccHabitatMigrationResourceDeleteVerification(t *testing.T) {
	outputPath := "/workspaces/souschef/test-output/habitat/delete_verify"
	os.MkdirAll(outputPath, 0755)

	resource.Test(t, resource.TestCase{
		PreCheck:                 func() { testAccPreCheck(t) },
		ProtoV6ProviderFactories: testAccProtoV6ProviderFactories,
		Steps: []resource.TestStep{
			{
				Config: testAccHabitatMigrationResourceConfigBase(testHabitatPlanPath, outputPath, ubuntuImageAttr),
			},
		},
		CheckDestroy: func(s *terraform.State) error {
			dockerfilePath := filepath.Join(outputPath, "Dockerfile")
			if _, err := os.Stat(dockerfilePath); err == nil {
				return fmt.Errorf("Dockerfile should have been deleted: %s", dockerfilePath)
			}
			return nil
		},
	})
}

// TestAccHabitatMigrationResourceMultipleOutputPaths tests multiple output locations
func TestAccHabitatMigrationResourceMultipleOutputPaths(t *testing.T) {
	outputPaths := []string{
		"/workspaces/souschef/test-output/habitat/out1",
		"/workspaces/souschef/test-output/habitat/out2",
		"/workspaces/souschef/test-output/habitat/out3",
	}

	for i, outputPath := range outputPaths {
		t.Run(fmt.Sprintf("output%d", i+1), func(t *testing.T) {
			os.MkdirAll(outputPath, 0755)

			resource.Test(t, resource.TestCase{
				PreCheck:                 func() { testAccPreCheck(t) },
				ProtoV6ProviderFactories: testAccProtoV6ProviderFactories,
				Steps: []resource.TestStep{
					{
						Config: testAccHabitatMigrationResourceConfigBase(testHabitatPlanPath, outputPath, ubuntuImageAttr),
						Check: resource.ComposeAggregateTestCheckFunc(
							resource.TestCheckResourceAttr(resourceHabitatMigrationTest, "output_path", outputPath),
						),
					},
				},
			})
		})
	}
}

func testAccHabitatMigrationResourceConfigBase(planPath, outputPath, baseImage string) string {
	return fmt.Sprintf(`
variable "souschef_path" {
  type = string
}

provider "souschef" {
  souschef_path = var.souschef_path
}

resource "souschef_habitat_migration" "test" {
  plan_path   = %[1]q
  output_path = %[2]q
  base_image  = %[3]q
}
`, planPath, outputPath, baseImage)
}

func testAccHabitatMigrationResourceConfigNoBase(planPath, outputPath string) string {
	return fmt.Sprintf(`
variable "souschef_path" {
  type = string
}

provider "souschef" {
  souschef_path = var.souschef_path
}

resource "souschef_habitat_migration" "test" {
  plan_path   = %[1]q
  output_path = %[2]q
}
`, planPath, outputPath)
}
