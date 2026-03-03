package provider

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"testing"

	"github.com/hashicorp/terraform-plugin-framework/resource"
	"github.com/hashicorp/terraform-plugin-framework/tfsdk"
	"github.com/hashicorp/terraform-plugin-go/tftypes"
)

const (
	invalidImportIDMsg = "Invalid import ID"
)

// TestBatchMigrationImportStateInvalidID tests ImportState with invalid ID format
func TestBatchMigrationImportStateInvalidID(t *testing.T) {
	r := &batchMigrationResource{
		client: &SousChefClient{Path: "souschef"},
	}

	// Create schema
	schemaReq := resource.SchemaRequest{}
	schemaResp := &resource.SchemaResponse{}
	r.Schema(context.Background(), schemaReq, schemaResp)

	tests := []struct {
		name        string
		importID    string
		expectError bool
		errorMsg    string
	}{
		{
			name:        "missing pipes",
			importID:    "just-one-part",
			expectError: true,
			errorMsg:    invalidImportIDMsg,
		},
		{
			name:        "only two parts",
			importID:    "/path/to/cookbook|/output",
			expectError: true,
			errorMsg:    invalidImportIDMsg,
		},
		{
			name:        "too many parts",
			importID:    "/path/to/cookbook|/output|recipe1|extra",
			expectError: true,
			errorMsg:    invalidImportIDMsg,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			req := resource.ImportStateRequest{
				ID: tt.importID,
			}
			resp := &resource.ImportStateResponse{}
			resp.State = tfsdk.State{
				Schema: schemaResp.Schema,
				Raw:    tftypes.NewValue(schemaResp.Schema.Type().TerraformType(context.Background()), nil),
			}

			r.ImportState(context.Background(), req, resp)

			if tt.expectError && !resp.Diagnostics.HasError() {
				t.Errorf("Expected error containing '%s', got no error", tt.errorMsg)
			}
			if !tt.expectError && resp.Diagnostics.HasError() {
				t.Errorf("Expected no error, got: %v", resp.Diagnostics.Errors())
			}
		})
	}
}

// TestBatchMigrationImportStateNonexistentCookbook tests ImportState with missing cookbook
func TestBatchMigrationImportStateNonexistentCookbook(t *testing.T) {
	r := &batchMigrationResource{
		client: &SousChefClient{Path: "souschef"},
	}

	// Create schema
	schemaReq := resource.SchemaRequest{}
	schemaResp := &resource.SchemaResponse{}
	r.Schema(context.Background(), schemaReq, schemaResp)

	req := resource.ImportStateRequest{
		ID: "/nonexistent/path|/output|default",
	}
	resp := &resource.ImportStateResponse{}
	resp.State = tfsdk.State{
		Schema: schemaResp.Schema,
		Raw:    tftypes.NewValue(schemaResp.Schema.Type().TerraformType(context.Background()), nil),
	}

	r.ImportState(context.Background(), req, resp)

	if !resp.Diagnostics.HasError() {
		t.Error("Expected error for nonexistent cookbook, got none")
	}
}

// TestBatchMigrationImportStateNonexistentPlaybook tests ImportState with missing playbook
func TestBatchMigrationImportStateNonexistentPlaybook(t *testing.T) {
	r := &batchMigrationResource{
		client: &SousChefClient{Path: "souschef"},
	}

	// Create schema
	schemaReq := resource.SchemaRequest{}
	schemaResp := &resource.SchemaResponse{}
	r.Schema(context.Background(), schemaReq, schemaResp)

	// Create temp directories but no playbook files
	tmpDir := t.TempDir()
	cookbookDir := filepath.Join(tmpDir, "cookbook")
	outputDir := filepath.Join(tmpDir, "output")

	err := os.MkdirAll(cookbookDir, 0755)
	if err != nil {
		t.Fatalf("Failed to create cookbook dir: %v", err)
	}

	err = os.MkdirAll(outputDir, 0755)
	if err != nil {
		t.Fatalf("Failed to create output dir: %v", err)
	}

	req := resource.ImportStateRequest{
		ID: fmt.Sprintf("%s|%s|default", cookbookDir, outputDir),
	}
	resp := &resource.ImportStateResponse{}
	resp.State = tfsdk.State{
		Schema: schemaResp.Schema,
		Raw:    tftypes.NewValue(schemaResp.Schema.Type().TerraformType(context.Background()), nil),
	}

	r.ImportState(context.Background(), req, resp)

	if !resp.Diagnostics.HasError() {
		t.Error("Expected error for nonexistent playbook, got none")
	}
}

// TestBatchMigrationImportStateMultipleRecipes tests ImportState with multiple recipes
func TestBatchMigrationImportStateMultipleRecipes(t *testing.T) {
	r := &batchMigrationResource{
		client: &SousChefClient{Path: "souschef"},
	}

	// Create schema
	schemaReq := resource.SchemaRequest{}
	schemaResp := &resource.SchemaResponse{}
	r.Schema(context.Background(), schemaReq, schemaResp)

	// Create temp directories and playbook files
	tmpDir := t.TempDir()
	cookbookDir := filepath.Join(tmpDir, "cookbook")
	outputDir := filepath.Join(tmpDir, "output")

	err := os.MkdirAll(cookbookDir, 0755)
	if err != nil {
		t.Fatalf("Failed to create cookbook dir: %v", err)
	}

	err = os.MkdirAll(outputDir, 0755)
	if err != nil {
		t.Fatalf("Failed to create output dir: %v", err)
	}

	// Create playbook files
	playbooks := map[string]string{
		"default": "---\n- name: default playbook\n",
		"server":  "---\n- name: server playbook\n",
	}

	for name, content := range playbooks {
		playbookPath := filepath.Join(outputDir, name+".yml")
		err := os.WriteFile(playbookPath, []byte(content), 0644)
		if err != nil {
			t.Fatalf("Failed to create playbook %s: %v", name, err)
		}
	}

	req := resource.ImportStateRequest{
		ID: fmt.Sprintf("%s|%s|default,server", cookbookDir, outputDir),
	}
	resp := &resource.ImportStateResponse{}
	resp.State = tfsdk.State{
		Schema: schemaResp.Schema,
		Raw:    tftypes.NewValue(schemaResp.Schema.Type().TerraformType(context.Background()), nil),
	}

	r.ImportState(context.Background(), req, resp)

	// Should succeed with both recipes
	if resp.Diagnostics.HasError() {
		t.Errorf("Expected no errors, got: %v", resp.Diagnostics.Errors())
	}

	// Verify state was set correctly
	var model batchMigrationResourceModel
	diags := resp.State.Get(context.Background(), &model)
	if diags.HasError() {
		t.Fatalf("Failed to get state: %v", diags.Errors())
	}

	if len(model.RecipeNames) != 2 {
		t.Errorf("Expected 2 recipes, got %d", len(model.RecipeNames))
	}

	if model.PlaybookCount.ValueInt64() != 2 {
		t.Errorf("Expected playbook_count to be 2, got %d", model.PlaybookCount.ValueInt64())
	}
}
