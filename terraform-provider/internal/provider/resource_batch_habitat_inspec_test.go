// Package provider contains tests for batch, habitat, and inspec resources.
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

const (
	testExpectedConvertError = "expected diagnostics for convert error"
)

func TestBatchMigrationResourceCreateUpdateReadDelete(t *testing.T) {
	r := &batchMigrationResource{client: &SousChefClient{Path: newFakeSousChef(t)}}
	schema := newResourceSchema(t, r)

	outputDir := t.TempDir()
	plan := newPlan(t, schema, batchMigrationResourceModel{
		CookbookPath: types.StringValue("/tmp/cookbook"),
		OutputPath:   types.StringValue(outputDir),
		RecipeNames: []types.String{
			types.StringValue("default"),
			types.StringValue("install"),
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

	updateResp := &resource.UpdateResponse{State: tfsdk.State{Schema: schema}}
	r.Update(context.Background(), resource.UpdateRequest{Plan: plan}, updateResp)
	if updateResp.Diagnostics.HasError() {
		t.Fatalf(testUnexpectedDiagnostics, updateResp.Diagnostics)
	}

	state := newState(t, schema, batchMigrationResourceModel{
		OutputPath:    types.StringValue(outputDir),
		RecipeNames:   []types.String{types.StringValue("default")},
		ID:            types.StringNull(),
		CookbookName:  types.StringNull(),
		PlaybookCount: types.Int64Null(),
		Playbooks:     types.MapNull(types.StringType),
	})
	readResp := &resource.ReadResponse{State: tfsdk.State{Schema: schema}}
	r.Read(context.Background(), resource.ReadRequest{State: state}, readResp)
	if readResp.Diagnostics.HasError() {
		t.Fatalf(testUnexpectedDiagnostics, readResp.Diagnostics)
	}

	deleteResp := &resource.DeleteResponse{}
	r.Delete(context.Background(), resource.DeleteRequest{State: state}, deleteResp)
	if deleteResp.Diagnostics.HasError() {
		t.Fatalf(testUnexpectedDiagnostics, deleteResp.Diagnostics)
	}

	defaultPath := filepath.Join(outputDir, "default.yml")
	if err := os.Remove(defaultPath); err != nil && !os.IsNotExist(err) {
		t.Fatalf("failed to remove playbook: %v", err)
	}
	if err := os.MkdirAll(defaultPath, 0755); err != nil {
		t.Fatalf("failed to create directory playbook: %v", err)
	}
	deleteResp = &resource.DeleteResponse{}
	r.Delete(context.Background(), resource.DeleteRequest{State: state}, deleteResp)
}

func TestBatchMigrationResourceErrors(t *testing.T) {
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

	t.Setenv("SOUSCHEF_TEST_FAIL", "convert-recipe")
	createResp := &resource.CreateResponse{State: tfsdk.State{Schema: schema}}
	r.Create(context.Background(), resource.CreateRequest{Plan: plan}, createResp)
	if !createResp.Diagnostics.HasError() {
		t.Fatal(testExpectedConvertError)
	}

	t.Setenv("SOUSCHEF_TEST_FAIL", "")
	t.Setenv("SOUSCHEF_TEST_SKIP_WRITE", "convert-recipe")
	updateResp := &resource.UpdateResponse{State: tfsdk.State{Schema: schema}}
	r.Update(context.Background(), resource.UpdateRequest{Plan: plan}, updateResp)
	if !updateResp.Diagnostics.HasError() {
		t.Fatal("expected diagnostics for missing playbook")
	}

	outputDir := t.TempDir()
	state := newState(t, schema, batchMigrationResourceModel{
		OutputPath:    types.StringValue(outputDir),
		RecipeNames:   []types.String{types.StringValue("missing")},
		ID:            types.StringNull(),
		CookbookName:  types.StringNull(),
		PlaybookCount: types.Int64Null(),
		Playbooks:     types.MapNull(types.StringType),
	})
	readResp := &resource.ReadResponse{State: tfsdk.State{Schema: schema}}
	r.Read(context.Background(), resource.ReadRequest{State: state}, readResp)
	if readResp.Diagnostics.HasError() {
		t.Fatalf(testUnexpectedDiagnostics, readResp.Diagnostics)
	}

	if !readResp.State.Raw.IsNull() {
		t.Fatal("expected resource to be removed when no playbooks exist")
	}
}

func TestBatchMigrationImportStateErrorsAndSuccess(t *testing.T) {
	r := &batchMigrationResource{}
	schema := newResourceSchema(t, r)

	resp := &resource.ImportStateResponse{State: newEmptyState(schema)}
	r.ImportState(context.Background(), resource.ImportStateRequest{ID: "|/tmp/output|"}, resp)
	if !resp.Diagnostics.HasError() {
		t.Fatal("expected diagnostics for empty recipe names")
	}

	cookbookDir := t.TempDir()
	outputDir := t.TempDir()
	playbookPath := filepath.Join(outputDir, "default.yml")
	if err := os.WriteFile(playbookPath, []byte("content"), 0644); err != nil {
		t.Fatalf("failed to write playbook: %v", err)
	}

	resp = &resource.ImportStateResponse{State: newEmptyState(schema)}
	req := resource.ImportStateRequest{ID: cookbookDir + "|" + outputDir + "|default"}
	r.ImportState(context.Background(), req, resp)
	if resp.Diagnostics.HasError() {
		t.Fatalf(testUnexpectedDiagnostics, resp.Diagnostics)
	}

	resp = &resource.ImportStateResponse{State: newEmptyState(schema)}
	r.ImportState(context.Background(), resource.ImportStateRequest{ID: cookbookDir + "|" + outputDir + "|missing"}, resp)
	if !resp.Diagnostics.HasError() {
		t.Fatal("expected diagnostics for missing playbook")
	}

	if err := os.Chmod(playbookPath, noPermissions); err != nil {
		t.Fatalf("failed to chmod playbook: %v", err)
	}
	resp = &resource.ImportStateResponse{State: newEmptyState(schema)}
	r.ImportState(context.Background(), req, resp)
	if !resp.Diagnostics.HasError() {
		t.Fatal("expected diagnostics for unreadable playbook")
	}
}

func TestHabitatMigrationResourceCoverage(t *testing.T) {
	r := &habitatMigrationResource{client: &SousChefClient{Path: newFakeSousChef(t)}}
	schema := newResourceSchema(t, r)

	planPath := filepath.Join(t.TempDir(), testPlanSh)
	if err := os.WriteFile(planPath, []byte(testPkgNameMyapp), 0644); err != nil {
		t.Fatalf(testFailedToWritePlan, err)
	}

	outputDir := t.TempDir()
	plan := newPlan(t, schema, habitatMigrationResourceModel{
		PlanPath:          types.StringValue(planPath),
		OutputPath:        types.StringValue(outputDir),
		BaseImage:         types.StringNull(),
		ID:                types.StringNull(),
		PackageName:       types.StringNull(),
		DockerfileContent: types.StringNull(),
	})
	createResp := &resource.CreateResponse{State: tfsdk.State{Schema: schema}}
	r.Create(context.Background(), resource.CreateRequest{Plan: plan}, createResp)
	if createResp.Diagnostics.HasError() {
		t.Fatalf(testUnexpectedDiagnostics, createResp.Diagnostics)
	}

	missingState := newState(t, schema, habitatMigrationResourceModel{
		OutputPath: types.StringValue(t.TempDir()),
	})
	readResp := &resource.ReadResponse{State: tfsdk.State{Schema: schema}}
	r.Read(context.Background(), resource.ReadRequest{State: missingState}, readResp)
	if readResp.Diagnostics.HasError() {
		t.Fatalf(testUnexpectedDiagnostics, readResp.Diagnostics)
	}
	if !readResp.State.Raw.IsNull() {
		t.Fatal("expected resource to be removed when dockerfile is missing")
	}

	updateResp := &resource.UpdateResponse{State: tfsdk.State{Schema: schema}}
	r.Update(context.Background(), resource.UpdateRequest{Plan: plan}, updateResp)
	if updateResp.Diagnostics.HasError() {
		t.Fatalf(testUnexpectedDiagnostics, updateResp.Diagnostics)
	}

	state := newState(t, schema, habitatMigrationResourceModel{
		OutputPath: types.StringValue(outputDir),
	})
	readResp = &resource.ReadResponse{State: tfsdk.State{Schema: schema}}
	r.Read(context.Background(), resource.ReadRequest{State: state}, readResp)
	if readResp.Diagnostics.HasError() {
		t.Fatalf(testUnexpectedDiagnostics, readResp.Diagnostics)
	}

	dockerfilePath := filepath.Join(outputDir, "Dockerfile")
	if err := os.Chmod(dockerfilePath, noPermissions); err != nil {
		t.Fatalf("failed to chmod dockerfile: %v", err)
	}
	readResp = &resource.ReadResponse{State: tfsdk.State{Schema: schema}}
	r.Read(context.Background(), resource.ReadRequest{State: state}, readResp)
	if !readResp.Diagnostics.HasError() {
		t.Fatal("expected diagnostics for unreadable dockerfile")
	}

	dirPath := filepath.Join(outputDir, "Dockerfile")
	deleteResp := &resource.DeleteResponse{}
	r.Delete(context.Background(), resource.DeleteRequest{State: newState(t, schema, habitatMigrationResourceModel{
		OutputPath: types.StringValue(outputDir),
	})}, deleteResp)
	if deleteResp.Diagnostics.HasError() {
		t.Fatalf(testUnexpectedDiagnostics, deleteResp.Diagnostics)
	}

	if err := os.MkdirAll(dirPath, 0755); err != nil {
		t.Fatalf("failed to recreate dir: %v", err)
	}
	deleteResp = &resource.DeleteResponse{}
	r.Delete(context.Background(), resource.DeleteRequest{State: newState(t, schema, habitatMigrationResourceModel{
		OutputPath: types.StringValue(outputDir),
	})}, deleteResp)
	if deleteResp.Diagnostics.HasError() {
		t.Fatalf(testUnexpectedDiagnostics, deleteResp.Diagnostics)
	}
}

func TestHabitatMigrationResourceErrors(t *testing.T) {
	r := &habitatMigrationResource{client: &SousChefClient{Path: newFakeSousChef(t)}}
	schema := newResourceSchema(t, r)

	planPath := filepath.Join(t.TempDir(), testPlanSh)
	if err := os.WriteFile(planPath, []byte(testPkgNameMyapp), 0644); err != nil {
		t.Fatalf(testFailedToWritePlan, err)
	}

	plan := newPlan(t, schema, habitatMigrationResourceModel{
		PlanPath:          types.StringValue(planPath),
		OutputPath:        types.StringValue(t.TempDir()),
		BaseImage:         types.StringValue("debian:stable"),
		ID:                types.StringNull(),
		PackageName:       types.StringNull(),
		DockerfileContent: types.StringNull(),
	})

	t.Setenv("SOUSCHEF_TEST_FAIL", "convert-habitat")
	createResp := &resource.CreateResponse{State: tfsdk.State{Schema: schema}}
	r.Create(context.Background(), resource.CreateRequest{Plan: plan}, createResp)
	if !createResp.Diagnostics.HasError() {
		t.Fatal(testExpectedConvertError)
	}

	t.Setenv("SOUSCHEF_TEST_FAIL", "")
	t.Setenv("SOUSCHEF_TEST_SKIP_WRITE", "convert-habitat")
	updateResp := &resource.UpdateResponse{State: tfsdk.State{Schema: schema}}
	r.Update(context.Background(), resource.UpdateRequest{Plan: plan}, updateResp)
	if !updateResp.Diagnostics.HasError() {
		t.Fatal("expected diagnostics for missing dockerfile")
	}

	createResp = &resource.CreateResponse{State: tfsdk.State{Schema: schema}}
	r.Create(context.Background(), resource.CreateRequest{Plan: plan}, createResp)
	if !createResp.Diagnostics.HasError() {
		t.Fatal("expected diagnostics for missing dockerfile on create")
	}
}

func TestHabitatMigrationImportStateCoverage(t *testing.T) {
	r := &habitatMigrationResource{}
	schema := newResourceSchema(t, r)

	resp := &resource.ImportStateResponse{State: newEmptyState(schema)}
	r.ImportState(context.Background(), resource.ImportStateRequest{ID: "missing|"}, resp)
	if !resp.Diagnostics.HasError() {
		t.Fatal("expected diagnostics for invalid import ID")
	}

	planPath := filepath.Join(t.TempDir(), testPlanSh)
	if err := os.WriteFile(planPath, []byte(testPkgNameMyapp), 0644); err != nil {
		t.Fatalf(testFailedToWritePlan, err)
	}
	outputDir := t.TempDir()
	dockerfilePath := filepath.Join(outputDir, "Dockerfile")
	if err := os.WriteFile(dockerfilePath, []byte("FROM ubuntu"), 0644); err != nil {
		t.Fatalf("failed to write dockerfile: %v", err)
	}

	req := resource.ImportStateRequest{ID: planPath + "|" + outputDir + "|"}
	resp = &resource.ImportStateResponse{State: newEmptyState(schema)}
	r.ImportState(context.Background(), req, resp)
	if resp.Diagnostics.HasError() {
		t.Fatalf(testUnexpectedDiagnostics, resp.Diagnostics)
	}

	if err := os.Chmod(dockerfilePath, noPermissions); err != nil {
		t.Fatalf("failed to chmod dockerfile: %v", err)
	}
	resp = &resource.ImportStateResponse{State: newEmptyState(schema)}
	r.ImportState(context.Background(), req, resp)
	if !resp.Diagnostics.HasError() {
		t.Fatal("expected diagnostics for unreadable dockerfile")
	}
}

func TestInSpecMigrationResourceCoverage(t *testing.T) {
	r := &inspecMigrationResource{client: &SousChefClient{Path: newFakeSousChef(t)}}
	schema := newResourceSchema(t, r)

	profileDir := t.TempDir()
	outputDir := t.TempDir()
	plan := newPlan(t, schema, inspecMigrationResourceModel{
		ProfilePath:  types.StringValue(profileDir),
		OutputPath:   types.StringValue(outputDir),
		OutputFormat: types.StringValue("testinfra"),
		ID:           types.StringNull(),
		ProfileName:  types.StringNull(),
		TestContent:  types.StringNull(),
	})

	createResp := &resource.CreateResponse{State: tfsdk.State{Schema: schema}}
	r.Create(context.Background(), resource.CreateRequest{Plan: plan}, createResp)
	if createResp.Diagnostics.HasError() {
		t.Fatalf(testUnexpectedDiagnostics, createResp.Diagnostics)
	}

	missingState := newState(t, schema, inspecMigrationResourceModel{
		OutputPath:   types.StringValue(t.TempDir()),
		OutputFormat: types.StringValue("testinfra"),
	})
	readResp := &resource.ReadResponse{State: tfsdk.State{Schema: schema}}
	r.Read(context.Background(), resource.ReadRequest{State: missingState}, readResp)
	if readResp.Diagnostics.HasError() {
		t.Fatalf(testUnexpectedDiagnostics, readResp.Diagnostics)
	}
	if !readResp.State.Raw.IsNull() {
		t.Fatal("expected resource to be removed when test file is missing")
	}

	updateResp := &resource.UpdateResponse{State: tfsdk.State{Schema: schema}}
	r.Update(context.Background(), resource.UpdateRequest{Plan: plan}, updateResp)
	if updateResp.Diagnostics.HasError() {
		t.Fatalf(testUnexpectedDiagnostics, updateResp.Diagnostics)
	}

	state := newState(t, schema, inspecMigrationResourceModel{
		OutputPath:   types.StringValue(outputDir),
		OutputFormat: types.StringValue("testinfra"),
	})
	readResp = &resource.ReadResponse{State: tfsdk.State{Schema: schema}}
	r.Read(context.Background(), resource.ReadRequest{State: state}, readResp)
	if readResp.Diagnostics.HasError() {
		t.Fatalf(testUnexpectedDiagnostics, readResp.Diagnostics)
	}

	testFilePath := filepath.Join(outputDir, testinfraFilename)
	if err := os.Chmod(testFilePath, noPermissions); err != nil {
		t.Fatalf("failed to chmod test file: %v", err)
	}
	readResp = &resource.ReadResponse{State: tfsdk.State{Schema: schema}}
	r.Read(context.Background(), resource.ReadRequest{State: state}, readResp)
	if !readResp.Diagnostics.HasError() {
		t.Fatal("expected diagnostics for unreadable test file")
	}

	deleteResp := &resource.DeleteResponse{}
	r.Delete(context.Background(), resource.DeleteRequest{State: state}, deleteResp)
	if deleteResp.Diagnostics.HasError() {
		t.Fatalf(testUnexpectedDiagnostics, deleteResp.Diagnostics)
	}

	if err := os.MkdirAll(filepath.Join(outputDir, testinfraFilename), 0755); err != nil {
		t.Fatalf("failed to create directory test file: %v", err)
	}
	deleteResp = &resource.DeleteResponse{}
	r.Delete(context.Background(), resource.DeleteRequest{State: state}, deleteResp)
}

func TestInSpecMigrationResourceErrors(t *testing.T) {
	r := &inspecMigrationResource{client: &SousChefClient{Path: newFakeSousChef(t)}}
	schema := newResourceSchema(t, r)

	profileDir := t.TempDir()
	plan := newPlan(t, schema, inspecMigrationResourceModel{
		ProfilePath:  types.StringValue(profileDir),
		OutputPath:   types.StringValue(t.TempDir()),
		OutputFormat: types.StringValue("serverspec"),
		ID:           types.StringNull(),
		ProfileName:  types.StringNull(),
		TestContent:  types.StringNull(),
	})

	t.Setenv("SOUSCHEF_TEST_FAIL", "convert-inspec")
	createResp := &resource.CreateResponse{State: tfsdk.State{Schema: schema}}
	r.Create(context.Background(), resource.CreateRequest{Plan: plan}, createResp)
	if !createResp.Diagnostics.HasError() {
		t.Fatal(testExpectedConvertError)
	}

	t.Setenv("SOUSCHEF_TEST_FAIL", "")
	t.Setenv("SOUSCHEF_TEST_SKIP_WRITE", "convert-inspec")
	updateResp := &resource.UpdateResponse{State: tfsdk.State{Schema: schema}}
	r.Update(context.Background(), resource.UpdateRequest{Plan: plan}, updateResp)
	if !updateResp.Diagnostics.HasError() {
		t.Fatal("expected diagnostics for missing test file")
	}

	createResp = &resource.CreateResponse{State: tfsdk.State{Schema: schema}}
	r.Create(context.Background(), resource.CreateRequest{Plan: plan}, createResp)
	if !createResp.Diagnostics.HasError() {
		t.Fatal("expected diagnostics for missing test file on create")
	}
}

func TestInSpecMigrationImportStateCoverage(t *testing.T) {
	r := &inspecMigrationResource{}
	schema := newResourceSchema(t, r)

	resp := &resource.ImportStateResponse{State: newEmptyState(schema)}
	r.ImportState(context.Background(), resource.ImportStateRequest{ID: "invalid"}, resp)
	if !resp.Diagnostics.HasError() {
		t.Fatal("expected diagnostics for invalid import ID")
	}

	profileDir := t.TempDir()
	outputDir := t.TempDir()
	testFilePath := filepath.Join(outputDir, testinfraFilename)
	if err := os.WriteFile(testFilePath, []byte("content"), 0644); err != nil {
		t.Fatalf("failed to write test file: %v", err)
	}

	req := resource.ImportStateRequest{ID: profileDir + "|" + outputDir + "|testinfra"}
	resp = &resource.ImportStateResponse{State: newEmptyState(schema)}
	r.ImportState(context.Background(), req, resp)
	if resp.Diagnostics.HasError() {
		t.Fatalf(testUnexpectedDiagnostics, resp.Diagnostics)
	}

	if err := os.Chmod(testFilePath, noPermissions); err != nil {
		t.Fatalf("failed to chmod test file: %v", err)
	}
	resp = &resource.ImportStateResponse{State: newEmptyState(schema)}
	r.ImportState(context.Background(), req, resp)
	if !resp.Diagnostics.HasError() {
		t.Fatal("expected diagnostics for unreadable test file")
	}
}
