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

const (
	expectedErrorDiagnostic = "expected error diagnostic"
	expectedTrue            = "expected true"
	unexpectedError         = "unexpected error: %v"
	permissionDenied        = "permission denied"
	expectedFalse           = "expected false"
	testFilePath            = "/test.txt"
	readState               = "Read State"
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
			t.Error(expectedErrorDiagnostic)
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
			t.Error(expectedTrue)
		}
		if diags.HasError() {
			t.Errorf(unexpectedError, diags)
		}
	})

	t.Run("mkdir fails", func(t *testing.T) {
		withOsMkdirAll(t, func(string, os.FileMode) error {
			return errors.New(permissionDenied)
		})
		diags := &diag.Diagnostics{}
		result := createOutputDirectory("/test", diags)
		if result {
			t.Error(expectedFalse)
		}
		if !diags.HasError() {
			t.Error(expectedErrorDiagnostic)
		}
	})
}

func TestReadGeneratedFile(t *testing.T) {
	t.Run("success", func(t *testing.T) {
		withOsReadFile(t, func(string) ([]byte, error) {
			return []byte("test content"), nil
		})
		diags := &diag.Diagnostics{}
		result := readGeneratedFile(testFilePath, "Test Read", diags)
		if result != "test content" {
			t.Errorf("expected 'test content', got '%s'", result)
		}
		if diags.HasError() {
			t.Errorf(unexpectedError, diags)
		}
	})

	t.Run("read error", func(t *testing.T) {
		withOsReadFile(t, func(string) ([]byte, error) {
			return nil, errors.New("file not found")
		})
		diags := &diag.Diagnostics{}
		result := readGeneratedFile(testFilePath, "Test Read", diags)
		if result != "" {
			t.Errorf("expected empty string, got '%s'", result)
		}
		if !diags.HasError() {
			t.Error(expectedErrorDiagnostic)
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
			t.Errorf(unexpectedError, diags)
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
			t.Error(expectedErrorDiagnostic)
		}
	})
}

func TestDeleteGeneratedFile(t *testing.T) {
	t.Run("success", func(t *testing.T) {
		withOsRemove(t, func(string) error {
			return nil
		})
		diags := &diag.Diagnostics{}
		deleteGeneratedFile(testFilePath, "playbook", diags)
		if diags.HasError() {
			t.Errorf(unexpectedError, diags)
		}
	})

	t.Run("file not found (should warn)", func(t *testing.T) {
		withOsRemove(t, func(string) error {
			return os.ErrNotExist
		})
		diags := &diag.Diagnostics{}
		deleteGeneratedFile(testFilePath, "playbook", diags)
		// Should not error for non-existent file
		if diags.HasError() {
			t.Errorf(unexpectedError, diags)
		}
	})

	t.Run("delete error (should warn)", func(t *testing.T) {
		withOsRemove(t, func(string) error {
			return errors.New("permission denied")
		})
		diags := &diag.Diagnostics{}
		deleteGeneratedFile(testFilePath, "playbook", diags)
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
		result := checkFileExists(testFilePath, "playbook", diags)
		if !result {
			t.Error(expectedTrue)
		}
		if diags.HasError() {
			t.Errorf(unexpectedError, diags)
		}
	})

	t.Run("file not found", func(t *testing.T) {
		withOsStat(t, func(string) (os.FileInfo, error) {
			return nil, os.ErrNotExist
		})
		diags := &diag.Diagnostics{}
		result := checkFileExists(testFilePath, "playbook", diags)
		if result {
			t.Error(expectedFalse)
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
		result := checkFileExists(testFilePath, "playbook", diags)
		// Non-NotExist errors are treated as file exists (function only checks IsNotExist)
		if !result {
			t.Error("expected true for non-NotExist error")
		}
	})
}

func readFileAndSetStateTestHelper(t *testing.T, statError error, readError error, expectRemove bool) (bool, *diag.Diagnostics) {
	t.Helper()
	withOsStat(t, func(string) (os.FileInfo, error) {
		return nil, statError
	})
	if readError == nil {
		withOsReadFile(t, func(string) ([]byte, error) {
			return []byte("state content"), nil
		})
	} else {
		withOsReadFile(t, func(string) ([]byte, error) {
			return nil, readError
		})
	}
	diags := &diag.Diagnostics{}
	contentSet := false
	removeResourceCalled := false
	result := readFileAndSetState(
		context.Background(),
		testFilePath,
		"unused",
		func(content string) {
			if statError != nil || readError != nil {
				t.Error("should not set content on error")
			} else {
				contentSet = true
				if content != "state content" {
					t.Errorf("expected 'state content', got '%s'", content)
				}
			}
		},
		readState,
		diags,
		func(ctx context.Context) {
			removeResourceCalled = true
		},
	)
	if statError == nil && readError == nil {
		if !result {
			t.Error(expectedTrue)
		}
		if !contentSet {
			t.Error("expected content to be set")
		}
		if diags.HasError() {
			t.Errorf(unexpectedError, diags)
		}
	} else if statError == os.ErrNotExist {
		if result {
			t.Error(expectedFalse)
		}
		if !removeResourceCalled {
			t.Error("expected removeResource to be called")
		}
	} else if readError != nil {
		if result {
			t.Error(expectedFalse)
		}
		if !diags.HasError() {
			t.Error(expectedErrorDiagnostic)
		}
	}
	return result, diags
}

func TestReadFileAndSetState(t *testing.T) {
	t.Run("file exists and is read successfully", func(t *testing.T) {
		readFileAndSetStateTestHelper(t, nil, nil, false)
	})

	t.Run("file not found (removes resource)", func(t *testing.T) {
		readFileAndSetStateTestHelper(t, os.ErrNotExist, nil, true)
	})

	t.Run("read fails", func(t *testing.T) {
		readFileAndSetStateTestHelper(t, nil, errors.New("read error"), false)
	})
}

func verifyStringSliceResult(t *testing.T, result, expected []string) {
	t.Helper()
	if len(result) != len(expected) {
		t.Errorf("expected length %d, got %d", len(expected), len(result))
		return
	}
	for i, v := range result {
		if v != expected[i] {
			t.Errorf("index %d: expected '%s', got '%s'", i, expected[i], v)
		}
	}
}

func TestStringSliceFromTypesList(t *testing.T) {
	tests := []struct {
		name     string
		input    []types.String
		expected []string
	}{
		{
			name:     "empty list",
			input:    []types.String{},
			expected: []string{},
		},
		{
			name:     "single value",
			input:    []types.String{types.StringValue("test")},
			expected: []string{"test"},
		},
		{
			name: "multiple values",
			input: []types.String{
				types.StringValue("recipe1"),
				types.StringValue("recipe2"),
				types.StringValue("recipe3"),
			},
			expected: []string{"recipe1", "recipe2", "recipe3"},
		},
		{
			name:     "null values",
			input:    []types.String{types.StringNull()},
			expected: []string{""},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := stringSliceFromTypesList(tt.input)
			verifyStringSliceResult(t, result, tt.expected)
		})
	}
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
