package provider

import (
	"context"
	"errors"
	"os"
	"os/exec"
	"testing"

	"github.com/hashicorp/terraform-plugin-framework/diag"
	"github.com/hashicorp/terraform-plugin-framework/resource"
	"github.com/hashicorp/terraform-plugin-framework/types"
)

func TestConfigureResource(t *testing.T) {
	t.Run("with nil provider data", func(t *testing.T) {
		req := resource.ConfigureRequest{ProviderData: nil}
		resp := &resource.ConfigureResponse{}
		result := configureResource(req, resp)
		if result != nil {
			t.Errorf("expected nil, got %v", result)
		}
	})

	t.Run("with valid client", func(t *testing.T) {
		client := &SousChefClient{Path: "/test"}
		req := resource.ConfigureRequest{ProviderData: client}
		resp := &resource.ConfigureResponse{}
		result := configureResource(req, resp)
		if result != client {
			t.Errorf("expected %v, got %v", client, result)
		}
		if resp.Diagnostics.HasError() {
			t.Errorf("unexpected diagnostics: %v", resp.Diagnostics)
		}
	})

	t.Run("with unexpected type", func(t *testing.T) {
		req := resource.ConfigureRequest{ProviderData: "invalid"}
		resp := &resource.ConfigureResponse{}
		result := configureResource(req, resp)
		if result != nil {
			t.Errorf("expected nil, got %v", result)
		}
		if !resp.Diagnostics.HasError() {
			t.Error("expected error diagnostic")
		}
	})
}

func TestCreateOutputDirectory(t *testing.T) {
	t.Run("success", func(t *testing.T) {
		withOsMkdirAll(t, func(string, os.FileMode) error {
			return nil
		})
		diags := &diag.Diagnostics{}
		result := createOutputDirectory("/test", diags)
		if !result {
			t.Error("expected true")
		}
		if diags.HasError() {
			t.Errorf("unexpected error: %v", diags)
		}
	})

	t.Run("mkdir fails", func(t *testing.T) {
		withOsMkdirAll(t, func(string, os.FileMode) error {
			return errors.New("permission denied")
		})
		diags := &diag.Diagnostics{}
		result := createOutputDirectory("/test", diags)
		if result {
			t.Error("expected false")
		}
		if !diags.HasError() {
			t.Error("expected error diagnostic")
		}
	})
}

func TestReadGeneratedFile(t *testing.T) {
	t.Run("success", func(t *testing.T) {
		withOsReadFile(t, func(string) ([]byte, error) {
			return []byte("test content"), nil
		})
		diags := &diag.Diagnostics{}
		result := readGeneratedFile("/test.txt", "Test Read", diags)
		if result != "test content" {
			t.Errorf("expected 'test content', got '%s'", result)
		}
		if diags.HasError() {
			t.Errorf("unexpected error: %v", diags)
		}
	})

	t.Run("read error", func(t *testing.T) {
		withOsReadFile(t, func(string) ([]byte, error) {
			return nil, errors.New("file not found")
		})
		diags := &diag.Diagnostics{}
		result := readGeneratedFile("/test.txt", "Test Read", diags)
		if result != "" {
			t.Errorf("expected empty string, got '%s'", result)
		}
		if !diags.HasError() {
			t.Error("expected error diagnostic")
		}
	})
}

func TestExecuteSousChefCommand(t *testing.T) {
	t.Run("success", func(t *testing.T) {
		withExecCommandContext(t, func(ctx context.Context, name string, args ...string) *exec.Cmd {
			cmd := exec.Command("echo", "test output")
			return cmd
		})
		diags := &diag.Diagnostics{}
		output, success := executeSousChefCommand(context.Background(), "/souschef", []string{"test"}, "Test Command", diags)
		if !success {
			t.Error("expected success")
		}
		if len(output) == 0 {
			t.Error("expected output")
		}
		if diags.HasError() {
			t.Errorf("unexpected error: %v", diags)
		}
	})

	t.Run("command failure", func(t *testing.T) {
		withExecCommandContext(t, func(ctx context.Context, name string, args ...string) *exec.Cmd {
			cmd := exec.Command("false")
			return cmd
		})
		diags := &diag.Diagnostics{}
		_, success := executeSousChefCommand(context.Background(), "/souschef", []string{"test"}, "Test Command", diags)
		if success {
			t.Error("expected failure")
		}
		if !diags.HasError() {
			t.Error("expected error diagnostic")
		}
	})
}

func TestDeleteGeneratedFile(t *testing.T) {
	t.Run("success", func(t *testing.T) {
		withOsRemove(t, func(string) error {
			return nil
		})
		diags := &diag.Diagnostics{}
		deleteGeneratedFile("/test.txt", "playbook", diags)
		if diags.HasError() {
			t.Errorf("unexpected error: %v", diags)
		}
	})

	t.Run("file not found (should warn)", func(t *testing.T) {
		withOsRemove(t, func(string) error {
			return os.ErrNotExist
		})
		diags := &diag.Diagnostics{}
		deleteGeneratedFile("/test.txt", "playbook", diags)
		// Should not error for non-existent file
		if diags.HasError() {
			t.Errorf("unexpected error: %v", diags)
		}
	})

	t.Run("delete error (should warn)", func(t *testing.T) {
		withOsRemove(t, func(string) error {
			return errors.New("permission denied")
		})
		diags := &diag.Diagnostics{}
		deleteGeneratedFile("/test.txt", "playbook", diags)
		// Check that a warning was added (warnings > 0)
		foundWarning := false
		for _, d := range *diags {
			if d.Severity() == diag.SeverityWarning {
				foundWarning = true
				break
			}
		}
		if !foundWarning {
			t.Error("expected warning diagnostic")
		}
	})
}

func TestCheckFileExists(t *testing.T) {
	t.Run("file exists", func(t *testing.T) {
		withOsStat(t, func(string) (os.FileInfo, error) {
			return nil, nil
		})
		diags := &diag.Diagnostics{}
		result := checkFileExists("/test.txt", "playbook", diags)
		if !result {
			t.Error("expected true")
		}
		if diags.HasError() {
			t.Errorf("unexpected error: %v", diags)
		}
	})

	t.Run("file not found", func(t *testing.T) {
		withOsStat(t, func(string) (os.FileInfo, error) {
			return nil, os.ErrNotExist
		})
		diags := &diag.Diagnostics{}
		result := checkFileExists("/test.txt", "playbook", diags)
		if result {
			t.Error("expected false")
		}
		if !diags.HasError() {
			t.Error("expected error diagnostic")
		}
	})

	t.Run("other stat error (returns true)", func(t *testing.T) {
		withOsStat(t, func(string) (os.FileInfo, error) {
			return nil, errors.New("permission denied")
		})
		diags := &diag.Diagnostics{}
		result := checkFileExists("/test.txt", "playbook", diags)
		// Non-NotExist errors are treated as file exists (function only checks IsNotExist)
		if !result {
			t.Error("expected true for non-NotExist error")
		}
	})
}

func TestReadFileAndSetState(t *testing.T) {
	t.Run("file exists and is read successfully", func(t *testing.T) {
		withOsStat(t, func(string) (os.FileInfo, error) {
			return nil, nil
		})
		withOsReadFile(t, func(string) ([]byte, error) {
			return []byte("state content"), nil
		})
		diags := &diag.Diagnostics{}
		contentSet := false
		result := readFileAndSetState(
			context.Background(),
			"/test.txt",
			"unused",
			func(content string) {
				contentSet = true
				if content != "state content" {
					t.Errorf("expected 'state content', got '%s'", content)
				}
			},
			"Read State",
			diags,
			func(ctx context.Context) {
				t.Error("should not remove resource")
			},
		)
		if !result {
			t.Error("expected true")
		}
		if !contentSet {
			t.Error("expected content to be set")
		}
		if diags.HasError() {
			t.Errorf("unexpected error: %v", diags)
		}
	})

	t.Run("file not found (removes resource)", func(t *testing.T) {
		withOsStat(t, func(string) (os.FileInfo, error) {
			return nil, os.ErrNotExist
		})
		diags := &diag.Diagnostics{}
		removeResourceCalled := false
		result := readFileAndSetState(
			context.Background(),
			"/test.txt",
			"unused",
			func(content string) {
				t.Error("should not set content")
			},
			"Read State",
			diags,
			func(ctx context.Context) {
				removeResourceCalled = true
			},
		)
		if result {
			t.Error("expected false")
		}
		if !removeResourceCalled {
			t.Error("expected removeResource to be called")
		}
	})

	t.Run("read fails", func(t *testing.T) {
		withOsStat(t, func(string) (os.FileInfo, error) {
			return nil, nil
		})
		withOsReadFile(t, func(string) ([]byte, error) {
			return nil, errors.New("read error")
		})
		diags := &diag.Diagnostics{}
		result := readFileAndSetState(
			context.Background(),
			"/test.txt",
			"unused",
			func(content string) {
				t.Error("should not set content on error")
			},
			"Read State",
			diags,
			func(ctx context.Context) {
				t.Error("should not remove resource when read fails")
			},
		)
		if result {
			t.Error("expected false")
		}
		if !diags.HasError() {
			t.Error("expected error diagnostic")
		}
	})
}

func TestStringSliceFromTypesList(t *testing.T) {
	t.Run("empty list", func(t *testing.T) {
		result := stringSliceFromTypesList([]types.String{})
		if len(result) != 0 {
			t.Errorf("expected empty slice, got %v", result)
		}
	})

	t.Run("single value", func(t *testing.T) {
		input := []types.String{types.StringValue("test")}
		result := stringSliceFromTypesList(input)
		if len(result) != 1 || result[0] != "test" {
			t.Errorf("expected ['test'], got %v", result)
		}
	})

	t.Run("multiple values", func(t *testing.T) {
		input := []types.String{
			types.StringValue("recipe1"),
			types.StringValue("recipe2"),
			types.StringValue("recipe3"),
		}
		result := stringSliceFromTypesList(input)
		if len(result) != 3 {
			t.Errorf("expected length 3, got %d", len(result))
		}
		expected := []string{"recipe1", "recipe2", "recipe3"}
		for i, v := range result {
			if v != expected[i] {
				t.Errorf("index %d: expected '%s', got '%s'", i, expected[i], v)
			}
		}
	})

	t.Run("null values", func(t *testing.T) {
		input := []types.String{types.StringNull()}
		result := stringSliceFromTypesList(input)
		if len(result) != 1 {
			t.Errorf("expected length 1, got %d", len(result))
		}
		// Null values should convert to empty strings
		if result[0] != "" {
			t.Errorf("expected empty string for null, got '%s'", result[0])
		}
	})
}

// Helper functions to manage dependency injection in tests

func withOsMkdirAll(t *testing.T, fn func(string, os.FileMode) error) {
	t.Helper()
	original := osMkdirAll
	osMkdirAll = fn
	t.Cleanup(func() {
		osMkdirAll = original
	})
}

func withOsStat(t *testing.T, fn func(string) (os.FileInfo, error)) {
	t.Helper()
	original := osStat
	osStat = fn
	t.Cleanup(func() {
		osStat = original
	})
}

func withExecCommandContext(t *testing.T, fn func(context.Context, string, ...string) *exec.Cmd) {
	t.Helper()
	original := execCommandContext
	execCommandContext = fn
	t.Cleanup(func() {
		execCommandContext = original
	})
}
