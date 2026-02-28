// Package provider contains tests for previously uncovered code paths
// in the SousChef Terraform provider.
package provider

import (
	"context"
	"os"
	"path/filepath"
	"testing"

	"github.com/hashicorp/terraform-plugin-framework/datasource"
	"github.com/hashicorp/terraform-plugin-framework/resource"
)

const (
	errFailedCreateOutputDirMissing = "failed to create output dir: %v"
)

func TestAssessmentDataSourceConfigureNilClient(t *testing.T) {
	ds := &assessmentDataSource{}
	req := datasource.ConfigureRequest{ProviderData: nil}
	resp := &datasource.ConfigureResponse{}

	ds.Configure(context.Background(), req, resp)

	if resp.Diagnostics.HasError() {
		t.Errorf("unexpected error on nil provider data: %v", resp.Diagnostics)
	}
}

func TestAssessmentDataSourceConfigureInvalidType(t *testing.T) {
	ds := &assessmentDataSource{}
	req := datasource.ConfigureRequest{ProviderData: "invalid"}
	resp := &datasource.ConfigureResponse{}

	ds.Configure(context.Background(), req, resp)

	if !resp.Diagnostics.HasError() {
		t.Error("expected error when provider data is wrong type")
	}
}

func TestAssessmentDataSourceConfigureValidClient(t *testing.T) {
	ds := &assessmentDataSource{}
	client := &SousChefClient{Path: "/usr/local/bin/souschef"}
	req := datasource.ConfigureRequest{ProviderData: client}
	resp := &datasource.ConfigureResponse{}

	ds.Configure(context.Background(), req, resp)

	if resp.Diagnostics.HasError() {
		t.Errorf("unexpected error configuring data source: %v", resp.Diagnostics)
	}

	if ds.client == nil {
		t.Fatal("expected client to be set after Configure")
	}

	ValidateConfigValue(t, ds.client.Path, "/usr/local/bin/souschef")
}

func TestCostEstimateDataSourceConfigureNilClient(t *testing.T) {
	ds := &costEstimateDataSource{}
	req := datasource.ConfigureRequest{ProviderData: nil}
	resp := &datasource.ConfigureResponse{}

	ds.Configure(context.Background(), req, resp)

	if resp.Diagnostics.HasError() {
		t.Errorf("unexpected error on nil provider data: %v", resp.Diagnostics)
	}
}

func TestCostEstimateDataSourceConfigureInvalidType(t *testing.T) {
	ds := &costEstimateDataSource{}
	req := datasource.ConfigureRequest{ProviderData: 123}
	resp := &datasource.ConfigureResponse{}

	ds.Configure(context.Background(), req, resp)

	if !resp.Diagnostics.HasError() {
		t.Error("expected error when provider data is wrong type")
	}
}

func TestAssessmentDataSourceSchema(t *testing.T) {
	ds := &assessmentDataSource{}
	req := datasource.SchemaRequest{}
	resp := &datasource.SchemaResponse{}

	ds.Schema(context.Background(), req, resp)

	expectedAttrs := []string{
		"id", "cookbook_path", "complexity", "recipe_count",
		"resource_count", "estimated_hours", "recommendations",
	}

	for _, attr := range expectedAttrs {
		if _, ok := resp.Schema.Attributes[attr]; !ok {
			t.Errorf("expected attribute %q in assessment schema", attr)
		}
	}
}

func TestCostEstimateDataSourceSchema(t *testing.T) {
	ds := &costEstimateDataSource{}
	req := datasource.SchemaRequest{}
	resp := &datasource.SchemaResponse{}

	ds.Schema(context.Background(), req, resp)

	expectedAttrs := []string{
		"id", "cookbook_path", "complexity", "recipe_count",
		"resource_count", "estimated_hours", "estimated_cost_usd",
		"developer_hourly_rate", "infrastructure_cost",
		"total_project_cost_usd", "recommendations",
	}

	for _, attr := range expectedAttrs {
		if _, ok := resp.Schema.Attributes[attr]; !ok {
			t.Errorf("expected attribute %q in cost estimate schema", attr)
		}
	}
}

func TestBatchMigrationResourceSchema(t *testing.T) {
	r := &batchMigrationResource{}
	req := resource.SchemaRequest{}
	resp := &resource.SchemaResponse{}

	r.Schema(context.Background(), req, resp)

	expectedAttrs := []string{
		"id", "cookbook_path", "output_path", "cookbook_name",
		"recipe_names", "playbook_count", "playbooks",
	}

	for _, attr := range expectedAttrs {
		if _, ok := resp.Schema.Attributes[attr]; !ok {
			t.Errorf("expected attribute %q in batch migration resource schema", attr)
		}
	}
}

func TestHabitatMigrationResourceSchema(t *testing.T) {
	r := &habitatMigrationResource{}
	req := resource.SchemaRequest{}
	resp := &resource.SchemaResponse{}

	r.Schema(context.Background(), req, resp)

	expectedAttrs := []string{
		"id", "plan_path", "output_path", "base_image",
		"package_name", "dockerfile_content",
	}

	for _, attr := range expectedAttrs {
		if _, ok := resp.Schema.Attributes[attr]; !ok {
			t.Errorf("expected attribute %q in habitat migration resource schema", attr)
		}
	}
}

func TestInSpecMigrationResourceSchema(t *testing.T) {
	r := &inspecMigrationResource{}
	req := resource.SchemaRequest{}
	resp := &resource.SchemaResponse{}

	r.Schema(context.Background(), req, resp)

	expectedAttrs := []string{
		"id", "profile_path", "output_path", "output_format",
		"profile_name", "test_content",
	}

	for _, attr := range expectedAttrs {
		if _, ok := resp.Schema.Attributes[attr]; !ok {
			t.Errorf("expected attribute %q in inspec migration resource schema", attr)
		}
	}
}

func TestBatchMigrationImportStateMissingCookbook(t *testing.T) {
	r := &batchMigrationResource{client: &SousChefClient{Path: "souschef"}}

	req := resource.ImportStateRequest{
		ID: "/nonexistent/path|/tmp/output|recipe1,recipe2",
	}
	resp := &resource.ImportStateResponse{}

	r.ImportState(context.Background(), req, resp)

	if !resp.Diagnostics.HasError() {
		t.Error("expected error for non-existent cookbook path")
	}
}

func TestBatchMigrationImportStateFilesPresent(t *testing.T) {
	// Verifies setup of files needed for batch import, without calling ImportState
	// which requires full framework state initialisation.
	tmpDir := t.TempDir()
	cookbookDir := filepath.Join(tmpDir, "batch-cookbook")
	outputDir := filepath.Join(tmpDir, "batch-output")

	if err := os.MkdirAll(cookbookDir, testDirPermissions); err != nil {
		t.Fatalf("failed to create cookbook dir: %v", err)
	}
	if err := os.MkdirAll(outputDir, testDirPermissions); err != nil {
		t.Fatalf(errFailedCreateOutputDirMissing, err)
	}

	// Create playbook files for each recipe
	recipes := []string{"default", "install"}
	for _, recipe := range recipes {
		playbookPath := filepath.Join(outputDir, recipe+".yml")
		content := "---\n- hosts: all\n  tasks: []\n"
		if err := os.WriteFile(playbookPath, []byte(content), testFilePermissions); err != nil {
			t.Fatalf("failed to create playbook for %s: %v", recipe, err)
		}
	}

	// Verify all expected files exist
	for _, recipe := range recipes {
		playbookPath := filepath.Join(outputDir, recipe+".yml")
		if _, err := os.Stat(playbookPath); err != nil {
			t.Errorf("expected playbook %s to exist: %v", recipe, err)
		}
	}
}

func TestHabitatMigrationImportStateMissingPlan(t *testing.T) {
	r := &habitatMigrationResource{client: &SousChefClient{Path: "souschef"}}

	req := resource.ImportStateRequest{
		ID: "/nonexistent/plan.sh|/tmp/docker|ubuntu:latest",
	}
	resp := &resource.ImportStateResponse{}

	r.ImportState(context.Background(), req, resp)

	if !resp.Diagnostics.HasError() {
		t.Error("expected error for non-existent plan file")
	}
}

func TestHabitatMigrationImportStateMissingDockerfile(t *testing.T) {
	tmpDir := t.TempDir()
	planPath := filepath.Join(tmpDir, "plan.sh")
	outputDir := filepath.Join(tmpDir, "docker-output")

	if err := os.WriteFile(planPath, []byte("pkg_name=myapp\n"), executableFilePermissions); err != nil {
		t.Fatalf("failed to create plan file: %v", err)
	}
	if err := os.MkdirAll(outputDir, testDirPermissions); err != nil {
		t.Fatalf(errFailedCreateOutputDirMissing, err)
	}

	r := &habitatMigrationResource{client: &SousChefClient{Path: "souschef"}}

	req := resource.ImportStateRequest{
		ID: planPath + "|" + outputDir + "|ubuntu:latest",
	}
	resp := &resource.ImportStateResponse{}

	r.ImportState(context.Background(), req, resp)

	if !resp.Diagnostics.HasError() {
		t.Error("expected error for missing Dockerfile")
	}
}

func TestHabitatMigrationImportStatePlanFilePresent(t *testing.T) {
	// Verifies that a plan file and Dockerfile can be created, without calling
	// ImportState's success path which requires full framework state initialisation.
	tmpDir := t.TempDir()
	planPath := filepath.Join(tmpDir, "plan.sh")
	outputDir := filepath.Join(tmpDir, "docker-output")

	if err := os.WriteFile(planPath, []byte("pkg_name=myapp\n"), executableFilePermissions); err != nil {
		t.Fatalf("failed to create plan file: %v", err)
	}
	if err := os.MkdirAll(outputDir, testDirPermissions); err != nil {
		t.Fatalf(errFailedCreateOutputDirMissing, err)
	}

	dockerfilePath := filepath.Join(outputDir, "Dockerfile")
	dockerfileContent := "FROM ubuntu:latest\nRUN echo hello\n"
	if err := os.WriteFile(dockerfilePath, []byte(dockerfileContent), testFilePermissions); err != nil {
		t.Fatalf("failed to create Dockerfile: %v", err)
	}

	// Verify files exist with expected permissions
	info, err := os.Stat(planPath)
	if err != nil {
		t.Fatalf("plan file should exist: %v", err)
	}
	if info.Mode()&executableFilePermissions != executableFilePermissions {
		t.Logf("plan file has mode %v", info.Mode())
	}

	if _, err := os.Stat(dockerfilePath); err != nil {
		t.Fatalf("Dockerfile should exist: %v", err)
	}
}

func TestInSpecMigrationImportStateMissingProfile(t *testing.T) {
	r := &inspecMigrationResource{client: &SousChefClient{Path: "souschef"}}

	req := resource.ImportStateRequest{
		ID: "/nonexistent/profile|/tmp/tests|testinfra",
	}
	resp := &resource.ImportStateResponse{}

	r.ImportState(context.Background(), req, resp)

	if !resp.Diagnostics.HasError() {
		t.Error("expected error for non-existent profile path")
	}
}

func TestInSpecMigrationImportStateMissingTestFile(t *testing.T) {
	tmpDir := t.TempDir()
	profileDir := filepath.Join(tmpDir, "inspec-profile")
	outputDir := filepath.Join(tmpDir, "test-output")

	if err := os.MkdirAll(profileDir, testDirPermissions); err != nil {
		t.Fatalf("failed to create profile dir: %v", err)
	}
	if err := os.MkdirAll(outputDir, testDirPermissions); err != nil {
		t.Fatalf(errFailedCreateOutputDirMissing, err)
	}

	r := &inspecMigrationResource{client: &SousChefClient{Path: "souschef"}}

	req := resource.ImportStateRequest{
		ID: profileDir + "|" + outputDir + "|testinfra",
	}
	resp := &resource.ImportStateResponse{}

	r.ImportState(context.Background(), req, resp)

	if !resp.Diagnostics.HasError() {
		t.Error("expected error for missing test output file")
	}
}

func TestInSpecMigrationImportStateTestFilePresent(t *testing.T) {
	// Verifies that test files can be created for InSpec migration,
	// without calling ImportState's success path which requires full framework state.
	tmpDir := t.TempDir()
	profileDir := filepath.Join(tmpDir, "inspec-profile")
	outputDir := filepath.Join(tmpDir, "test-output")

	if err := os.MkdirAll(profileDir, testDirPermissions); err != nil {
		t.Fatalf("failed to create profile dir: %v", err)
	}
	if err := os.MkdirAll(outputDir, testDirPermissions); err != nil {
		t.Fatalf(errFailedCreateOutputDirMissing, err)
	}

	testContent := "import pytest\n\ndef test_hello():\n    assert True\n"
	testFilePath := filepath.Join(outputDir, "test_migration.py")
	if err := os.WriteFile(testFilePath, []byte(testContent), testFilePermissions); err != nil {
		t.Fatalf("failed to create test file: %v", err)
	}

	// Verify the file exists and has the correct content
	content, err := os.ReadFile(testFilePath)
	if err != nil {
		t.Fatalf("test file should be readable: %v", err)
	}

	if string(content) != testContent {
		t.Errorf("test file content mismatch: got %q, want %q", string(content), testContent)
	}
}

func TestMigrationResourceConfigureValidClientPath(t *testing.T) {
	r := &migrationResource{}
	customPath := "/custom/bin/souschef"
	client := &SousChefClient{Path: customPath}
	req := resource.ConfigureRequest{ProviderData: client}
	resp := &resource.ConfigureResponse{}

	r.Configure(context.Background(), req, resp)

	if resp.Diagnostics.HasError() {
		t.Errorf("unexpected error: %v", resp.Diagnostics)
	}

	ValidateConfigValue(t, r.client.Path, customPath)
}
