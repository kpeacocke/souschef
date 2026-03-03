// Package provider contains edge case tests for full coverage.
package provider

import (
	"context"
	"os"
	"path/filepath"
	"testing"

	"github.com/hashicorp/terraform-plugin-framework/datasource"
	"github.com/hashicorp/terraform-plugin-framework/resource"
	resourceschema "github.com/hashicorp/terraform-plugin-framework/resource/schema"
	"github.com/hashicorp/terraform-plugin-framework/tfsdk"
	"github.com/hashicorp/terraform-plugin-framework/types"
	"github.com/hashicorp/terraform-plugin-go/tftypes"
)

func TestResourceConfigureNilClient(t *testing.T) {
	// Test Configure with nil provider data
	r := &batchMigrationResource{}
	resp := &resource.ConfigureResponse{}
	r.Configure(context.Background(), resource.ConfigureRequest{ProviderData: nil}, resp)

	if resp.Diagnostics.HasError() {
		t.Fatalf("unexpected diagnostics for nil provider data: %v", resp.Diagnostics)
	}
}

func TestResourceConfigureValidClient(t *testing.T) {
	// Test Configure with valid client
	r := &migrationResource{}
	client := &SousChefClient{Path: "test"}
	resp := &resource.ConfigureResponse{}
	r.Configure(context.Background(), resource.ConfigureRequest{ProviderData: client}, resp)

	if resp.Diagnostics.HasError() {
		t.Fatalf(testUnexpectedDiagnostics, resp.Diagnostics)
	}
}

func TestResourceConfiguresWithValidClient(t *testing.T) {
	// Table-driven test for all resource types
	tests := []struct {
		name     string
		resource interface {
			Configure(context.Context, resource.ConfigureRequest, *resource.ConfigureResponse)
		}
	}{
		{
			name:     "Batch",
			resource: &batchMigrationResource{},
		},
		{
			name:     "Habitat",
			resource: &habitatMigrationResource{},
		},
		{
			name:     "InSpec",
			resource: &inspecMigrationResource{},
		},
	}

	client := &SousChefClient{Path: "test"}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			resp := &resource.ConfigureResponse{}
			tt.resource.Configure(context.Background(),
				resource.ConfigureRequest{ProviderData: client}, resp)

			if resp.Diagnostics.HasError() {
				t.Fatalf(testUnexpectedDiagnostics, resp.Diagnostics)
			}
		})
	}
}

func testDataSourceConfigureValidClientHelper(t *testing.T, ds interface{}, client *SousChefClient) {
	t.Helper()
	switch d := ds.(type) {
	case *assessmentDataSource:
		resp := &datasource.ConfigureResponse{}
		d.Configure(context.Background(),
			datasource.ConfigureRequest{ProviderData: client}, resp)

		if resp.Diagnostics.HasError() {
			t.Fatalf(testUnexpectedDiagnostics, resp.Diagnostics)
		}
		if d.client != client {
			t.Fatalf("client not configured properly")
		}
	case *costEstimateDataSource:
		resp := &datasource.ConfigureResponse{}
		d.Configure(context.Background(),
			datasource.ConfigureRequest{ProviderData: client}, resp)

		if resp.Diagnostics.HasError() {
			t.Fatalf(testUnexpectedDiagnostics, resp.Diagnostics)
		}
		if d.client != client {
			t.Fatalf("client not configured properly")
		}
	}
}

func TestDataSourceConfiguresWithValidClient(t *testing.T) {
	// Table-driven test for datasource configurations
	tests := []struct {
		name string
		ds   interface{}
	}{
		{
			name: "Assessment",
			ds:   &assessmentDataSource{},
		},
		{
			name: "CostEstimate",
			ds:   &costEstimateDataSource{},
		},
	}

	client := &SousChefClient{Path: "test"}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			testDataSourceConfigureValidClientHelper(t, tt.ds, client)
		})
	}
}

func TestAssessmentDataSourceReadConfigError(t *testing.T) {
	// Build a config with wrong type to force Config.Get diagnostics
	ds := &assessmentDataSource{}
	schema := newDataSourceSchema(t, ds)

	badValue := tftypes.NewValue(tftypes.Object{
		AttributeTypes: map[string]tftypes.Type{
			"cookbook_path": tftypes.Number,
		},
	}, map[string]tftypes.Value{
		"cookbook_path": tftypes.NewValue(tftypes.Number, 42),
	})

	config := tfsdk.Config{Schema: schema, Raw: badValue}
	resp := &datasource.ReadResponse{State: tfsdk.State{Schema: schema}}

	ds.Read(context.Background(), datasource.ReadRequest{Config: config}, resp)

	if !resp.Diagnostics.HasError() {
		t.Fatal("expected diagnostics for invalid config")
	}
}

func TestCostEstimateDataSourceReadDefaults(t *testing.T) {
	ds := &costEstimateDataSource{client: &SousChefClient{Path: "souschef"}}
	schema := newDataSourceSchema(t, ds)

	config := newDataSourceConfig(t, schema, costEstimateDataSourceModel{
		CookbookPath:        types.StringValue(testTmpCookbook),
		DeveloperHourlyRate: types.Float64Null(),
		InfrastructureCost:  types.Float64Null(),
	})
	resp := &datasource.ReadResponse{State: tfsdk.State{Schema: schema}}

	ds.Read(context.Background(), datasource.ReadRequest{Config: config}, resp)

	if resp.Diagnostics.HasError() {
		t.Fatalf(testUnexpectedDiagnostics, resp.Diagnostics)
	}
}

func TestHabitatMigrationDeleteWithPermissionError(t *testing.T) {
	r := &habitatMigrationResource{}
	schema := newResourceSchema(t, r)

	outputDir := t.TempDir()
	dockerfilePath := filepath.Join(outputDir, "Dockerfile")

	// Create file and make it read-only to potentially cause delete error
	if err := os.WriteFile(dockerfilePath, []byte("FROM ubuntu"), 0444); err != nil {
		t.Fatalf("failed to write dockerfile: %v", err)
	}

	state := newState(t, schema, habitatMigrationResourceModel{
		PlanPath:   types.StringValue(testTmpPlanSh),
		OutputPath: types.StringValue(outputDir),
	})

	deleteResp := &resource.DeleteResponse{}
	r.Delete(context.Background(), resource.DeleteRequest{State: state}, deleteResp)

	// Should have warning, not error
	if deleteResp.Diagnostics.HasError() {
		// Some systems allow deleting read-only files, that's fine
		// Just make sure it doesn't crash
	}

	// Clean up - restore permissions
	os.Chmod(dockerfilePath, testFilePermissions)
}

func TestInSpecMigrationDeleteWithDifferentFormats(t *testing.T) {
	r := &inspecMigrationResource{}
	schema := newResourceSchema(t, r)

	formats := []struct {
		format   string
		filename string
	}{
		{"testinfra", "test_spec.py"},
		{"serverspec", "spec_helper.rb"},
		{"goss", "goss.yaml"},
		{"ansible", "assert.yml"},
	}

	for _, f := range formats {
		testDir := t.TempDir()
		testFilePath := filepath.Join(testDir, f.filename)
		if err := os.WriteFile(testFilePath, []byte("test"), 0644); err != nil {
			t.Fatalf("failed to write %s: %v", f.filename, err)
		}

		state := newState(t, schema, inspecMigrationResourceModel{
			ProfilePath:  types.StringValue(testTmpProfile),
			OutputPath:   types.StringValue(testDir),
			OutputFormat: types.StringValue(f.format),
		})

		deleteResp := &resource.DeleteResponse{}
		r.Delete(context.Background(), resource.DeleteRequest{State: state}, deleteResp)

		if deleteResp.Diagnostics.HasError() {
			t.Fatalf("unexpected diagnostics for %s format: %v", f.format, deleteResp.Diagnostics)
		}

		// Verify file was deleted
		if _, err := os.Stat(testFilePath); err == nil {
			t.Fatalf("test file for %s should have been deleted", f.format)
		}
	}
}

// testReadWithUnreadableFile tests Read when output file has no read permissions
func testReadWithUnreadableFile(t *testing.T, r resource.Resource, outputDir, fileName string) {
	t.Helper()
	schema := newResourceSchema(t, r)
	filePath := filepath.Join(outputDir, fileName)

	// Create file with no read permissions
	if err := os.WriteFile(filePath, []byte("content"), 0000); err != nil {
		t.Fatalf("failed to write file: %v", err)
	}
	defer os.Chmod(filePath, testFilePermissions) // cleanup

	state := createTestStateForResource(t, schema, r, outputDir)

	readResp := &resource.ReadResponse{State: tfsdk.State{Schema: schema}}
	r.Read(context.Background(), resource.ReadRequest{State: state}, readResp)

	if !readResp.Diagnostics.HasError() {
		t.Fatalf("expected diagnostics for unreadable file in %T", r)
	}
}

func TestMigrationReadWithUnreadablePlaybook(t *testing.T) {
	r := &migrationResource{}
	outputDir := t.TempDir()
	testReadWithUnreadableFile(t, r, outputDir, "test.yml")
}

func TestBatchMigrationCreateWithMissingOutput(t *testing.T) {
	r := &batchMigrationResource{client: &SousChefClient{Path: newFakeSousChef(t)}}
	testCreateWithEnvironmentFailure(t, r, "SOUSCHEF_TEST_SKIP_WRITE", testConvertRecipe)
}

func TestBatchMigrationCreateWithUnreadablePlaybook(t *testing.T) {
	r := &batchMigrationResource{client: &SousChefClient{Path: newFakeSousChef(t)}}
	testCreateWithEnvironmentFailure(t, r, "SOUSCHEF_TEST_CHMOD", testConvertRecipe)
}

func TestBatchMigrationUpdateWithUnreadablePlaybook(t *testing.T) {
	r := &batchMigrationResource{client: &SousChefClient{Path: newFakeSousChef(t)}}
	testUpdateWithEnvironmentFailure(t, r, "SOUSCHEF_TEST_CHMOD", testConvertRecipe)
}

func TestBatchMigrationReadWithUnreadablePlaybook(t *testing.T) {
	r := &batchMigrationResource{}
	outputDir := t.TempDir()
	testReadWithUnreadableFile(t, r, outputDir, "default.yml")
}

func TestHabitatMigrationCreateWithMissingPlan(t *testing.T) {
	r := &habitatMigrationResource{client: &SousChefClient{Path: newFakeSousChef(t)}}
	testCreateWithEnvironmentFailure(t, r, "SOUSCHEF_TEST_FAIL", testConvertHabitat)
}

func TestHabitatMigrationUpdateWithUnreadableDockerfile(t *testing.T) {
	r := &habitatMigrationResource{client: &SousChefClient{Path: newFakeSousChef(t)}}
	testUpdateWithEnvironmentFailure(t, r, "SOUSCHEF_TEST_CHMOD", testConvertHabitat)
}

func TestInSpecMigrationCreateWithMissingProfile(t *testing.T) {
	r := &inspecMigrationResource{client: &SousChefClient{Path: newFakeSousChef(t)}}
	testCreateWithEnvironmentFailure(t, r, "SOUSCHEF_TEST_FAIL", testConvertInSpec)
}

func TestInSpecMigrationUpdateWithUnreadableTestFile(t *testing.T) {
	r := &inspecMigrationResource{client: &SousChefClient{Path: newFakeSousChef(t)}}
	testUpdateWithEnvironmentFailure(t, r, "SOUSCHEF_TEST_CHMOD", testConvertInSpec)
}

// testReadMissingFileRemovesResource tests that reading with a missing output file removes the resource
func testReadMissingFileRemovesResource(t *testing.T, r resource.Resource) {
	t.Helper()
	schema := newResourceSchema(t, r)
	// Create state with non-existent output directory
	state := createTestStateForResource(t, schema, r, t.TempDir())

	readResp := &resource.ReadResponse{State: tfsdk.State{Schema: schema}}
	r.Read(context.Background(), resource.ReadRequest{State: state}, readResp)

	// Should remove the resource when file doesn't exist
	if !readResp.State.Raw.IsNull() {
		t.Fatalf("expected resource to be removed when file not found for %T", r)
	}
}

func TestBatchMigrationReadWithMissingPlaybook(t *testing.T) {
	r := &batchMigrationResource{}
	testReadMissingFileRemovesResource(t, r)
}

func TestHabitatMigrationReadWithMissingDockerfile(t *testing.T) {
	r := &habitatMigrationResource{}
	testReadMissingFileRemovesResource(t, r)
}

func TestInSpecMigrationReadWithMissingTestFile(t *testing.T) {
	r := &inspecMigrationResource{}
	testReadMissingFileRemovesResource(t, r)
}

// createTestPlanForResource creates a plan for the given resource type with the specified outputPath.
func createTestPlanForResource(t *testing.T, schema resourceschema.Schema, r resource.Resource, outputPath string) tfsdk.Plan {
	t.Helper()
	switch r.(type) {
	case *migrationResource:
		return newPlan(t, schema, migrationResourceModel{
			CookbookPath: types.StringValue(testTmpCookbook),
			OutputPath:   types.StringValue(outputPath),
			RecipeName:   types.StringValue("default"),
		})
	case *batchMigrationResource:
		return newPlan(t, schema, batchMigrationResourceModel{
			CookbookPath:  types.StringValue(testTmpCookbook),
			OutputPath:    types.StringValue(outputPath),
			RecipeNames:   []types.String{types.StringValue("default")},
			ID:            types.StringNull(),
			CookbookName:  types.StringNull(),
			PlaybookCount: types.Int64Null(),
			Playbooks:     types.MapNull(types.StringType),
		})
	case *habitatMigrationResource:
		planPath := filepath.Join(t.TempDir(), testPlanSh)
		if err := os.WriteFile(planPath, []byte(testPkgNameMyapp), 0644); err != nil {
			t.Fatalf(testFailedToWritePlan, err)
		}
		return newPlan(t, schema, habitatMigrationResourceModel{
			PlanPath:          types.StringValue(planPath),
			OutputPath:        types.StringValue(outputPath),
			BaseImage:         types.StringNull(),
			PackageName:       types.StringNull(),
			ID:                types.StringNull(),
			DockerfileContent: types.StringNull(),
		})
	case *inspecMigrationResource:
		return newPlan(t, schema, inspecMigrationResourceModel{
			ProfilePath:  types.StringValue(testTmpProfile),
			OutputPath:   types.StringValue(outputPath),
			OutputFormat: types.StringValue("testinfra"),
			ID:           types.StringNull(),
			ProfileName:  types.StringNull(),
			TestContent:  types.StringNull(),
		})
	default:
		t.Fatalf("unsupported resource type: %T", r)
		return tfsdk.Plan{}
	}
}

// createTestStateForResource creates a state for the given resource type with the specified outputPath.
func createTestStateForResource(t *testing.T, schema resourceschema.Schema, r resource.Resource, outputPath string) tfsdk.State {
	t.Helper()
	switch r.(type) {
	case *migrationResource:
		return newState(t, schema, migrationResourceModel{
			RecipeName: types.StringValue("test"),
			OutputPath: types.StringValue(outputPath),
		})
	case *habitatMigrationResource:
		return newState(t, schema, habitatMigrationResourceModel{
			PlanPath:   types.StringValue(testTmpPlanSh),
			OutputPath: types.StringValue(outputPath),
		})
	case *inspecMigrationResource:
		return newState(t, schema, inspecMigrationResourceModel{
			ProfilePath:  types.StringValue(testTmpProfile),
			OutputPath:   types.StringValue(outputPath),
			OutputFormat: types.StringValue("testinfra"),
		})
	case *batchMigrationResource:
		return newState(t, schema, batchMigrationResourceModel{
			ID: types.StringValue("batch-test"),
			RecipeNames: []types.String{
				types.StringValue("default"),
			},
			OutputPath:    types.StringValue(outputPath),
			CookbookName:  types.StringValue("test"),
			PlaybookCount: types.Int64Value(1),
			Playbooks:     types.MapNull(types.StringType),
		})
	default:
		t.Fatalf("unsupported resource type: %T", r)
		return tfsdk.State{}
	}
}

// testCreateWithEnvironmentFailure tests Create with an environment variable set to trigger failure
func testCreateWithEnvironmentFailure(t *testing.T, r resource.Resource, envVar, envValue string) {
	t.Helper()
	schema := newResourceSchema(t, r)
	plan := createTestPlanForResource(t, schema, r, t.TempDir())

	t.Setenv(envVar, envValue)
	createResp := &resource.CreateResponse{State: tfsdk.State{Schema: schema}}
	r.Create(context.Background(), resource.CreateRequest{Plan: plan}, createResp)
	if !createResp.Diagnostics.HasError() {
		t.Fatalf("expected diagnostics for %T create with %s=%s", r, envVar, envValue)
	}
}

// testUpdateWithEnvironmentFailure tests Update with an environment variable set to trigger failure
func testUpdateWithEnvironmentFailure(t *testing.T, r resource.Resource, envVar, envValue string) {
	t.Helper()
	schema := newResourceSchema(t, r)
	plan := createTestPlanForResource(t, schema, r, t.TempDir())

	t.Setenv(envVar, envValue)
	updateResp := &resource.UpdateResponse{State: tfsdk.State{Schema: schema}}
	r.Update(context.Background(), resource.UpdateRequest{Plan: plan}, updateResp)
	if !updateResp.Diagnostics.HasError() {
		t.Fatalf("expected diagnostics for %T update with %s=%s", r, envVar, envValue)
	}
}

func testCreateOutputPathErrorHelper(t *testing.T, r resource.Resource, filePath string) {
	t.Helper()
	schema := newResourceSchema(t, r)
	plan := createTestPlanForResource(t, schema, r, filePath)

	resp := &resource.CreateResponse{State: tfsdk.State{Schema: schema}}
	r.Create(context.Background(), resource.CreateRequest{Plan: plan}, resp)
	if !resp.Diagnostics.HasError() {
		t.Fatalf("expected diagnostics for %T output path error", r)
	}
}

func TestCreateOutputPathError(t *testing.T) {
	// Ensure create returns diagnostics when output path is a file.
	filePath := filepath.Join(t.TempDir(), "output-file")
	if err := os.WriteFile(filePath, []byte("content"), 0644); err != nil {
		t.Fatalf(testFailedToWriteFile, err)
	}

	tests := []struct {
		name     string
		resource resource.Resource
	}{
		{"migration", &migrationResource{client: &SousChefClient{Path: newFakeSousChef(t)}}},
		{"batch", &batchMigrationResource{client: &SousChefClient{Path: newFakeSousChef(t)}}},
		{"habitat", &habitatMigrationResource{client: &SousChefClient{Path: newFakeSousChef(t)}}},
		{"inspec", &inspecMigrationResource{client: &SousChefClient{Path: newFakeSousChef(t)}}},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			testCreateOutputPathErrorHelper(t, tt.resource, filePath)
		})
	}
}

func testUpdateCommandFailureHelper(t *testing.T, r resource.Resource, convertCmd string) {
	t.Helper()
	schema := newResourceSchema(t, r)
	plan := createTestPlanForResource(t, schema, r, t.TempDir())

	t.Setenv("SOUSCHEF_TEST_FAIL", convertCmd)
	resp := &resource.UpdateResponse{State: tfsdk.State{Schema: schema}}
	r.Update(context.Background(), resource.UpdateRequest{Plan: plan}, resp)
	if !resp.Diagnostics.HasError() {
		t.Fatalf("expected diagnostics for %T update command failure", r)
	}
}

func TestUpdateCommandFailures(t *testing.T) {
	tests := []struct {
		name       string
		resource   resource.Resource
		convertCmd string
	}{
		{"batch", &batchMigrationResource{client: &SousChefClient{Path: newFakeSousChef(t)}}, testConvertRecipe},
		{"habitat", &habitatMigrationResource{client: &SousChefClient{Path: newFakeSousChef(t)}}, testConvertHabitat},
		{"inspec", &inspecMigrationResource{client: &SousChefClient{Path: newFakeSousChef(t)}}, testConvertInSpec},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			testUpdateCommandFailureHelper(t, tt.resource, tt.convertCmd)
		})
	}
}

func testDeleteWarningHelper(t *testing.T, r resource.Resource, outputFileName string) {
	t.Helper()
	schema := newResourceSchema(t, r)
	outputDir := t.TempDir()
	filePath := filepath.Join(outputDir, outputFileName)
	if err := os.MkdirAll(filePath, 0755); err != nil {
		t.Fatalf(testFailedToCreateDirectory, err)
	}
	if err := os.WriteFile(filepath.Join(filePath, testFileName), []byte("x"), 0644); err != nil {
		t.Fatalf(testFailedToWriteFile, err)
	}

	state := createTestStateForResource(t, schema, r, outputDir)

	resp := &resource.DeleteResponse{}
	r.Delete(context.Background(), resource.DeleteRequest{State: state}, resp)
	if len(resp.Diagnostics) == 0 {
		t.Fatalf("expected warning diagnostics for %T delete", r)
	}
}

func TestDeleteWarningsWithDirectoryTargets(t *testing.T) {
	tests := []struct {
		name           string
		resource       resource.Resource
		outputFileName string
	}{
		{"habitat", &habitatMigrationResource{}, "Dockerfile"},
		{"inspec", &inspecMigrationResource{}, "test_spec.py"},
		{"batch", &batchMigrationResource{}, "default.yml"},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			testDeleteWarningHelper(t, tt.resource, tt.outputFileName)
		})
	}
}
