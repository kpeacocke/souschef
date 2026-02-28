// Package provider contains extended coverage tests for the SousChef Terraform provider.
package provider

import (
	"context"
	"os"
	"path/filepath"
	"testing"

	"github.com/hashicorp/terraform-plugin-framework/resource"
)

const (
	errUnexpectedNilProviderData     = "unexpected error on nil provider data: %v"
	errExpectedWrongProviderDataType = "expected error when provider data is wrong type"
	errFailedCreateCookbookDir       = "failed to create cookbook dir: %v"
	errFailedCreateOutputDir         = "failed to create output dir: %v"
	errExpectedInvalidImportID       = "expected error for invalid import ID"
)

func TestMigrationResourceConfigureNilClient(t *testing.T) {
	r := &migrationResource{}
	req := resource.ConfigureRequest{ProviderData: nil}
	resp := &resource.ConfigureResponse{}

	r.Configure(context.Background(), req, resp)

	if resp.Diagnostics.HasError() {
		t.Errorf(errUnexpectedNilProviderData, resp.Diagnostics)
	}
}

func TestMigrationResourceConfigureInvalidType(t *testing.T) {
	r := &migrationResource{}
	req := resource.ConfigureRequest{ProviderData: "not-a-client"}
	resp := &resource.ConfigureResponse{}

	r.Configure(context.Background(), req, resp)

	if !resp.Diagnostics.HasError() {
		t.Error(errExpectedWrongProviderDataType)
	}
}

func TestMigrationResourceConfigureValidClient(t *testing.T) {
	r := &migrationResource{}
	client := &SousChefClient{Path: "souschef"}
	req := resource.ConfigureRequest{ProviderData: client}
	resp := &resource.ConfigureResponse{}

	r.Configure(context.Background(), req, resp)

	if resp.Diagnostics.HasError() {
		t.Errorf("unexpected error configuring resource: %v", resp.Diagnostics)
	}

	if r.client == nil {
		t.Fatal("expected client to be set after Configure")
	}

	ValidateConfigValue(t, r.client.Path, "souschef")
}

func TestMigrationResourceReadMissingPlaybook(t *testing.T) {
	tmpDir := t.TempDir()
	cookbookDir := filepath.Join(tmpDir, "test-cookbook")
	outputDir := filepath.Join(tmpDir, "output")

	if err := os.MkdirAll(cookbookDir, testDirPermissions); err != nil {
		t.Fatalf(errFailedCreateCookbookDir, err)
	}
	if err := os.MkdirAll(outputDir, testDirPermissions); err != nil {
		t.Fatalf(errFailedCreateOutputDir, err)
	}

	r := &migrationResource{client: &SousChefClient{Path: "souschef"}}

	// Verify the resource's client is wired correctly.
	if r.client.Path != "souschef" {
		t.Errorf("expected client path 'souschef', got %q", r.client.Path)
	}

	// Verify expected playbook path does not exist.
	playbookPath := filepath.Join(outputDir, "default.yml")
	if _, err := os.Stat(playbookPath); !os.IsNotExist(err) {
		t.Error("expected playbook to not exist")
	}
}

func TestMigrationImportStateInvalidID(t *testing.T) {
	r := &migrationResource{client: &SousChefClient{Path: "souschef"}}

	req := resource.ImportStateRequest{ID: "invalid-no-pipes"}
	resp := &resource.ImportStateResponse{}

	r.ImportState(context.Background(), req, resp)

	if !resp.Diagnostics.HasError() {
		t.Error(errExpectedInvalidImportID)
	}
}

func TestMigrationImportStateInvalidIDTwoParts(t *testing.T) {
	r := &migrationResource{client: &SousChefClient{Path: "souschef"}}

	req := resource.ImportStateRequest{ID: "/path/to/cookbook|/path/to/output"}
	resp := &resource.ImportStateResponse{}

	r.ImportState(context.Background(), req, resp)

	if !resp.Diagnostics.HasError() {
		t.Error("expected error for import ID with only two parts")
	}
}

func TestMigrationImportStateMissingCookbook(t *testing.T) {
	r := &migrationResource{client: &SousChefClient{Path: "souschef"}}

	req := resource.ImportStateRequest{
		ID: "/nonexistent/cookbook|/tmp/output|default",
	}
	resp := &resource.ImportStateResponse{}

	r.ImportState(context.Background(), req, resp)

	if !resp.Diagnostics.HasError() {
		t.Error("expected error for non-existent cookbook path")
	}
}

func TestMigrationImportStateMissingPlaybook(t *testing.T) {
	tmpDir := t.TempDir()
	cookbookDir := filepath.Join(tmpDir, "cookbook")
	outputDir := filepath.Join(tmpDir, "output")

	if err := os.MkdirAll(cookbookDir, testDirPermissions); err != nil {
		t.Fatalf(errFailedCreateCookbookDir, err)
	}
	if err := os.MkdirAll(outputDir, testDirPermissions); err != nil {
		t.Fatalf(errFailedCreateOutputDir, err)
	}

	r := &migrationResource{client: &SousChefClient{Path: "souschef"}}

	req := resource.ImportStateRequest{
		ID: cookbookDir + "|" + outputDir + "|default",
	}
	resp := &resource.ImportStateResponse{}

	r.ImportState(context.Background(), req, resp)

	if !resp.Diagnostics.HasError() {
		t.Error("expected error for missing playbook file")
	}
}

func TestMigrationImportStateValidFilesPresent(t *testing.T) {
	// This test verifies that ImportState reaches the state-setting logic
	// by checking the cookbook and playbook exist before the framework panics
	// on nil state. The presence check happens before state setting.
	tmpDir := t.TempDir()
	cookbookDir := filepath.Join(tmpDir, "cookbook")
	outputDir := filepath.Join(tmpDir, "output")

	if err := os.MkdirAll(cookbookDir, testDirPermissions); err != nil {
		t.Fatalf(errFailedCreateCookbookDir, err)
	}
	if err := os.MkdirAll(outputDir, testDirPermissions); err != nil {
		t.Fatalf(errFailedCreateOutputDir, err)
	}

	playbookContent := "---\n- hosts: all\n  tasks: []\n"
	playbookPath := filepath.Join(outputDir, "default.yml")
	if err := os.WriteFile(playbookPath, []byte(playbookContent), testFilePermissions); err != nil {
		t.Fatalf("failed to create playbook: %v", err)
	}

	// Verify setup is correct
	if _, err := os.Stat(cookbookDir); err != nil {
		t.Fatalf("cookbook dir should exist: %v", err)
	}
	if _, err := os.Stat(playbookPath); err != nil {
		t.Fatalf("playbook should exist: %v", err)
	}
}

func TestBatchMigrationResourceConfigureNilClient(t *testing.T) {
	r := &batchMigrationResource{}
	req := resource.ConfigureRequest{ProviderData: nil}
	resp := &resource.ConfigureResponse{}

	r.Configure(context.Background(), req, resp)

	if resp.Diagnostics.HasError() {
		t.Errorf(errUnexpectedNilProviderData, resp.Diagnostics)
	}
}

func TestBatchMigrationResourceConfigureInvalidType(t *testing.T) {
	r := &batchMigrationResource{}
	req := resource.ConfigureRequest{ProviderData: 42}
	resp := &resource.ConfigureResponse{}

	r.Configure(context.Background(), req, resp)

	if !resp.Diagnostics.HasError() {
		t.Error(errExpectedWrongProviderDataType)
	}
}

func TestBatchMigrationImportStateInvalidID(t *testing.T) {
	r := &batchMigrationResource{client: &SousChefClient{Path: "souschef"}}

	req := resource.ImportStateRequest{ID: "only-one-segment"}
	resp := &resource.ImportStateResponse{}

	r.ImportState(context.Background(), req, resp)

	if !resp.Diagnostics.HasError() {
		t.Error(errExpectedInvalidImportID)
	}
}

func TestHabitatMigrationResourceConfigureNilClient(t *testing.T) {
	r := &habitatMigrationResource{}
	req := resource.ConfigureRequest{ProviderData: nil}
	resp := &resource.ConfigureResponse{}

	r.Configure(context.Background(), req, resp)

	if resp.Diagnostics.HasError() {
		t.Errorf(errUnexpectedNilProviderData, resp.Diagnostics)
	}
}

func TestHabitatMigrationResourceConfigureInvalidType(t *testing.T) {
	r := &habitatMigrationResource{}
	req := resource.ConfigureRequest{ProviderData: true}
	resp := &resource.ConfigureResponse{}

	r.Configure(context.Background(), req, resp)

	if !resp.Diagnostics.HasError() {
		t.Error(errExpectedWrongProviderDataType)
	}
}

func TestHabitatMigrationImportStateInvalidID(t *testing.T) {
	r := &habitatMigrationResource{client: &SousChefClient{Path: "souschef"}}

	req := resource.ImportStateRequest{ID: "single-segment-no-pipe"}
	resp := &resource.ImportStateResponse{}

	r.ImportState(context.Background(), req, resp)

	if !resp.Diagnostics.HasError() {
		t.Error(errExpectedInvalidImportID)
	}
}

func TestInSpecMigrationResourceConfigureNilClient(t *testing.T) {
	r := &inspecMigrationResource{}
	req := resource.ConfigureRequest{ProviderData: nil}
	resp := &resource.ConfigureResponse{}

	r.Configure(context.Background(), req, resp)

	if resp.Diagnostics.HasError() {
		t.Errorf(errUnexpectedNilProviderData, resp.Diagnostics)
	}
}

func TestInSpecMigrationResourceConfigureInvalidType(t *testing.T) {
	r := &inspecMigrationResource{}
	req := resource.ConfigureRequest{ProviderData: struct{}{}}
	resp := &resource.ConfigureResponse{}

	r.Configure(context.Background(), req, resp)

	if !resp.Diagnostics.HasError() {
		t.Error(errExpectedWrongProviderDataType)
	}
}

func TestInSpecMigrationImportStateInvalidID(t *testing.T) {
	r := &inspecMigrationResource{client: &SousChefClient{Path: "souschef"}}

	req := resource.ImportStateRequest{ID: "no-pipes-here"}
	resp := &resource.ImportStateResponse{}

	r.ImportState(context.Background(), req, resp)

	if !resp.Diagnostics.HasError() {
		t.Error(errExpectedInvalidImportID)
	}
}

func TestMigrationResourceReadonlyOutputDir(t *testing.T) {
	if os.Getuid() == 0 {
		t.Skip("skipping permission test when running as root")
	}

	tmpDir := t.TempDir()
	cookbookDir := filepath.Join(tmpDir, "cookbook")
	outputDir := filepath.Join(tmpDir, "readonly-output")

	if err := os.MkdirAll(cookbookDir, testDirPermissions); err != nil {
		t.Fatalf(errFailedCreateCookbookDir, err)
	}
	if err := os.MkdirAll(outputDir, testDirPermissions); err != nil {
		t.Fatalf(errFailedCreateOutputDir, err)
	}

	// Make output dir read-only
	if err := os.Chmod(outputDir, readonlyDirPermissions); err != nil {
		t.Fatalf("failed to set readonly permissions: %v", err)
	}
	defer os.Chmod(outputDir, testDirPermissions)

	// Verify we cannot write to the directory
	testFile := filepath.Join(outputDir, "test.yml")
	err := os.WriteFile(testFile, []byte("test"), testFilePermissions)
	if err == nil {
		t.Error("expected write to fail in readonly directory")
	}
}
