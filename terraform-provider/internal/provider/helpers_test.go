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
	"github.com/hashicorp/terraform-plugin-framework/provider"
	providerschema "github.com/hashicorp/terraform-plugin-framework/provider/schema"
	"github.com/hashicorp/terraform-plugin-framework/resource"
	resourceschema "github.com/hashicorp/terraform-plugin-framework/resource/schema"
	"github.com/hashicorp/terraform-plugin-framework/tfsdk"
	"github.com/hashicorp/terraform-plugin-go/tftypes"
)

const fakeSousChefScript = "#!/bin/sh\n" +
	"set -e\n" +
	"cmd=\"$1\"\n" +
	"shift\n" +
	"case \"$cmd\" in\n" +
	"  convert-recipe)\n" +
	"    while [ $# -gt 0 ]; do\n" +
	"      case \"$1\" in\n" +
	"        --output-path) out=\"$2\"; shift 2 ;;\n" +
	"        --recipe-name) recipe=\"$2\"; shift 2 ;;\n" +
	"        --cookbook-path) shift 2 ;;\n" +
	"        *) shift ;;\n" +
	"      esac\n" +
	"    done\n" +
	"    if [ \"$SOUSCHEF_TEST_FAIL\" = \"convert-recipe\" ]; then\n" +
	"      echo \"forced error\" >&2\n" +
	"      exit 1\n" +
	"    fi\n" +
	"    if [ \"$SOUSCHEF_TEST_SKIP_WRITE\" = \"convert-recipe\" ]; then\n" +
	"      exit 0\n" +
	"    fi\n" +
	"    mkdir -p \"$out\"\n" +
	"    echo \"recipe: $recipe\" > \"$out/$recipe.yml\"\n" +
	"    if [ \"$SOUSCHEF_TEST_CHMOD\" = \"convert-recipe\" ]; then\n" +
	"      chmod 000 \"$out/$recipe.yml\"\n" +
	"    fi\n" +
	"    ;;\n" +
	"  convert-habitat)\n" +
	"    while [ $# -gt 0 ]; do\n" +
	"      case \"$1\" in\n" +
	"        --output-path) out=\"$2\"; shift 2 ;;\n" +
	"        --plan-path) shift 2 ;;\n" +
	"        --base-image) shift 2 ;;\n" +
	"        *) shift ;;\n" +
	"      esac\n" +
	"    done\n" +
	"    if [ \"$SOUSCHEF_TEST_FAIL\" = \"convert-habitat\" ]; then\n" +
	"      echo \"forced error\" >&2\n" +
	"      exit 1\n" +
	"    fi\n" +
	"    if [ \"$SOUSCHEF_TEST_SKIP_WRITE\" = \"convert-habitat\" ]; then\n" +
	"      exit 0\n" +
	"    fi\n" +
	"    mkdir -p \"$out\"\n" +
	"    echo \"FROM ubuntu:latest\" > \"$out/Dockerfile\"\n" +
	"    if [ \"$SOUSCHEF_TEST_CHMOD\" = \"convert-habitat\" ]; then\n" +
	"      chmod 000 \"$out/Dockerfile\"\n" +
	"    fi\n" +
	"    ;;\n" +
	"  convert-inspec)\n" +
	"    while [ $# -gt 0 ]; do\n" +
	"      case \"$1\" in\n" +
	"        --output-path) out=\"$2\"; shift 2 ;;\n" +
	"        --format) format=\"$2\"; shift 2 ;;\n" +
	"        --profile-path) shift 2 ;;\n" +
	"        *) shift ;;\n" +
	"      esac\n" +
	"    done\n" +
	"    if [ \"$SOUSCHEF_TEST_FAIL\" = \"convert-inspec\" ]; then\n" +
	"      echo \"forced error\" >&2\n" +
	"      exit 1\n" +
	"    fi\n" +
	"    if [ \"$SOUSCHEF_TEST_SKIP_WRITE\" = \"convert-inspec\" ]; then\n" +
	"      exit 0\n" +
	"    fi\n" +
	"    case \"$format\" in\n" +
	"      testinfra) filename=\"test_spec.py\" ;;\n" +
	"      serverspec) filename=\"spec_helper.rb\" ;;\n" +
	"      goss) filename=\"goss.yaml\" ;;\n" +
	"      ansible) filename=\"assert.yml\" ;;\n" +
	"      *) filename=\"test.txt\" ;;\n" +
	"    esac\n" +
	"    mkdir -p \"$out\"\n" +
	"    echo \"test content\" > \"$out/$filename\"\n" +
	"    if [ \"$SOUSCHEF_TEST_CHMOD\" = \"convert-inspec\" ]; then\n" +
	"      chmod 000 \"$out/$filename\"\n" +
	"    fi\n" +
	"    ;;\n" +
	"  assess-cookbook)\n" +
	"    if [ \"$SOUSCHEF_TEST_FAIL\" = \"assess-cookbook\" ]; then\n" +
	"      echo \"forced error\" >&2\n" +
	"      exit 1\n" +
	"    fi\n" +
	"    if [ \"$SOUSCHEF_TEST_BAD_JSON\" = \"1\" ]; then\n" +
	"      echo \"{bad json\"\n" +
	"      exit 0\n" +
	"    fi\n" +
	"    echo '{\"complexity\":\"Low\",\"recipe_count\":2,\"resource_count\":5,\"estimated_hours\":3.5,\"recommendations\":\"ok\"}'\n" +
	"    ;;\n" +
	"  *)\n" +
	"    echo \"unknown command\" >&2\n" +
	"    exit 1\n" +
	"    ;;\n" +
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
