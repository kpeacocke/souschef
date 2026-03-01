// Package provider contains helper functions for Terraform provider tests.
package provider

import (
	"context"
	"os"
	"path/filepath"
	"testing"

	"github.com/hashicorp/terraform-plugin-framework/attr"
	"github.com/hashicorp/terraform-plugin-framework/datasource"
	datasourceschema "github.com/hashicorp/terraform-plugin-framework/datasource/schema"
	"github.com/hashicorp/terraform-plugin-framework/diag"
	"github.com/hashicorp/terraform-plugin-framework/provider"
	providerschema "github.com/hashicorp/terraform-plugin-framework/provider/schema"
	"github.com/hashicorp/terraform-plugin-framework/resource"
	resourceschema "github.com/hashicorp/terraform-plugin-framework/resource/schema"
	"github.com/hashicorp/terraform-plugin-framework/tfsdk"
	"github.com/hashicorp/terraform-plugin-framework/types"
	"github.com/hashicorp/terraform-plugin-go/tftypes"
)

const (
	scriptWhileArgsLoop  = "    while [ $# -gt 0 ]; do\n"
	scriptCaseFirstArg   = "      case \"$1\" in\n"
	scriptOutputPathArg  = "        --output-path) out=\"$2\"; shift 2 ;;\n"
	scriptDefaultShift   = "        *) shift ;;\n"
	scriptCaseEnd        = "      esac\n"
	scriptLoopDone       = "    done\n"
	scriptForcedError    = "      echo \"forced error\" >&2\n"
	scriptExitFailure    = "      exit 1\n"
	scriptIfEnd          = "    fi\n"
	scriptExitSuccess    = "      exit 0\n"
	scriptMakeOutputPath = "    mkdir -p \"$out\"\n"
	scriptCaseClauseEnd  = "    ;;\n"
)

const fakeSousChefScript = "#!/bin/sh\n" +
	"set -e\n" +
	"cmd=\"$1\"\n" +
	"shift\n" +
	"case \"$cmd\" in\n" +
	"  convert-recipe)\n" +
	scriptWhileArgsLoop +
	scriptCaseFirstArg +
	scriptOutputPathArg +
	"        --recipe-name) recipe=\"$2\"; shift 2 ;;\n" +
	"        --cookbook-path) shift 2 ;;\n" +
	scriptDefaultShift +
	scriptCaseEnd +
	scriptLoopDone +
	"    if [ \"$SOUSCHEF_TEST_FAIL\" = \"convert-recipe\" ]; then\n" +
	scriptForcedError +
	scriptExitFailure +
	scriptIfEnd +
	"    if [ \"$SOUSCHEF_TEST_SKIP_WRITE\" = \"convert-recipe\" ]; then\n" +
	scriptExitSuccess +
	scriptIfEnd +
	scriptMakeOutputPath +
	"    echo \"recipe: $recipe\" > \"$out/$recipe.yml\"\n" +
	"    if [ \"$SOUSCHEF_TEST_CHMOD\" = \"convert-recipe\" ]; then\n" +
	"      chmod 000 \"$out/$recipe.yml\"\n" +
	scriptIfEnd +
	scriptCaseClauseEnd +
	"  convert-habitat)\n" +
	scriptWhileArgsLoop +
	scriptCaseFirstArg +
	scriptOutputPathArg +
	"        --plan-path) shift 2 ;;\n" +
	"        --base-image) shift 2 ;;\n" +
	scriptDefaultShift +
	scriptCaseEnd +
	scriptLoopDone +
	"    if [ \"$SOUSCHEF_TEST_FAIL\" = \"convert-habitat\" ]; then\n" +
	scriptForcedError +
	scriptExitFailure +
	scriptIfEnd +
	"    if [ \"$SOUSCHEF_TEST_SKIP_WRITE\" = \"convert-habitat\" ]; then\n" +
	scriptExitSuccess +
	scriptIfEnd +
	scriptMakeOutputPath +
	"    echo \"FROM ubuntu:latest\" > \"$out/Dockerfile\"\n" +
	"    if [ \"$SOUSCHEF_TEST_CHMOD\" = \"convert-habitat\" ]; then\n" +
	"      chmod 000 \"$out/Dockerfile\"\n" +
	scriptIfEnd +
	scriptCaseClauseEnd +
	"  convert-inspec)\n" +
	scriptWhileArgsLoop +
	scriptCaseFirstArg +
	scriptOutputPathArg +
	"        --format) format=\"$2\"; shift 2 ;;\n" +
	"        --profile-path) shift 2 ;;\n" +
	scriptDefaultShift +
	scriptCaseEnd +
	scriptLoopDone +
	"    if [ \"$SOUSCHEF_TEST_FAIL\" = \"convert-inspec\" ]; then\n" +
	scriptForcedError +
	scriptExitFailure +
	scriptIfEnd +
	"    if [ \"$SOUSCHEF_TEST_SKIP_WRITE\" = \"convert-inspec\" ]; then\n" +
	scriptExitSuccess +
	scriptIfEnd +
	"    case \"$format\" in\n" +
	"      testinfra) filename=\"test_spec.py\" ;;\n" +
	"      serverspec) filename=\"spec_helper.rb\" ;;\n" +
	"      goss) filename=\"goss.yaml\" ;;\n" +
	"      ansible) filename=\"assert.yml\" ;;\n" +
	"      *) filename=\"test.txt\" ;;\n" +
	"    esac\n" +
	scriptMakeOutputPath +
	"    echo \"test content\" > \"$out/$filename\"\n" +
	"    if [ \"$SOUSCHEF_TEST_CHMOD\" = \"convert-inspec\" ]; then\n" +
	"      chmod 000 \"$out/$filename\"\n" +
	scriptIfEnd +
	scriptCaseClauseEnd +
	"  assess-cookbook)\n" +
	"    if [ \"$SOUSCHEF_TEST_FAIL\" = \"assess-cookbook\" ]; then\n" +
	scriptForcedError +
	scriptExitFailure +
	scriptIfEnd +
	"    if [ \"$SOUSCHEF_TEST_BAD_JSON\" = \"1\" ]; then\n" +
	"      echo \"{bad json\"\n" +
	scriptExitSuccess +
	scriptIfEnd +
	"    echo '{\"complexity\":\"Low\",\"recipe_count\":2,\"resource_count\":5,\"estimated_hours\":3.5,\"recommendations\":\"ok\"}'\n" +
	scriptCaseClauseEnd +
	"  *)\n" +
	"    echo \"unknown command\" >&2\n" +
	scriptExitFailure +
	scriptCaseClauseEnd +
	"esac\n"

func newFakeSousChef(t *testing.T) string {
	t.Helper()

	dir := t.TempDir()
	path := filepath.Join(dir, "souschef")

	if err := os.WriteFile(path, []byte(fakeSousChefScript), 0755); err != nil {
		t.Fatalf("failed to write fake souschef: %v", err)
	}

	return path
}

func newResourceSchema(t *testing.T, res resource.Resource) resourceschema.Schema {
	t.Helper()

	var resp resource.SchemaResponse
	res.Schema(context.Background(), resource.SchemaRequest{}, &resp)

	return resp.Schema
}

func newProviderSchema(t *testing.T, p provider.Provider) providerschema.Schema {
	t.Helper()

	var resp provider.SchemaResponse
	p.Schema(context.Background(), provider.SchemaRequest{}, &resp)

	return resp.Schema
}

func newDataSourceSchema(t *testing.T, ds datasource.DataSource) datasourceschema.Schema {
	t.Helper()

	var resp datasource.SchemaResponse
	ds.Schema(context.Background(), datasource.SchemaRequest{}, &resp)

	return resp.Schema
}

func newPlan(t *testing.T, schema resourceschema.Schema, val interface{}) tfsdk.Plan {
	t.Helper()

	plan := tfsdk.Plan{Schema: schema}
	diags := plan.Set(context.Background(), val)
	if diags.HasError() {
		t.Fatalf("failed to set plan: %v", diags)
	}

	return plan
}

func newState(t *testing.T, schema resourceschema.Schema, val interface{}) tfsdk.State {
	t.Helper()

	state := tfsdk.State{Schema: schema}
	diags := state.Set(context.Background(), val)
	if diags.HasError() {
		t.Fatalf("failed to set state: %v", diags)
	}

	return state
}

func newEmptyState(schema resourceschema.Schema) tfsdk.State {
	ctx := context.Background()

	// Build a map of null values for each attribute  in the schema
	attrValues := make(map[string]tftypes.Value)
	for attrName, attr := range schema.Attributes {
		attrType := attr.GetType()
		tfType := attrType.TerraformType(ctx)
		attrValues[attrName] = tftypes.NewValue(tfType, nil)
	}

	// Get the terraform object type from the schema
	schemaObjType := schema.Type().TerraformType(ctx)
	objType, isObj := schemaObjType.(tftypes.Object)
	if !isObj {
		// Fallback: create a null value
		return tfsdk.State{
			Schema: schema,
			Raw:    tftypes.NewValue(schemaObjType, nil),
		}
	}

	// Create the object with the null attributes
	rawValue := tftypes.NewValue(objType, attrValues)

	return tfsdk.State{
		Schema: schema,
		Raw:    rawValue,
	}
}

func newProviderConfig(t *testing.T, schema providerschema.Schema, val interface{}) tfsdk.Config {
	t.Helper()

	return tfsdk.Config{
		Schema: schema,
		Raw:    newConfigValue(t, schema.Type(), val),
	}
}

func newDataSourceConfig(t *testing.T, schema datasourceschema.Schema, val interface{}) tfsdk.Config {
	t.Helper()

	return tfsdk.Config{
		Schema: schema,
		Raw:    newConfigValue(t, schema.Type(), val),
	}
}

func newConfigValue(t *testing.T, schemaType attr.Type, val interface{}) tftypes.Value {
	t.Helper()

	var attrValue attr.Value
	diags := tfsdk.ValueFrom(context.Background(), val, schemaType, &attrValue)
	if diags.HasError() {
		t.Fatalf("failed to build config value: %v", diags)
	}

	terraformValue, err := attrValue.ToTerraformValue(context.Background())
	if err != nil {
		t.Fatalf("failed to convert config value: %v", err)
	}

	return terraformValue
}

// withTypesMapValueFrom temporarily overrides the typesMapValueFrom function for testing.
func withTypesMapValueFrom(t *testing.T, fn func(context.Context, attr.Type, any) (types.Map, diag.Diagnostics)) {
	t.Helper()
	original := typesMapValueFrom
	typesMapValueFrom = fn
	t.Cleanup(func() {
		typesMapValueFrom = original
	})
}

// withOsRemove temporarily overrides the osRemove function for testing.
func withOsRemove(t *testing.T, fn func(string) error) {
	t.Helper()
	original := osRemove
	osRemove = fn
	t.Cleanup(func() {
		osRemove = original
	})
}

// withOsReadFile temporarily overrides the osReadFile function for testing.
func withOsReadFile(t *testing.T, fn func(string) ([]byte, error)) {
	t.Helper()
	original := osReadFile
	osReadFile = fn
	t.Cleanup(func() {
		osReadFile = original
	})
}

// badPlan creates a tfsdk.Plan with an invalid attribute type for error testing.
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

// badState creates a tfsdk.State with an invalid attribute type for error testing.
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
