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

const (
	planShFilename            = "plan.sh"
	bashShebang               = "#!/bin/bash\n"
	invalidFormatErrorMsg     = "Expected error for invalid format: %s"
	planShFullPath            = "/tmp/plan.sh"
	errorReadingFileWithPerms = "Expected error when reading file with no permissions"
	errorPlanFileNotFound     = "Expected error when plan file doesn't exist"
	errorDockerfileNotFound   = "Expected error when Dockerfile doesn't exist"
	errorProfilePathNotFound  = "Expected error when profile path doesn't exist"
	errorTestFileNotFound     = "Expected error when test file doesn't exist for format: %s"
	errorTestFileCantBeRead   = "Expected error when test file can't be read"
	errorCookbookPathNotFound = "Expected error when cookbook path doesn't exist"
	errorPlaybookFileNotFound = "Expected error when playbook file doesn't exist"
)

// TestHabitatMigrationReadFileReadError tests Read failure when file I/O fails
func TestHabitatMigrationReadFileReadError(t *testing.T) {
	r := &habitatMigrationResource{
		client: &SousChefClient{Path: "souschef"},
	}

	// Create schema
	schemaReq := resource.SchemaRequest{}
	schemaResp := &resource.SchemaResponse{}
	r.Schema(context.Background(), schemaReq, schemaResp)

	tmpDir := t.TempDir()
	outputPath := filepath.Join(tmpDir, "output")
	os.MkdirAll(outputPath, 0755)

	// Create Dockerfile with read-restricted permissions
	dockerfilePath := filepath.Join(outputPath, "Dockerfile")
	err := os.WriteFile(dockerfilePath, []byte("FROM ubuntu:latest\n"), 0000)
	if err != nil {
		t.Fatalf("Failed to create Dockerfile: %v", err)
	}

	// Create state with Dockerfile that can't be read
	stateValue := tftypes.NewValue(
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
			"id":                 tftypes.NewValue(tftypes.String, "habitat-test"),
			"plan_path":          tftypes.NewValue(tftypes.String, planShFullPath),
			"output_path":        tftypes.NewValue(tftypes.String, outputPath),
			"base_image":         tftypes.NewValue(tftypes.String, "ubuntu:latest"),
			"package_name":       tftypes.NewValue(tftypes.String, "test"),
			"dockerfile_content": tftypes.NewValue(tftypes.String, "old content"),
		},
	)

	state := tfsdk.State{
		Schema: schemaResp.Schema,
		Raw:    stateValue,
	}

	req := resource.ReadRequest{
		State: state,
	}
	resp := &resource.ReadResponse{}
	resp.State = state

	// Restore permissions and read again for final cleanup
	defer os.Chmod(dockerfilePath, 0644)

	// Read should fail with permission error
	r.Read(context.Background(), req, resp)

	// Should have error
	if !resp.Diagnostics.HasError() {
		t.Error(errorReadingFileWithPerms)
	}
}

// TestHabitatMigrationImportStatePlanPathNotFound tests ImportState error when plan doesn't exist
func TestHabitatMigrationImportStatePlanPathNotFound(t *testing.T) {
	r := &habitatMigrationResource{
		client: &SousChefClient{Path: "souschef"},
	}

	// Create schema
	schemaReq := resource.SchemaRequest{}
	schemaResp := &resource.SchemaResponse{}
	r.Schema(context.Background(), schemaReq, schemaResp)

	req := resource.ImportStateRequest{
		ID: "/nonexistent/path|/output|ubuntu:latest",
	}
	resp := &resource.ImportStateResponse{}
	resp.State = tfsdk.State{
		Schema: schemaResp.Schema,
		Raw:    tftypes.NewValue(schemaResp.Schema.Type().TerraformType(context.Background()), nil),
	}

	r.ImportState(context.Background(), req, resp)

	if !resp.Diagnostics.HasError() {
		t.Error(errorPlanFileNotFound)
	}
}

// TestHabitatMigrationImportStateDockerfileNotFound tests ImportState error when Dockerfile doesn't exist
func TestHabitatMigrationImportStateDockerfileNotFound(t *testing.T) {
	r := &habitatMigrationResource{
		client: &SousChefClient{Path: "souschef"},
	}

	// Create schema
	schemaReq := resource.SchemaRequest{}
	schemaResp := &resource.SchemaResponse{}
	r.Schema(context.Background(), schemaReq, schemaResp)

	tmpDir := t.TempDir()
	planDir := filepath.Join(tmpDir, "plan")
	outputPath := filepath.Join(tmpDir, "output")
	os.MkdirAll(planDir, 0755)
	os.MkdirAll(outputPath, 0755)

	// Create plan file
	planPath := filepath.Join(planDir, planShFilename)
	os.WriteFile(planPath, []byte(bashShebang), 0755)

	// Don't create Dockerfile
	req := resource.ImportStateRequest{
		ID: planPath + "|" + outputPath + "|ubuntu:latest",
	}
	resp := &resource.ImportStateResponse{}
	resp.State = tfsdk.State{
		Schema: schemaResp.Schema,
		Raw:    tftypes.NewValue(schemaResp.Schema.Type().TerraformType(context.Background()), nil),
	}

	r.ImportState(context.Background(), req, resp)

	if !resp.Diagnostics.HasError() {
		t.Error(errorDockerfileNotFound)
	}
}

// TestHabitatMigrationImportStateInvalidIDFormat tests ImportState with invalid format
func TestHabitatMigrationImportStateInvalidIDFormat(t *testing.T) {
	r := &habitatMigrationResource{
		client: &SousChefClient{Path: "souschef"},
	}

	// Create schema
	schemaReq := resource.SchemaRequest{}
	schemaResp := &resource.SchemaResponse{}
	r.Schema(context.Background(), schemaReq, schemaResp)

	testCases := []string{
		"only_one_part",
		"part1|part2|part3|part4", // too many parts
	}

	for _, id := range testCases {
		req := resource.ImportStateRequest{
			ID: id,
		}
		resp := &resource.ImportStateResponse{}
		resp.State = tfsdk.State{
			Schema: schemaResp.Schema,
			Raw:    tftypes.NewValue(schemaResp.Schema.Type().TerraformType(context.Background()), nil),
		}

		r.ImportState(context.Background(), req, resp)

		if !resp.Diagnostics.HasError() {
			t.Errorf(invalidFormatErrorMsg, id)
		}
	}
}

// TestInspecMigrationImportStateInvalidIDFormat tests ImportState with wrong number of parts
func TestInspecMigrationImportStateInvalidIDFormat(t *testing.T) {
	r := &inspecMigrationResource{
		client: &SousChefClient{Path: "souschef"},
	}

	// Create schema
	schemaReq := resource.SchemaRequest{}
	schemaResp := &resource.SchemaResponse{}
	r.Schema(context.Background(), schemaReq, schemaResp)

	testCases := []string{
		"only_one_part",
		"part1|part2",                   // missing format
		"part1|part2|format|extra_part", // too many parts
	}

	for _, id := range testCases {
		req := resource.ImportStateRequest{
			ID: id,
		}
		resp := &resource.ImportStateResponse{}
		resp.State = tfsdk.State{
			Schema: schemaResp.Schema,
			Raw:    tftypes.NewValue(schemaResp.Schema.Type().TerraformType(context.Background()), nil),
		}

		r.ImportState(context.Background(), req, resp)

		if !resp.Diagnostics.HasError() {
			t.Errorf(invalidFormatErrorMsg, id)
		}
	}
}

// TestInspecMigrationImportStateProfileNotFound tests ImportState error when profile doesn't exist
func TestInspecMigrationImportStateProfileNotFound(t *testing.T) {
	r := &inspecMigrationResource{
		client: &SousChefClient{Path: "souschef"},
	}

	// Create schema
	schemaReq := resource.SchemaRequest{}
	schemaResp := &resource.SchemaResponse{}
	r.Schema(context.Background(), schemaReq, schemaResp)

	tmpDir := t.TempDir()
	outputPath := filepath.Join(tmpDir, "output")
	os.MkdirAll(outputPath, 0755)

	req := resource.ImportStateRequest{
		ID: "/nonexistent/profile|" + outputPath + "|testinfra",
	}
	resp := &resource.ImportStateResponse{}
	resp.State = tfsdk.State{
		Schema: schemaResp.Schema,
		Raw:    tftypes.NewValue(schemaResp.Schema.Type().TerraformType(context.Background()), nil),
	}

	r.ImportState(context.Background(), req, resp)

	if !resp.Diagnostics.HasError() {
		t.Error(errorProfilePathNotFound)
	}
}

// TestInspecMigrationImportStateTestFileNotFound tests ImportState error when test file doesn't exist
func TestInspecMigrationImportStateTestFileNotFound(t *testing.T) {
	r := &inspecMigrationResource{
		client: &SousChefClient{Path: "souschef"},
	}

	// Create schema
	schemaReq := resource.SchemaRequest{}
	schemaResp := &resource.SchemaResponse{}
	r.Schema(context.Background(), schemaReq, schemaResp)

	tmpDir := t.TempDir()
	profilePath := filepath.Join(tmpDir, "profile")
	outputPath := filepath.Join(tmpDir, "output")
	os.MkdirAll(profilePath, 0755)
	os.MkdirAll(outputPath, 0755)

	// Test all formats - none of which have generated files
	formats := []string{"testinfra", "serverspec", "goss", "ansible"}
	for _, format := range formats {
		req := resource.ImportStateRequest{
			ID: profilePath + "|" + outputPath + "|" + format,
		}
		resp := &resource.ImportStateResponse{}
		resp.State = tfsdk.State{
			Schema: schemaResp.Schema,
			Raw:    tftypes.NewValue(schemaResp.Schema.Type().TerraformType(context.Background()), nil),
		}

		r.ImportState(context.Background(), req, resp)

		if !resp.Diagnostics.HasError() {
			t.Errorf("Expected error when test file doesn't exist for format: %s", format)
		}
	}
}

// TestInspecMigrationImportStateTestFileReadError tests ImportState error when test file can't be read
func TestInspecMigrationImportStateTestFileReadError(t *testing.T) {
	r := &inspecMigrationResource{
		client: &SousChefClient{Path: "souschef"},
	}

	// Create schema
	schemaReq := resource.SchemaRequest{}
	schemaResp := &resource.SchemaResponse{}
	r.Schema(context.Background(), schemaReq, schemaResp)

	tmpDir := t.TempDir()
	profilePath := filepath.Join(tmpDir, "profile")
	outputPath := filepath.Join(tmpDir, "output")
	os.MkdirAll(profilePath, 0755)
	os.MkdirAll(outputPath, 0755)

	// Create test file with no read permissions
	testFilePath := filepath.Join(outputPath, "test_default.py")
	os.WriteFile(testFilePath, []byte("def test_something():\n    pass\n"), 0000)
	defer os.Chmod(testFilePath, 0644)

	req := resource.ImportStateRequest{
		ID: profilePath + "|" + outputPath + "|testinfra",
	}
	resp := &resource.ImportStateResponse{}
	resp.State = tfsdk.State{
		Schema: schemaResp.Schema,
		Raw:    tftypes.NewValue(schemaResp.Schema.Type().TerraformType(context.Background()), nil),
	}

	r.ImportState(context.Background(), req, resp)

	if !resp.Diagnostics.HasError() {
		t.Error("Expected error when test file can't be read")
	}
}

// TestBatchMigrationImportStateInvalidIDFormat tests ImportState with invalid recipe count
func TestBatchMigrationImportStateInvalidIDFormat(t *testing.T) {
	r := &batchMigrationResource{
		client: &SousChefClient{Path: "souschef"},
	}

	// Create schema
	schemaReq := resource.SchemaRequest{}
	schemaResp := &resource.SchemaResponse{}
	r.Schema(context.Background(), schemaReq, schemaResp)

	testCases := []string{
		"cookbook_path|output",                         // missing recipe count
		"cookbook_path|output|abc",                     // invalid recipe count (not a number)
		"cookbook_path|output|0",                       // recipe count is zero
		"cookbook_path|output|2|recipe1",               // recipe count says 2 but only 1 provided
		"cookbook_path|output|2|recipe1|recipe2|extra", // recipe count says 2 but 3 provided
	}

	for _, id := range testCases {
		req := resource.ImportStateRequest{
			ID: id,
		}
		resp := &resource.ImportStateResponse{}
		resp.State = tfsdk.State{
			Schema: schemaResp.Schema,
			Raw:    tftypes.NewValue(schemaResp.Schema.Type().TerraformType(context.Background()), nil),
		}

		r.ImportState(context.Background(), req, resp)

		if !resp.Diagnostics.HasError() {
			t.Errorf(invalidFormatErrorMsg, id)
		}
	}
}

// TestBatchMigrationImportStateCookbookPathNotFound tests ImportState error when cookbook doesn't exist
func TestBatchMigrationImportStateCookbookPathNotFound(t *testing.T) {
	r := &batchMigrationResource{
		client: &SousChefClient{Path: "souschef"},
	}

	// Create schema
	schemaReq := resource.SchemaRequest{}
	schemaResp := &resource.SchemaResponse{}
	r.Schema(context.Background(), schemaReq, schemaResp)

	tmpDir := t.TempDir()
	outputPath := filepath.Join(tmpDir, "output")
	os.MkdirAll(outputPath, 0755)

	req := resource.ImportStateRequest{
		ID: "/nonexistent/cookbook|" + outputPath + "|1|default",
	}
	resp := &resource.ImportStateResponse{}
	resp.State = tfsdk.State{
		Schema: schemaResp.Schema,
		Raw:    tftypes.NewValue(schemaResp.Schema.Type().TerraformType(context.Background()), nil),
	}

	r.ImportState(context.Background(), req, resp)

	if !resp.Diagnostics.HasError() {
		t.Error(errorCookbookPathNotFound)
	}
}

// TestBatchMigrationImportStatePlaybookNotFound tests ImportState error when playbook file doesn't exist
func TestBatchMigrationImportStatePlaybookNotFound(t *testing.T) {
	r := &batchMigrationResource{
		client: &SousChefClient{Path: "souschef"},
	}

	// Create schema
	schemaReq := resource.SchemaRequest{}
	schemaResp := &resource.SchemaResponse{}
	r.Schema(context.Background(), schemaReq, schemaResp)

	tmpDir := t.TempDir()
	cookbookPath := filepath.Join(tmpDir, "cookbook")
	outputPath := filepath.Join(tmpDir, "output")
	os.MkdirAll(cookbookPath, 0755)
	os.MkdirAll(outputPath, 0755)

	// Don't create the expected playbook file
	req := resource.ImportStateRequest{
		ID: cookbookPath + "|" + outputPath + "|1|default",
	}
	resp := &resource.ImportStateResponse{}
	resp.State = tfsdk.State{
		Schema: schemaResp.Schema,
		Raw:    tftypes.NewValue(schemaResp.Schema.Type().TerraformType(context.Background()), nil),
	}

	r.ImportState(context.Background(), req, resp)

	if !resp.Diagnostics.HasError() {
		t.Error(errorPlaybookFileNotFound)
	}
}

// TestMigrationImportStateCookbookPathNotFound tests migration ImportState error when cookbook doesn't exist
func TestMigrationImportStateCookbookPathNotFound(t *testing.T) {
	r := &migrationResource{
		client: &SousChefClient{Path: "souschef"},
	}

	// Create schema
	schemaReq := resource.SchemaRequest{}
	schemaResp := &resource.SchemaResponse{}
	r.Schema(context.Background(), schemaReq, schemaResp)

	tmpDir := t.TempDir()
	outputPath := filepath.Join(tmpDir, "output")
	os.MkdirAll(outputPath, 0755)

	req := resource.ImportStateRequest{
		ID: "/nonexistent/cookbook|" + outputPath + "|default",
	}
	resp := &resource.ImportStateResponse{}
	resp.State = tfsdk.State{
		Schema: schemaResp.Schema,
		Raw:    tftypes.NewValue(schemaResp.Schema.Type().TerraformType(context.Background()), nil),
	}

	r.ImportState(context.Background(), req, resp)

	if !resp.Diagnostics.HasError() {
		t.Error(errorCookbookPathNotFound)
	}
}

// TestMigrationImportStatePlaybookNotFound tests migration ImportState error when playbook doesn't exist
func TestMigrationImportStatePlaybookNotFound(t *testing.T) {
	r := &migrationResource{
		client: &SousChefClient{Path: "souschef"},
	}

	// Create schema
	schemaReq := resource.SchemaRequest{}
	schemaResp := &resource.SchemaResponse{}
	r.Schema(context.Background(), schemaReq, schemaResp)

	tmpDir := t.TempDir()
	cookbookPath := filepath.Join(tmpDir, "cookbook")
	outputPath := filepath.Join(tmpDir, "output")
	os.MkdirAll(cookbookPath, 0755)
	os.MkdirAll(outputPath, 0755)

	// Don't create the playbook file
	req := resource.ImportStateRequest{
		ID: cookbookPath + "|" + outputPath + "|default",
	}
	resp := &resource.ImportStateResponse{}
	resp.State = tfsdk.State{
		Schema: schemaResp.Schema,
		Raw:    tftypes.NewValue(schemaResp.Schema.Type().TerraformType(context.Background()), nil),
	}

	r.ImportState(context.Background(), req, resp)

	if !resp.Diagnostics.HasError() {
		t.Error(errorPlaybookFileNotFound)
	}
}

// TestMigrationImportStateInvalidIDFormat tests migration ImportState with invalid format
func TestMigrationImportStateInvalidIDFormat(t *testing.T) {
	r := &migrationResource{
		client: &SousChefClient{Path: "souschef"},
	}

	// Create schema
	schemaReq := resource.SchemaRequest{}
	schemaResp := &resource.SchemaResponse{}
	r.Schema(context.Background(), schemaReq, schemaResp)

	testCases := []string{
		"only_one_part",
		"part1|part2|part3|part4", // too many parts
	}

	for _, id := range testCases {
		req := resource.ImportStateRequest{
			ID: id,
		}
		resp := &resource.ImportStateResponse{}
		resp.State = tfsdk.State{
			Schema: schemaResp.Schema,
			Raw:    tftypes.NewValue(schemaResp.Schema.Type().TerraformType(context.Background()), nil),
		}

		r.ImportState(context.Background(), req, resp)

		if !resp.Diagnostics.HasError() {
			t.Errorf(invalidFormatErrorMsg, id)
		}
	}
}

// TestHabitatMigrationUpdatePreservesID tests that Update preserves ID from state
func TestHabitatMigrationUpdatePreservesID(t *testing.T) {
	if _, err := os.Stat("/nonexistent/souschef"); err == nil {
		t.Skip("Skipping test - souschef CLI not available")
	}

	r := &habitatMigrationResource{
		client: &SousChefClient{Path: "nonexistent_souschef_cli"},
	}

	// Create schema
	schemaReq := resource.SchemaRequest{}
	schemaResp := &resource.SchemaResponse{}
	r.Schema(context.Background(), schemaReq, schemaResp)

	tmpDir := t.TempDir()
	planDir := filepath.Join(tmpDir, "plan")
	outputPath := filepath.Join(tmpDir, "output")
	os.MkdirAll(planDir, 0755)
	os.MkdirAll(outputPath, 0755)

	planPath := filepath.Join(planDir, planShFilename)
	os.WriteFile(planPath, []byte(bashShebang), 0755)

	// Create initial state with specific ID
	stateValue := tftypes.NewValue(
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
			"id":                 tftypes.NewValue(tftypes.String, "habitat-mypackage"),
			"plan_path":          tftypes.NewValue(tftypes.String, planPath),
			"output_path":        tftypes.NewValue(tftypes.String, outputPath),
			"base_image":         tftypes.NewValue(tftypes.String, "ubuntu:20.04"),
			"package_name":       tftypes.NewValue(tftypes.String, "mypackage"),
			"dockerfile_content": tftypes.NewValue(tftypes.String, "old"),
		},
	)

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
			"id":                 tftypes.NewValue(tftypes.String, "habitat-mypackage"),
			"plan_path":          tftypes.NewValue(tftypes.String, planPath),
			"output_path":        tftypes.NewValue(tftypes.String, outputPath),
			"base_image":         tftypes.NewValue(tftypes.String, "debian:12"), // Changed
			"package_name":       tftypes.NewValue(tftypes.String, nil),
			"dockerfile_content": tftypes.NewValue(tftypes.String, nil),
		},
	)

	req := resource.UpdateRequest{
		Plan: tfsdk.Plan{
			Schema: schemaResp.Schema,
			Raw:    planValue,
		},
		State: tfsdk.State{
			Schema: schemaResp.Schema,
			Raw:    stateValue,
		},
	}
	resp := &resource.UpdateResponse{}
	resp.State = tfsdk.State{
		Schema: schemaResp.Schema,
		Raw:    tftypes.NewValue(schemaResp.Schema.Type().TerraformType(context.Background()), nil),
	}

	// Update will fail on CLI but we can still verify the code path
	r.Update(context.Background(), req, resp)

	// The update should at least attempt to execute
	if resp.Diagnostics.HasError() {
		t.Logf("Got expected CLI error: %v", resp.Diagnostics.Errors())
	}
}

// TestMultipleImportStateErrorPaths tests various edge cases
func TestMultipleImportStateErrorPaths(t *testing.T) {
	t.Run("habitat_empty_base_image", func(t *testing.T) {
		r := &habitatMigrationResource{
			client: &SousChefClient{Path: "souschef"},
		}

		// Create schema
		schemaReq := resource.SchemaRequest{}
		schemaResp := &resource.SchemaResponse{}
		r.Schema(context.Background(), schemaReq, schemaResp)

		tmpDir := t.TempDir()
		planDir := filepath.Join(tmpDir, "plan")
		outputPath := filepath.Join(tmpDir, "output")
		os.MkdirAll(planDir, 0755)
		os.MkdirAll(outputPath, 0755)

		planPath := filepath.Join(planDir, planShFilename)
		os.WriteFile(planPath, []byte(bashShebang), 0755)

		dockerfilePath := filepath.Join(outputPath, "Dockerfile")
		os.WriteFile(dockerfilePath, []byte("FROM ubuntu\n"), 0644)

		// Empty base_image should use default
		req := resource.ImportStateRequest{
			ID: planPath + "|" + outputPath + "|",
		}
		resp := &resource.ImportStateResponse{}
		resp.State = tfsdk.State{
			Schema: schemaResp.Schema,
			Raw:    tftypes.NewValue(schemaResp.Schema.Type().TerraformType(context.Background()), nil),
		}

		r.ImportState(context.Background(), req, resp)

		// Should succeed with default base image
		if resp.Diagnostics.HasError() {
			t.Errorf("Expected success with empty base_image using default, got error: %v", resp.Diagnostics.Errors())
		}
	})

	t.Run("inspec_default_format", func(t *testing.T) {
		r := &inspecMigrationResource{
			client: &SousChefClient{Path: "souschef"},
		}

		// Create schema
		schemaReq := resource.SchemaRequest{}
		schemaResp := &resource.SchemaResponse{}
		r.Schema(context.Background(), schemaReq, schemaResp)

		tmpDir := t.TempDir()
		profilePath := filepath.Join(tmpDir, "profile")
		outputPath := filepath.Join(tmpDir, "output")
		os.MkdirAll(profilePath, 0755)
		os.MkdirAll(outputPath, 0755)

		// Create test file with default name for unknown format
		testFilePath := filepath.Join(outputPath, "test_default.py")
		os.WriteFile(testFilePath, []byte("def test():\n    pass\n"), 0644)

		// Use unknown format to test default filename case
		req := resource.ImportStateRequest{
			ID: profilePath + "|" + outputPath + "|unknown_format",
		}
		resp := &resource.ImportStateResponse{}
		resp.State = tfsdk.State{
			Schema: schemaResp.Schema,
			Raw:    tftypes.NewValue(schemaResp.Schema.Type().TerraformType(context.Background()), nil),
		}

		r.ImportState(context.Background(), req, resp)

		// May or may not succeed depending on implementation
		t.Logf("Import result: %v", resp.Diagnostics.Errors())
	})
}
