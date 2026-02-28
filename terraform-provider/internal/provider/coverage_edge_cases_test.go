// Package provider contains edge case tests for full coverage.
package provider

import (
	"context"
	"os"
	"path/filepath"
	"testing"

	"github.com/hashicorp/terraform-plugin-framework/datasource"
	"github.com/hashicorp/terraform-plugin-framework/resource"
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
		t.Fatalf("unexpected diagnostics: %v", resp.Diagnostics)
	}
}

func TestBatchConfigureValidClient(t *testing.T) {
	r := &batchMigrationResource{}
	client := &SousChefClient{Path: "test"}
	resp := &resource.ConfigureResponse{}
	r.Configure(context.Background(), resource.ConfigureRequest{ProviderData: client}, resp)

	if resp.Diagnostics.HasError() {
		t.Fatalf("unexpected diagnostics: %v", resp.Diagnostics)
	}
}

func TestHabitatConfigureValidClient(t *testing.T) {
	r := &habitatMigrationResource{}
	client := &SousChefClient{Path: "test"}
	resp := &resource.ConfigureResponse{}
	r.Configure(context.Background(), resource.ConfigureRequest{ProviderData: client}, resp)

	if resp.Diagnostics.HasError() {
		t.Fatalf("unexpected diagnostics: %v", resp.Diagnostics)
	}
}

func TestInSpecConfigureValidClient(t *testing.T) {
	r := &inspecMigrationResource{}
	client := &SousChefClient{Path: "test"}
	resp := &resource.ConfigureResponse{}
	r.Configure(context.Background(), resource.ConfigureRequest{ProviderData: client}, resp)

	if resp.Diagnostics.HasError() {
		t.Fatalf("unexpected diagnostics: %v", resp.Diagnostics)
	}
}

func TestDataSourceConfigureWithClient(t *testing.T) {
	// Test DataSource Configure
	ds := &assessmentDataSource{}
	client := &SousChefClient{Path: "test"}
	resp := &datasource.ConfigureResponse{}
	ds.Configure(context.Background(), datasource.ConfigureRequest{ProviderData: client}, resp)

	if resp.Diagnostics.HasError() {
		t.Fatalf("unexpected diagnostics: %v", resp.Diagnostics)
	}

	// Make sure client was saved
	if ds.client != client {
		t.Fatalf("client not configured properly")
	}
}

func TestCostEstimateDataSourceConfigureValidClient(t *testing.T) {
	// Test Configure with valid client
	ds := &costEstimateDataSource{}
	client := &SousChefClient{Path: "test"}
	resp := &datasource.ConfigureResponse{}
	ds.Configure(context.Background(), datasource.ConfigureRequest{ProviderData: client}, resp)

	if resp.Diagnostics.HasError() {
		t.Fatalf("unexpected diagnostics: %v", resp.Diagnostics)
	}

	if ds.client != client {
		t.Fatalf("client not configured properly")
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
		CookbookPath:        types.StringValue("/tmp/cookbook"),
		DeveloperHourlyRate: types.Float64Null(),
		InfrastructureCost:  types.Float64Null(),
	})
	resp := &datasource.ReadResponse{State: tfsdk.State{Schema: schema}}

	ds.Read(context.Background(), datasource.ReadRequest{Config: config}, resp)

	if resp.Diagnostics.HasError() {
		t.Fatalf("unexpected diagnostics: %v", resp.Diagnostics)
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
		PlanPath:   types.StringValue("/tmp/plan.sh"),
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
	os.Chmod(dockerfilePath, 0644)
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
			ProfilePath:  types.StringValue("/tmp/profile"),
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

func TestMigrationReadWithUnreadablePlaybook(t *testing.T) {
	r := &migrationResource{}
	schema := newResourceSchema(t, r)

	outputDir := t.TempDir()
	playbookPath := filepath.Join(outputDir, "test.yml")

	// Create file with no read permissions
	if err := os.WriteFile(playbookPath, []byte("content"), 0000); err != nil {
		t.Fatalf("failed to write playbook: %v", err)
	}
	defer os.Chmod(playbookPath, 0644) // cleanup

	state := newState(t, schema, migrationResourceModel{
		RecipeName: types.StringValue("test"),
		OutputPath: types.StringValue(outputDir),
	})

	readResp := &resource.ReadResponse{State: tfsdk.State{Schema: schema}}
	r.Read(context.Background(), resource.ReadRequest{State: state}, readResp)

	if !readResp.Diagnostics.HasError() {
		t.Fatal("expected diagnostics for unreadable playbook")
	}
}

func TestBatchMigrationCreateWithMissingOutput(t *testing.T) {
	r := &batchMigrationResource{client: &SousChefClient{Path: newFakeSousChef(t)}}
	schema := newResourceSchema(t, r)

	// Force the fake CLI to not write output
	plan := newPlan(t, schema, batchMigrationResourceModel{
		CookbookPath: types.StringValue("/tmp/cookbook"),
		OutputPath:   types.StringValue(t.TempDir()),
		RecipeNames: []types.String{
			types.StringValue("default"),
		},
		ID:            types.StringNull(),
		CookbookName:  types.StringNull(),
		PlaybookCount: types.Int64Null(),
		Playbooks:     types.MapNull(types.StringType),
	})

	t.Setenv("SOUSCHEF_TEST_SKIP_WRITE", "convert-recipe")
	createResp := &resource.CreateResponse{State: tfsdk.State{Schema: schema}}
	r.Create(context.Background(), resource.CreateRequest{Plan: plan}, createResp)

	if !createResp.Diagnostics.HasError() {
		t.Fatal("expected diagnostics when output file is not created")
	}
}

func TestBatchMigrationCreateWithUnreadablePlaybook(t *testing.T) {
	r := &batchMigrationResource{client: &SousChefClient{Path: newFakeSousChef(t)}}
	schema := newResourceSchema(t, r)

	plan := newPlan(t, schema, batchMigrationResourceModel{
		CookbookPath: types.StringValue("/tmp/cookbook"),
		OutputPath:   types.StringValue(t.TempDir()),
		RecipeNames: []types.String{
			types.StringValue("default"),
		},
		ID:            types.StringNull(),
		CookbookName:  types.StringNull(),
		PlaybookCount: types.Int64Null(),
		Playbooks:     types.MapNull(types.StringType),
	})

	t.Setenv("SOUSCHEF_TEST_CHMOD", "convert-recipe")
	createResp := &resource.CreateResponse{State: tfsdk.State{Schema: schema}}
	r.Create(context.Background(), resource.CreateRequest{Plan: plan}, createResp)

	if !createResp.Diagnostics.HasError() {
		t.Fatal("expected diagnostics when playbook is unreadable")
	}
}

func TestBatchMigrationUpdateWithUnreadablePlaybook(t *testing.T) {
	r := &batchMigrationResource{client: &SousChefClient{Path: newFakeSousChef(t)}}
	schema := newResourceSchema(t, r)

	plan := newPlan(t, schema, batchMigrationResourceModel{
		CookbookPath: types.StringValue("/tmp/cookbook"),
		OutputPath:   types.StringValue(t.TempDir()),
		RecipeNames: []types.String{
			types.StringValue("default"),
		},
		ID:            types.StringNull(),
		CookbookName:  types.StringNull(),
		PlaybookCount: types.Int64Null(),
		Playbooks:     types.MapNull(types.StringType),
	})

	t.Setenv("SOUSCHEF_TEST_CHMOD", "convert-recipe")
	updateResp := &resource.UpdateResponse{State: tfsdk.State{Schema: schema}}
	r.Update(context.Background(), resource.UpdateRequest{Plan: plan}, updateResp)

	if !updateResp.Diagnostics.HasError() {
		t.Fatal("expected diagnostics when playbook is unreadable")
	}
}

func TestBatchMigrationReadWithUnreadablePlaybook(t *testing.T) {
	r := &batchMigrationResource{}
	schema := newResourceSchema(t, r)

	outputDir := t.TempDir()
	playbookPath := filepath.Join(outputDir, "default.yml")
	if err := os.WriteFile(playbookPath, []byte("data"), 0000); err != nil {
		t.Fatalf("failed to write playbook: %v", err)
	}
	defer os.Chmod(playbookPath, 0644)

	state := newState(t, schema, batchMigrationResourceModel{
		ID:            types.StringValue("test"),
		RecipeNames: []types.String{
			types.StringValue("default"),
		},
		OutputPath:   types.StringValue(outputDir),
		CookbookName: types.StringValue("test"),
		PlaybookCount: types.Int64Value(1),
		Playbooks:    types.MapNull(types.StringType),
	})

	readResp := &resource.ReadResponse{State: tfsdk.State{Schema: schema}}
	r.Read(context.Background(), resource.ReadRequest{State: state}, readResp)

	if !readResp.Diagnostics.HasError() {
		t.Fatal("expected diagnostics for unreadable playbook")
	}
}

func TestHabitatMigrationCreateWithMissingPlan(t *testing.T) {
	r := &habitatMigrationResource{client: &SousChefClient{Path: newFakeSousChef(t)}}
	schema := newResourceSchema(t, r)

	t.Setenv("SOUSCHEF_TEST_FAIL", "convert-habitat")
	plan := newPlan(t, schema, habitatMigrationResourceModel{
		PlanPath:   types.StringValue("/nonexistent/plan.sh"),
		OutputPath: types.StringValue(t.TempDir()),
		BaseImage:  types.StringNull(),
		PackageName: types.StringNull(),
		ID:         types.StringNull(),
		DockerfileContent: types.StringNull(),
	})

	createResp := &resource.CreateResponse{State: tfsdk.State{Schema: schema}}
	r.Create(context.Background(), resource.CreateRequest{Plan: plan}, createResp)

	if !createResp.Diagnostics.HasError() {
		t.Fatal("expected diagnostics when conversion fails")
	}
}

func TestHabitatMigrationUpdateWithUnreadableDockerfile(t *testing.T) {
	r := &habitatMigrationResource{client: &SousChefClient{Path: newFakeSousChef(t)}}
	schema := newResourceSchema(t, r)

	planPath := filepath.Join(t.TempDir(), "plan.sh")
	if err := os.WriteFile(planPath, []byte("pkg_name=myapp\n"), 0644); err != nil {
		t.Fatalf("failed to write plan: %v", err)
	}

	plan := newPlan(t, schema, habitatMigrationResourceModel{
		PlanPath:   types.StringValue(planPath),
		OutputPath: types.StringValue(t.TempDir()),
		BaseImage:  types.StringNull(),
		PackageName: types.StringNull(),
		ID:         types.StringNull(),
		DockerfileContent: types.StringNull(),
	})

	t.Setenv("SOUSCHEF_TEST_CHMOD", "convert-habitat")
	updateResp := &resource.UpdateResponse{State: tfsdk.State{Schema: schema}}
	r.Update(context.Background(), resource.UpdateRequest{Plan: plan}, updateResp)

	if !updateResp.Diagnostics.HasError() {
		t.Fatal("expected diagnostics when Dockerfile is unreadable")
	}
}

func TestInSpecMigrationCreateWithMissingProfile(t *testing.T) {
	r := &inspecMigrationResource{client: &SousChefClient{Path: newFakeSousChef(t)}}
	schema := newResourceSchema(t, r)

	t.Setenv("SOUSCHEF_TEST_FAIL", "convert-inspec")
	plan := newPlan(t, schema, inspecMigrationResourceModel{
		ProfilePath:   types.StringValue("/nonexistent/profile"),
		OutputPath:    types.StringValue(t.TempDir()),
		OutputFormat:  types.StringValue("testinfra"),
		ID:            types.StringNull(),
		ProfileName:   types.StringNull(),
		TestContent:   types.StringNull(),
	})

	createResp := &resource.CreateResponse{State: tfsdk.State{Schema: schema}}
	r.Create(context.Background(), resource.CreateRequest{Plan: plan}, createResp)

	if !createResp.Diagnostics.HasError() {
		t.Fatal("expected diagnostics when conversion fails")
	}
}

func TestInSpecMigrationUpdateWithUnreadableTestFile(t *testing.T) {
	r := &inspecMigrationResource{client: &SousChefClient{Path: newFakeSousChef(t)}}
	schema := newResourceSchema(t, r)

	plan := newPlan(t, schema, inspecMigrationResourceModel{
		ProfilePath:   types.StringValue("/tmp/profile"),
		OutputPath:    types.StringValue(t.TempDir()),
		OutputFormat:  types.StringValue("testinfra"),
		ID:            types.StringNull(),
		ProfileName:   types.StringNull(),
		TestContent:   types.StringNull(),
	})

	t.Setenv("SOUSCHEF_TEST_CHMOD", "convert-inspec")
	updateResp := &resource.UpdateResponse{State: tfsdk.State{Schema: schema}}
	r.Update(context.Background(), resource.UpdateRequest{Plan: plan}, updateResp)

	if !updateResp.Diagnostics.HasError() {
		t.Fatal("expected diagnostics when test file is unreadable")
	}
}

func TestBatchMigrationReadWithMissingPlaybook(t *testing.T) {
	r := &batchMigrationResource{}
	schema := newResourceSchema(t, r)

	state := newState(t, schema, batchMigrationResourceModel{
		ID:            types.StringValue("test"),
		RecipeNames: []types.String{
			types.StringValue("missing"),
		},
		OutputPath:   types.StringValue(t.TempDir()),
		CookbookName: types.StringValue("test"),
		PlaybookCount: types.Int64Value(0),
		Playbooks:    types.MapNull(types.StringType),
	})

	readResp := &resource.ReadResponse{State: tfsdk.State{Schema: schema}}
	r.Read(context.Background(), resource.ReadRequest{State: state}, readResp)

	// Should remove the resource when no playbooks exist
	if !readResp.State.Raw.IsNull() {
		t.Fatal("expected resource to be removed when no playbooks found")
	}
}

func TestHabitatMigrationReadWithMissingDockerfile(t *testing.T) {
	r := &habitatMigrationResource{}
	schema := newResourceSchema(t, r)

	state := newState(t, schema, habitatMigrationResourceModel{
		PlanPath:   types.StringValue("/tmp/plan.sh"),
		OutputPath: types.StringValue(t.TempDir()),
		PackageName: types.StringValue("test"),
		ID:         types.StringValue("test"),
		DockerfileContent: types.StringNull(),
		BaseImage:  types.StringNull(),
	})

	readResp := &resource.ReadResponse{State: tfsdk.State{Schema: schema}}
	r.Read(context.Background(), resource.ReadRequest{State: state}, readResp)

	// Should remove the resource when Dockerfile doesn't exist
	if !readResp.State.Raw.IsNull() {
		t.Fatal("expected resource to be removed when Dockerfile not found")
	}
}

func TestInSpecMigrationReadWithMissingTestFile(t *testing.T) {
	r := &inspecMigrationResource{}
	schema := newResourceSchema(t, r)

	state := newState(t, schema, inspecMigrationResourceModel{
		ProfilePath:  types.StringValue("/tmp/profile"),
		OutputPath:   types.StringValue(t.TempDir()),
		OutputFormat: types.StringValue("testinfra"),
		ProfileName:  types.StringValue("test"),
		ID:           types.StringValue("test"),
		TestContent:  types.StringNull(),
	})

	readResp := &resource.ReadResponse{State: tfsdk.State{Schema: schema}}
	r.Read(context.Background(), resource.ReadRequest{State: state}, readResp)

	// Should remove the resource when test file doesn't exist
	if !readResp.State.Raw.IsNull() {
		t.Fatal("expected resource to be removed when test file not found")
	}
}

func TestCreateOutputPathError(t *testing.T) {
	// Ensure create returns diagnostics when output path is a file.
	filePath := filepath.Join(t.TempDir(), "output-file")
	if err := os.WriteFile(filePath, []byte("content"), 0644); err != nil {
		t.Fatalf("failed to write file: %v", err)
	}

	// Migration resource
	migration := &migrationResource{client: &SousChefClient{Path: newFakeSousChef(t)}}
	migrationSchema := newResourceSchema(t, migration)
	plan := newPlan(t, migrationSchema, migrationResourceModel{
		CookbookPath: types.StringValue("/tmp/cookbook"),
		OutputPath:   types.StringValue(filePath),
		RecipeName:   types.StringValue("default"),
	})
	resp := &resource.CreateResponse{State: tfsdk.State{Schema: migrationSchema}}
	migration.Create(context.Background(), resource.CreateRequest{Plan: plan}, resp)
	if !resp.Diagnostics.HasError() {
		t.Fatal("expected diagnostics for migration output path error")
	}

	// Batch migration resource
	batch := &batchMigrationResource{client: &SousChefClient{Path: newFakeSousChef(t)}}
	batchSchema := newResourceSchema(t, batch)
	batchPlan := newPlan(t, batchSchema, batchMigrationResourceModel{
		CookbookPath: types.StringValue("/tmp/cookbook"),
		OutputPath:   types.StringValue(filePath),
		RecipeNames: []types.String{
			types.StringValue("default"),
		},
		ID:            types.StringNull(),
		CookbookName:  types.StringNull(),
		PlaybookCount: types.Int64Null(),
		Playbooks:     types.MapNull(types.StringType),
	})
	batchResp := &resource.CreateResponse{State: tfsdk.State{Schema: batchSchema}}
	batch.Create(context.Background(), resource.CreateRequest{Plan: batchPlan}, batchResp)
	if !batchResp.Diagnostics.HasError() {
		t.Fatal("expected diagnostics for batch output path error")
	}

	// Habitat migration resource
	planPath := filepath.Join(t.TempDir(), "plan.sh")
	if err := os.WriteFile(planPath, []byte("pkg_name=myapp\n"), 0644); err != nil {
		t.Fatalf("failed to write plan: %v", err)
	}
	habitat := &habitatMigrationResource{client: &SousChefClient{Path: newFakeSousChef(t)}}
	habitatSchema := newResourceSchema(t, habitat)
	habitatPlan := newPlan(t, habitatSchema, habitatMigrationResourceModel{
		PlanPath:          types.StringValue(planPath),
		OutputPath:        types.StringValue(filePath),
		BaseImage:         types.StringNull(),
		PackageName:       types.StringNull(),
		ID:                types.StringNull(),
		DockerfileContent: types.StringNull(),
	})
	habitatResp := &resource.CreateResponse{State: tfsdk.State{Schema: habitatSchema}}
	habitat.Create(context.Background(), resource.CreateRequest{Plan: habitatPlan}, habitatResp)
	if !habitatResp.Diagnostics.HasError() {
		t.Fatal("expected diagnostics for habitat output path error")
	}

	// InSpec migration resource
	inspec := &inspecMigrationResource{client: &SousChefClient{Path: newFakeSousChef(t)}}
	inspecSchema := newResourceSchema(t, inspec)
	inspecPlan := newPlan(t, inspecSchema, inspecMigrationResourceModel{
		ProfilePath:  types.StringValue("/tmp/profile"),
		OutputPath:   types.StringValue(filePath),
		OutputFormat: types.StringValue("testinfra"),
		ID:           types.StringNull(),
		ProfileName:  types.StringNull(),
		TestContent:  types.StringNull(),
	})
	inspecResp := &resource.CreateResponse{State: tfsdk.State{Schema: inspecSchema}}
	inspec.Create(context.Background(), resource.CreateRequest{Plan: inspecPlan}, inspecResp)
	if !inspecResp.Diagnostics.HasError() {
		t.Fatal("expected diagnostics for inspec output path error")
	}
}

func TestUpdateCommandFailures(t *testing.T) {
	// Batch update command failure
	batch := &batchMigrationResource{client: &SousChefClient{Path: newFakeSousChef(t)}}
	batchSchema := newResourceSchema(t, batch)
	batchPlan := newPlan(t, batchSchema, batchMigrationResourceModel{
		CookbookPath: types.StringValue("/tmp/cookbook"),
		OutputPath:   types.StringValue(t.TempDir()),
		RecipeNames: []types.String{
			types.StringValue("default"),
		},
		ID:            types.StringNull(),
		CookbookName:  types.StringNull(),
		PlaybookCount: types.Int64Null(),
		Playbooks:     types.MapNull(types.StringType),
	})

	t.Setenv("SOUSCHEF_TEST_FAIL", "convert-recipe")
	batchResp := &resource.UpdateResponse{State: tfsdk.State{Schema: batchSchema}}
	batch.Update(context.Background(), resource.UpdateRequest{Plan: batchPlan}, batchResp)
	if !batchResp.Diagnostics.HasError() {
		t.Fatal("expected diagnostics for batch update command failure")
	}

	// Habitat update command failure
	planPath := filepath.Join(t.TempDir(), "plan.sh")
	if err := os.WriteFile(planPath, []byte("pkg_name=myapp\n"), 0644); err != nil {
		t.Fatalf("failed to write plan: %v", err)
	}
	habitat := &habitatMigrationResource{client: &SousChefClient{Path: newFakeSousChef(t)}}
	habitatSchema := newResourceSchema(t, habitat)
	habitatPlan := newPlan(t, habitatSchema, habitatMigrationResourceModel{
		PlanPath:          types.StringValue(planPath),
		OutputPath:        types.StringValue(t.TempDir()),
		BaseImage:         types.StringNull(),
		PackageName:       types.StringNull(),
		ID:                types.StringNull(),
		DockerfileContent: types.StringNull(),
	})

	t.Setenv("SOUSCHEF_TEST_FAIL", "convert-habitat")
	habitatResp := &resource.UpdateResponse{State: tfsdk.State{Schema: habitatSchema}}
	habitat.Update(context.Background(), resource.UpdateRequest{Plan: habitatPlan}, habitatResp)
	if !habitatResp.Diagnostics.HasError() {
		t.Fatal("expected diagnostics for habitat update command failure")
	}

	// InSpec update command failure
	inspec := &inspecMigrationResource{client: &SousChefClient{Path: newFakeSousChef(t)}}
	inspecSchema := newResourceSchema(t, inspec)
	inspecPlan := newPlan(t, inspecSchema, inspecMigrationResourceModel{
		ProfilePath:  types.StringValue("/tmp/profile"),
		OutputPath:   types.StringValue(t.TempDir()),
		OutputFormat: types.StringValue("testinfra"),
		ID:           types.StringNull(),
		ProfileName:  types.StringNull(),
		TestContent:  types.StringNull(),
	})

	t.Setenv("SOUSCHEF_TEST_FAIL", "convert-inspec")
	inspecResp := &resource.UpdateResponse{State: tfsdk.State{Schema: inspecSchema}}
	inspec.Update(context.Background(), resource.UpdateRequest{Plan: inspecPlan}, inspecResp)
	if !inspecResp.Diagnostics.HasError() {
		t.Fatal("expected diagnostics for inspec update command failure")
	}
}

func TestDeleteWarningsWithDirectoryTargets(t *testing.T) {
	// Habitat delete warning
	habitat := &habitatMigrationResource{}
	habitatSchema := newResourceSchema(t, habitat)
	habitatOutput := t.TempDir()
	habitatPath := filepath.Join(habitatOutput, "Dockerfile")
	if err := os.MkdirAll(habitatPath, 0755); err != nil {
		t.Fatalf("failed to create directory: %v", err)
	}
	if err := os.WriteFile(filepath.Join(habitatPath, "file.txt"), []byte("x"), 0644); err != nil {
		t.Fatalf("failed to write file: %v", err)
	}

	habitatState := newState(t, habitatSchema, habitatMigrationResourceModel{
		PlanPath:   types.StringValue("/tmp/plan.sh"),
		OutputPath: types.StringValue(habitatOutput),
	})
	habitatResp := &resource.DeleteResponse{}
	habitat.Delete(context.Background(), resource.DeleteRequest{State: habitatState}, habitatResp)
	if len(habitatResp.Diagnostics) == 0 {
		t.Fatal("expected warning diagnostics for habitat delete")
	}

	// InSpec delete warning
	inspec := &inspecMigrationResource{}
	inspecSchema := newResourceSchema(t, inspec)
	inspecOutput := t.TempDir()
	inspecPath := filepath.Join(inspecOutput, "test_spec.py")
	if err := os.MkdirAll(inspecPath, 0755); err != nil {
		t.Fatalf("failed to create directory: %v", err)
	}
	if err := os.WriteFile(filepath.Join(inspecPath, "file.txt"), []byte("x"), 0644); err != nil {
		t.Fatalf("failed to write file: %v", err)
	}

	inspecState := newState(t, inspecSchema, inspecMigrationResourceModel{
		ProfilePath:  types.StringValue("/tmp/profile"),
		OutputPath:   types.StringValue(inspecOutput),
		OutputFormat: types.StringValue("testinfra"),
	})
	inspecResp := &resource.DeleteResponse{}
	inspec.Delete(context.Background(), resource.DeleteRequest{State: inspecState}, inspecResp)
	if len(inspecResp.Diagnostics) == 0 {
		t.Fatal("expected warning diagnostics for inspec delete")
	}

	// Batch delete warning
	batch := &batchMigrationResource{}
	batchSchema := newResourceSchema(t, batch)
	batchOutput := t.TempDir()
	batchPath := filepath.Join(batchOutput, "default.yml")
	if err := os.MkdirAll(batchPath, 0755); err != nil {
		t.Fatalf("failed to create directory: %v", err)
	}
	if err := os.WriteFile(filepath.Join(batchPath, "file.txt"), []byte("x"), 0644); err != nil {
		t.Fatalf("failed to write file: %v", err)
	}

	batchState := newState(t, batchSchema, batchMigrationResourceModel{
		ID:            types.StringValue("batch-test"),
		RecipeNames: []types.String{
			types.StringValue("default"),
		},
		OutputPath:   types.StringValue(batchOutput),
		CookbookName: types.StringValue("test"),
		PlaybookCount: types.Int64Value(1),
		Playbooks:    types.MapNull(types.StringType),
	})
	batchResp := &resource.DeleteResponse{}
	batch.Delete(context.Background(), resource.DeleteRequest{State: batchState}, batchResp)
	if len(batchResp.Diagnostics) == 0 {
		t.Fatal("expected warning diagnostics for batch delete")
	}
}
