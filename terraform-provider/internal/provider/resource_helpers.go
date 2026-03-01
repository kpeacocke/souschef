// Package provider contains common helper functions for Terraform resources
package provider

import (
	"context"
	"fmt"
	"os"

	"github.com/hashicorp/terraform-plugin-framework/diag"
	"github.com/hashicorp/terraform-plugin-framework/resource"
	"github.com/hashicorp/terraform-plugin-framework/types"
)

// configureResource is a common helper for resource Configure methods.
// It extracts the SousChefClient from ProviderData and returns it,
// or adds an error diagnostic if the type is unexpected.
func configureResource(req resource.ConfigureRequest, resp *resource.ConfigureResponse) *SousChefClient {
	if req.ProviderData == nil {
		return nil
	}

	client, ok := req.ProviderData.(*SousChefClient)
	if !ok {
		resp.Diagnostics.AddError(
			"Unexpected Resource Configure Type",
			fmt.Sprintf("Expected *SousChefClient, got: %T", req.ProviderData),
		)
		return nil
	}

	return client
}

// createOutputDirectory creates a directory with the specified permissions.
// Adds an error diagnostic on failure and returns false if there was an error.
func createOutputDirectory(outputPath string, diagnostics *diag.Diagnostics) bool {
	if err := osMkdirAll(outputPath, 0755); err != nil {
		diagnostics.AddError(
			"Error creating output directory",
			fmt.Sprintf("Could not create directory %s: %s", outputPath, err),
		)
		return false
	}
	return true
}

// readGeneratedFile reads a file and returns its content as a string.
// Adds an error diagnostic on failure and returns empty string.
func readGeneratedFile(filePath, errorTitle string, diagnostics *diag.Diagnostics) string {
	content, err := osReadFile(filePath)
	if err != nil {
		diagnostics.AddError(
			errorTitle,
			fmt.Sprintf("Could not read file %s: %s", filePath, err),
		)
		return ""
	}
	return string(content)
}

// executeSousChefCommand runs a souschef CLI command and returns the output.
// Adds an error diagnostic on failure and returns false.
func executeSousChefCommand(
	ctx context.Context,
	clientPath string,
	args []string,
	errorTitle string,
	diagnostics *diag.Diagnostics,
) ([]byte, bool) {
	cmd := execCommandContext(ctx, clientPath, args...)
	output, err := cmd.CombinedOutput()
	if err != nil {
		diagnostics.AddError(
			errorTitle,
			fmt.Sprintf("Command failed: %s\nOutput: %s", err, string(output)),
		)
		return output, false
	}
	return output, true
}

// deleteGeneratedFile deletes a file and adds a warning if deletion fails
// (but not if the file doesn't exist).
func deleteGeneratedFile(filePath, fileType string, diagnostics *diag.Diagnostics) {
	if err := osRemove(filePath); err != nil && !os.IsNotExist(err) {
		diagnostics.AddWarning(
			fmt.Sprintf("Error deleting %s", fileType),
			fmt.Sprintf("Could not delete file %s: %s", filePath, err),
		)
	}
}

// checkFileExists checks if a file exists and returns whether it exists.
// If it doesn't exist, adds an error diagnostic and returns false.
func checkFileExists(filePath, fileType string, diagnostics *diag.Diagnostics) bool {
	if _, err := osStat(filePath); os.IsNotExist(err) {
		diagnostics.AddError(
			fmt.Sprintf("%s not found", fileType),
			fmt.Sprintf("%s does not exist: %s", fileType, filePath),
		)
		return false
	}
	return true
}

// readFileAndSetState is a helper for Read operations that reads a file,
// checks if it exists, and updates a types.String attribute in the model.
// Returns true if successful, false otherwise.
func readFileAndSetState(
	ctx context.Context,
	filePath string,
	fieldName string,
	contentSetter func(string),
	errorTitle string,
	diagnostics *diag.Diagnostics,
	removeResource func(context.Context),
) bool {
	// Check if file exists
	if _, err := osStat(filePath); os.IsNotExist(err) {
		removeResource(ctx)
		return false
	}

	// Read file content
	content := readGeneratedFile(filePath, errorTitle, diagnostics)
	if diagnostics.HasError() {
		return false
	}

	// Update the content field
	contentSetter(content)
	return true
}

// stringSliceFromTypesList converts []types.String to []string.
func stringSliceFromTypesList(typesList []types.String) []string {
	result := make([]string, len(typesList))
	for i, v := range typesList {
		result[i] = v.ValueString()
	}
	return result
}

// setStateAttributes is a helper for ImportState that sets multiple attributes.
// It appends all diagnostics from setting attributes.
func setStateAttributes(
	ctx context.Context,
	stateSetAttr func(context.Context, interface{}, interface{}) diag.Diagnostics,
	attributes map[interface{}]interface{},
	diagnostics *diag.Diagnostics,
) {
	for path, value := range attributes {
		diagnostics.Append(stateSetAttr(ctx, path, value)...)
	}
}
