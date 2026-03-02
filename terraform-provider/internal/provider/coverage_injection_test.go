// Package provider contains coverage tests that use dependency injection.
package provider

import (
	"context"
	"errors"
	"os"
	"testing"

	"github.com/hashicorp/terraform-plugin-framework/attr"
	"github.com/hashicorp/terraform-plugin-framework/datasource"
	"github.com/hashicorp/terraform-plugin-framework/diag"
	"github.com/hashicorp/terraform-plugin-framework/provider"
	"github.com/hashicorp/terraform-plugin-framework/resource"
	"github.com/hashicorp/terraform-plugin-framework/tfsdk"
	"github.com/hashicorp/terraform-plugin-framework/types"
	"github.com/hashicorp/terraform-plugin-go/tftypes"
)

const permissionDeniedErr = "permission denied"

func TestBatchMapValueFromErrors(t *testing.T) {
	errDiag := diag.Diagnostics{diag.NewErrorDiagnostic("map error", "forced map error")}
	withTypesMapValueFrom(t, func(_ context.Context, _ attr.Type, _ any) (types.Map, diag.Diagnostics) {
		return types.MapNull(types.StringType), errDiag
	})

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

	outputDir := t.TempDir()
	createTestPlaybookFile(t, outputDir)

	state := newState(t, schema, batchMigrationResourceModel{
		ID: types.StringValue("test"),
		RecipeNames: []types.String{
			types.StringValue("default"),
		},
		OutputPath:    types.StringValue(outputDir),
		CookbookName:  types.StringValue("test"),
		PlaybookCount: types.Int64Value(1),
		Playbooks:     types.MapNull(types.StringType),
	})

	// Test operations that encounter map conversion errors
	// Create operation
	testLifecycleOperation(t, "create map conversion", func() diag.Diagnostics {
		createResp := &resource.CreateResponse{State: tfsdk.State{Schema: schema}}
		r.Create(context.Background(), resource.CreateRequest{Plan: plan}, createResp)
		return createResp.Diagnostics
	})

	// Update operation
	testLifecycleOperation(t, "update map conversion", func() diag.Diagnostics {
		updateResp := &resource.UpdateResponse{State: tfsdk.State{Schema: schema}}
		r.Update(context.Background(), resource.UpdateRequest{Plan: plan}, updateResp)
		return updateResp.Diagnostics
	})

	// Read operation
	testLifecycleOperation(t, "read map conversion", func() diag.Diagnostics {
		readResp := &resource.ReadResponse{State: tfsdk.State{Schema: schema}}
		r.Read(context.Background(), resource.ReadRequest{State: state}, readResp)
		return readResp.Diagnostics
	})

	// Import operation
	t.Run("import", func(t *testing.T) {
		cookbookDir, importOutputDir := setupBatchImportTestFiles(t)
		testLifecycleOperation(t, "import map conversion", func() diag.Diagnostics {
			importResp := &resource.ImportStateResponse{State: newEmptyState(schema)}
			r.ImportState(context.Background(), resource.ImportStateRequest{ID: cookbookDir + "|" + importOutputDir + "|default"}, importResp)
			return importResp.Diagnostics
		})
	})
}

// testLifecycleOperation executes a lifecycle operation and checks for errors
func testLifecycleOperation(t *testing.T, name string, op func() diag.Diagnostics) {
	t.Helper()
	diags := op()
	if !diags.HasError() {
		t.Errorf("expected diagnostics for %s", name)
	}
}

// createDeleteTestStateForResource creates appropriate delete test state for a resource type
func createDeleteTestStateForResource(t *testing.T, r resource.Resource, outputDir string) tfsdk.State {
	schema := newResourceSchema(t, r)
	switch r.(type) {
	case *migrationResource:
		return newState(t, schema, migrationResourceModel{RecipeName: types.StringValue("test"), OutputPath: types.StringValue(outputDir)})
	case *habitatMigrationResource:
		return newState(t, schema, habitatMigrationResourceModel{PlanPath: types.StringValue("/tmp/plan.sh"), OutputPath: types.StringValue(outputDir)})
	case *inspecMigrationResource:
		return newState(t, schema, inspecMigrationResourceModel{ProfilePath: types.StringValue("/tmp/profile"), OutputPath: types.StringValue(outputDir), OutputFormat: types.StringValue("testinfra")})
	case *batchMigrationResource:
		return newState(t, schema, batchMigrationResourceModel{
			ID:            types.StringValue("batch"),
			RecipeNames:   []types.String{types.StringValue("default")},
			OutputPath:    types.StringValue(outputDir),
			CookbookName:  types.StringValue("test"),
			PlaybookCount: types.Int64Value(1),
			Playbooks:     types.MapNull(types.StringType),
		})
	}
	return tfsdk.State{}
}

func TestDeleteHandlesErrors(t *testing.T) {
	tests := []struct {
		name      string
		resource  resource.Resource
		errorType error
		checkPred func(diag.Diagnostics) bool
		checkMsg  string
	}{
		// Should ignore missing files (NotExist)
		{
			name:      "migration_ignores_missing",
			resource:  &migrationResource{},
			errorType: os.ErrNotExist,
			checkPred: func(d diag.Diagnostics) bool { return !d.HasError() },
			checkMsg:  "unexpected diagnostics for missing migration file",
		},
		{
			name:      "habitat_ignores_missing",
			resource:  &habitatMigrationResource{},
			errorType: os.ErrNotExist,
			checkPred: func(d diag.Diagnostics) bool { return !d.HasError() },
			checkMsg:  "unexpected diagnostics for missing dockerfile",
		},
		{
			name:      "inspec_ignores_missing",
			resource:  &inspecMigrationResource{},
			errorType: os.ErrNotExist,
			checkPred: func(d diag.Diagnostics) bool { return !d.HasError() },
			checkMsg:  "unexpected diagnostics for missing test file",
		},
		{
			name:      "batch_ignores_missing",
			resource:  &batchMigrationResource{},
			errorType: os.ErrNotExist,
			checkPred: func(d diag.Diagnostics) bool { return !d.HasError() },
			checkMsg:  "unexpected diagnostics for missing batch files",
		},
		// Should report permission errors (migration) or warnings (others)
		{
			name:      "migration_reports_error",
			resource:  &migrationResource{},
			errorType: errors.New(permissionDeniedErr),
			checkPred: func(d diag.Diagnostics) bool { return d.HasError() },
			checkMsg:  "expected diagnostics for migration delete error",
		},
		{
			name:      "habitat_reports_warning",
			resource:  &habitatMigrationResource{},
			errorType: errors.New(permissionDeniedErr),
			checkPred: func(d diag.Diagnostics) bool { return len(d) > 0 },
			checkMsg:  "expected warning diagnostics for habitat delete error",
		},
		{
			name:      "inspec_reports_warning",
			resource:  &inspecMigrationResource{},
			errorType: errors.New(permissionDeniedErr),
			checkPred: func(d diag.Diagnostics) bool { return len(d) > 0 },
			checkMsg:  "expected warning diagnostics for inspec delete error",
		},
		{
			name:      "batch_reports_warning",
			resource:  &batchMigrationResource{},
			errorType: errors.New(permissionDeniedErr),
			checkPred: func(d diag.Diagnostics) bool { return len(d) > 0 },
			checkMsg:  "expected warning diagnostics for batch delete error",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			withOsRemove(t, func(string) error {
				return tt.errorType
			})

			state := createDeleteTestStateForResource(t, tt.resource, t.TempDir())
			resp := &resource.DeleteResponse{}
			tt.resource.Delete(context.Background(), resource.DeleteRequest{State: state}, resp)
			if !tt.checkPred(resp.Diagnostics) {
				t.Fatalf("%s: %v", tt.checkMsg, resp.Diagnostics)
			}
		})
	}
}

// testConfigError executes config validation and verifies expected error
func testConfigError(t *testing.T, configExecutor func(config tfsdk.Config) diag.Diagnostics, fieldName string, errorMsg string) {
	t.Helper()
	badValue := tftypes.NewValue(tftypes.Object{
		AttributeTypes: map[string]tftypes.Type{
			fieldName: tftypes.Number,
		},
	}, map[string]tftypes.Value{
		fieldName: tftypes.NewValue(tftypes.Number, 1),
	})

	// Create a minimal schema just for the config structure
	config := tfsdk.Config{Raw: badValue}
	diags := configExecutor(config)
	if !diags.HasError() {
		t.Fatal(errorMsg)
	}
}

func TestProviderConfigureConfigError(t *testing.T) {
	p := &SousChefProvider{}
	schema := newProviderSchema(t, p)
	testConfigError(t, func(config tfsdk.Config) diag.Diagnostics {
		config.Schema = schema
		resp := &provider.ConfigureResponse{}
		p.Configure(context.Background(), provider.ConfigureRequest{Config: config}, resp)
		return resp.Diagnostics
	}, "souschef_path", "expected diagnostics for invalid provider config")
}

func TestCostEstimateDataSourceReadConfigError(t *testing.T) {
	ds := &costEstimateDataSource{}
	schema := newDataSourceSchema(t, ds)
	testConfigError(t, func(config tfsdk.Config) diag.Diagnostics {
		config.Schema = schema
		resp := &datasource.ReadResponse{State: tfsdk.State{Schema: schema}}
		ds.Read(context.Background(), datasource.ReadRequest{Config: config}, resp)
		return resp.Diagnostics
	}, "cookbook_path", "expected diagnostics for invalid cost estimate config")
}

func TestResourcePlanStateGetDiagnostics(t *testing.T) {
	tests := []struct {
		name      string
		resource  resource.Resource
		fieldName string
	}{
		{
			name:      "migration",
			resource:  &migrationResource{},
			fieldName: "cookbook_path",
		},
		{
			name:      "batch",
			resource:  &batchMigrationResource{},
			fieldName: "cookbook_path",
		},
		{
			name:      "habitat",
			resource:  &habitatMigrationResource{},
			fieldName: "plan_path",
		},
		{
			name:      "inspec",
			resource:  &inspecMigrationResource{},
			fieldName: "profile_path",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			schema := newResourceSchema(t, tt.resource)

			// Test Create with bad plan
			testLifecycleOperation(t, tt.name+" create plan", func() diag.Diagnostics {
				createResp := &resource.CreateResponse{State: tfsdk.State{Schema: schema}}
				tt.resource.Create(context.Background(), resource.CreateRequest{Plan: badPlan(schema, tt.fieldName)}, createResp)
				return createResp.Diagnostics
			})

			// Test Update with bad plan
			testLifecycleOperation(t, tt.name+" update plan", func() diag.Diagnostics {
				updateResp := &resource.UpdateResponse{State: tfsdk.State{Schema: schema}}
				tt.resource.Update(context.Background(), resource.UpdateRequest{Plan: badPlan(schema, tt.fieldName)}, updateResp)
				return updateResp.Diagnostics
			})

			// Test Read with bad state
			testLifecycleOperation(t, tt.name+" read state", func() diag.Diagnostics {
				readResp := &resource.ReadResponse{State: tfsdk.State{Schema: schema}}
				tt.resource.Read(context.Background(), resource.ReadRequest{State: badState(schema, tt.fieldName)}, readResp)
				return readResp.Diagnostics
			})

			// Test Delete with bad state
			testLifecycleOperation(t, tt.name+" delete state", func() diag.Diagnostics {
				deleteResp := &resource.DeleteResponse{}
				tt.resource.Delete(context.Background(), resource.DeleteRequest{State: badState(schema, tt.fieldName)}, deleteResp)
				return deleteResp.Diagnostics
			})
		})
	}
}

// testImportStateDiagnosticsError executes ImportState and verifies expected diagnostics error
func testImportStateDiagnosticsError(t *testing.T, r *batchMigrationResource, id string, errMsg string) {
	t.Helper()
	schema := newResourceSchema(t, r)
	resp := &resource.ImportStateResponse{State: newEmptyState(schema)}
	req := resource.ImportStateRequest{ID: id}
	r.ImportState(context.Background(), req, resp)
	if !resp.Diagnostics.HasError() {
		t.Fatal(errMsg)
	}
}

func TestBatchImportStateReadError(t *testing.T) {
	r := &batchMigrationResource{}
	cookbookDir, outputDir := setupBatchImportTestFiles(t)

	withOsReadFile(t, func(string) ([]byte, error) {
		return nil, errors.New("read error")
	})

	testImportStateDiagnosticsError(t, r, cookbookDir+"|"+outputDir+"|default", "expected diagnostics for import read error")
}

func TestBatchImportStateRecipeNamesError(t *testing.T) {
	r := &batchMigrationResource{}
	cookbookDir, outputDir := setupBatchImportTestFiles(t)
	testImportStateDiagnosticsError(t, r, cookbookDir+"|"+outputDir+"| , ", "expected diagnostics for invalid recipe names")
}
