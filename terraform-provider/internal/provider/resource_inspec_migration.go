// Package provider implements the SousChef Terraform provider resources
package provider

import (
	"context"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"

	"github.com/hashicorp/terraform-plugin-framework/path"
	"github.com/hashicorp/terraform-plugin-framework/resource"
	"github.com/hashicorp/terraform-plugin-framework/resource/schema"
	"github.com/hashicorp/terraform-plugin-framework/types"
)

// Ensure the implementation satisfies the expected interfaces
var (
	_ resource.Resource                = &inspecMigrationResource{}
	_ resource.ResourceWithImportState = &inspecMigrationResource{}
)

// NewInSpecMigrationResource creates a new InSpec migration resource
func NewInSpecMigrationResource() resource.Resource {
	return &inspecMigrationResource{}
}

// inspecMigrationResource is the resource implementation
type inspecMigrationResource struct {
	client *SousChefClient
}

// inspecMigrationResourceModel describes the resource data model
type inspecMigrationResourceModel struct {
	ID           types.String `tfsdk:"id"`
	ProfilePath  types.String `tfsdk:"profile_path"`
	OutputPath   types.String `tfsdk:"output_path"`
	OutputFormat types.String `tfsdk:"output_format"`
	ProfileName  types.String `tfsdk:"profile_name"`
	TestContent  types.String `tfsdk:"test_content"`
}

const (
	testinfraFilename   = "test_spec.py"
	serverspecFilename  = "spec_helper.rb"
	gossFilename        = "goss.yaml"
	ansibleFilename     = "assert.yml"
	defaultTestFilename = "test.txt"
	errReadingTestFile  = "Error reading test file"
	inspecIDFormat      = "inspec-%s-%s"
)

// Metadata returns the resource type name
func (r *inspecMigrationResource) Metadata(ctx context.Context, req resource.MetadataRequest, resp *resource.MetadataResponse) {
	resp.TypeName = req.ProviderTypeName + "_inspec_migration"
}

// Schema defines the schema for the resource
func (r *inspecMigrationResource) Schema(ctx context.Context, req resource.SchemaRequest, resp *resource.SchemaResponse) {
	resp.Schema = schema.Schema{
		MarkdownDescription: "Manages conversion of Chef InSpec profiles to various test frameworks.",

		Attributes: map[string]schema.Attribute{
			"id": schema.StringAttribute{
				Computed:            true,
				MarkdownDescription: "Unique identifier for the InSpec migration",
			},
			"profile_path": schema.StringAttribute{
				Required:            true,
				MarkdownDescription: "Path to the InSpec profile directory",
			},
			"output_path": schema.StringAttribute{
				Required:            true,
				MarkdownDescription: "Directory where converted tests will be written",
			},
			"output_format": schema.StringAttribute{
				Required:            true,
				MarkdownDescription: "Output test framework format (testinfra, serverspec, goss, or ansible)",
			},
			"profile_name": schema.StringAttribute{
				Computed:            true,
				MarkdownDescription: "Name of the InSpec profile",
			},
			"test_content": schema.StringAttribute{
				Computed:            true,
				MarkdownDescription: "Generated test content",
			},
		},
	}
}

// Configure adds the provider configured client to the resource
func (r *inspecMigrationResource) Configure(ctx context.Context, req resource.ConfigureRequest, resp *resource.ConfigureResponse) {
	if req.ProviderData == nil {
		return
	}

	client, ok := req.ProviderData.(*SousChefClient)
	if !ok {
		resp.Diagnostics.AddError(
			"Unexpected Resource Configure Type",
			fmt.Sprintf("Expected *SousChefClient, got: %T", req.ProviderData),
		)
		return
	}

	r.client = client
}

// Create creates the resource and sets the initial Terraform state
func (r *inspecMigrationResource) Create(ctx context.Context, req resource.CreateRequest, resp *resource.CreateResponse) {
	var plan inspecMigrationResourceModel
	diags := req.Plan.Get(ctx, &plan)
	resp.Diagnostics.Append(diags...)
	if resp.Diagnostics.HasError() {
		return
	}

	profilePath := plan.ProfilePath.ValueString()
	outputPath := plan.OutputPath.ValueString()
	outputFormat := plan.OutputFormat.ValueString()

	// Create output directory
	if err := os.MkdirAll(outputPath, 0755); err != nil {
		resp.Diagnostics.AddError(
			"Error creating output directory",
			fmt.Sprintf("Could not create directory %s: %s", outputPath, err),
		)
		return
	}

	// Call souschef CLI to convert InSpec profile
	cmd := exec.CommandContext(ctx, r.client.Path, "convert-inspec",
		"--profile-path", profilePath,
		"--output-path", outputPath,
		"--format", outputFormat)

	output, err := cmd.CombinedOutput()
	if err != nil {
		resp.Diagnostics.AddError(
			"Error converting InSpec profile",
			fmt.Sprintf("Could not convert profile: %s\nOutput: %s", err, string(output)),
		)
		return
	}

	// Determine output file extension based on format
	var testFilename string
	switch outputFormat {
	case "testinfra":
		testFilename = testinfraFilename
	case "serverspec":
		testFilename = serverspecFilename
	case "goss":
		testFilename = gossFilename
	case "ansible":
		testFilename = ansibleFilename
	default:
		testFilename = defaultTestFilename
	}

	// Read generated test file
	testFilePath := filepath.Join(outputPath, testFilename)
	content, err := os.ReadFile(testFilePath)
	if err != nil {
		resp.Diagnostics.AddError(
			errReadingTestFile,
			fmt.Sprintf("Could not read generated test file: %s", err),
		)
		return
	}

	// Extract profile name from path
	profileName := filepath.Base(profilePath)

	// Set state
	plan.ID = types.StringValue(fmt.Sprintf(inspecIDFormat, profileName, outputFormat))
	plan.ProfileName = types.StringValue(profileName)
	plan.TestContent = types.StringValue(string(content))

	diags = resp.State.Set(ctx, plan)
	resp.Diagnostics.Append(diags...)
}

// Read refreshes the Terraform state with the latest data
func (r *inspecMigrationResource) Read(ctx context.Context, req resource.ReadRequest, resp *resource.ReadResponse) {
	var state inspecMigrationResourceModel
	diags := req.State.Get(ctx, &state)
	resp.Diagnostics.Append(diags...)
	if resp.Diagnostics.HasError() {
		return
	}

	outputPath := state.OutputPath.ValueString()
	outputFormat := state.OutputFormat.ValueString()

	var testFilename string
	switch outputFormat {
	case "testinfra":
		testFilename = "test_spec.py"
	case "serverspec":
		testFilename = "spec_helper.rb"
	case "goss":
		testFilename = "goss.yaml"
	case "ansible":
		testFilename = "assert.yml"
	default:
		testFilename = "test.txt"
	}

	testFilePath := filepath.Join(outputPath, testFilename)

	if _, err := os.Stat(testFilePath); os.IsNotExist(err) {
		resp.State.RemoveResource(ctx)
		return
	}

	content, err := os.ReadFile(testFilePath)
	if err != nil {
		resp.Diagnostics.AddError(
			errReadingTestFile,
			fmt.Sprintf("Could not read test file: %s", err),
		)
		return
	}

	state.TestContent = types.StringValue(string(content))

	diags = resp.State.Set(ctx, state)
	resp.Diagnostics.Append(diags...)
}

// Update updates the resource and sets the updated Terraform state on success
func (r *inspecMigrationResource) Update(ctx context.Context, req resource.UpdateRequest, resp *resource.UpdateResponse) {
	var plan inspecMigrationResourceModel
	diags := req.Plan.Get(ctx, &plan)
	resp.Diagnostics.Append(diags...)
	if resp.Diagnostics.HasError() {
		return
	}

	profilePath := plan.ProfilePath.ValueString()
	outputPath := plan.OutputPath.ValueString()
	outputFormat := plan.OutputFormat.ValueString()

	cmd := exec.CommandContext(ctx, r.client.Path, "convert-inspec",
		"--profile-path", profilePath,
		"--output-path", outputPath,
		"--format", outputFormat)

	output, err := cmd.CombinedOutput()
	if err != nil {
		resp.Diagnostics.AddError(
			"Error converting InSpec profile",
			fmt.Sprintf("Could not convert profile: %s\nOutput: %s", err, string(output)),
		)
		return
	}

	var testFilename string
	switch outputFormat {
	case "testinfra":
		testFilename = testinfraFilename
	case "serverspec":
		testFilename = serverspecFilename
	case "goss":
		testFilename = gossFilename
	case "ansible":
		testFilename = ansibleFilename
	default:
		testFilename = defaultTestFilename
	}

	testFilePath := filepath.Join(outputPath, testFilename)
	content, err := os.ReadFile(testFilePath)
	if err != nil {
		resp.Diagnostics.AddError(
			errReadingTestFile,
			fmt.Sprintf("Could not read updated test file: %s", err),
		)
		return
	}

	// Extract profile name from path
	profileName := filepath.Base(profilePath)

	// Set state
	plan.ID = types.StringValue(fmt.Sprintf(inspecIDFormat, profileName, outputFormat))
	plan.ProfileName = types.StringValue(profileName)
	plan.TestContent = types.StringValue(string(content))

	diags = resp.State.Set(ctx, plan)
	resp.Diagnostics.Append(diags...)
}

// Delete deletes the resource and removes the Terraform state on success
func (r *inspecMigrationResource) Delete(ctx context.Context, req resource.DeleteRequest, resp *resource.DeleteResponse) {
	var state inspecMigrationResourceModel
	diags := req.State.Get(ctx, &state)
	resp.Diagnostics.Append(diags...)
	if resp.Diagnostics.HasError() {
		return
	}

	outputPath := state.OutputPath.ValueString()
	outputFormat := state.OutputFormat.ValueString()

	var testFilename string
	switch outputFormat {
	case "testinfra":
		testFilename = testinfraFilename
	case "serverspec":
		testFilename = serverspecFilename
	case "goss":
		testFilename = gossFilename
	case "ansible":
		testFilename = ansibleFilename
	default:
		testFilename = defaultTestFilename
	}

	testFilePath := filepath.Join(outputPath, testFilename)
	if err := os.Remove(testFilePath); err != nil && !os.IsNotExist(err) {
		resp.Diagnostics.AddWarning(
			"Error deleting test file",
			fmt.Sprintf("Could not delete test file: %s", err),
		)
	}
}

// ImportState imports an existing resource into Terraform
func (r *inspecMigrationResource) ImportState(ctx context.Context, req resource.ImportStateRequest, resp *resource.ImportStateResponse) {
	// Import ID format: profile_path|output_path|output_format
	parts := strings.Split(req.ID, "|")
	if len(parts) != 3 {
		resp.Diagnostics.AddError(
			"Invalid import ID",
			"Import ID must be in format: profile_path|output_path|output_format",
		)
		return
	}

	profilePath := parts[0]
	outputPath := parts[1]
	outputFormat := parts[2]

	// Validate that the profile directory exists
	if _, err := os.Stat(profilePath); os.IsNotExist(err) {
		resp.Diagnostics.AddError(
			"Profile not found",
			fmt.Sprintf("Profile path does not exist: %s", profilePath),
		)
		return
	}

	// Determine test filename based on output format
	var testFilename string
	switch outputFormat {
	case "testinfra":
		testFilename = testinfraFilename
	case "serverspec":
		testFilename = serverspecFilename
	case "goss":
		testFilename = gossFilename
	case "ansible":
		testFilename = ansibleFilename
	default:
		testFilename = defaultTestFilename
	}

	// Check if test file exists
	testFilePath := filepath.Join(outputPath, testFilename)
	if _, err := os.Stat(testFilePath); os.IsNotExist(err) {
		resp.Diagnostics.AddError(
			"Test file not found",
			fmt.Sprintf("Test file does not exist: %s", testFilePath),
		)
		return
	}

	// Read test content
	content, err := os.ReadFile(testFilePath)
	if err != nil {
		resp.Diagnostics.AddError(
			errReadingTestFile,
			fmt.Sprintf("Could not read test file: %s", err),
		)
		return
	}

	// Extract profile name from path
	profileName := filepath.Base(profilePath)

	// Set state
	resp.Diagnostics.Append(resp.State.SetAttribute(ctx, path.Root("profile_path"), profilePath)...)
	resp.Diagnostics.Append(resp.State.SetAttribute(ctx, path.Root("output_path"), outputPath)...)
	resp.Diagnostics.Append(resp.State.SetAttribute(ctx, path.Root("output_format"), outputFormat)...)
	resp.Diagnostics.Append(resp.State.SetAttribute(ctx, path.Root("profile_name"), profileName)...)
	resp.Diagnostics.Append(resp.State.SetAttribute(ctx, path.Root("test_content"), string(content))...)
	resp.Diagnostics.Append(resp.State.SetAttribute(ctx, path.Root("id"), fmt.Sprintf(inspecIDFormat, profileName, outputFormat))...)
}
