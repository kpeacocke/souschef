// Package provider contains coverage tests that use dependency injection.
package provider

import (
	"context"
	"errors"
	"os"
	"path/filepath"
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

	createResp := &resource.CreateResponse{State: tfsdk.State{Schema: schema}}
	r.Create(context.Background(), resource.CreateRequest{Plan: plan}, createResp)
	if !createResp.Diagnostics.HasError() {
		t.Fatal("expected diagnostics from map conversion in create")
	}

	updateResp := &resource.UpdateResponse{State: tfsdk.State{Schema: schema}}
	r.Update(context.Background(), resource.UpdateRequest{Plan: plan}, updateResp)
	if !updateResp.Diagnostics.HasError() {
		t.Fatal("expected diagnostics from map conversion in update")
	}

	outputDir := t.TempDir()
	playbookPath := filepath.Join(outputDir, testDefaultYml)
	if err := os.WriteFile(playbookPath, []byte("content"), 0644); err != nil {
		t.Fatalf(testFailedToWritePlaybook, err)
	}

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
	readResp := &resource.ReadResponse{State: tfsdk.State{Schema: schema}}
	r.Read(context.Background(), resource.ReadRequest{State: state}, readResp)
	if !readResp.Diagnostics.HasError() {
		t.Fatal("expected diagnostics from map conversion in read")
	}

	cookbookDir := t.TempDir()
	outputDir = t.TempDir()
	playbookPath = filepath.Join(outputDir, testDefaultYml)
	if err := os.WriteFile(playbookPath, []byte("content"), 0644); err != nil {
		t.Fatalf(testFailedToWritePlaybook, err)
	}

	importResp := &resource.ImportStateResponse{State: newEmptyState(schema)}
	r.ImportState(context.Background(), resource.ImportStateRequest{ID: cookbookDir + "|" + outputDir + "|default"}, importResp)
	if !importResp.Diagnostics.HasError() {
		t.Fatal("expected diagnostics from map conversion in import")
	}
}

func TestDeleteHandlesErrors(t *testing.T) {
	tests := []struct {
		name      string
		resource  resource.Resource
		state     tfsdk.State
		errorType error
		checkPred func(diag.Diagnostics) bool
		checkMsg  string
	}{
		// Should ignore missing files (NotExist)
		{
			name:      "migration_ignores_missing",
			resource:  &migrationResource{},
			state:     newState(t, newResourceSchema(t, &migrationResource{}), migrationResourceModel{RecipeName: types.StringValue("missing"), OutputPath: types.StringValue(t.TempDir())}),
			errorType: os.ErrNotExist,
			checkPred: func(d diag.Diagnostics) bool { return !d.HasError() },
			checkMsg:  "unexpected diagnostics for missing migration file",
		},
		{
			name:      "habitat_ignores_missing",
			resource:  &habitatMigrationResource{},
			state:     newState(t, newResourceSchema(t, &habitatMigrationResource{}), habitatMigrationResourceModel{PlanPath: types.StringValue("/tmp/plan.sh"), OutputPath: types.StringValue(t.TempDir())}),
			errorType: os.ErrNotExist,
			checkPred: func(d diag.Diagnostics) bool { return !d.HasError() },
			checkMsg:  "unexpected diagnostics for missing dockerfile",
		},
		{
			name:      "inspec_ignores_missing",
			resource:  &inspecMigrationResource{},
			state:     newState(t, newResourceSchema(t, &inspecMigrationResource{}), inspecMigrationResourceModel{ProfilePath: types.StringValue("/tmp/profile"), OutputPath: types.StringValue(t.TempDir()), OutputFormat: types.StringValue("testinfra")}),
			errorType: os.ErrNotExist,
			checkPred: func(d diag.Diagnostics) bool { return !d.HasError() },
			checkMsg:  "unexpected diagnostics for missing test file",
		},
		{
			name:     "batch_ignores_missing",
			resource: &batchMigrationResource{},
			state: newState(t, newResourceSchema(t, &batchMigrationResource{}), batchMigrationResourceModel{
				ID:            types.StringValue("batch"),
				RecipeNames:   []types.String{types.StringValue("default")},
				OutputPath:    types.StringValue(t.TempDir()),
				CookbookName:  types.StringValue("test"),
				PlaybookCount: types.Int64Value(1),
				Playbooks:     types.MapNull(types.StringType),
			}),
			errorType: os.ErrNotExist,
			checkPred: func(d diag.Diagnostics) bool { return !d.HasError() },
			checkMsg:  "unexpected diagnostics for missing batch files",
		},
		// Should report permission errors (migration) or warnings (others)
		{
			name:      "migration_reports_error",
			resource:  &migrationResource{},
			state:     newState(t, newResourceSchema(t, &migrationResource{}), migrationResourceModel{RecipeName: types.StringValue("test"), OutputPath: types.StringValue(t.TempDir())}),
			errorType: errors.New("permission denied"),
			checkPred: func(d diag.Diagnostics) bool { return d.HasError() },
			checkMsg:  "expected diagnostics for migration delete error",
		},
		{
			name:      "habitat_reports_warning",
			resource:  &habitatMigrationResource{},
			state:     newState(t, newResourceSchema(t, &habitatMigrationResource{}), habitatMigrationResourceModel{PlanPath: types.StringValue("/tmp/plan.sh"), OutputPath: types.StringValue(t.TempDir())}),
			errorType: errors.New("permission denied"),
			checkPred: func(d diag.Diagnostics) bool { return len(d) > 0 },
			checkMsg:  "expected warning diagnostics for habitat delete error",
		},
		{
			name:      "inspec_reports_warning",
			resource:  &inspecMigrationResource{},
			state:     newState(t, newResourceSchema(t, &inspecMigrationResource{}), inspecMigrationResourceModel{ProfilePath: types.StringValue("/tmp/profile"), OutputPath: types.StringValue(t.TempDir()), OutputFormat: types.StringValue("testinfra")}),
			errorType: errors.New("permission denied"),
			checkPred: func(d diag.Diagnostics) bool { return len(d) > 0 },
			checkMsg:  "expected warning diagnostics for inspec delete error",
		},
		{
			name:     "batch_reports_warning",
			resource: &batchMigrationResource{},
			state: newState(t, newResourceSchema(t, &batchMigrationResource{}), batchMigrationResourceModel{
				ID:            types.StringValue("batch"),
				RecipeNames:   []types.String{types.StringValue("default")},
				OutputPath:    types.StringValue(t.TempDir()),
				CookbookName:  types.StringValue("test"),
				PlaybookCount: types.Int64Value(1),
				Playbooks:     types.MapNull(types.StringType),
			}),
			errorType: errors.New("permission denied"),
			checkPred: func(d diag.Diagnostics) bool { return len(d) > 0 },
			checkMsg:  "expected warning diagnostics for batch delete error",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			withOsRemove(t, func(string) error {
				return tt.errorType
			})

			resp := &resource.DeleteResponse{}
			tt.resource.Delete(context.Background(), resource.DeleteRequest{State: tt.state}, resp)
			if !tt.checkPred(resp.Diagnostics) {
				t.Fatalf("%s: %v", tt.checkMsg, resp.Diagnostics)
			}
		})
	}
}

func TestProviderConfigureConfigError(t *testing.T) {
	p := &SousChefProvider{}
	schema := newProviderSchema(t, p)

	badValue := tftypes.NewValue(tftypes.Object{
		AttributeTypes: map[string]tftypes.Type{
			"souschef_path": tftypes.Number,
		},
	}, map[string]tftypes.Value{
		"souschef_path": tftypes.NewValue(tftypes.Number, 1),
	})

	config := tfsdk.Config{Schema: schema, Raw: badValue}
	resp := &provider.ConfigureResponse{}

	p.Configure(context.Background(), provider.ConfigureRequest{Config: config}, resp)
	if !resp.Diagnostics.HasError() {
		t.Fatal("expected diagnostics for invalid provider config")
	}
}

func TestCostEstimateDataSourceReadConfigError(t *testing.T) {
	ds := &costEstimateDataSource{}
	schema := newDataSourceSchema(t, ds)

	badValue := tftypes.NewValue(tftypes.Object{
		AttributeTypes: map[string]tftypes.Type{
			"cookbook_path": tftypes.Number,
		},
	}, map[string]tftypes.Value{
		"cookbook_path": tftypes.NewValue(tftypes.Number, 1),
	})

	config := tfsdk.Config{Schema: schema, Raw: badValue}
	resp := &datasource.ReadResponse{State: tfsdk.State{Schema: schema}}

	ds.Read(context.Background(), datasource.ReadRequest{Config: config}, resp)
	if !resp.Diagnostics.HasError() {
		t.Fatal("expected diagnostics for invalid cost estimate config")
	}
}

func TestResourcePlanStateGetDiagnostics(t *testing.T) {
	tests := []struct {
		name      string
		resource  interface{}
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
			r := tt.resource.(resource.Resource)
			schema := newResourceSchema(t, r)

			// Test Create with bad plan
			createResp := &resource.CreateResponse{State: tfsdk.State{Schema: schema}}
			r.Create(context.Background(), resource.CreateRequest{Plan: badPlan(schema, tt.fieldName)}, createResp)
			if !createResp.Diagnostics.HasError() {
				t.Fatalf("expected diagnostics for %s create plan", tt.name)
			}

			// Test Update with bad plan
			updateResp := &resource.UpdateResponse{State: tfsdk.State{Schema: schema}}
			r.Update(context.Background(), resource.UpdateRequest{Plan: badPlan(schema, tt.fieldName)}, updateResp)
			if !updateResp.Diagnostics.HasError() {
				t.Fatalf("expected diagnostics for %s update plan", tt.name)
			}

			// Test Read with bad state
			readResp := &resource.ReadResponse{State: tfsdk.State{Schema: schema}}
			r.Read(context.Background(), resource.ReadRequest{State: badState(schema, tt.fieldName)}, readResp)
			if !readResp.Diagnostics.HasError() {
				t.Fatalf("expected diagnostics for %s read state", tt.name)
			}

			// Test Delete with bad state
			deleteResp := &resource.DeleteResponse{}
			r.Delete(context.Background(), resource.DeleteRequest{State: badState(schema, tt.fieldName)}, deleteResp)
			if !deleteResp.Diagnostics.HasError() {
				t.Fatalf("expected diagnostics for %s delete state", tt.name)
			}
		})
	}
}

func TestBatchImportStateReadError(t *testing.T) {
	r := &batchMigrationResource{}
	schema := newResourceSchema(t, r)

	cookbookDir := t.TempDir()
	outputDir := t.TempDir()
	playbookPath := filepath.Join(outputDir, testDefaultYml)
	if err := os.WriteFile(playbookPath, []byte("content"), 0644); err != nil {
		t.Fatalf(testFailedToWritePlaybook, err)
	}

	withOsReadFile(t, func(string) ([]byte, error) {
		return nil, errors.New("read error")
	})

	resp := &resource.ImportStateResponse{State: newEmptyState(schema)}
	req := resource.ImportStateRequest{ID: cookbookDir + "|" + outputDir + "|default"}
	r.ImportState(context.Background(), req, resp)
	if !resp.Diagnostics.HasError() {
		t.Fatal("expected diagnostics for import read error")
	}
}

func TestBatchImportStateRecipeNamesError(t *testing.T) {
	r := &batchMigrationResource{}

	cookbookDir := t.TempDir()
	outputDir := t.TempDir()

	resp := &resource.ImportStateResponse{State: newEmptyState(newResourceSchema(t, r))}
	req := resource.ImportStateRequest{ID: cookbookDir + "|" + outputDir + "| , "}
	r.ImportState(context.Background(), req, resp)
	if !resp.Diagnostics.HasError() {
		t.Fatal("expected diagnostics for invalid recipe names")
	}
}
