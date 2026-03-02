// Package provider contains tests for batch, habitat, and inspec resources.
package provider

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"testing"

	"github.com/hashicorp/terraform-plugin-framework/resource"
	resourceschema "github.com/hashicorp/terraform-plugin-framework/resource/schema"
	"github.com/hashicorp/terraform-plugin-framework/tfsdk"
	"github.com/hashicorp/terraform-plugin-framework/types"
)

const failedToChmodFileFmt = "failed to chmod file: %v"

// testResourceCreatePhase executes and validates the Create operation.
func testResourceCreatePhase(t *testing.T, r resource.Resource, schema resourceschema.Schema, plan tfsdk.Plan) {
	createResp := &resource.CreateResponse{State: tfsdk.State{Schema: schema}}
	r.Create(context.Background(), resource.CreateRequest{Plan: plan}, createResp)
	if createResp.Diagnostics.HasError() {
		t.Fatalf(testUnexpectedDiagnostics, createResp.Diagnostics)
	}
}

// testResourceReadMissingPhase validates that reading a missing file removes the resource.
func testResourceReadMissingPhase(t *testing.T, r resource.Resource, schema resourceschema.Schema, state tfsdk.State, missingMsg string) {
	readResp := &resource.ReadResponse{State: tfsdk.State{Schema: schema}}
	r.Read(context.Background(), resource.ReadRequest{State: state}, readResp)
	if readResp.Diagnostics.HasError() {
		t.Fatalf(testUnexpectedDiagnostics, readResp.Diagnostics)
	}
	if !readResp.State.Raw.IsNull() {
		t.Fatal(missingMsg)
	}
}

// testResourceUpdatePhase executes and validates the Update operation.
func testResourceUpdatePhase(t *testing.T, r resource.Resource, schema resourceschema.Schema, plan tfsdk.Plan) {
	updateResp := &resource.UpdateResponse{State: tfsdk.State{Schema: schema}}
	r.Update(context.Background(), resource.UpdateRequest{Plan: plan}, updateResp)
	if updateResp.Diagnostics.HasError() {
		t.Fatalf(testUnexpectedDiagnostics, updateResp.Diagnostics)
	}
}

// testResourceCreateErrorPhase executes Create and expects an error.
func testResourceCreateErrorPhase(t *testing.T, r resource.Resource, schema resourceschema.Schema, plan tfsdk.Plan, errorMsg string) {
	createResp := &resource.CreateResponse{State: tfsdk.State{Schema: schema}}
	r.Create(context.Background(), resource.CreateRequest{Plan: plan}, createResp)
	if !createResp.Diagnostics.HasError() {
		t.Fatal(errorMsg)
	}
}

// testResourceUpdateErrorPhase executes Update and expects an error.
func testResourceUpdateErrorPhase(t *testing.T, r resource.Resource, schema resourceschema.Schema, plan tfsdk.Plan, errorMsg string) {
	updateResp := &resource.UpdateResponse{State: tfsdk.State{Schema: schema}}
	r.Update(context.Background(), resource.UpdateRequest{Plan: plan}, updateResp)
	if !updateResp.Diagnostics.HasError() {
		t.Fatal(errorMsg)
	}
}

// testResourceReadExistingPhase executes and validates reading an existing file.
func testResourceReadExistingPhase(t *testing.T, r resource.Resource, schema resourceschema.Schema, state tfsdk.State) {
	readResp := &resource.ReadResponse{State: tfsdk.State{Schema: schema}}
	r.Read(context.Background(), resource.ReadRequest{State: state}, readResp)
	if readResp.Diagnostics.HasError() {
		t.Fatalf(testUnexpectedDiagnostics, readResp.Diagnostics)
	}
}

// testResourceReadPermissionErrorPhase validates that permission errors are handled.
func testResourceReadPermissionErrorPhase(t *testing.T, r resource.Resource, schema resourceschema.Schema, state tfsdk.State, filePath, fileErrMsg string) {
	if err := os.Chmod(filePath, noPermissions); err != nil {
		t.Fatalf(failedToChmodFileFmt, err)
	}
	readResp := &resource.ReadResponse{State: tfsdk.State{Schema: schema}}
	r.Read(context.Background(), resource.ReadRequest{State: state}, readResp)
	if !readResp.Diagnostics.HasError() {
		t.Fatal(fileErrMsg)
	}
}

// testResourceDeletePhase executes and validates the Delete operation.
func testResourceDeletePhase(t *testing.T, r resource.Resource, state tfsdk.State) {
	deleteResp := &resource.DeleteResponse{}
	r.Delete(context.Background(), resource.DeleteRequest{State: state}, deleteResp)
	if deleteResp.Diagnostics.HasError() {
		t.Fatalf(testUnexpectedDiagnostics, deleteResp.Diagnostics)
	}
}

// testResourceDeleteAsDirectoryPhase recreates the file as a directory and validates deletion.
func testResourceDeleteAsDirectoryPhase(t *testing.T, r resource.Resource, state tfsdk.State, filePath string) {
	if err := os.MkdirAll(filePath, 0755); err != nil {
		t.Fatalf("failed to recreate as dir: %v", err)
	}
	deleteResp := &resource.DeleteResponse{}
	r.Delete(context.Background(), resource.DeleteRequest{State: state}, deleteResp)
	if deleteResp.Diagnostics.HasError() {
		t.Fatalf(testUnexpectedDiagnostics, deleteResp.Diagnostics)
	}
}

// testResourceImportStateHelper executes ImportState and validates the response.
func testResourceImportStateHelper(t *testing.T, r resource.ResourceWithImportState, schema resourceschema.Schema, importID string, expectError bool, errorMsg string) {
	t.Helper()
	resp := &resource.ImportStateResponse{State: newEmptyState(schema)}
	r.ImportState(context.Background(), resource.ImportStateRequest{ID: importID}, resp)
	if expectError {
		if !resp.Diagnostics.HasError() {
			t.Fatal(errorMsg)
		}
	} else {
		if resp.Diagnostics.HasError() {
			t.Fatalf(testUnexpectedDiagnostics, resp.Diagnostics)
		}
	}
}

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

	// Create and Update phases
	testResourceCreatePhase(t, r, schema, plan)
	testResourceUpdatePhase(t, r, schema, plan)

	// Read phase
	state := newState(t, schema, batchMigrationResourceModel{
		OutputPath:    types.StringValue(outputDir),
		RecipeNames:   []types.String{types.StringValue("default")},
		ID:            types.StringNull(),
		CookbookName:  types.StringNull(),
		PlaybookCount: types.Int64Null(),
		Playbooks:     types.MapNull(types.StringType),
	})
	testResourceReadExistingPhase(t, r, schema, state)

	// Delete phase
	testResourceDeletePhase(t, r, state)

	// Delete as directory phase
	defaultPath := filepath.Join(outputDir, "default.yml")
	if err := os.Remove(defaultPath); err != nil && !os.IsNotExist(err) {
		t.Fatalf("failed to remove playbook: %v", err)
	}
	testResourceDeleteAsDirectoryPhase(t, r, state, defaultPath)
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

	// Test empty recipe names
	testResourceImportStateHelper(t, r, schema, "|/tmp/output|", true, "expected diagnostics for empty recipe names")

	// Setup test files
	cookbookDir := t.TempDir()
	outputDir := t.TempDir()
	playbookPath := filepath.Join(outputDir, "default.yml")
	if err := os.WriteFile(playbookPath, []byte("content"), 0644); err != nil {
		t.Fatalf("failed to write playbook: %v", err)
	}

	// Test valid import
	validImportID := cookbookDir + "|" + outputDir + "|default"
	testResourceImportStateHelper(t, r, schema, validImportID, false, "")

	// Test missing playbook
	missingImportID := cookbookDir + "|" + outputDir + "|missing"
	testResourceImportStateHelper(t, r, schema, missingImportID, true, "expected diagnostics for missing playbook")

	// Test unreadable playbook
	if err := os.Chmod(playbookPath, noPermissions); err != nil {
		t.Fatalf("failed to chmod playbook: %v", err)
	}
	testResourceImportStateHelper(t, r, schema, validImportID, true, "expected diagnostics for unreadable playbook")
}

func TestHabitatAndInSpecResourceCoverage(t *testing.T) {
	tests := []struct {
		name             string
		resource         interface{}
		setupFile        func(t *testing.T) string
		createResourceFn func(*testing.T, resource.Resource, resourceschema.Schema, string, string) tfsdk.Plan
		createStateFn    func(*testing.T, resource.Resource, resourceschema.Schema, string) tfsdk.State
		outputFile       string
		missingMsg       string
		fileErrMsg       string
	}{
		{
			name:     "habitat",
			resource: &habitatMigrationResource{client: &SousChefClient{Path: newFakeSousChef(t)}},
			setupFile: func(t *testing.T) string {
				planPath := filepath.Join(t.TempDir(), testPlanSh)
				if err := os.WriteFile(planPath, []byte(testPkgNameMyapp), 0644); err != nil {
					t.Fatalf(testFailedToWritePlan, err)
				}
				return planPath
			},
			createResourceFn: func(t *testing.T, res resource.Resource, schema resourceschema.Schema, setupPath string, outputDir string) tfsdk.Plan {
				return newPlan(t, schema, habitatMigrationResourceModel{
					PlanPath:          types.StringValue(setupPath),
					OutputPath:        types.StringValue(outputDir),
					BaseImage:         types.StringNull(),
					ID:                types.StringNull(),
					PackageName:       types.StringNull(),
					DockerfileContent: types.StringNull(),
				})
			},
			createStateFn: func(t *testing.T, res resource.Resource, schema resourceschema.Schema, outputDir string) tfsdk.State {
				return newState(t, schema, habitatMigrationResourceModel{
					OutputPath: types.StringValue(outputDir),
				})
			},
			outputFile: "Dockerfile",
			missingMsg: "expected resource to be removed when dockerfile is missing",
			fileErrMsg: "expected diagnostics for unreadable dockerfile",
		},
		{
			name:     "inspec",
			resource: &inspecMigrationResource{client: &SousChefClient{Path: newFakeSousChef(t)}},
			setupFile: func(t *testing.T) string {
				return t.TempDir()
			},
			createResourceFn: func(t *testing.T, res resource.Resource, schema resourceschema.Schema, setupPath string, outputDir string) tfsdk.Plan {
				return newPlan(t, schema, inspecMigrationResourceModel{
					ProfilePath:  types.StringValue(setupPath),
					OutputPath:   types.StringValue(outputDir),
					OutputFormat: types.StringValue("testinfra"),
					ID:           types.StringNull(),
					ProfileName:  types.StringNull(),
					TestContent:  types.StringNull(),
				})
			},
			createStateFn: func(t *testing.T, res resource.Resource, schema resourceschema.Schema, outputDir string) tfsdk.State {
				return newState(t, schema, inspecMigrationResourceModel{
					OutputPath:   types.StringValue(outputDir),
					OutputFormat: types.StringValue("testinfra"),
				})
			},
			outputFile: testinfraFilename,
			missingMsg: "expected resource to be removed when test file is missing",
			fileErrMsg: "expected diagnostics for unreadable test file",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			r := tt.resource.(resource.Resource)
			schema := newResourceSchema(t, r)
			setupPath := tt.setupFile(t)
			outputDir := t.TempDir()

			// Create phase
			plan := tt.createResourceFn(t, r, schema, setupPath, outputDir)
			testResourceCreatePhase(t, r, schema, plan)

			// Read missing file - should be removed
			missingState := tt.createStateFn(t, r, schema, t.TempDir())
			testResourceReadMissingPhase(t, r, schema, missingState, tt.missingMsg)

			// Update phase
			updatePlan := tt.createResourceFn(t, r, schema, setupPath, outputDir)
			testResourceUpdatePhase(t, r, schema, updatePlan)

			// Read existing file
			state := tt.createStateFn(t, r, schema, outputDir)
			testResourceReadExistingPhase(t, r, schema, state)

			// Read with permission error
			filePath := filepath.Join(outputDir, tt.outputFile)
			testResourceReadPermissionErrorPhase(t, r, schema, state, filePath, tt.fileErrMsg)

			// Delete file
			testResourceDeletePhase(t, r, state)

			// Delete as directory
			testResourceDeleteAsDirectoryPhase(t, r, state, filePath)
		})
	}
}

func TestHabitatAndInSpecResourceErrors(t *testing.T) {
	tests := []struct {
		name           string
		resource       interface{}
		setupFile      func(t *testing.T) string
		setupPlan      func(t *testing.T, schema resourceschema.Schema, path string) tfsdk.Plan
		convertCommand string
		missingMsg     string
	}{
		{
			name:     "habitat",
			resource: &habitatMigrationResource{client: &SousChefClient{Path: newFakeSousChef(t)}},
			setupFile: func(t *testing.T) string {
				planPath := filepath.Join(t.TempDir(), testPlanSh)
				if err := os.WriteFile(planPath, []byte(testPkgNameMyapp), 0644); err != nil {
					t.Fatalf(testFailedToWritePlan, err)
				}
				return planPath
			},
			setupPlan: func(t *testing.T, schema resourceschema.Schema, path string) tfsdk.Plan {
				return newPlan(t, schema, habitatMigrationResourceModel{
					PlanPath:          types.StringValue(path),
					OutputPath:        types.StringValue(t.TempDir()),
					BaseImage:         types.StringValue("debian:stable"),
					ID:                types.StringNull(),
					PackageName:       types.StringNull(),
					DockerfileContent: types.StringNull(),
				})
			},
			convertCommand: testConvertHabitat,
			missingMsg:     "expected diagnostics for missing dockerfile",
		},
		{
			name:     "inspec",
			resource: &inspecMigrationResource{client: &SousChefClient{Path: newFakeSousChef(t)}},
			setupFile: func(t *testing.T) string {
				return t.TempDir()
			},
			setupPlan: func(t *testing.T, schema resourceschema.Schema, path string) tfsdk.Plan {
				return newPlan(t, schema, inspecMigrationResourceModel{
					ProfilePath:  types.StringValue(path),
					OutputPath:   types.StringValue(t.TempDir()),
					OutputFormat: types.StringValue("serverspec"),
					ID:           types.StringNull(),
					ProfileName:  types.StringNull(),
					TestContent:  types.StringNull(),
				})
			},
			convertCommand: testConvertInSpec,
			missingMsg:     "expected diagnostics for missing test file",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			r := tt.resource.(resource.Resource)
			schema := newResourceSchema(t, r)
			setupPath := tt.setupFile(t)
			plan := tt.setupPlan(t, schema, setupPath)

			// Test convert error
			t.Setenv("SOUSCHEF_TEST_FAIL", tt.convertCommand)
			testResourceCreateErrorPhase(t, r, schema, plan, testExpectedConvertError)

			// Test missing file on update
			t.Setenv("SOUSCHEF_TEST_FAIL", "")
			t.Setenv("SOUSCHEF_TEST_SKIP_WRITE", tt.convertCommand)
			testResourceUpdateErrorPhase(t, r, schema, plan, tt.missingMsg)

			// Test missing file on create
			testResourceCreateErrorPhase(t, r, schema, plan, tt.missingMsg+" on create")
		})
	}
}

func testImportStatePhase(t *testing.T, r resource.ResourceWithImportState, schema resourceschema.Schema, invalidImportID, validImportIDFmt string, setupImportPath func(t *testing.T) (string, string), setupOutputFile func(t *testing.T, outputDir string) string) {
	// Invalid import ID
	testResourceImportStateHelper(t, r, schema, invalidImportID, true, "expected diagnostics for invalid import ID")

	// Setup files
	path, outputDir := setupImportPath(t)
	filePath := setupOutputFile(t, outputDir)

	// Valid import
	validImportID := fmt.Sprintf(validImportIDFmt, path, outputDir)
	testResourceImportStateHelper(t, r, schema, validImportID, false, "")

	// Permission error
	if err := os.Chmod(filePath, noPermissions); err != nil {
		t.Fatalf(failedToChmodFileFmt, err)
	}
	testResourceImportStateHelper(t, r, schema, validImportID, true, "expected diagnostics for unreadable file")
}

func TestHabitatAndInSpecImportStateCoverage(t *testing.T) {
	habTests := []struct {
		name             string
		resource         interface{}
		invalidImportID  string
		setupImportPath  func(t *testing.T) (string, string)
		setupOutputFile  func(t *testing.T, outputDir string) string
		validImportIDFmt string
	}{
		{
			name:            "habitat",
			resource:        &habitatMigrationResource{},
			invalidImportID: "missing|",
			setupImportPath: func(t *testing.T) (string, string) {
				planPath := filepath.Join(t.TempDir(), testPlanSh)
				if err := os.WriteFile(planPath, []byte(testPkgNameMyapp), 0644); err != nil {
					t.Fatalf(testFailedToWritePlan, err)
				}
				return planPath, t.TempDir()
			},
			setupOutputFile: func(t *testing.T, outputDir string) string {
				dockerfilePath := filepath.Join(outputDir, "Dockerfile")
				if err := os.WriteFile(dockerfilePath, []byte("FROM ubuntu"), 0644); err != nil {
					t.Fatalf("failed to write dockerfile: %v", err)
				}
				return dockerfilePath
			},
			validImportIDFmt: "%s|%s|",
		},
		{
			name:            "inspec",
			resource:        &inspecMigrationResource{},
			invalidImportID: "invalid",
			setupImportPath: func(t *testing.T) (string, string) {
				return t.TempDir(), t.TempDir()
			},
			setupOutputFile: func(t *testing.T, outputDir string) string {
				testFilePath := filepath.Join(outputDir, testinfraFilename)
				if err := os.WriteFile(testFilePath, []byte("content"), 0644); err != nil {
					t.Fatalf("failed to write test file: %v", err)
				}
				return testFilePath
			},
			validImportIDFmt: "%s|%s|testinfra",
		},
	}

	for _, tt := range habTests {
		t.Run(tt.name, func(t *testing.T) {
			r := tt.resource.(resource.Resource)
			rImport := tt.resource.(resource.ResourceWithImportState)
			schema := newResourceSchema(t, r)
			testImportStatePhase(t, rImport, schema, tt.invalidImportID, tt.validImportIDFmt, tt.setupImportPath, tt.setupOutputFile)
		})
	}
}
