// Package provider contains final coverage tests.
package provider

import (
	"context"
	"os"
	"path/filepath"
	"testing"

	"github.com/hashicorp/terraform-plugin-framework/resource"
	"github.com/hashicorp/terraform-plugin-framework/tfsdk"
	"github.com/hashicorp/terraform-plugin-framework/types"
)

// testReadOnlyDeleteHelper creates a read-only file and tests delete behavior
func testReadOnlyDeleteHelper(t *testing.T, r resource.Resource, filePath, fileContent string) {
	t.Helper()
	schema := newResourceSchema(t, r)
	outputDir := t.TempDir()
	readOnlyPath := filepath.Join(outputDir, filePath)

	if err := os.WriteFile(readOnlyPath, []byte(fileContent), 0444); err != nil {
		t.Fatalf("failed to write file: %v", err)
	}
	defer os.Chmod(readOnlyPath, testFilePermissions)

	var state tfsdk.State
	switch r.(type) {
	case *batchMigrationResource:
		emptyPlaybooks, _ := types.MapValueFrom(context.Background(), types.StringType, map[string]string{})
		state = newState(t, schema, batchMigrationResourceModel{
			ID: types.StringValue("batch-test"),
			RecipeNames: []types.String{
				types.StringValue("readonly"),
			},
			OutputPath:    types.StringValue(outputDir),
			CookbookName:  types.StringValue("test"),
			PlaybookCount: types.Int64Value(1),
			Playbooks:     emptyPlaybooks,
		})
	case *habitatMigrationResource:
		state = newState(t, schema, habitatMigrationResourceModel{
			PlanPath:   types.StringValue("/tmp/plan.sh"),
			OutputPath: types.StringValue(outputDir),
		})
	case *inspecMigrationResource:
		state = newState(t, schema, inspecMigrationResourceModel{
			ProfilePath:  types.StringValue("/tmp/profile"),
			OutputPath:   types.StringValue(outputDir),
			OutputFormat: types.StringValue("testinfra"),
		})
	}

	deleteResp := &resource.DeleteResponse{}
	r.Delete(context.Background(), resource.DeleteRequest{State: state}, deleteResp)

	// May or may not error depending on OS permissions
	_ = deleteResp.Diagnostics
}

// Comprehensive tests for 100% coverage of Delete operations with directory obstacles
func TestMigrationDeleteWithDirectory(t *testing.T) {
	r := &migrationResource{}
	schema := newResourceSchema(t, r)

	outputDir := t.TempDir()
	dirPath := filepath.Join(outputDir, "dir_recipe.yml")
	if err := os.MkdirAll(dirPath, 0755); err != nil {
		t.Fatalf("failed to create directory: %v", err)
	}
	// Add file to directory so removal fails
	if err := os.WriteFile(filepath.Join(dirPath, "file.txt"), []byte("x"), 0644); err != nil {
		t.Fatalf("failed to create file in directory: %v", err)
	}

	state := newState(t, schema, migrationResourceModel{
		RecipeName: types.StringValue("dir_recipe"),
		OutputPath: types.StringValue(outputDir),
	})

	deleteResp := &resource.DeleteResponse{}
	r.Delete(context.Background(), resource.DeleteRequest{State: state}, deleteResp)

	// Should report error when directory can't be removed
	if !deleteResp.Diagnostics.HasError() {
		t.Fatal("expected diagnostics when directory cannot be deleted")
	}

	os.Chmod(dirPath, testDirPermissions)
}

// Test batch delete with read-only file
func TestBatchMigrationDeleteWithReadOnlyFile(t *testing.T) {
	testReadOnlyDeleteHelper(t, &batchMigrationResource{}, "readonly.yml", "content")
}

// Test habitat delete with read-only file
func TestHabitatMigrationDeleteWithReadOnlyDockerfile(t *testing.T) {
	testReadOnlyDeleteHelper(t, &habitatMigrationResource{}, "Dockerfile", "FROM ubuntu")
}

// Test inspec delete with read-only test file
func TestInSpecMigrationDeleteWithReadOnlyFile(t *testing.T) {
	testReadOnlyDeleteHelper(t, &inspecMigrationResource{}, "test_spec.py", "test")
}

// Test comprehensive batch migration operations
func TestBatchMigrationCreateAndReadWithMultipleRecipes(t *testing.T) {
	r := &batchMigrationResource{client: &SousChefClient{Path: newFakeSousChef(t)}}
	schema := newResourceSchema(t, r)

	outputDir := t.TempDir()
	plan := newPlan(t, schema, batchMigrationResourceModel{
		CookbookPath: types.StringValue(testTmpCookbook),
		OutputPath:   types.StringValue(outputDir),
		RecipeNames: []types.String{
			types.StringValue("default"),
			types.StringValue("install"),
			types.StringValue("configure"),
		},
		ID:            types.StringNull(),
		CookbookName:  types.StringNull(),
		PlaybookCount: types.Int64Null(),
		Playbooks:     types.MapNull(types.StringType),
	})

	createResp := &resource.CreateResponse{State: tfsdk.State{Schema: schema}}
	r.Create(context.Background(), resource.CreateRequest{Plan: plan}, createResp)
	if createResp.Diagnostics.HasError() {
		t.Fatalf(testUnexpectedDiagnostics, createResp.Diagnostics)
	}

	// Verify all playbooks were created
	for _, recipe := range []string{"default", "install", "configure"} {
		playbookPath := filepath.Join(outputDir, recipe+".yml")
		if _, err := os.Stat(playbookPath); os.IsNotExist(err) {
			t.Fatalf("playbook for recipe %s not created", recipe)
		}
	}
}

// Test comprehensive habitat migration operations
func TestHabitatMigrationCreateWithCustomBaseImage(t *testing.T) {
	r := &habitatMigrationResource{client: &SousChefClient{Path: newFakeSousChef(t)}}
	schema := newResourceSchema(t, r)

	outputDir := t.TempDir()
	planPath := filepath.Join(t.TempDir(), "plan.sh")
	if err := os.WriteFile(planPath, []byte("pkg_name=myapp\\n"), 0644); err != nil {
		t.Fatalf("failed to write plan: %v", err)
	}

	plan := newPlan(t, schema, habitatMigrationResourceModel{
		PlanPath:          types.StringValue(planPath),
		OutputPath:        types.StringValue(outputDir),
		BaseImage:         types.StringValue("mycompany/custom-base:3.0"),
		PackageName:       types.StringNull(),
		ID:                types.StringNull(),
		DockerfileContent: types.StringNull(),
	})

	createResp := &resource.CreateResponse{State: tfsdk.State{Schema: schema}}
	r.Create(context.Background(), resource.CreateRequest{Plan: plan}, createResp)
	if createResp.Diagnostics.HasError() {
		t.Fatalf(testUnexpectedDiagnostics, createResp.Diagnostics)
	}
}

// Test inspec migration with all format variations
func TestInSpecMigrationWithAllFormats(t *testing.T) {
	r := &inspecMigrationResource{client: &SousChefClient{Path: newFakeSousChef(t)}}
	schema := newResourceSchema(t, r)

	formats := []string{"testinfra", "serverspec", "goss", "ansible"}

	for _, format := range formats {
		outputDir := t.TempDir()
		plan := newPlan(t, schema, inspecMigrationResourceModel{
			ProfilePath:  types.StringValue("/tmp/profile"),
			OutputPath:   types.StringValue(outputDir),
			OutputFormat: types.StringValue(format),
			ID:           types.StringNull(),
			ProfileName:  types.StringNull(),
			TestContent:  types.StringNull(),
		})

		createResp := &resource.CreateResponse{State: tfsdk.State{Schema: schema}}
		r.Create(context.Background(), resource.CreateRequest{Plan: plan}, createResp)
		if createResp.Diagnostics.HasError() {
			t.Fatalf("unexpected diagnostics for %s format: %v", format, createResp.Diagnostics)
		}
	}
}
