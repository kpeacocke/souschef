package provider

import (
	"fmt"
	"testing"

	"github.com/hashicorp/terraform-plugin-testing/helper/resource"
)

var (
	testAssessmentResourceName = "data.souschef_assessment.test"
	testCookbookPath           = getFixturePath("sample_cookbook")
)

func TestAccAssessmentDataSource(t *testing.T) {
	resource.Test(t, resource.TestCase{
		PreCheck:                 func() { testAccPreCheck(t) },
		ProtoV6ProviderFactories: testAccProtoV6ProviderFactories,
		Steps: []resource.TestStep{
			// Read testing
			{
				Config: testAccAssessmentDataSourceConfig(testCookbookPath),
				Check: resource.ComposeAggregateTestCheckFunc(
					resource.TestCheckResourceAttr(testAssessmentResourceName, "cookbook_path", testCookbookPath),
					resource.TestCheckResourceAttrSet(testAssessmentResourceName, "id"),
					resource.TestCheckResourceAttrSet(testAssessmentResourceName, "complexity"),
					resource.TestCheckResourceAttrSet(testAssessmentResourceName, "recipe_count"),
					resource.TestCheckResourceAttrSet(testAssessmentResourceName, "resource_count"),
					resource.TestCheckResourceAttrSet(testAssessmentResourceName, "estimated_hours"),
					resource.TestCheckResourceAttrSet(testAssessmentResourceName, "recommendations"),
				),
			},
		},
	})
}

func testAccAssessmentDataSourceConfig(cookbookPath string) string {
	return fmt.Sprintf(`
variable "souschef_path" {
  type = string
}

provider "souschef" {
  souschef_path = var.souschef_path
}

data "souschef_assessment" "test" {
  cookbook_path = %[1]q
}
`, cookbookPath)
}
