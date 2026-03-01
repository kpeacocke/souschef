// Package provider contains test generators to eliminate duplication patterns.
package provider

import (
	"context"
	"testing"

	"github.com/hashicorp/terraform-plugin-framework/diag"
	"github.com/hashicorp/terraform-plugin-framework/resource"
	"github.com/hashicorp/terraform-plugin-framework/tfsdk"
	"github.com/hashicorp/terraform-plugin-framework/types"
)

// ResourceConfigurator is an interface for resources that can be configured.
type ResourceConfigurator interface {
	Configure(context.Context, resource.ConfigureRequest, *resource.ConfigureResponse)
}

// testResourceConfigureCase defines a single configure test case.
type testResourceConfigureCase struct {
	name         string
	resource     ResourceConfigurator
	providerData interface{}
	expectError  bool
}

// testResourceCreateCase defines a generic create/update test case for any resource.
type testResourceCreateCase struct {
	name        string
	resource    string      // resource type: "migration", "batch", "habitat", "inspec"
	model       interface{} // the resource model
	expectError bool
	errorMsg    string // substring to match in error
}

// RunTableResourceConfigureTests runs table-driven configure tests for resources.
// Eliminates duplication of repetitive configure test code.
func RunTableResourceConfigureTests(t *testing.T, cases []testResourceConfigureCase) {
	t.Helper()
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			t.Helper()
			resp := &resource.ConfigureResponse{}
			tc.resource.Configure(context.Background(),
				resource.ConfigureRequest{ProviderData: tc.providerData},
				resp)

			if tc.expectError && !resp.Diagnostics.HasError() {
				t.Fatalf("expected error, got none")
			}
			if !tc.expectError && resp.Diagnostics.HasError() {
				t.Fatalf("unexpected error: %v", resp.Diagnostics)
			}
		})
	}
}

// assertDiagnosticsHelper is a reusable diagnostic assertion function.
func assertDiagnosticsHelper(t *testing.T, diags diag.Diagnostics, expectError bool, msg string) {
	t.Helper()
	if expectError && !diags.HasError() {
		t.Fatalf("%s: expected error, got none", msg)
	}
	if !expectError && diags.HasError() {
		t.Fatalf("%s: unexpected error: %v", msg, diags)
	}
}

// assertFileExistsHelper checks if a file exists and returns the result.
func assertFileExistsHelper(t *testing.T, path string, shouldExist bool) {
	t.Helper()
	exists := fileExists(path)
	if shouldExist && !exists {
		t.Fatalf("expected file to exist: %s", path)
	}
	if !shouldExist && exists {
		t.Fatalf("expected file to not exist: %s", path)
	}
}

// fileExists checks if a file exists without error handling.
func fileExists(path string) bool {
	_, err := osStat(path)
	return err == nil
}

// assertStateValuePairHelper checks that two state values match expected values.
func assertStateValuePairHelper(t *testing.T, plan, state tfsdk.Plan,
	key1, key2 string, val1, val2 types.String) {
	t.Helper()

	// Get both from plan
	var planModel interface{}
	if err := plan.Get(context.Background(), &planModel); err != nil {
		t.Fatalf("failed to get plan: %v", err)
	}
}

// batchResourceTestModel creates a batch migration resource model for testing.
func batchResourceTestModel(cookbookPath, outputPath string, recipeNames []string) interface{} {
	recipes := make([]types.String, len(recipeNames))
	for i, name := range recipeNames {
		recipes[i] = types.StringValue(name)
	}

	return map[string]interface{}{
		"cookbook_path":  types.StringValue(cookbookPath),
		"output_path":    types.StringValue(outputPath),
		"recipe_names":   recipes,
		"id":             types.StringNull(),
		"cookbook_name":  types.StringNull(),
		"playbook_count": types.Int64Null(),
		"playbooks":      types.MapNull(types.StringType),
	}
}

// habitatResourceTestModel creates a habitat migration resource model for testing.
func habitatResourceTestModel(planPath, outputPath string) interface{} {
	return map[string]interface{}{
		"plan_path":          types.StringValue(planPath),
		"output_path":        types.StringValue(outputPath),
		"base_image":         types.StringNull(),
		"id":                 types.StringNull(),
		"package_name":       types.StringNull(),
		"dockerfile_content": types.StringNull(),
	}
}

// inspecResourceTestModel creates an inspec migration resource model for testing.
func inspecResourceTestModel(profilePath, outputPath, format string) interface{} {
	return map[string]interface{}{
		"profile_path":  types.StringValue(profilePath),
		"output_path":   types.StringValue(outputPath),
		"output_format": types.StringValue(format),
		"id":            types.StringNull(),
		"profile_name":  types.StringNull(),
		"test_content":  types.StringNull(),
	}
}

// migrationResourceTestModel creates a migration resource model for testing.
func migrationResourceTestModel(recipeName, outputPath string) interface{} {
	return map[string]interface{}{
		"recipe_name": types.StringValue(recipeName),
		"output_path": types.StringValue(outputPath),
		"id":          types.StringNull(),
		"ans_name":    types.StringNull(),
		"playbook":    types.StringNull(),
	}
}
