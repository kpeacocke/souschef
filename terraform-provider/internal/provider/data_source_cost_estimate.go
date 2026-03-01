// Package provider implements the SousChef Terraform provider data sources
package provider

import (
	"context"
	"fmt"

	"github.com/hashicorp/terraform-plugin-framework/datasource"
	"github.com/hashicorp/terraform-plugin-framework/datasource/schema"
	"github.com/hashicorp/terraform-plugin-framework/types"
)

// Ensure the implementation satisfies the expected interfaces
var (
	_ datasource.DataSource              = &costEstimateDataSource{}
	_ datasource.DataSourceWithConfigure = &costEstimateDataSource{}
)

// NewCostEstimateDataSource creates a new cost estimate data source
func NewCostEstimateDataSource() datasource.DataSource {
	return &costEstimateDataSource{}
}

// costEstimateDataSource is the data source implementation
type costEstimateDataSource struct {
	client *SousChefClient
}

// costEstimateDataSourceModel describes the data source data model
type costEstimateDataSourceModel struct {
	ID                  types.String  `tfsdk:"id"`
	CookbookPath        types.String  `tfsdk:"cookbook_path"`
	Complexity          types.String  `tfsdk:"complexity"`
	RecipeCount         types.Int64   `tfsdk:"recipe_count"`
	ResourceCount       types.Int64   `tfsdk:"resource_count"`
	EstimatedHours      types.Float64 `tfsdk:"estimated_hours"`
	EstimatedCostUSD    types.Float64 `tfsdk:"estimated_cost_usd"`
	DeveloperHourlyRate types.Float64 `tfsdk:"developer_hourly_rate"`
	InfrastructureCost  types.Float64 `tfsdk:"infrastructure_cost"`
	TotalProjectCostUSD types.Float64 `tfsdk:"total_project_cost_usd"`
	Recommendations     types.String  `tfsdk:"recommendations"`
}

// Metadata returns the data source type name
func (d *costEstimateDataSource) Metadata(_ context.Context, req datasource.MetadataRequest, resp *datasource.MetadataResponse) {
	resp.TypeName = req.ProviderTypeName + "_cost_estimate"
}

// Schema defines the schema for the data source
func (d *costEstimateDataSource) Schema(_ context.Context, _ datasource.SchemaRequest, resp *datasource.SchemaResponse) {
	resp.Schema = schema.Schema{
		MarkdownDescription: "Fetches migration cost estimation for a Chef cookbook, suitable for Terraform Cloud cost estimation features.",

		Attributes: map[string]schema.Attribute{
			"id": schema.StringAttribute{
				Computed:            true,
				MarkdownDescription: "Unique identifier (cookbook path)",
			},
			"cookbook_path": schema.StringAttribute{
				Required:            true,
				MarkdownDescription: "Path to the Chef cookbook directory",
			},
			"complexity": schema.StringAttribute{
				Computed:            true,
				MarkdownDescription: "Migration complexity level (Low/Medium/High)",
			},
			"recipe_count": schema.Int64Attribute{
				Computed:            true,
				MarkdownDescription: "Number of recipes in cookbook",
			},
			"resource_count": schema.Int64Attribute{
				Computed:            true,
				MarkdownDescription: "Total Chef resources across all recipes",
			},
			"estimated_hours": schema.Float64Attribute{
				Computed:            true,
				MarkdownDescription: "Estimated migration effort in hours",
			},
			"estimated_cost_usd": schema.Float64Attribute{
				Computed:            true,
				MarkdownDescription: "Estimated labour cost in USD based on developer hourly rate",
			},
			"developer_hourly_rate": schema.Float64Attribute{
				Optional:            true,
				MarkdownDescription: "Developer hourly rate in USD for cost calculation (default: 150)",
			},
			"infrastructure_cost": schema.Float64Attribute{
				Optional:            true,
				MarkdownDescription: "Additional infrastructure/tooling cost in USD (default: 500)",
			},
			"total_project_cost_usd": schema.Float64Attribute{
				Computed:            true,
				MarkdownDescription: "Total estimated project cost including labour and infrastructure",
			},
			"recommendations": schema.StringAttribute{
				Computed:            true,
				MarkdownDescription: "Migration recommendations and best practices",
			},
		},
	}
}

// Configure adds the provider configured client to the data source
func (d *costEstimateDataSource) Configure(_ context.Context, req datasource.ConfigureRequest, resp *datasource.ConfigureResponse) {
	if req.ProviderData == nil {
		return
	}

	client, ok := req.ProviderData.(*SousChefClient)
	if !ok {
		resp.Diagnostics.AddError(
			"Unexpected Data Source Configure Type",
			fmt.Sprintf("Expected *SousChefClient, got: %T", req.ProviderData),
		)
		return
	}

	d.client = client
}

// getClient returns the configured SousChef client. Used for testing.
func (d *costEstimateDataSource) getClient() *SousChefClient {
	return d.client
}

// Read refreshes the Terraform state with the latest data
func (d *costEstimateDataSource) Read(ctx context.Context, req datasource.ReadRequest, resp *datasource.ReadResponse) {
	var config costEstimateDataSourceModel
	diags := req.Config.Get(ctx, &config)
	resp.Diagnostics.Append(diags...)
	if resp.Diagnostics.HasError() {
		return
	}

	cookbookPath := config.CookbookPath.ValueString()

	// Default rates
	developerRate := 150.0
	if !config.DeveloperHourlyRate.IsNull() {
		developerRate = config.DeveloperHourlyRate.ValueFloat64()
	}

	infraCost := 500.0
	if !config.InfrastructureCost.IsNull() {
		infraCost = config.InfrastructureCost.ValueFloat64()
	}

	// Get assessment data using existing assess-cookbook command
	// This would normally call the CLI, but for cost estimation we'll calculate based on patterns

	// For now, we'll do a simple analysis similar to assessment
	// In production, this would call: souschef assess-cookbook --cookbook-path <path> --format json

	// Simplified analysis (in production this would parse actual cookbook)
	recipeCount := int64(1)    // Placeholder
	resourceCount := int64(10) // Placeholder
	complexity := "Medium"

	estimatedHours, labourCost, totalCost := calculateCostEstimate(complexity, resourceCount, developerRate, infraCost)

	recommendations := fmt.Sprintf(
		"Cookbook requires approximately %.1f hours of migration effort. "+
			"Estimated labour cost: $%.2f USD (at $%.2f/hour). "+
			"Including infrastructure costs: $%.2f USD total. "+
			"Complexity level: %s.",
		estimatedHours, labourCost, developerRate, totalCost, complexity,
	)

	// Set computed values
	config.ID = types.StringValue(cookbookPath)
	config.Complexity = types.StringValue(complexity)
	config.RecipeCount = types.Int64Value(recipeCount)
	config.ResourceCount = types.Int64Value(resourceCount)
	config.EstimatedHours = types.Float64Value(estimatedHours)
	config.EstimatedCostUSD = types.Float64Value(labourCost)
	config.DeveloperHourlyRate = types.Float64Value(developerRate)
	config.InfrastructureCost = types.Float64Value(infraCost)
	config.TotalProjectCostUSD = types.Float64Value(totalCost)
	config.Recommendations = types.StringValue(recommendations)

	diags = resp.State.Set(ctx, &config)
	resp.Diagnostics.Append(diags...)
}

func calculateCostEstimate(complexity string, resourceCount int64, developerRate float64, infraCost float64) (float64, float64, float64) {
	var estimatedHours float64
	switch complexity {
	case "Low":
		estimatedHours = float64(resourceCount) * 0.5
	case "Medium":
		estimatedHours = float64(resourceCount) * 1.0
	case "High":
		estimatedHours = float64(resourceCount) * 1.5
	default:
		estimatedHours = float64(resourceCount) * 1.0
	}

	labourCost := estimatedHours * developerRate
	totalCost := labourCost + infraCost

	return estimatedHours, labourCost, totalCost
}
