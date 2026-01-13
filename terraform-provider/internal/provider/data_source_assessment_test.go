package provider

import (
	"fmt"
	"testing"

	"github.com/hashicorp/terraform-plugin-testing/helper/resource"
)

func TestAccAssessmentDataSource(t *testing.T) {
	resource.Test(t, resource.TestCase{
		PreCheck:                 func() { testAccPreCheck(t) },
		ProtoV6ProviderFactories: testAccProtoV6ProviderFactories,
		Steps: []resource.TestStep{
			// Read testing
			{
				Config: testAccAssessmentDataSourceConfig("/tmp/cookbooks/test"),
				Check: resource.ComposeAggregateTestCheckFunc(
					resource.TestCheckResourceAttr("data.souschef_assessment.test", "cookbook_path", "/tmp/cookbooks/test"),
					resource.TestCheckResourceAttrSet("data.souschef_assessment.test", "id"),
					resource.TestCheckResourceAttrSet("data.souschef_assessment.test", "complexity"),
					resource.TestCheckResourceAttrSet("data.souschef_assessment.test", "recipe_count"),
					resource.TestCheckResourceAttrSet("data.souschef_assessment.test", "resource_count"),
					resource.TestCheckResourceAttrSet("data.souschef_assessment.test", "estimated_hours"),
					resource.TestCheckResourceAttrSet("data.souschef_assessment.test", "recommendations"),
				),
			},
		},
	})
}

func testAccAssessmentDataSourceConfig(cookbookPath string) string {
	return fmt.Sprintf(`
data "souschef_assessment" "test" {
  cookbook_path = %[1]q
}
`, cookbookPath)
}
