// Package provider implements the SousChef Terraform provider
package provider

import (
	"context"

	"github.com/hashicorp/terraform-plugin-framework/datasource"
	"github.com/hashicorp/terraform-plugin-framework/path"
	"github.com/hashicorp/terraform-plugin-framework/provider"
	"github.com/hashicorp/terraform-plugin-framework/provider/schema"
	"github.com/hashicorp/terraform-plugin-framework/resource"
	"github.com/hashicorp/terraform-plugin-framework/types"
)

// Ensure the implementation satisfies the expected interfaces
var (
	_ provider.Provider = &SousChefProvider{}
)

// SousChefProvider defines the provider implementation.
type SousChefProvider struct {
	// version is set to the provider version on release
	version string
}

// SousChefProviderModel describes the provider data model.
type SousChefProviderModel struct {
	SousChefPath types.String `tfsdk:"souschef_path"`
}

// New is a helper function to simplify provider server setup.
func New(version string) func() provider.Provider {
	return func() provider.Provider {
		return &SousChefProvider{
			version: version,
		}
	}
}

// Metadata returns the provider type name.
func (p *SousChefProvider) Metadata(_ context.Context, _ provider.MetadataRequest, resp *provider.MetadataResponse) {
	resp.TypeName = "souschef"
	resp.Version = p.version
}

// Schema defines the provider-level schema for configuration data.
func (p *SousChefProvider) Schema(_ context.Context, _ provider.SchemaRequest, resp *provider.SchemaResponse) {
	resp.Schema = schema.Schema{
		Description: "Terraform provider for managing Chef to Ansible migrations using SousChef.",
		Attributes: map[string]schema.Attribute{
			"souschef_path": schema.StringAttribute{
				Description: "Path to the SousChef CLI executable. Defaults to 'souschef' in PATH.",
				Optional:    true,
			},
		},
	}
}

// Configure prepares a SousChef API client for data sources and resources.
func (p *SousChefProvider) Configure(ctx context.Context, req provider.ConfigureRequest, resp *provider.ConfigureResponse) {
	var config SousChefProviderModel

	resp.Diagnostics.Append(req.Config.Get(ctx, &config)...)

	if resp.Diagnostics.HasError() {
		return
	}

	// Configuration values are now available via config
	if config.SousChefPath.IsUnknown() {
		resp.Diagnostics.AddAttributeError(
			path.Root("souschef_path"),
			"Unknown SousChef Path",
			"The provider cannot create the SousChef client as there is an unknown configuration value for the SousChef path.",
		)
	}

	if resp.Diagnostics.HasError() {
		return
	}

	// Default values
	sousChefPath := "souschef"
	if !config.SousChefPath.IsNull() {
		sousChefPath = config.SousChefPath.ValueString()
	}

	// Create client data that resources can use
	client := &SousChefClient{
		Path: sousChefPath,
	}

	resp.DataSourceData = client
	resp.ResourceData = client
}

// SousChefClient is a simple client that wraps CLI calls
type SousChefClient struct {
	Path string
}

// DataSources defines the data sources implemented in the provider.
func (p *SousChefProvider) DataSources(_ context.Context) []func() datasource.DataSource {
	return []func() datasource.DataSource{
		NewAssessmentDataSource,
		NewCostEstimateDataSource,
	}
}

// Resources defines the resources implemented in the provider.
func (p *SousChefProvider) Resources(_ context.Context) []func() resource.Resource {
	return []func() resource.Resource{
		NewMigrationResource,
		NewBatchMigrationResource,
		NewHabitatMigrationResource,
		NewInSpecMigrationResource,
	}
}
