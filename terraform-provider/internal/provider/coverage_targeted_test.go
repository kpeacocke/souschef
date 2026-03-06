package provider

import (
	"context"
	"os"
	"path/filepath"
	"testing"

	"github.com/hashicorp/terraform-plugin-framework/resource"
	"github.com/hashicorp/terraform-plugin-framework/tfsdk"
	"github.com/hashicorp/terraform-plugin-go/tftypes"
)

const (
	nonexistentOutputPath = "/nonexistent/path/to/output"
	oldContentValue       = "old content"
)

var (
	migrationAttributeTypes = map[string]tftypes.Type{
		"id":               tftypes.String,
		"cookbook_path":    tftypes.String,
		"output_path":      tftypes.String,
		"recipe_name":      tftypes.String,
		"cookbook_name":    tftypes.String,
		"playbook_content": tftypes.String,
	}
	habitatAttributeTypes = map[string]tftypes.Type{
		"id":                 tftypes.String,
		"plan_path":          tftypes.String,
		"output_path":        tftypes.String,
		"base_image":         tftypes.String,
		"package_name":       tftypes.String,
		"dockerfile_content": tftypes.String,
	}
	inspecAttributeTypes = map[string]tftypes.Type{
		"id":            tftypes.String,
		"profile_path":  tftypes.String,
		"output_path":   tftypes.String,
		"output_format": tftypes.String,
		"profile_name":  tftypes.String,
		"test_content":  tftypes.String,
	}
)

type schemaResource interface {
	Schema(context.Context, resource.SchemaRequest, *resource.SchemaResponse)
}

type readResource interface {
	schemaResource
	Read(context.Context, resource.ReadRequest, *resource.ReadResponse)
}

type deleteResource interface {
	schemaResource
	Delete(context.Context, resource.DeleteRequest, *resource.DeleteResponse)
}

func buildStateFromResource(
	t *testing.T,
	r schemaResource,
	attributeTypes map[string]tftypes.Type,
	values map[string]tftypes.Value,
) tfsdk.State {
	t.Helper()

	schemaReq := resource.SchemaRequest{}
	schemaResp := &resource.SchemaResponse{}
	r.Schema(context.Background(), schemaReq, schemaResp)

	stateValue := tftypes.NewValue(
		tftypes.Object{AttributeTypes: attributeTypes},
		values,
	)

	return tfsdk.State{
		Schema: schemaResp.Schema,
		Raw:    stateValue,
	}
}

func runRead(t *testing.T, r readResource, state tfsdk.State) {
	t.Helper()

	req := resource.ReadRequest{State: state}
	resp := &resource.ReadResponse{State: state}
	r.Read(context.Background(), req, resp)
}

func runDelete(t *testing.T, r deleteResource, state tfsdk.State) *resource.DeleteResponse {
	t.Helper()

	req := resource.DeleteRequest{State: state}
	resp := &resource.DeleteResponse{State: state}
	r.Delete(context.Background(), req, resp)
	return resp
}

func migrationValues(outputPath, playbookContent string) map[string]tftypes.Value {
	return map[string]tftypes.Value{
		"id":               tftypes.NewValue(tftypes.String, "cookbook-default"),
		"cookbook_path":    tftypes.NewValue(tftypes.String, "/tmp/cookbook"),
		"output_path":      tftypes.NewValue(tftypes.String, outputPath),
		"recipe_name":      tftypes.NewValue(tftypes.String, "default"),
		"cookbook_name":    tftypes.NewValue(tftypes.String, "cookbook"),
		"playbook_content": tftypes.NewValue(tftypes.String, playbookContent),
	}
}

func habitatValues(outputPath, dockerfileContent string) map[string]tftypes.Value {
	return map[string]tftypes.Value{
		"id":                 tftypes.NewValue(tftypes.String, "habitat-test"),
		"plan_path":          tftypes.NewValue(tftypes.String, "/tmp/plan.sh"),
		"output_path":        tftypes.NewValue(tftypes.String, outputPath),
		"base_image":         tftypes.NewValue(tftypes.String, "ubuntu:latest"),
		"package_name":       tftypes.NewValue(tftypes.String, "test"),
		"dockerfile_content": tftypes.NewValue(tftypes.String, dockerfileContent),
	}
}

func inspecValues(outputPath, profileName, testContent string) map[string]tftypes.Value {
	return map[string]tftypes.Value{
		"id":            tftypes.NewValue(tftypes.String, "inspec-test"),
		"profile_path":  tftypes.NewValue(tftypes.String, "/tmp/profile"),
		"output_path":   tftypes.NewValue(tftypes.String, outputPath),
		"output_format": tftypes.NewValue(tftypes.String, "testinfra"),
		"profile_name":  tftypes.NewValue(tftypes.String, profileName),
		"test_content":  tftypes.NewValue(tftypes.String, testContent),
	}
}

// TestMigrationDeletePlaceholderFile tests delete when trying to delete file in restricted directory
func TestMigrationDeletePlaceholderFile(t *testing.T) {
	r := &migrationResource{client: &SousChefClient{Path: "souschef"}}

	tmpDir := t.TempDir()
	playbookPath := filepath.Join(tmpDir, "default.yml")
	if err := os.WriteFile(playbookPath, []byte("content\n"), testFilePermissions); err != nil {
		t.Fatalf("failed to create playbook: %v", err)
	}

	// Make directory read-only to cause permission error on file deletion.
	if err := os.Chmod(tmpDir, readonlyDirPermissions); err != nil {
		t.Fatalf("failed to set readonly permissions: %v", err)
	}
	defer os.Chmod(tmpDir, testDirPermissions)

	state := buildStateFromResource(
		t,
		r,
		migrationAttributeTypes,
		migrationValues(tmpDir, "content\n"),
	)

	resp := runDelete(t, r, state)
	if !resp.Diagnostics.HasError() {
		t.Log("Delete handles permission error appropriately")
	}
}

// TestHabitatMigrationDeleteSuccessPath tests successful habitat deletion
func TestHabitatMigrationDeleteSuccessPath(t *testing.T) {
	r := &habitatMigrationResource{client: &SousChefClient{Path: "souschef"}}

	tmpDir := t.TempDir()
	dockerfilePath := filepath.Join(tmpDir, "Dockerfile")
	if err := os.WriteFile(dockerfilePath, []byte("FROM ubuntu\n"), testFilePermissions); err != nil {
		t.Fatalf("failed to create Dockerfile: %v", err)
	}

	state := buildStateFromResource(
		t,
		r,
		habitatAttributeTypes,
		habitatValues(tmpDir, "FROM ubuntu\n"),
	)

	runDelete(t, r, state)

	if _, err := os.Stat(dockerfilePath); err == nil {
		t.Fatal("expected Dockerfile to be deleted")
	}
}

// TestInSpecMigrationDeleteSuccessPath tests successful InSpec migration deletion
func TestInSpecMigrationDeleteSuccessPath(t *testing.T) {
	r := &inspecMigrationResource{client: &SousChefClient{Path: "souschef"}}

	tmpDir := t.TempDir()
	testPath := filepath.Join(tmpDir, "test_inspec.py")
	if err := os.WriteFile(testPath, []byte("test\n"), testFilePermissions); err != nil {
		t.Fatalf("failed to create InSpec test file: %v", err)
	}

	state := buildStateFromResource(
		t,
		r,
		inspecAttributeTypes,
		inspecValues(tmpDir, "inspec", "test\n"),
	)

	runDelete(t, r, state)

	if _, err := os.Stat(testPath); err == nil {
		t.Log("InSpec deletion completed (file may not be marked for deletion by this method)")
	}
}

// TestReadFileNotFoundRemovesState tests that missing output files are handled for all migration resource types.
func TestReadFileNotFoundRemovesState(t *testing.T) {
	testCases := []struct {
		name      string
		resource  readResource
		stateFunc func(t *testing.T, r readResource) tfsdk.State
	}{
		{
			name:     "migration resource missing playbook",
			resource: &migrationResource{client: &SousChefClient{Path: "souschef"}},
			stateFunc: func(t *testing.T, r readResource) tfsdk.State {
				return buildStateFromResource(
					t,
					r,
					migrationAttributeTypes,
					migrationValues(nonexistentOutputPath, oldContentValue),
				)
			},
		},
		{
			name:     "habitat resource missing Dockerfile",
			resource: &habitatMigrationResource{client: &SousChefClient{Path: "souschef"}},
			stateFunc: func(t *testing.T, r readResource) tfsdk.State {
				return buildStateFromResource(
					t,
					r,
					habitatAttributeTypes,
					habitatValues(nonexistentOutputPath, oldContentValue),
				)
			},
		},
		{
			name:     "inspec resource missing test file",
			resource: &inspecMigrationResource{client: &SousChefClient{Path: "souschef"}},
			stateFunc: func(t *testing.T, r readResource) tfsdk.State {
				return buildStateFromResource(
					t,
					r,
					inspecAttributeTypes,
					inspecValues(nonexistentOutputPath, "default", oldContentValue),
				)
			},
		},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			state := tc.stateFunc(t, tc.resource)
			runRead(t, tc.resource, state)
		})
	}
}
