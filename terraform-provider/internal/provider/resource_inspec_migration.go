// Package provider implements the SousChef Terraform provider resources
package provider

import (
	"context"
	"fmt"
	"path/filepath"
	"strings"

	"github.com/hashicorp/terraform-plugin-framework/diag"
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

func inspecTestFilename(outputFormat string) string {
	switch outputFormat {
	case "testinfra":
		return testinfraFilename
	case "serverspec":
		return serverspecFilename
	case "goss":
		return gossFilename
	case "ansible":
		return ansibleFilename
	default:
		return defaultTestFilename
	}
}

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
	r.client = configureResource(req, resp)
}

// executeInSpecConversion executes the InSpec profile conversion and updates the model state.
func (r *inspecMigrationResource) executeInSpecConversion(
	ctx context.Context,
	model *inspecMigrationResourceModel,
	diagnostics *diag.Diagnostics,
) {
	profilePath := model.ProfilePath.ValueString()
	outputPath := model.OutputPath.ValueString()
	outputFormat := model.OutputFormat.ValueString()

	// Call souschef CLI to convert InSpec profile
	args := []string{"convert-inspec", "--profile-path", profilePath, "--output-path", outputPath, "--format", outputFormat}
	if _, ok := executeSousChefCommand(ctx, r.client.Path, args, "Error converting InSpec profile", diagnostics); !ok {
		return
	}

	// Read generated test file
	testFilePath := filepath.Join(outputPath, inspecTestFilename(outputFormat))
	content := readGeneratedFile(testFilePath, errReadingTestFile, diagnostics)
	if diagnostics.HasError() {
		return
	}

	// Extract profile name from path and set state
	profileName := filepath.Base(profilePath)
	model.ID = types.StringValue(fmt.Sprintf(inspecIDFormat, profileName, outputFormat))
	model.ProfileName = types.StringValue(profileName)
	model.TestContent = types.StringValue(string(content))
}

// Create creates the resource and sets the initial Terraform state
func (r *inspecMigrationResource) Create(ctx context.Context, req resource.CreateRequest, resp *resource.CreateResponse) {
	var plan inspecMigrationResourceModel
	diags := req.Plan.Get(ctx, &plan)
	resp.Diagnostics.Append(diags...)
	if resp.Diagnostics.HasError() {
		return
	}

	// Create output directory
	if !createOutputDirectory(plan.OutputPath.ValueString(), &resp.Diagnostics) {
		return
	}

	// Execute conversion and set state
	r.executeInSpecConversion(ctx, &plan, &resp.Diagnostics)
	if resp.Diagnostics.HasError() {
		return
	}

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

	testFilePath := filepath.Join(outputPath, inspecTestFilename(outputFormat))

	// Check if file exists and read content
	if !readFileAndSetState(
		ctx,
		testFilePath,
		"test_content",
		func(content string) { state.TestContent = types.StringValue(content) },
		errReadingTestFile,
		&resp.Diagnostics,
		resp.State.RemoveResource,
	) {
		return
	}

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

	// Execute conversion and set state
	r.executeInSpecConversion(ctx, &plan, &resp.Diagnostics)
	if resp.Diagnostics.HasError() {
		return
	}

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

	testFilePath := filepath.Join(outputPath, inspecTestFilename(outputFormat))
	deleteGeneratedFile(testFilePath, "test file", &resp.Diagnostics)
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
	if !checkFileExists(profilePath, "Profile", &resp.Diagnostics) {
		return
	}

	// Check if test file exists
	testFilePath := filepath.Join(outputPath, inspecTestFilename(outputFormat))
	if !checkFileExists(testFilePath, "Test file", &resp.Diagnostics) {
		return
	}

	// Read test content
	content := readGeneratedFile(testFilePath, errReadingTestFile, &resp.Diagnostics)
	if resp.Diagnostics.HasError() {
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
