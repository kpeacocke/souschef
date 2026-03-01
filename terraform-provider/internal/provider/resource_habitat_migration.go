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
	"github.com/hashicorp/terraform-plugin-framework/resource/schema/planmodifier"
	"github.com/hashicorp/terraform-plugin-framework/resource/schema/stringplanmodifier"
	"github.com/hashicorp/terraform-plugin-framework/types"
)

// Ensure the implementation satisfies the expected interfaces
var (
	_ resource.Resource                = &habitatMigrationResource{}
	_ resource.ResourceWithImportState = &habitatMigrationResource{}
)

// NewHabitatMigrationResource creates a new Habitat migration resource
func NewHabitatMigrationResource() resource.Resource {
	return &habitatMigrationResource{}
}

// habitatMigrationResource is the resource implementation
type habitatMigrationResource struct {
	client *SousChefClient
}

// habitatMigrationResourceModel describes the resource data model
type habitatMigrationResourceModel struct {
	ID                types.String `tfsdk:"id"`
	PlanPath          types.String `tfsdk:"plan_path"`
	OutputPath        types.String `tfsdk:"output_path"`
	BaseImage         types.String `tfsdk:"base_image"`
	PackageName       types.String `tfsdk:"package_name"`
	DockerfileContent types.String `tfsdk:"dockerfile_content"`
}

const (
	errReadingDockerfile = "Error reading Dockerfile"
	defaultBaseImage     = "ubuntu:latest"
	habitatIDFormat      = "habitat-%s"
)

// Metadata returns the resource type name
func (r *habitatMigrationResource) Metadata(ctx context.Context, req resource.MetadataRequest, resp *resource.MetadataResponse) {
	resp.TypeName = req.ProviderTypeName + "_habitat_migration"
}

// Schema defines the schema for the resource
func (r *habitatMigrationResource) Schema(ctx context.Context, req resource.SchemaRequest, resp *resource.SchemaResponse) {
	resp.Schema = schema.Schema{
		MarkdownDescription: "Manages conversion of Chef Habitat plans to Dockerfiles.",

		Attributes: map[string]schema.Attribute{
			"id": schema.StringAttribute{
				Computed:            true,
				MarkdownDescription: "Unique identifier for the Habitat migration",
			},
			"plan_path": schema.StringAttribute{
				Required:            true,
				MarkdownDescription: "Path to the Habitat plan.sh file",
			},
			"output_path": schema.StringAttribute{
				Required:            true,
				MarkdownDescription: "Directory where Dockerfile will be written",
			},
			"base_image": schema.StringAttribute{
				Optional:            true,
				Computed:            true,
				MarkdownDescription: "Base Docker image to use (default: ubuntu:latest)",
				PlanModifiers: []planmodifier.String{
					stringplanmodifier.UseStateForUnknown(),
				},
			},
			"package_name": schema.StringAttribute{
				Computed:            true,
				MarkdownDescription: "Name of the Habitat package",
			},
			"dockerfile_content": schema.StringAttribute{
				Computed:            true,
				MarkdownDescription: "Generated Dockerfile content",
			},
		},
	}
}

// Configure adds the provider configured client to the resource
func (r *habitatMigrationResource) Configure(ctx context.Context, req resource.ConfigureRequest, resp *resource.ConfigureResponse) {
	r.client = configureResource(req, resp)
}

// Create creates the resource and sets the initial Terraform state
func (r *habitatMigrationResource) Create(ctx context.Context, req resource.CreateRequest, resp *resource.CreateResponse) {
	var plan habitatMigrationResourceModel
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
	r.executeHabitatConversion(ctx, &plan, &resp.Diagnostics)
	if resp.Diagnostics.HasError() {
		return
	}

	diags = resp.State.Set(ctx, plan)
	resp.Diagnostics.Append(diags...)
}

// Read refreshes the Terraform state with the latest data
func (r *habitatMigrationResource) Read(ctx context.Context, req resource.ReadRequest, resp *resource.ReadResponse) {
	var state habitatMigrationResourceModel
	diags := req.State.Get(ctx, &state)
	resp.Diagnostics.Append(diags...)
	if resp.Diagnostics.HasError() {
		return
	}

	dockerfilePath := filepath.Join(state.OutputPath.ValueString(), "Dockerfile")

	// Check if file exists and read content
	if !readFileAndSetState(
		ctx,
		dockerfilePath,
		"dockerfile_content",
		func(content string) { state.DockerfileContent = types.StringValue(content) },
		errReadingDockerfile,
		&resp.Diagnostics,
		resp.State.RemoveResource,
	) {
		return
	}

	diags = resp.State.Set(ctx, state)
	resp.Diagnostics.Append(diags...)
}

// Update updates the resource and sets the updated Terraform state on success
func (r *habitatMigrationResource) Update(ctx context.Context, req resource.UpdateRequest, resp *resource.UpdateResponse) {
	var plan habitatMigrationResourceModel
	diags := req.Plan.Get(ctx, &plan)
	resp.Diagnostics.Append(diags...)
	if resp.Diagnostics.HasError() {
		return
	}

	// Execute conversion and set state
	r.executeHabitatConversion(ctx, &plan, &resp.Diagnostics)
	if resp.Diagnostics.HasError() {
		return
	}

	diags = resp.State.Set(ctx, plan)
	resp.Diagnostics.Append(diags...)
}

// Delete deletes the resource and removes the Terraform state on success
func (r *habitatMigrationResource) Delete(ctx context.Context, req resource.DeleteRequest, resp *resource.DeleteResponse) {
	var state habitatMigrationResourceModel
	diags := req.State.Get(ctx, &state)
	resp.Diagnostics.Append(diags...)
	if resp.Diagnostics.HasError() {
		return
	}

	dockerfilePath := filepath.Join(state.OutputPath.ValueString(), "Dockerfile")
	deleteGeneratedFile(dockerfilePath, "Dockerfile", &resp.Diagnostics)
}

// executeHabitatConversion is a helper that encapsulates the common logic for Create and Update.
// It executes the habitat conversion, reads the output, and updates the model state.
func (r *habitatMigrationResource) executeHabitatConversion(ctx context.Context, model *habitatMigrationResourceModel, diagnostics *diag.Diagnostics) {
	planPath := model.PlanPath.ValueString()
	outputPath := model.OutputPath.ValueString()
	baseImage := defaultBaseImage
	if !model.BaseImage.IsNull() && model.BaseImage.ValueString() != "" {
		baseImage = model.BaseImage.ValueString()
	}

	// Call souschef CLI to convert Habitat plan
	args := []string{"convert-habitat", "--plan-path", planPath, "--output-path", outputPath, "--base-image", baseImage}
	if _, ok := executeSousChefCommand(ctx, r.client.Path, args, "Error converting Habitat plan", diagnostics); !ok {
		return
	}

	// Read generated Dockerfile
	dockerfilePath := filepath.Join(outputPath, "Dockerfile")
	content := readGeneratedFile(dockerfilePath, errReadingDockerfile, diagnostics)
	if diagnostics.HasError() {
		return
	}

	// Extract package name from plan path
	packageName := filepath.Base(filepath.Dir(planPath))

	// Set state
	model.ID = types.StringValue(fmt.Sprintf(habitatIDFormat, packageName))
	model.BaseImage = types.StringValue(baseImage)
	model.PackageName = types.StringValue(packageName)
	model.DockerfileContent = types.StringValue(string(content))
}

// ImportState imports an existing resource into Terraform
func (r *habitatMigrationResource) ImportState(ctx context.Context, req resource.ImportStateRequest, resp *resource.ImportStateResponse) {
	// Import ID format: plan_path|output_path|base_image (base_image is optional)
	parts := strings.Split(req.ID, "|")
	if len(parts) < 2 || len(parts) > 3 {
		resp.Diagnostics.AddError(
			"Invalid import ID",
			"Import ID must be in format: plan_path|output_path or plan_path|output_path|base_image",
		)
		return
	}

	planPath := parts[0]
	outputPath := parts[1]
	baseImage := defaultBaseImage // default
	if len(parts) == 3 && parts[2] != "" {
		baseImage = parts[2]
	}

	// Validate that the plan file exists
	if !checkFileExists(planPath, "Plan file", &resp.Diagnostics) {
		return
	}

	// Check if Dockerfile exists
	dockerfilePath := filepath.Join(outputPath, "Dockerfile")
	if !checkFileExists(dockerfilePath, "Dockerfile", &resp.Diagnostics) {
		return
	}

	// Read Dockerfile content
	content := readGeneratedFile(dockerfilePath, errReadingDockerfile, &resp.Diagnostics)
	if resp.Diagnostics.HasError() {
		return
	}

	// Extract package name from plan path (parent directory name)
	packageName := filepath.Base(filepath.Dir(planPath))

	// Set state
	resp.Diagnostics.Append(resp.State.SetAttribute(ctx, path.Root("plan_path"), planPath)...)
	resp.Diagnostics.Append(resp.State.SetAttribute(ctx, path.Root("output_path"), outputPath)...)
	resp.Diagnostics.Append(resp.State.SetAttribute(ctx, path.Root("base_image"), baseImage)...)
	resp.Diagnostics.Append(resp.State.SetAttribute(ctx, path.Root("package_name"), packageName)...)
	resp.Diagnostics.Append(resp.State.SetAttribute(ctx, path.Root("dockerfile_content"), string(content))...)
	resp.Diagnostics.Append(resp.State.SetAttribute(ctx, path.Root("id"), fmt.Sprintf(habitatIDFormat, packageName))...)
}
