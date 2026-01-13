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
func (r *habitatMigrationResource) Create(ctx context.Context, req resource.CreateRequest, resp *resource.CreateResponse) {
	var plan habitatMigrationResourceModel
	diags := req.Plan.Get(ctx, &plan)
	resp.Diagnostics.Append(diags...)
	if resp.Diagnostics.HasError() {
		return
	}

	planPath := plan.PlanPath.ValueString()
	outputPath := plan.OutputPath.ValueString()
	baseImage := defaultBaseImage
	if !plan.BaseImage.IsNull() && plan.BaseImage.ValueString() != "" {
		baseImage = plan.BaseImage.ValueString()
	}

	// Create output directory
	if err := os.MkdirAll(outputPath, 0755); err != nil {
		resp.Diagnostics.AddError(
			"Error creating output directory",
			fmt.Sprintf("Could not create directory %s: %s", outputPath, err),
		)
		return
	}

	// Call souschef CLI to convert Habitat plan
	cmd := exec.CommandContext(ctx, r.client.Path, "convert-habitat",
		"--plan-path", planPath,
		"--output-path", outputPath,
		"--base-image", baseImage)

	output, err := cmd.CombinedOutput()
	if err != nil {
		resp.Diagnostics.AddError(
			"Error converting Habitat plan",
			fmt.Sprintf("Could not convert plan: %s\nOutput: %s", err, string(output)),
		)
		return
	}

	// Read generated Dockerfile
	dockerfilePath := filepath.Join(outputPath, "Dockerfile")
	content, err := os.ReadFile(dockerfilePath)
	if err != nil {
		resp.Diagnostics.AddError(
			errReadingDockerfile,
			fmt.Sprintf("Could not read generated Dockerfile: %s", err),
		)
		return
	}

	// Extract package name from plan path
	packageName := filepath.Base(filepath.Dir(planPath))

	// Set state
	plan.ID = types.StringValue(fmt.Sprintf(habitatIDFormat, packageName))
	plan.BaseImage = types.StringValue(baseImage)
	plan.PackageName = types.StringValue(packageName)
	plan.DockerfileContent = types.StringValue(string(content))

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

	if _, err := os.Stat(dockerfilePath); os.IsNotExist(err) {
		resp.State.RemoveResource(ctx)
		return
	}

	content, err := os.ReadFile(dockerfilePath)
	if err != nil {
		resp.Diagnostics.AddError(
			errReadingDockerfile,
			fmt.Sprintf("Could not read Dockerfile: %s", err),
		)
		return
	}

	state.DockerfileContent = types.StringValue(string(content))

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

	planPath := plan.PlanPath.ValueString()
	outputPath := plan.OutputPath.ValueString()
	baseImage := defaultBaseImage
	if !plan.BaseImage.IsNull() && plan.BaseImage.ValueString() != "" {
		baseImage = plan.BaseImage.ValueString()
	}

	cmd := exec.CommandContext(ctx, r.client.Path, "convert-habitat",
		"--plan-path", planPath,
		"--output-path", outputPath,
		"--base-image", baseImage)

	output, err := cmd.CombinedOutput()
	if err != nil {
		resp.Diagnostics.AddError(
			"Error converting Habitat plan",
			fmt.Sprintf("Could not convert plan: %s\nOutput: %s", err, string(output)),
		)
		return
	}

	dockerfilePath := filepath.Join(outputPath, "Dockerfile")
	content, err := os.ReadFile(dockerfilePath)
	if err != nil {
		resp.Diagnostics.AddError(
			errReadingDockerfile,
			fmt.Sprintf("Could not read updated Dockerfile: %s", err),
		)
		return
	}

	// Extract package name from plan path
	packageName := filepath.Base(filepath.Dir(planPath))

	// Set state
	plan.ID = types.StringValue(fmt.Sprintf(habitatIDFormat, packageName))
	plan.BaseImage = types.StringValue(baseImage)
	plan.PackageName = types.StringValue(packageName)
	plan.DockerfileContent = types.StringValue(string(content))

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
	if err := os.Remove(dockerfilePath); err != nil && !os.IsNotExist(err) {
		resp.Diagnostics.AddWarning(
			"Error deleting Dockerfile",
			fmt.Sprintf("Could not delete Dockerfile: %s", err),
		)
	}
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
	if _, err := os.Stat(planPath); os.IsNotExist(err) {
		resp.Diagnostics.AddError(
			"Plan file not found",
			fmt.Sprintf("Plan file does not exist: %s", planPath),
		)
		return
	}

	// Check if Dockerfile exists
	dockerfilePath := filepath.Join(outputPath, "Dockerfile")
	if _, err := os.Stat(dockerfilePath); os.IsNotExist(err) {
		resp.Diagnostics.AddError(
			"Dockerfile not found",
			fmt.Sprintf("Dockerfile does not exist: %s", dockerfilePath),
		)
		return
	}

	// Read Dockerfile content
	content, err := os.ReadFile(dockerfilePath)
	if err != nil {
		resp.Diagnostics.AddError(
			errReadingDockerfile,
			fmt.Sprintf("Could not read Dockerfile: %s", err),
		)
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
