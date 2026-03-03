// Package provider implements the SousChef Terraform provider data sources
package provider

import (
	"context"
	"encoding/json"
	"fmt"

	"github.com/hashicorp/terraform-plugin-framework/datasource"
	"github.com/hashicorp/terraform-plugin-framework/datasource/schema"
	"github.com/hashicorp/terraform-plugin-framework/types"
	"github.com/hashicorp/terraform-plugin-log/tflog"
)

// Ensure the implementation satisfies the expected interfaces
var (
	_ datasource.DataSource              = &assessmentDataSource{}
	_ datasource.DataSourceWithConfigure = &assessmentDataSource{}
)

// NewAssessmentDataSource is a helper function to simplify the provider implementation.
func NewAssessmentDataSource() datasource.DataSource {
	return &assessmentDataSource{}
}

// assessmentDataSource is the data source implementation.
type assessmentDataSource struct {
	client *SousChefClient
}

// assessmentDataSourceModel maps the data source schema data.
type assessmentDataSourceModel struct {
	ID              types.String  `tfsdk:"id"`
	CookbookPath    types.String  `tfsdk:"cookbook_path"`
	Complexity      types.String  `tfsdk:"complexity"`
	RecipeCount     types.Int64   `tfsdk:"recipe_count"`
	ResourceCount   types.Int64   `tfsdk:"resource_count"`
	EstimatedHours  types.Float64 `tfsdk:"estimated_hours"`
	Recommendations types.String  `tfsdk:"recommendations"`
}

// Metadata returns the data source type name.
func (d *assessmentDataSource) Metadata(_ context.Context, req datasource.MetadataRequest, resp *datasource.MetadataResponse) {
	resp.TypeName = req.ProviderTypeName + "_assessment"
}

// Schema defines the schema for the data source.
func (d *assessmentDataSource) Schema(_ context.Context, _ datasource.SchemaRequest, resp *datasource.SchemaResponse) {
	resp.Schema = schema.Schema{
		Description: "Fetches migration assessment for a Chef cookbook.",
		Attributes: map[string]schema.Attribute{
			"id": schema.StringAttribute{
				Description: "Unique identifier (cookbook path).",
				Computed:    true,
			},
			"cookbook_path": schema.StringAttribute{
				Description: "Path to the Chef cookbook directory.",
				Required:    true,
			},
			"complexity": schema.StringAttribute{
				Description: "Migration complexity level (Low/Medium/High).",
				Computed:    true,
			},
			"recipe_count": schema.Int64Attribute{
				Description: "Number of recipes in cookbook.",
				Computed:    true,
			},
			"resource_count": schema.Int64Attribute{
				Description: "Total Chef resources across all recipes.",
				Computed:    true,
			},
			"estimated_hours": schema.Float64Attribute{
				Description: "Estimated migration effort in hours.",
				Computed:    true,
			},
			"recommendations": schema.StringAttribute{
				Description: "Migration recommendations and best practices.",
				Computed:    true,
			},
		},
	}
}

// Configure adds the provider configured client to the data source.
func (d *assessmentDataSource) Configure(_ context.Context, req datasource.ConfigureRequest, resp *datasource.ConfigureResponse) {
	if req.ProviderData == nil {
		return
	}

	client, ok := req.ProviderData.(*SousChefClient)

	if !ok {
		resp.Diagnostics.AddError(
			"Unexpected Data Source Configure Type",
			fmt.Sprintf("Expected *SousChefClient, got: %T. Please report this issue to the provider developers.", req.ProviderData),
		)
		return
	}

	d.client = client
}

// Read refreshes the Terraform state with the latest data.
func (d *assessmentDataSource) Read(ctx context.Context, req datasource.ReadRequest, resp *datasource.ReadResponse) {
	var config assessmentDataSourceModel
	diags := req.Config.Get(ctx, &config)
	resp.Diagnostics.Append(diags...)
	if resp.Diagnostics.HasError() {
		return
	}

	cookbookPath := config.CookbookPath.ValueString()

	// Call souschef CLI to assess cookbook
	cmd := execCommandContext(ctx, d.client.Path, "assess-cookbook",
		"--cookbook-path", cookbookPath,
		"--format", "json",
	)

	tflog.Debug(ctx, "Executing SousChef assessment", map[string]interface{}{
		"command": cmd.String(),
	})

	output, err := cmd.CombinedOutput()
	if err != nil {
		resp.Diagnostics.AddError(
			"Error assessing cookbook",
			fmt.Sprintf("Could not assess cookbook: %s\n%s", err, string(output)),
		)
		return
	}

	// Parse JSON output
	var assessment struct {
		Complexity      string  `json:"complexity"`
		RecipeCount     int64   `json:"recipe_count"`
		ResourceCount   int64   `json:"resource_count"`
		EstimatedHours  float64 `json:"estimated_hours"`
		Recommendations string  `json:"recommendations"`
	}

	if err := json.Unmarshal(output, &assessment); err != nil {
		resp.Diagnostics.AddError(
			"Error parsing assessment",
			fmt.Sprintf("Could not parse JSON output: %s", err),
		)
		return
	}

	// Set state
	config.ID = types.StringValue(cookbookPath)
	config.Complexity = types.StringValue(assessment.Complexity)
	config.RecipeCount = types.Int64Value(assessment.RecipeCount)
	config.ResourceCount = types.Int64Value(assessment.ResourceCount)
	config.EstimatedHours = types.Float64Value(assessment.EstimatedHours)
	config.Recommendations = types.StringValue(assessment.Recommendations)

	diags = resp.State.Set(ctx, &config)
	resp.Diagnostics.Append(diags...)
}
