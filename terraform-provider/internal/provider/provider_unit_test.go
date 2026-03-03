// Package provider contains unit tests for the SousChef Terraform provider.
package provider

import (
	"context"
	"os"
	"path/filepath"
	"testing"

	"github.com/hashicorp/terraform-plugin-framework/datasource"
	"github.com/hashicorp/terraform-plugin-framework/provider"
	"github.com/hashicorp/terraform-plugin-framework/providerserver"
	"github.com/hashicorp/terraform-plugin-framework/resource"
)

func TestSousChefProviderNew(t *testing.T) {
	factory := New("1.0.0")
	if factory == nil {
		t.Fatal("expected non-nil provider factory")
	}

	p := factory()
	if p == nil {
		t.Fatal("expected non-nil provider")
	}

	scp, ok := p.(*SousChefProvider)
	if !ok {
		t.Fatal("expected *SousChefProvider")
	}

	ValidateConfigValue(t, scp.version, "1.0.0")
}

func TestSousChefProviderNewEmpty(t *testing.T) {
	factory := New("")
	p := factory()

	scp, ok := p.(*SousChefProvider)
	if !ok {
		t.Fatal("expected *SousChefProvider")
	}

	ValidateConfigValue(t, scp.version, "")
}

func TestSousChefProviderMetadata(t *testing.T) {
	p := &SousChefProvider{version: "2.0.0"}
	req := provider.MetadataRequest{}
	resp := &provider.MetadataResponse{}

	p.Metadata(context.Background(), req, resp)

	ValidateConfigValue(t, resp.TypeName, "souschef")
	ValidateConfigValue(t, resp.Version, "2.0.0")
}

func TestSousChefProviderMetadataEmpty(t *testing.T) {
	p := &SousChefProvider{}
	req := provider.MetadataRequest{}
	resp := &provider.MetadataResponse{}

	p.Metadata(context.Background(), req, resp)

	ValidateConfigValue(t, resp.TypeName, "souschef")
	ValidateConfigValue(t, resp.Version, "")
}

func TestSousChefProviderSchema(t *testing.T) {
	p := &SousChefProvider{}
	req := provider.SchemaRequest{}
	resp := &provider.SchemaResponse{}

	p.Schema(context.Background(), req, resp)

	if resp.Schema.Description == "" {
		t.Error("expected non-empty schema description")
	}

	if _, ok := resp.Schema.Attributes["souschef_path"]; !ok {
		t.Error("expected 'souschef_path' attribute in schema")
	}
}

func TestSousChefProviderResources(t *testing.T) {
	p := &SousChefProvider{}
	resources := p.Resources(context.Background())

	if len(resources) == 0 {
		t.Fatal("expected provider to register resources")
	}

	for i, factory := range resources {
		r := factory()
		if r == nil {
			t.Errorf("resource factory %d returned nil", i)
		}
	}
}

func TestSousChefProviderDataSources(t *testing.T) {
	p := &SousChefProvider{}
	dataSources := p.DataSources(context.Background())

	if len(dataSources) == 0 {
		t.Fatal("expected provider to register data sources")
	}

	for i, factory := range dataSources {
		ds := factory()
		if ds == nil {
			t.Errorf("data source factory %d returned nil", i)
		}
	}
}

func TestSousChefProviderResourcesImplementInterfaces(t *testing.T) {
	p := &SousChefProvider{}
	resources := p.Resources(context.Background())

	for i, factory := range resources {
		r := factory()
		if r == nil {
			t.Errorf("resource %d returned nil", i)
		}
	}
}

func TestSousChefProviderDataSourcesImplementInterfaces(t *testing.T) {
	p := &SousChefProvider{}
	dataSources := p.DataSources(context.Background())

	for i, factory := range dataSources {
		ds := factory()
		if ds == nil {
			t.Errorf("data source %d returned nil", i)
		}
	}
}

func TestSousChefClientPath(t *testing.T) {
	client := &SousChefClient{Path: "souschef"}
	ValidateConfigValue(t, client.Path, "souschef")
}

func TestSousChefClientCustomPath(t *testing.T) {
	customPath := "/usr/local/bin/souschef"
	client := &SousChefClient{Path: customPath}
	ValidateConfigValue(t, client.Path, customPath)
}

func TestSousChefClientEmptyPath(t *testing.T) {
	client := &SousChefClient{Path: ""}
	ValidateConfigValue(t, client.Path, "")
}

func TestProviderSchemaAttributeOptional(t *testing.T) {
	p := &SousChefProvider{}
	req := provider.SchemaRequest{}
	resp := &provider.SchemaResponse{}

	p.Schema(context.Background(), req, resp)

	attr, ok := resp.Schema.Attributes["souschef_path"]
	if !ok {
		t.Fatal("expected 'souschef_path' attribute")
	}

	if attr.IsRequired() {
		t.Error("expected 'souschef_path' to be optional, not required")
	}
}

func TestProviderProtocol6Server(t *testing.T) {
	server := providerserver.NewProtocol6(New("test")())
	if server == nil {
		t.Fatal("expected non-nil protocol v6 server")
	}
}

func TestProviderProtocol6WithError(t *testing.T) {
	factory := providerserver.NewProtocol6WithError(New("test")())

	server, err := factory()
	if err != nil {
		t.Fatalf("unexpected error creating provider server: %v", err)
	}

	if server == nil {
		t.Fatal("expected non-nil provider server")
	}

}

func TestGetFixturePath(t *testing.T) {
	path := getFixturePath("sample_cookbook")
	if path == "" {
		t.Fatal("expected non-empty fixture path")
	}

	if !filepath.IsAbs(path) {
		t.Errorf("expected absolute path, got %q", path)
	}
}

func TestGetFixturePathMultiple(t *testing.T) {
	fixtures := []string{
		"sample_cookbook",
		"habitat_package",
		"sample_inspec_profile",
	}

	for _, fixtureName := range fixtures {
		path := getFixturePath(fixtureName)
		if path == "" {
			t.Errorf("expected non-empty path for fixture %q", fixtureName)
		}
	}
}

func TestNewMigrationResource(t *testing.T) {
	r := NewMigrationResource()
	if r == nil {
		t.Fatal("expected non-nil migration resource")
	}
}

func TestNewBatchMigrationResource(t *testing.T) {
	r := NewBatchMigrationResource()
	if r == nil {
		t.Fatal("expected non-nil batch migration resource")
	}
}

func TestNewHabitatMigrationResource(t *testing.T) {
	r := NewHabitatMigrationResource()
	if r == nil {
		t.Fatal("expected non-nil habitat migration resource")
	}
}

func TestNewInSpecMigrationResource(t *testing.T) {
	r := NewInSpecMigrationResource()
	if r == nil {
		t.Fatal("expected non-nil inspec migration resource")
	}
}

func TestNewAssessmentDataSource(t *testing.T) {
	ds := NewAssessmentDataSource()
	if ds == nil {
		t.Fatal("expected non-nil assessment data source")
	}
}

func TestNewCostEstimateDataSource(t *testing.T) {
	ds := NewCostEstimateDataSource()
	if ds == nil {
		t.Fatal("expected non-nil cost estimate data source")
	}
}

func TestMigrationResourceSchema(t *testing.T) {
	r := &migrationResource{}
	req := resource.SchemaRequest{}
	resp := &resource.SchemaResponse{}

	r.Schema(context.Background(), req, resp)

	expectedAttrs := []string{
		"id", "cookbook_path", "output_path", "cookbook_name",
		"recipe_name", "playbook_content",
	}

	for _, attr := range expectedAttrs {
		if _, ok := resp.Schema.Attributes[attr]; !ok {
			t.Errorf("expected attribute %q in migration resource schema", attr)
		}
	}
}

func TestMigrationResourceMetadata(t *testing.T) {
	r := &migrationResource{}
	req := resource.MetadataRequest{ProviderTypeName: "souschef"}
	resp := &resource.MetadataResponse{}

	r.Metadata(context.Background(), req, resp)

	ValidateConfigValue(t, resp.TypeName, "souschef_migration")
}

func TestBatchMigrationResourceMetadata(t *testing.T) {
	r := &batchMigrationResource{}
	req := resource.MetadataRequest{ProviderTypeName: "souschef"}
	resp := &resource.MetadataResponse{}

	r.Metadata(context.Background(), req, resp)

	ValidateConfigValue(t, resp.TypeName, "souschef_batch_migration")
}

func TestHabitatMigrationResourceMetadata(t *testing.T) {
	r := &habitatMigrationResource{}
	req := resource.MetadataRequest{ProviderTypeName: "souschef"}
	resp := &resource.MetadataResponse{}

	r.Metadata(context.Background(), req, resp)

	ValidateConfigValue(t, resp.TypeName, "souschef_habitat_migration")
}

func TestInSpecMigrationResourceMetadata(t *testing.T) {
	r := &inspecMigrationResource{}
	req := resource.MetadataRequest{ProviderTypeName: "souschef"}
	resp := &resource.MetadataResponse{}

	r.Metadata(context.Background(), req, resp)

	ValidateConfigValue(t, resp.TypeName, "souschef_inspec_migration")
}

func TestAssessmentDataSourceMetadata(t *testing.T) {
	ds := &assessmentDataSource{}
	req := datasource.MetadataRequest{ProviderTypeName: "souschef"}
	resp := &datasource.MetadataResponse{}

	ds.Metadata(context.Background(), req, resp)

	ValidateConfigValue(t, resp.TypeName, "souschef_assessment")
}

func TestCostEstimateDataSourceMetadata(t *testing.T) {
	ds := &costEstimateDataSource{}
	req := datasource.MetadataRequest{ProviderTypeName: "souschef"}
	resp := &datasource.MetadataResponse{}

	ds.Metadata(context.Background(), req, resp)

	ValidateConfigValue(t, resp.TypeName, "souschef_cost_estimate")
}

func TestAccPreCheckDefaultPath(t *testing.T) {
	// Ensure pre-check runs without panicking when no env var is set.
	originalVal := os.Getenv("TF_VAR_souschef_path")
	os.Unsetenv("TF_VAR_souschef_path")
	defer func() {
		if originalVal != "" {
			os.Setenv("TF_VAR_souschef_path", originalVal)
		}
	}()

	// testAccPreCheck should not panic
	testAccPreCheck(t)
}
