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
	resourceschema "github.com/hashicorp/terraform-plugin-framework/resource/schema"
	"github.com/hashicorp/terraform-plugin-framework/tfsdk"
	"github.com/hashicorp/terraform-plugin-framework/types"
	"github.com/hashicorp/terraform-plugin-go/tftypes"
)

func withTypesMapValueFrom(t *testing.T, fn func(context.Context, attr.Type, any) (types.Map, diag.Diagnostics)) {
	t.Helper()
	original := typesMapValueFrom
	typesMapValueFrom = fn
	t.Cleanup(func() {
		typesMapValueFrom = original
	})
}

func withOsRemove(t *testing.T, fn func(string) error) {
	t.Helper()
	original := osRemove
	osRemove = fn
	t.Cleanup(func() {
		osRemove = original
	})
}

func withOsReadFile(t *testing.T, fn func(string) ([]byte, error)) {
	t.Helper()
	original := osReadFile
	osReadFile = fn
	t.Cleanup(func() {
		osReadFile = original
	})
}

func badPlan(schema resourceschema.Schema, attrName string) tfsdk.Plan {
	raw := tftypes.NewValue(tftypes.Object{
		AttributeTypes: map[string]tftypes.Type{
			attrName: tftypes.Number,
		},
	}, map[string]tftypes.Value{
		attrName: tftypes.NewValue(tftypes.Number, 1),
	})

	return tfsdk.Plan{Schema: schema, Raw: raw}
}

func badState(schema resourceschema.Schema, attrName string) tfsdk.State {
	raw := tftypes.NewValue(tftypes.Object{
		AttributeTypes: map[string]tftypes.Type{
			attrName: tftypes.Number,
		},
	}, map[string]tftypes.Value{
		attrName: tftypes.NewValue(tftypes.Number, 1),
	})

	return tfsdk.State{Schema: schema, Raw: raw}
}

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
	playbookPath := filepath.Join(outputDir, "default.yml")
	if err := os.WriteFile(playbookPath, []byte("content"), 0644); err != nil {
		t.Fatalf("failed to write playbook: %v", err)
	}

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
		t.Fatal("expected diagnostics from map conversion in read")
	}

	cookbookDir := t.TempDir()
	outputDir = t.TempDir()
	playbookPath = filepath.Join(outputDir, "default.yml")
	if err := os.WriteFile(playbookPath, []byte("content"), 0644); err != nil {
		t.Fatalf("failed to write playbook: %v", err)
	}

	importResp := &resource.ImportStateResponse{State: newEmptyState(schema)}
	r.ImportState(context.Background(), resource.ImportStateRequest{ID: cookbookDir + "|" + outputDir + "|default"}, importResp)
	if !importResp.Diagnostics.HasError() {
		t.Fatal("expected diagnostics from map conversion in import")
	}
}

func TestDeleteIgnoresMissingFiles(t *testing.T) {
	withOsRemove(t, func(string) error {
		return os.ErrNotExist
	})

	// Migration delete should ignore missing file
	migration := &migrationResource{}
	migrationSchema := newResourceSchema(t, migration)
	migrationState := newState(t, migrationSchema, migrationResourceModel{
		RecipeName: types.StringValue("missing"),
		OutputPath: types.StringValue(t.TempDir()),
	})
	migrationResp := &resource.DeleteResponse{}
	migration.Delete(context.Background(), resource.DeleteRequest{State: migrationState}, migrationResp)
	if migrationResp.Diagnostics.HasError() {
		t.Fatalf("unexpected diagnostics for missing migration file: %v", migrationResp.Diagnostics)
	}

	// Habitat delete should ignore missing file
	habitat := &habitatMigrationResource{}
	habitatSchema := newResourceSchema(t, habitat)
	habitatState := newState(t, habitatSchema, habitatMigrationResourceModel{
		PlanPath:   types.StringValue("/tmp/plan.sh"),
		OutputPath: types.StringValue(t.TempDir()),
	})
	habitatResp := &resource.DeleteResponse{}
	habitat.Delete(context.Background(), resource.DeleteRequest{State: habitatState}, habitatResp)
	if habitatResp.Diagnostics.HasError() {
		t.Fatalf("unexpected diagnostics for missing dockerfile: %v", habitatResp.Diagnostics)
	}

	// InSpec delete should ignore missing file
	inspec := &inspecMigrationResource{}
	inspecSchema := newResourceSchema(t, inspec)
	inspecState := newState(t, inspecSchema, inspecMigrationResourceModel{
		ProfilePath:  types.StringValue("/tmp/profile"),
		OutputPath:   types.StringValue(t.TempDir()),
		OutputFormat: types.StringValue("testinfra"),
	})
	inspecResp := &resource.DeleteResponse{}
	inspec.Delete(context.Background(), resource.DeleteRequest{State: inspecState}, inspecResp)
	if inspecResp.Diagnostics.HasError() {
		t.Fatalf("unexpected diagnostics for missing test file: %v", inspecResp.Diagnostics)
	}

	// Batch delete should ignore missing files
	batch := &batchMigrationResource{}
	batchSchema := newResourceSchema(t, batch)
	batchState := newState(t, batchSchema, batchMigrationResourceModel{
		ID:            types.StringValue("batch"),
		RecipeNames: []types.String{
			types.StringValue("default"),
		},
		OutputPath:   types.StringValue(t.TempDir()),
		CookbookName: types.StringValue("test"),
		PlaybookCount: types.Int64Value(1),
		Playbooks:    types.MapNull(types.StringType),
	})
	batchResp := &resource.DeleteResponse{}
	batch.Delete(context.Background(), resource.DeleteRequest{State: batchState}, batchResp)
	if batchResp.Diagnostics.HasError() {
		t.Fatalf("unexpected diagnostics for missing batch files: %v", batchResp.Diagnostics)
	}
}

func TestDeleteReportsPermissionError(t *testing.T) {
	withOsRemove(t, func(string) error {
		return errors.New("permission denied")
	})

	// Migration delete should report error
	migration := &migrationResource{}
	migrationSchema := newResourceSchema(t, migration)
	migrationState := newState(t, migrationSchema, migrationResourceModel{
		RecipeName: types.StringValue("test"),
		OutputPath: types.StringValue(t.TempDir()),
	})
	migrationResp := &resource.DeleteResponse{}
	migration.Delete(context.Background(), resource.DeleteRequest{State: migrationState}, migrationResp)
	if !migrationResp.Diagnostics.HasError() {
		t.Fatal("expected diagnostics for migration delete error")
	}

	// Habitat delete should report warning
	habitat := &habitatMigrationResource{}
	habitatSchema := newResourceSchema(t, habitat)
	habitatState := newState(t, habitatSchema, habitatMigrationResourceModel{
		PlanPath:   types.StringValue("/tmp/plan.sh"),
		OutputPath: types.StringValue(t.TempDir()),
	})
	habitatResp := &resource.DeleteResponse{}
	habitat.Delete(context.Background(), resource.DeleteRequest{State: habitatState}, habitatResp)
	if len(habitatResp.Diagnostics) == 0 {
		t.Fatal("expected warning diagnostics for habitat delete error")
	}

	// InSpec delete should report warning
	inspec := &inspecMigrationResource{}
	inspecSchema := newResourceSchema(t, inspec)
	inspecState := newState(t, inspecSchema, inspecMigrationResourceModel{
		ProfilePath:  types.StringValue("/tmp/profile"),
		OutputPath:   types.StringValue(t.TempDir()),
		OutputFormat: types.StringValue("testinfra"),
	})
	inspecResp := &resource.DeleteResponse{}
	inspec.Delete(context.Background(), resource.DeleteRequest{State: inspecState}, inspecResp)
	if len(inspecResp.Diagnostics) == 0 {
		t.Fatal("expected warning diagnostics for inspec delete error")
	}

	// Batch delete should report warning
	batch := &batchMigrationResource{}
	batchSchema := newResourceSchema(t, batch)
	batchState := newState(t, batchSchema, batchMigrationResourceModel{
		ID:            types.StringValue("batch"),
		RecipeNames: []types.String{
			types.StringValue("default"),
		},
		OutputPath:   types.StringValue(t.TempDir()),
		CookbookName: types.StringValue("test"),
		PlaybookCount: types.Int64Value(1),
		Playbooks:    types.MapNull(types.StringType),
	})
	batchResp := &resource.DeleteResponse{}
	batch.Delete(context.Background(), resource.DeleteRequest{State: batchState}, batchResp)
	if len(batchResp.Diagnostics) == 0 {
		t.Fatal("expected warning diagnostics for batch delete error")
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

func TestMigrationPlanStateGetDiagnostics(t *testing.T) {
	r := &migrationResource{}
	schema := newResourceSchema(t, r)

	createResp := &resource.CreateResponse{State: tfsdk.State{Schema: schema}}
	r.Create(context.Background(), resource.CreateRequest{Plan: badPlan(schema, "cookbook_path")}, createResp)
	if !createResp.Diagnostics.HasError() {
		t.Fatal("expected diagnostics for migration create plan")
	}

	updateResp := &resource.UpdateResponse{State: tfsdk.State{Schema: schema}}
	r.Update(context.Background(), resource.UpdateRequest{Plan: badPlan(schema, "cookbook_path")}, updateResp)
	if !updateResp.Diagnostics.HasError() {
		t.Fatal("expected diagnostics for migration update plan")
	}

	readResp := &resource.ReadResponse{State: tfsdk.State{Schema: schema}}
	r.Read(context.Background(), resource.ReadRequest{State: badState(schema, "cookbook_path")}, readResp)
	if !readResp.Diagnostics.HasError() {
		t.Fatal("expected diagnostics for migration read state")
	}

	deleteResp := &resource.DeleteResponse{}
	r.Delete(context.Background(), resource.DeleteRequest{State: badState(schema, "cookbook_path")}, deleteResp)
	if !deleteResp.Diagnostics.HasError() {
		t.Fatal("expected diagnostics for migration delete state")
	}
}

func TestBatchPlanStateGetDiagnostics(t *testing.T) {
	r := &batchMigrationResource{}
	schema := newResourceSchema(t, r)

	createResp := &resource.CreateResponse{State: tfsdk.State{Schema: schema}}
	r.Create(context.Background(), resource.CreateRequest{Plan: badPlan(schema, "cookbook_path")}, createResp)
	if !createResp.Diagnostics.HasError() {
		t.Fatal("expected diagnostics for batch create plan")
	}

	updateResp := &resource.UpdateResponse{State: tfsdk.State{Schema: schema}}
	r.Update(context.Background(), resource.UpdateRequest{Plan: badPlan(schema, "cookbook_path")}, updateResp)
	if !updateResp.Diagnostics.HasError() {
		t.Fatal("expected diagnostics for batch update plan")
	}

	readResp := &resource.ReadResponse{State: tfsdk.State{Schema: schema}}
	r.Read(context.Background(), resource.ReadRequest{State: badState(schema, "cookbook_path")}, readResp)
	if !readResp.Diagnostics.HasError() {
		t.Fatal("expected diagnostics for batch read state")
	}

	deleteResp := &resource.DeleteResponse{}
	r.Delete(context.Background(), resource.DeleteRequest{State: badState(schema, "cookbook_path")}, deleteResp)
	if !deleteResp.Diagnostics.HasError() {
		t.Fatal("expected diagnostics for batch delete state")
	}
}

func TestHabitatPlanStateGetDiagnostics(t *testing.T) {
	r := &habitatMigrationResource{}
	schema := newResourceSchema(t, r)

	createResp := &resource.CreateResponse{State: tfsdk.State{Schema: schema}}
	r.Create(context.Background(), resource.CreateRequest{Plan: badPlan(schema, "plan_path")}, createResp)
	if !createResp.Diagnostics.HasError() {
		t.Fatal("expected diagnostics for habitat create plan")
	}

	updateResp := &resource.UpdateResponse{State: tfsdk.State{Schema: schema}}
	r.Update(context.Background(), resource.UpdateRequest{Plan: badPlan(schema, "plan_path")}, updateResp)
	if !updateResp.Diagnostics.HasError() {
		t.Fatal("expected diagnostics for habitat update plan")
	}

	readResp := &resource.ReadResponse{State: tfsdk.State{Schema: schema}}
	r.Read(context.Background(), resource.ReadRequest{State: badState(schema, "plan_path")}, readResp)
	if !readResp.Diagnostics.HasError() {
		t.Fatal("expected diagnostics for habitat read state")
	}

	deleteResp := &resource.DeleteResponse{}
	r.Delete(context.Background(), resource.DeleteRequest{State: badState(schema, "plan_path")}, deleteResp)
	if !deleteResp.Diagnostics.HasError() {
		t.Fatal("expected diagnostics for habitat delete state")
	}
}

func TestInSpecPlanStateGetDiagnostics(t *testing.T) {
	r := &inspecMigrationResource{}
	schema := newResourceSchema(t, r)

	createResp := &resource.CreateResponse{State: tfsdk.State{Schema: schema}}
	r.Create(context.Background(), resource.CreateRequest{Plan: badPlan(schema, "profile_path")}, createResp)
	if !createResp.Diagnostics.HasError() {
		t.Fatal("expected diagnostics for inspec create plan")
	}

	updateResp := &resource.UpdateResponse{State: tfsdk.State{Schema: schema}}
	r.Update(context.Background(), resource.UpdateRequest{Plan: badPlan(schema, "profile_path")}, updateResp)
	if !updateResp.Diagnostics.HasError() {
		t.Fatal("expected diagnostics for inspec update plan")
	}

	readResp := &resource.ReadResponse{State: tfsdk.State{Schema: schema}}
	r.Read(context.Background(), resource.ReadRequest{State: badState(schema, "profile_path")}, readResp)
	if !readResp.Diagnostics.HasError() {
		t.Fatal("expected diagnostics for inspec read state")
	}

	deleteResp := &resource.DeleteResponse{}
	r.Delete(context.Background(), resource.DeleteRequest{State: badState(schema, "profile_path")}, deleteResp)
	if !deleteResp.Diagnostics.HasError() {
		t.Fatal("expected diagnostics for inspec delete state")
	}
}

func TestBatchImportStateReadError(t *testing.T) {
	r := &batchMigrationResource{}
	schema := newResourceSchema(t, r)

	cookbookDir := t.TempDir()
	outputDir := t.TempDir()
	playbookPath := filepath.Join(outputDir, "default.yml")
	if err := os.WriteFile(playbookPath, []byte("content"), 0644); err != nil {
		t.Fatalf("failed to write playbook: %v", err)
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
