// Package provider contains additional tests to improve coverage.
package provider

import (
	"context"
	"os"
	"path/filepath"
	"testing"

	"github.com/hashicorp/terraform-plugin-framework/datasource"
	"github.com/hashicorp/terraform-plugin-framework/provider"
	"github.com/hashicorp/terraform-plugin-framework/resource"
	"github.com/hashicorp/terraform-plugin-framework/tfsdk"
	"github.com/hashicorp/terraform-plugin-framework/types"
)

func TestCalculateCostEstimate(t *testing.T) {
	cases := []struct {
		name       string
		complexity string
		count      int64
		devRate    float64
		infraCost  float64
		wantHours  float64
	}{
		{name: "low", complexity: "Low", count: 2, devRate: 10, infraCost: 5, wantHours: 1.0},
		{name: "medium", complexity: "Medium", count: 2, devRate: 10, infraCost: 5, wantHours: 2.0},
		{name: "high", complexity: "High", count: 2, devRate: 10, infraCost: 5, wantHours: 3.0},
		{name: "default", complexity: "Other", count: 2, devRate: 10, infraCost: 5, wantHours: 2.0},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			hours, labour, total := calculateCostEstimate(tc.complexity, tc.count, tc.devRate, tc.infraCost)
			if hours != tc.wantHours {
				t.Fatalf("expected hours %.1f, got %.1f", tc.wantHours, hours)
			}
			if labour != tc.wantHours*tc.devRate {
				t.Fatalf("unexpected labour cost %.1f", labour)
			}
			if total != labour+tc.infraCost {
				t.Fatalf("unexpected total cost %.1f", total)
			}
		})
	}
}

func TestInSpecTestFilename(t *testing.T) {
	cases := []struct {
		format string
		want   string
	}{
		{format: "testinfra", want: testinfraFilename},
		{format: "serverspec", want: serverspecFilename},
		{format: "goss", want: gossFilename},
		{format: "ansible", want: ansibleFilename},
		{format: "unknown", want: defaultTestFilename},
	}

	for _, tc := range cases {
		if got := inspecTestFilename(tc.format); got != tc.want {
			t.Fatalf("expected %q for %q, got %q", tc.want, tc.format, got)
		}
	}
}

func TestParseBatchRecipeNames(t *testing.T) {
	if _, err := parseBatchRecipeNames(""); err == nil {
		t.Fatal("expected error for empty recipe names")
	}

	if _, err := parseBatchRecipeNames("   "); err == nil {
		t.Fatal("expected error for whitespace-only recipe names")
	}

	// Test with commas only (all empty after trim)
	if _, err := parseBatchRecipeNames(" , , "); err == nil {
		t.Fatal("expected error for empty recipe names after trimming")
	}

	names, err := parseBatchRecipeNames("default,install")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(names) != 2 {
		t.Fatalf("expected 2 recipe names, got %d", len(names))
	}

	// Test with whitespace around names
	namesWithSpaces, err := parseBatchRecipeNames("  default , install  ")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(namesWithSpaces) != 2 || namesWithSpaces[0] != "default" || namesWithSpaces[1] != "install" {
		t.Fatalf("expected trimmed names, got %v", namesWithSpaces)
	}

	// Test with single recipe
	singleName, err := parseBatchRecipeNames("custom")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(singleName) != 1 || singleName[0] != "custom" {
		t.Fatalf("expected single name, got %v", singleName)
	}
}


func TestProviderConfigureUnknownPath(t *testing.T) {
	p := &SousChefProvider{}
	schema := newProviderSchema(t, p)

	config := newProviderConfig(t, schema, SousChefProviderModel{SousChefPath: types.StringUnknown()})
	resp := &provider.ConfigureResponse{}

	p.Configure(context.Background(), provider.ConfigureRequest{Config: config}, resp)

	if !resp.Diagnostics.HasError() {
		t.Fatal("expected diagnostics error for unknown path")
	}
}

func TestProviderConfigureDefaultsAndCustomPath(t *testing.T) {
	p := &SousChefProvider{}
	schema := newProviderSchema(t, p)

	defaultConfig := newProviderConfig(t, schema, SousChefProviderModel{SousChefPath: types.StringNull()})
	defaultResp := &provider.ConfigureResponse{}
	p.Configure(context.Background(), provider.ConfigureRequest{Config: defaultConfig}, defaultResp)

	if defaultResp.Diagnostics.HasError() {
		t.Fatalf("unexpected diagnostics: %v", defaultResp.Diagnostics)
	}

	client, ok := defaultResp.ResourceData.(*SousChefClient)
	if !ok || client.Path != "souschef" {
		t.Fatalf("expected default souschef path, got %#v", defaultResp.ResourceData)
	}

	customConfig := newProviderConfig(t, schema, SousChefProviderModel{SousChefPath: types.StringValue("/custom/souschef")})
	customResp := &provider.ConfigureResponse{}
	p.Configure(context.Background(), provider.ConfigureRequest{Config: customConfig}, customResp)

	customClient, ok := customResp.DataSourceData.(*SousChefClient)
	if !ok || customClient.Path != "/custom/souschef" {
		t.Fatalf("expected custom souschef path, got %#v", customResp.DataSourceData)
	}
}

func TestAssessmentDataSourceRead(t *testing.T) {
	ds := &assessmentDataSource{client: &SousChefClient{Path: newFakeSousChef(t)}}
	schema := newDataSourceSchema(t, ds)

	config := newDataSourceConfig(t, schema, assessmentDataSourceModel{CookbookPath: types.StringValue("/tmp/cookbook")})
	resp := &datasource.ReadResponse{State: tfsdk.State{Schema: schema}}

	ds.Read(context.Background(), datasource.ReadRequest{Config: config}, resp)

	if resp.Diagnostics.HasError() {
		t.Fatalf("unexpected diagnostics: %v", resp.Diagnostics)
	}

	var state assessmentDataSourceModel
	if diags := resp.State.Get(context.Background(), &state); diags.HasError() {
		t.Fatalf("failed to read state: %v", diags)
	}
	if state.Complexity.ValueString() == "" {
		t.Fatal("expected complexity to be set")
	}
}

func TestAssessmentDataSourceReadErrors(t *testing.T) {
	ds := &assessmentDataSource{client: &SousChefClient{Path: newFakeSousChef(t)}}
	schema := newDataSourceSchema(t, ds)

	t.Setenv("SOUSCHEF_TEST_FAIL", "assess-cookbook")
	config := newDataSourceConfig(t, schema, assessmentDataSourceModel{CookbookPath: types.StringValue("/tmp/cookbook")})
	resp := &datasource.ReadResponse{State: tfsdk.State{Schema: schema}}
	ds.Read(context.Background(), datasource.ReadRequest{Config: config}, resp)
	if !resp.Diagnostics.HasError() {
		t.Fatal("expected diagnostics for CLI error")
	}

	t.Setenv("SOUSCHEF_TEST_FAIL", "")
	t.Setenv("SOUSCHEF_TEST_BAD_JSON", "1")
	resp = &datasource.ReadResponse{State: tfsdk.State{Schema: schema}}
	ds.Read(context.Background(), datasource.ReadRequest{Config: config}, resp)
	if !resp.Diagnostics.HasError() {
		t.Fatal("expected diagnostics for JSON parse error")
	}
}

func TestCostEstimateDataSourceRead(t *testing.T) {
	ds := &costEstimateDataSource{client: &SousChefClient{Path: "souschef"}}
	schema := newDataSourceSchema(t, ds)

	config := newDataSourceConfig(t, schema, costEstimateDataSourceModel{
		CookbookPath:        types.StringValue("/tmp/cookbook"),
		DeveloperHourlyRate: types.Float64Value(200),
		InfrastructureCost:  types.Float64Value(1000),
	})
	resp := &datasource.ReadResponse{State: tfsdk.State{Schema: schema}}

	ds.Read(context.Background(), datasource.ReadRequest{Config: config}, resp)

	if resp.Diagnostics.HasError() {
		t.Fatalf("unexpected diagnostics: %v", resp.Diagnostics)
	}
}

func TestMigrationResourceUpdateAndRead(t *testing.T) {
	r := &migrationResource{client: &SousChefClient{Path: newFakeSousChef(t)}}
	schema := newResourceSchema(t, r)

	outputDir := t.TempDir()
	plan := newPlan(t, schema, migrationResourceModel{
		CookbookPath: types.StringValue("/tmp/cookbook"),
		OutputPath:   types.StringValue(outputDir),
		RecipeName:   types.StringValue("default"),
	})
	updateResp := &resource.UpdateResponse{State: tfsdk.State{Schema: schema}}

	r.Update(context.Background(), resource.UpdateRequest{Plan: plan}, updateResp)
	if updateResp.Diagnostics.HasError() {
		t.Fatalf("unexpected diagnostics: %v", updateResp.Diagnostics)
	}

	state := newState(t, schema, migrationResourceModel{
		RecipeName: types.StringValue("default"),
		OutputPath: types.StringValue(outputDir),
	})
	readResp := &resource.ReadResponse{State: tfsdk.State{Schema: schema}}
	r.Read(context.Background(), resource.ReadRequest{State: state}, readResp)
	if readResp.Diagnostics.HasError() {
		t.Fatalf("unexpected diagnostics: %v", readResp.Diagnostics)
	}
}

func TestMigrationResourceUpdateErrors(t *testing.T) {
	r := &migrationResource{client: &SousChefClient{Path: newFakeSousChef(t)}}
	schema := newResourceSchema(t, r)

	plan := newPlan(t, schema, migrationResourceModel{
		CookbookPath: types.StringValue("/tmp/cookbook"),
		OutputPath:   types.StringValue(t.TempDir()),
		RecipeName:   types.StringValue("default"),
	})

	t.Setenv("SOUSCHEF_TEST_FAIL", "convert-recipe")
	resp := &resource.UpdateResponse{State: tfsdk.State{Schema: schema}}
	r.Update(context.Background(), resource.UpdateRequest{Plan: plan}, resp)
	if !resp.Diagnostics.HasError() {
		t.Fatal("expected diagnostics for update error")
	}

	t.Setenv("SOUSCHEF_TEST_FAIL", "")
	t.Setenv("SOUSCHEF_TEST_SKIP_WRITE", "convert-recipe")
	resp = &resource.UpdateResponse{State: tfsdk.State{Schema: schema}}
	r.Update(context.Background(), resource.UpdateRequest{Plan: plan}, resp)
	if !resp.Diagnostics.HasError() {
		t.Fatal("expected diagnostics for missing playbook")
	}
}

func TestMigrationResourceCreateSuccess(t *testing.T) {
	r := &migrationResource{client: &SousChefClient{Path: newFakeSousChef(t)}}
	schema := newResourceSchema(t, r)

	outputDir := t.TempDir()
	plan := newPlan(t, schema, migrationResourceModel{
		CookbookPath: types.StringValue("/tmp/cookbook"),
		OutputPath:   types.StringValue(outputDir),
		RecipeName:   types.StringValue("myrecipe"),
	})

	createResp := &resource.CreateResponse{State: tfsdk.State{Schema: schema}}
	r.Create(context.Background(), resource.CreateRequest{Plan: plan}, createResp)
	if createResp.Diagnostics.HasError() {
		t.Fatalf("unexpected diagnostics: %v", createResp.Diagnostics)
	}

	// Verify the playbook was created with correct path
	playbookPath := filepath.Join(outputDir, "myrecipe.yml")
	if _, err := os.Stat(playbookPath); os.IsNotExist(err) {
		t.Fatalf("playbook should have been created at %s", playbookPath)
	}

	// Test with null recipe name (should default to "default")
	outputDir2 := t.TempDir()
	plan2 := newPlan(t, schema, migrationResourceModel{
		CookbookPath: types.StringValue("/tmp/cookbook"),
		OutputPath:   types.StringValue(outputDir2),
		RecipeName:   types.StringNull(),
	})

	createResp2 := &resource.CreateResponse{State: tfsdk.State{Schema: schema}}
	r.Create(context.Background(), resource.CreateRequest{Plan: plan2}, createResp2)
	if createResp2.Diagnostics.HasError() {
		t.Fatalf("unexpected diagnostics: %v", createResp2.Diagnostics)
	}

	// Verify it used "default" recipe name
	defaultPath := filepath.Join(outputDir2, "default.yml")
	if _, err := os.Stat(defaultPath); os.IsNotExist(err) {
		t.Fatalf("playbook should have been created at %s with default recipe name", defaultPath)
	}
}

func TestMigrationResourceCreateErrors(t *testing.T) {
	r := &migrationResource{client: &SousChefClient{Path: newFakeSousChef(t)}}
	schema := newResourceSchema(t, r)

	plan := newPlan(t, schema, migrationResourceModel{
		CookbookPath: types.StringValue("/tmp/cookbook"),
		OutputPath:   types.StringValue(t.TempDir()),
		RecipeName:   types.StringNull(),
	})

	t.Setenv("SOUSCHEF_TEST_FAIL", "convert-recipe")
	resp := &resource.CreateResponse{State: tfsdk.State{Schema: schema}}
	r.Create(context.Background(), resource.CreateRequest{Plan: plan}, resp)
	if !resp.Diagnostics.HasError() {
		t.Fatal("expected diagnostics for convert error")
	}

	t.Setenv("SOUSCHEF_TEST_FAIL", "")
	t.Setenv("SOUSCHEF_TEST_SKIP_WRITE", "convert-recipe")
	resp = &resource.CreateResponse{State: tfsdk.State{Schema: schema}}
	r.Create(context.Background(), resource.CreateRequest{Plan: plan}, resp)
	if !resp.Diagnostics.HasError() {
		t.Fatal("expected diagnostics for missing playbook")
	}
}

func TestMigrationResourceReadAndDeleteErrors(t *testing.T) {
	r := &migrationResource{}
	schema := newResourceSchema(t, r)

	outputDir := t.TempDir()
	playbookPath := filepath.Join(outputDir, "default.yml")
	if err := os.WriteFile(playbookPath, []byte("data"), 0000); err != nil {
		t.Fatalf("failed to write playbook: %v", err)
	}

	state := newState(t, schema, migrationResourceModel{
		RecipeName: types.StringValue("default"),
		OutputPath: types.StringValue(outputDir),
	})

	readResp := &resource.ReadResponse{State: tfsdk.State{Schema: schema}}
	r.Read(context.Background(), resource.ReadRequest{State: state}, readResp)
	if !readResp.Diagnostics.HasError() {
		t.Fatal("expected diagnostics for unreadable playbook")
	}

	// Test Delete fails when trying to delete a directory instead of file
	// os.Remove() succeeds on empty directories but fails on non-empty ones or when it's a directory with contents
	dirPath := filepath.Join(outputDir, "dir.yml")
	if err := os.MkdirAll(dirPath, 0755); err != nil {
		t.Fatalf("failed to create directory: %v", err)
	}
	// Put a file in the directory so os.Remove fails
	if err := os.WriteFile(filepath.Join(dirPath, "file.txt"), []byte("content"), 0644); err != nil {
		t.Fatalf("failed to write file in directory: %v", err)
	}

	dirState := newState(t, schema, migrationResourceModel{
		RecipeName: types.StringValue("dir"),
		OutputPath: types.StringValue(outputDir),
	})
	deleteResp := &resource.DeleteResponse{}
	r.Delete(context.Background(), resource.DeleteRequest{State: dirState}, deleteResp)
	if !deleteResp.Diagnostics.HasError() {
		t.Fatal("expected diagnostics for delete error when resource is non-empty directory")
	}
}

func TestMigrationResourceReadRemovesMissingPlaybook(t *testing.T) {
	r := &migrationResource{}
	schema := newResourceSchema(t, r)

	state := newState(t, schema, migrationResourceModel{
		RecipeName: types.StringValue("default"),
		OutputPath: types.StringValue(t.TempDir()),
	})
	readResp := &resource.ReadResponse{State: tfsdk.State{Schema: schema}}

	r.Read(context.Background(), resource.ReadRequest{State: state}, readResp)
	if readResp.Diagnostics.HasError() {
		t.Fatalf("unexpected diagnostics: %v", readResp.Diagnostics)
	}
	if !readResp.State.Raw.IsNull() {
		t.Fatal("expected resource to be removed when playbook is missing")
	}
}

func TestMigrationResourceImportStateSuccessAndErrors(t *testing.T) {
	r := &migrationResource{}
	schema := newResourceSchema(t, r)

	cookbookDir := t.TempDir()
	outputDir := t.TempDir()
	playbookPath := filepath.Join(outputDir, "default.yml")
	if err := os.WriteFile(playbookPath, []byte("content"), 0644); err != nil {
		t.Fatalf("failed to write playbook: %v", err)
	}

	resp := &resource.ImportStateResponse{State: newEmptyState(schema)}
	req := resource.ImportStateRequest{ID: cookbookDir + "|" + outputDir + "|default"}
	r.ImportState(context.Background(), req, resp)
	if resp.Diagnostics.HasError() {
		t.Fatalf("unexpected diagnostics: %v", resp.Diagnostics)
	}

	if err := os.Chmod(playbookPath, 0000); err != nil {
		t.Fatalf("failed to chmod playbook: %v", err)
	}
	resp = &resource.ImportStateResponse{State: newEmptyState(schema)}
	r.ImportState(context.Background(), req, resp)
	if !resp.Diagnostics.HasError() {
		t.Fatal("expected diagnostics for unreadable playbook")
	}
}

func TestDeleteOperationsWithWarnings(t *testing.T) {
	// Test Habitat Migration Delete with non-existent file (should be silent)
	r := &habitatMigrationResource{}
	schema := newResourceSchema(t, r)

	state := newState(t, schema, habitatMigrationResourceModel{
		PlanPath:   types.StringValue("/tmp/plan.sh"),
		OutputPath: types.StringValue(t.TempDir()),
	})
	deleteResp := &resource.DeleteResponse{}
	r.Delete(context.Background(), resource.DeleteRequest{State: state}, deleteResp)
	// No diagnostics expected for missing file
	if deleteResp.Diagnostics.HasError() {
		t.Fatalf("unexpected diagnostics for missing file: %v", deleteResp.Diagnostics)
	}

	// Test InSpec Migration Delete with actual file (should succeed)
	inspecR := &inspecMigrationResource{}
	inspecSchema := newResourceSchema(t, inspecR)

	outputDir := t.TempDir()
	testFilePath := filepath.Join(outputDir, "test_spec.py")
	if err := os.WriteFile(testFilePath, []byte("test"), 0644); err != nil {
		t.Fatalf("failed to write test file: %v", err)
	}

	inspecState := newState(t, inspecSchema, inspecMigrationResourceModel{
		OutputPath:   types.StringValue(outputDir),
		OutputFormat: types.StringValue("testinfra"),
	})
	inspecDeleteResp := &resource.DeleteResponse{}
	inspecR.Delete(context.Background(), resource.DeleteRequest{State: inspecState}, inspecDeleteResp)
	if inspecDeleteResp.Diagnostics.HasError() {
		t.Fatalf("unexpected diagnostics: %v", inspecDeleteResp.Diagnostics)
	}

	// Verify file was deleted
	if _, err := os.Stat(testFilePath); err == nil {
		t.Fatal("test file should have been deleted")
	}
}

func TestMigrationDeleteSuccess(t *testing.T) {
	r := &migrationResource{}
	schema := newResourceSchema(t, r)

	outputDir := t.TempDir()
	playbookPath := filepath.Join(outputDir, "success.yml")
	if err := os.WriteFile(playbookPath, []byte("content"), 0644); err != nil {
		t.Fatalf("failed to write playbook: %v", err)
	}

	state := newState(t, schema, migrationResourceModel{
		RecipeName: types.StringValue("success"),
		OutputPath: types.StringValue(outputDir),
	})

	deleteResp := &resource.DeleteResponse{}
	r.Delete(context.Background(), resource.DeleteRequest{State: state}, deleteResp)

	if deleteResp.Diagnostics.HasError() {
		t.Fatalf("unexpected diagnostics: %v", deleteResp.Diagnostics)
	}

	// Verify file was deleted
	if _, err := os.Stat(playbookPath); err == nil {
		t.Fatal("playbook should have been deleted")
	}
}

func TestBatchMigrationDeleteSuccess(t *testing.T) {
	r := &batchMigrationResource{}
	schema := newResourceSchema(t, r)

	outputDir := t.TempDir()
	recipe1Path := filepath.Join(outputDir, "default.yml")
	recipe2Path := filepath.Join(outputDir, "install.yml")

	if err := os.WriteFile(recipe1Path, []byte("content1"), 0644); err != nil {
		t.Fatalf("failed to write recipe 1: %v", err)
	}
	if err := os.WriteFile(recipe2Path, []byte("content2"), 0644); err != nil {
		t.Fatalf("failed to write recipe 2: %v", err)
	}

	// Create state with proper Map initialization
	emptyPlaybooks, _ := types.MapValueFrom(context.Background(), types.StringType, map[string]string{})

	state := newState(t, schema, batchMigrationResourceModel{
		ID:            types.StringValue("batch-test"),
		RecipeNames: []types.String{
			types.StringValue("default"),
			types.StringValue("install"),
		},
		OutputPath:   types.StringValue(outputDir),
		CookbookName: types.StringValue("test"),
		PlaybookCount: types.Int64Value(2),
		Playbooks:    emptyPlaybooks,
	})

	deleteResp := &resource.DeleteResponse{}
	r.Delete(context.Background(), resource.DeleteRequest{State: state}, deleteResp)

	if deleteResp.Diagnostics.HasError() {
		t.Fatalf("unexpected diagnostics: %v", deleteResp.Diagnostics)
	}

	// Verify files were deleted
	if _, err := os.Stat(recipe1Path); err == nil {
		t.Fatal("recipe 1 should have been deleted")
	}
	if _, err := os.Stat(recipe2Path); err == nil {
		t.Fatal("recipe 2 should have been deleted")
	}
}
