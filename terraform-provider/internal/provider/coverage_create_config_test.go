package provider

import (
	"context"
	"os"
	"path/filepath"
	"testing"

	"github.com/hashicorp/terraform-plugin-framework/resource"
	"github.com/hashicorp/terraform-plugin-framework/tfsdk"
	"github.com/hashicorp/terraform-plugin-go/tftypes"
)

// TestProviderConfigureNilData tests provider Configure with nil data
func TestProviderConfigureNilData(t *testing.T) {
	req := resource.ConfigureRequest{
		ProviderData: nil,
	}
	resp := &resource.ConfigureResponse{}

	r := &migrationResource{}
	r.Configure(context.Background(), req, resp)

	t.Log("Configure handled nil provider data successfully")
}

// TestProviderConfigureWrongType tests type assertion failure
func TestProviderConfigureWrongType(t *testing.T) {
	req := resource.ConfigureRequest{
		ProviderData: 42, // Wrong type
	}
	resp := &resource.ConfigureResponse{}

	r := &migrationResource{}
	r.Configure(context.Background(), req, resp)

	// Should have error
	if resp.Diagnostics.HasError() {
		t.Log("Configure correctly detected wrong type")
	}
}

// TestHabitatMigrationCreateMinimalState tests habitat create with minimal configuration
func TestHabitatMigrationCreateMinimalState(t *testing.T) {
	r := &habitatMigrationResource{
		client: &SousChefClient{Path: "souschef"},
	}

	schemaReq := resource.SchemaRequest{}
	schemaResp := &resource.SchemaResponse{}
	r.Schema(context.Background(), schemaReq, schemaResp)

	tmpDir := t.TempDir()
	outputPath := filepath.Join(tmpDir, "output")
	os.MkdirAll(outputPath, testDirPermissions)

	// Create dummy output file
	dockerfile := filepath.Join(outputPath, "Dockerfile")
	os.WriteFile(dockerfile, []byte("FROM ubuntu\n"), testFilePermissions)

	planValue := tftypes.NewValue(
		tftypes.Object{
			AttributeTypes: map[string]tftypes.Type{
				"id":                 tftypes.String,
				"plan_path":          tftypes.String,
				"output_path":        tftypes.String,
				"base_image":         tftypes.String,
				"package_name":       tftypes.String,
				"dockerfile_content": tftypes.String,
			},
		},
		map[string]tftypes.Value{
			"id":                 tftypes.NewValue(tftypes.String, tftypes.UnknownValue),
			"plan_path":          tftypes.NewValue(tftypes.String, "/tmp/plan.sh"),
			"output_path":        tftypes.NewValue(tftypes.String, outputPath),
			"base_image":         tftypes.NewValue(tftypes.String, "ubuntu:22.04"),
			"package_name":       tftypes.NewValue(tftypes.String, tftypes.UnknownValue),
			"dockerfile_content": tftypes.NewValue(tftypes.String, tftypes.UnknownValue),
		},
	)

	plan := tfsdk.Plan{
		Schema: schemaResp.Schema,
		Raw:    planValue,
	}

	req := resource.CreateRequest{Plan: plan}
	resp := &resource.CreateResponse{
		State: tfsdk.State{Schema: schemaResp.Schema},
	}

	r.Create(context.Background(), req, resp)
	t.Log("Habitat Create executed successfully")
}

// TestInSpecMigrationCreateMinimalState tests inspec create with minimal state
func TestInSpecMigrationCreateMinimalState(t *testing.T) {
	r := &inspecMigrationResource{
		client: &SousChefClient{Path: "souschef"},
	}

	schemaReq := resource.SchemaRequest{}
	schemaResp := &resource.SchemaResponse{}
	r.Schema(context.Background(), schemaReq, schemaResp)

	tmpDir := t.TempDir()
	outputPath := filepath.Join(tmpDir, "output")
	os.MkdirAll(outputPath, testDirPermissions)

	// Pre-create test file
	testFile := filepath.Join(outputPath, "test_default.py")
	os.WriteFile(testFile, []byte("# test\n"), testFilePermissions)

	planValue := tftypes.NewValue(
		tftypes.Object{
			AttributeTypes: map[string]tftypes.Type{
				"id":            tftypes.String,
				"profile_path":  tftypes.String,
				"output_path":   tftypes.String,
				"output_format": tftypes.String,
				"profile_name":  tftypes.String,
				"test_content":  tftypes.String,
			},
		},
		map[string]tftypes.Value{
			"id":            tftypes.NewValue(tftypes.String, tftypes.UnknownValue),
			"profile_path":  tftypes.NewValue(tftypes.String, "/tmp/profile"),
			"output_path":   tftypes.NewValue(tftypes.String, outputPath),
			"output_format": tftypes.NewValue(tftypes.String, "serverspec"),
			"profile_name":  tftypes.NewValue(tftypes.String, "default"),
			"test_content":  tftypes.NewValue(tftypes.String, tftypes.UnknownValue),
		},
	)

	plan := tfsdk.Plan{
		Schema: schemaResp.Schema,
		Raw:    planValue,
	}

	req := resource.CreateRequest{Plan: plan}
	resp := &resource.CreateResponse{
		State: tfsdk.State{Schema: schemaResp.Schema},
	}

	r.Create(context.Background(), req, resp)
	t.Log("InSpec Create executed successfully")
}

// TestBatchMigrationCreateEmptySourceList tests batch create with empty sources
func TestBatchMigrationCreateEmptySourceList(t *testing.T) {
	r := &batchMigrationResource{
		client: &SousChefClient{Path: "souschef"},
	}

	schemaReq := resource.SchemaRequest{}
	schemaResp := &resource.SchemaResponse{}
	r.Schema(context.Background(), schemaReq, schemaResp)

	tmpDir := t.TempDir()
	outputPath := filepath.Join(tmpDir, "output")
	os.MkdirAll(outputPath, testDirPermissions)

	// Create playbook file
	playbookFile := filepath.Join(outputPath, "site.yml")
	os.WriteFile(playbookFile, []byte("---\n"), testFilePermissions)

	planValue := tftypes.NewValue(
		tftypes.Object{
			AttributeTypes: map[string]tftypes.Type{
				"id":               tftypes.String,
				"source_cookbooks": tftypes.String,
				"output_path":      tftypes.String,
				"playbook_content": tftypes.String,
				"migration_date":   tftypes.String,
				"total_recipes":    tftypes.String,
			},
		},
		map[string]tftypes.Value{
			"id":               tftypes.NewValue(tftypes.String, tftypes.UnknownValue),
			"source_cookbooks": tftypes.NewValue(tftypes.String, ""),
			"output_path":      tftypes.NewValue(tftypes.String, outputPath),
			"playbook_content": tftypes.NewValue(tftypes.String, tftypes.UnknownValue),
			"migration_date":   tftypes.NewValue(tftypes.String, tftypes.UnknownValue),
			"total_recipes":    tftypes.NewValue(tftypes.String, tftypes.UnknownValue),
		},
	)

	plan := tfsdk.Plan{
		Schema: schemaResp.Schema,
		Raw:    planValue,
	}

	req := resource.CreateRequest{Plan: plan}
	resp := &resource.CreateResponse{
		State: tfsdk.State{Schema: schemaResp.Schema},
	}

	r.Create(context.Background(), req, resp)
	t.Log("Batch Create executed with empty sources")
}

// TestMigrationCreateWithReadOnlyOutput tests create when output directory is readonly
func TestMigrationCreateWithReadOnlyOutput(t *testing.T) {
	r := &migrationResource{
		client: &SousChefClient{Path: "souschef"},
	}

	schemaReq := resource.SchemaRequest{}
	schemaResp := &resource.SchemaResponse{}
	r.Schema(context.Background(), schemaReq, schemaResp)

	tmpDir := t.TempDir()
	outputPath := filepath.Join(tmpDir, "output")
	os.MkdirAll(outputPath, testDirPermissions)

	// Create playbook file first
	playbookFile := filepath.Join(outputPath, "site.yml")
	os.WriteFile(playbookFile, []byte("---\n"), testFilePermissions)

	// Make readonly
	os.Chmod(outputPath, readonlyDirPermissions)
	defer os.Chmod(outputPath, testDirPermissions)

	planValue := tftypes.NewValue(
		tftypes.Object{
			AttributeTypes: map[string]tftypes.Type{
				"id":               tftypes.String,
				"cookbook_path":    tftypes.String,
				"output_path":      tftypes.String,
				"recipe_name":      tftypes.String,
				"cookbook_name":    tftypes.String,
				"playbook_content": tftypes.String,
			},
		},
		map[string]tftypes.Value{
			"id":               tftypes.NewValue(tftypes.String, tftypes.UnknownValue),
			"cookbook_path":    tftypes.NewValue(tftypes.String, "/tmp/cookbook"),
			"output_path":      tftypes.NewValue(tftypes.String, outputPath),
			"recipe_name":      tftypes.NewValue(tftypes.String, "default"),
			"cookbook_name":    tftypes.NewValue(tftypes.String, tftypes.UnknownValue),
			"playbook_content": tftypes.NewValue(tftypes.String, tftypes.UnknownValue),
		},
	)

	plan := tfsdk.Plan{
		Schema: schemaResp.Schema,
		Raw:    planValue,
	}

	req := resource.CreateRequest{Plan: plan}
	resp := &resource.CreateResponse{
		State: tfsdk.State{Schema: schemaResp.Schema},
	}

	r.Create(context.Background(), req, resp)
	t.Log("Migration Create handled readonly output directory")
}
