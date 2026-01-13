package provider

import (
	"fmt"
	"testing"

	"github.com/hashicorp/terraform-plugin-testing/helper/resource"
)

var (
	testCostEstimateResourceName = "data.souschef_cost_estimate.test"
	testCostCookbookPath         = getFixturePath("sample_cookbook")
)

func TestAccCostEstimateDataSource(t *testing.T) {
	resource.Test(t, resource.TestCase{
		PreCheck:                 func() { testAccPreCheck(t) },
		ProtoV6ProviderFactories: testAccProtoV6ProviderFactories,
		Steps: []resource.TestStep{
			// Read testing with default rates
			{
				Config: testAccCostEstimateDataSourceConfig(testCostCookbookPath, 0, 0),
				Check: resource.ComposeAggregateTestCheckFunc(
					resource.TestCheckResourceAttr(testCostEstimateResourceName, "cookbook_path", testCostCookbookPath),
					resource.TestCheckResourceAttr(testCostEstimateResourceName, "developer_hourly_rate", "150"),
					resource.TestCheckResourceAttr(testCostEstimateResourceName, "infrastructure_cost", "500"),
					resource.TestCheckResourceAttrSet(testCostEstimateResourceName, "id"),
					resource.TestCheckResourceAttrSet(testCostEstimateResourceName, "complexity"),
					resource.TestCheckResourceAttrSet(testCostEstimateResourceName, "recipe_count"),
					resource.TestCheckResourceAttrSet(testCostEstimateResourceName, "resource_count"),
					resource.TestCheckResourceAttrSet(testCostEstimateResourceName, "estimated_hours"),
					resource.TestCheckResourceAttrSet(testCostEstimateResourceName, "estimated_cost_usd"),
					resource.TestCheckResourceAttrSet(testCostEstimateResourceName, "total_project_cost_usd"),
					resource.TestCheckResourceAttrSet(testCostEstimateResourceName, "recommendations"),
				),
			},
			// Read testing with custom rates
			{
				Config: testAccCostEstimateDataSourceConfig(testCostCookbookPath, 200, 1000),
				Check: resource.ComposeAggregateTestCheckFunc(
					resource.TestCheckResourceAttr(testCostEstimateResourceName, "developer_hourly_rate", "200"),
					resource.TestCheckResourceAttr(testCostEstimateResourceName, "infrastructure_cost", "1000"),
					resource.TestCheckResourceAttrSet(testCostEstimateResourceName, "estimated_cost_usd"),
					resource.TestCheckResourceAttrSet(testCostEstimateResourceName, "total_project_cost_usd"),
				),
			},
		},
	})
}

func testAccCostEstimateDataSourceConfig(cookbookPath string, hourlyRate, infraCost float64) string {
	config := fmt.Sprintf(`
variable "souschef_path" {
  type = string
}

provider "souschef" {
  souschef_path = var.souschef_path
}

data "souschef_cost_estimate" "test" {
  cookbook_path = %[1]q`, cookbookPath)

	if hourlyRate > 0 {
		config += fmt.Sprintf(`
  developer_hourly_rate = %f`, hourlyRate)
	}

	if infraCost > 0 {
		config += fmt.Sprintf(`
  infrastructure_cost = %f`, infraCost)
	}

	config += `
}
`
	return config
}
