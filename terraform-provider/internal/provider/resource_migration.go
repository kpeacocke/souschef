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
	"github.com/hashicorp/terraform-plugin-log/tflog"
)

const errorReadingPlaybook = "Error reading playbook"

// Ensure the implementation satisfies the expected interfaces
var (
	_ resource.Resource                = &migrationResource{}
	_ resource.ResourceWithConfigure   = &migrationResource{}
	_ resource.ResourceWithImportState = &migrationResource{}
)

// NewMigrationResource is a helper function to simplify the provider implementation.
func NewMigrationResource() resource.Resource {
	return &migrationResource{}
}

// migrationResource is the resource implementation.
type migrationResource struct {
	client *SousChefClient
}

// migrationResourceModel maps the resource schema data.
type migrationResourceModel struct {
	ID              types.String `tfsdk:"id"`
	CookbookPath    types.String `tfsdk:"cookbook_path"`
	OutputPath      types.String `tfsdk:"output_path"`
	CookbookName    types.String `tfsdk:"cookbook_name"`
	RecipeName      types.String `tfsdk:"recipe_name"`
	PlaybookContent types.String `tfsdk:"playbook_content"`
}

// Metadata returns the resource type name.
func (r *migrationResource) Metadata(_ context.Context, req resource.MetadataRequest, resp *resource.MetadataResponse) {
	resp.TypeName = req.ProviderTypeName + "_migration"
}

// Schema defines the schema for the resource.
func (r *migrationResource) Schema(_ context.Context, _ resource.SchemaRequest, resp *resource.SchemaResponse) {
	resp.Schema = schema.Schema{
		Description: "Manages a Chef cookbook to Ansible playbook migration.",
		Attributes: map[string]schema.Attribute{
			"id": schema.StringAttribute{
				Description: "Unique identifier for the migration (cookbook-recipe).",
				Computed:    true,
				PlanModifiers: []planmodifier.String{
					stringplanmodifier.UseStateForUnknown(),
				},
			},
			"cookbook_path": schema.StringAttribute{
				Description: "Path to the Chef cookbook directory.",
				Required:    true,
			},
			"output_path": schema.StringAttribute{
				Description: "Directory where Ansible playbook will be written.",
				Required:    true,
			},
			"cookbook_name": schema.StringAttribute{
				Description: "Name of the cookbook (parsed from metadata.rb).",
				Computed:    true,
			},
			"recipe_name": schema.StringAttribute{
				Description: "Name of the recipe to convert (default: 'default').",
				Optional:    true,
			},
			"playbook_content": schema.StringAttribute{
				Description: "Generated Ansible playbook YAML content.",
				Computed:    true,
			},
		},
	}
}

// Configure adds the provider configured client to the resource.
func (r *migrationResource) Configure(_ context.Context, req resource.ConfigureRequest, resp *resource.ConfigureResponse) {
	if req.ProviderData == nil {
		return
	}

	client, ok := req.ProviderData.(*SousChefClient)

	if !ok {
		resp.Diagnostics.AddError(
			"Unexpected Resource Configure Type",
			fmt.Sprintf("Expected *SousChefClient, got: %T. Please report this issue to the provider developers.", req.ProviderData),
		)
		return
	}

	r.client = client
}

// Create creates the resource and sets the initial Terraform state.
func (r *migrationResource) Create(ctx context.Context, req resource.CreateRequest, resp *resource.CreateResponse) {
	var plan migrationResourceModel
	diags := req.Plan.Get(ctx, &plan)
	resp.Diagnostics.Append(diags...)
	if resp.Diagnostics.HasError() {
		return
	}

	// Get recipe name or default
	recipeName := "default"
	if !plan.RecipeName.IsNull() {
		recipeName = plan.RecipeName.ValueString()
	}

	// Parse cookbook metadata
	cookbookPath := plan.CookbookPath.ValueString()
	outputPath := plan.OutputPath.ValueString()

	// Call souschef CLI to convert recipe
	cmd := exec.CommandContext(ctx, r.client.Path, "convert-recipe",
		"--cookbook-path", cookbookPath,
		"--recipe-name", recipeName,
		"--output-path", outputPath,
	)

	tflog.Debug(ctx, "Executing SousChef", map[string]interface{}{
		"command": cmd.String(),
	})

	output, err := cmd.CombinedOutput()
	if err != nil {
		resp.Diagnostics.AddError(
			"Error converting recipe",
			fmt.Sprintf("Could not convert recipe: %s\n%s", err, string(output)),
		)
		return
	}

	// Read generated playbook
	playbookPath := filepath.Join(outputPath, recipeName+".yml")
	content, err := os.ReadFile(playbookPath)
	if err != nil {
		resp.Diagnostics.AddError(
			errorReadingPlaybook,
			fmt.Sprintf("Could not read generated playbook: %s", err),
		)
		return
	}

	// Extract cookbook name from path
	cookbookName := filepath.Base(cookbookPath)

	// Set state
	plan.ID = types.StringValue(fmt.Sprintf("%s-%s", cookbookName, recipeName))
	plan.CookbookName = types.StringValue(cookbookName)
	plan.RecipeName = types.StringValue(recipeName)
	plan.PlaybookContent = types.StringValue(string(content))

	diags = resp.State.Set(ctx, plan)
	resp.Diagnostics.Append(diags...)
}

// Read refreshes the Terraform state with the latest data.
func (r *migrationResource) Read(ctx context.Context, req resource.ReadRequest, resp *resource.ReadResponse) {
	var state migrationResourceModel
	diags := req.State.Get(ctx, &state)
	resp.Diagnostics.Append(diags...)
	if resp.Diagnostics.HasError() {
		return
	}

	// Check if playbook still exists
	recipeName := state.RecipeName.ValueString()
	outputPath := state.OutputPath.ValueString()
	playbookPath := filepath.Join(outputPath, recipeName+".yml")

	if _, err := os.Stat(playbookPath); os.IsNotExist(err) {
		resp.State.RemoveResource(ctx)
		return
	}

	// Read current content
	content, err := os.ReadFile(playbookPath)
	if err != nil {
		resp.Diagnostics.AddError(
			errorReadingPlaybook,
			fmt.Sprintf("Could not read playbook: %s", err),
		)
		return
	}

	state.PlaybookContent = types.StringValue(string(content))

	diags = resp.State.Set(ctx, &state)
	resp.Diagnostics.Append(diags...)
}

// Update updates the resource and sets the updated Terraform state on success.
func (r *migrationResource) Update(ctx context.Context, req resource.UpdateRequest, resp *resource.UpdateResponse) {
	var plan migrationResourceModel
	diags := req.Plan.Get(ctx, &plan)
	resp.Diagnostics.Append(diags...)
	if resp.Diagnostics.HasError() {
		return
	}

	// Re-run conversion
	recipeName := plan.RecipeName.ValueString()
	cookbookPath := plan.CookbookPath.ValueString()
	outputPath := plan.OutputPath.ValueString()

	// Extract cookbook name from path
	cookbookName := filepath.Base(cookbookPath)

	cmd := exec.CommandContext(ctx, r.client.Path, "convert-recipe",
		"--cookbook-path", cookbookPath,
		"--recipe-name", recipeName,
		"--output-path", outputPath,
	)

	output, err := cmd.CombinedOutput()
	if err != nil {
		resp.Diagnostics.AddError(
			"Error updating migration",
			fmt.Sprintf("Could not re-convert recipe: %s\n%s", err, string(output)),
		)
		return
	}

	// Read updated playbook
	playbookPath := filepath.Join(outputPath, recipeName+".yml")
	content, err := os.ReadFile(playbookPath)
	if err != nil {
		resp.Diagnostics.AddError(
			errorReadingPlaybook,
			fmt.Sprintf("Could not read updated playbook: %s", err),
		)
		return
	}

	plan.PlaybookContent = types.StringValue(string(content))
	plan.CookbookName = types.StringValue(cookbookName)
	plan.ID = types.StringValue(fmt.Sprintf("%s-%s", cookbookName, recipeName))

	diags = resp.State.Set(ctx, plan)
	resp.Diagnostics.Append(diags...)
}

// Delete deletes the resource and removes the Terraform state on success.
func (r *migrationResource) Delete(ctx context.Context, req resource.DeleteRequest, resp *resource.DeleteResponse) {
	var state migrationResourceModel
	diags := req.State.Get(ctx, &state)
	resp.Diagnostics.Append(diags...)
	if resp.Diagnostics.HasError() {
		return
	}

	// Remove generated playbook
	recipeName := state.RecipeName.ValueString()
	outputPath := state.OutputPath.ValueString()
	playbookPath := filepath.Join(outputPath, recipeName+".yml")

	if err := os.Remove(playbookPath); err != nil && !os.IsNotExist(err) {
		resp.Diagnostics.AddError(
			"Error deleting playbook",
			fmt.Sprintf("Could not delete playbook: %s", err),
		)
		return
	}

	tflog.Info(ctx, "Deleted migration resource", map[string]interface{}{
		"id": state.ID.ValueString(),
	})
}

// ImportState imports an existing resource into Terraform
func (r *migrationResource) ImportState(ctx context.Context, req resource.ImportStateRequest, resp *resource.ImportStateResponse) {
	// Import ID format: cookbook_path|output_path|recipe_name
	parts := strings.Split(req.ID, "|")
	if len(parts) != 3 {
		resp.Diagnostics.AddError(
			"Invalid import ID",
			"Import ID must be in format: cookbook_path|output_path|recipe_name",
		)
		return
	}

	cookbookPath := parts[0]
	outputPath := parts[1]
	recipeName := parts[2]

	// Validate that the cookbook exists
	if _, err := os.Stat(cookbookPath); os.IsNotExist(err) {
		resp.Diagnostics.AddError(
			"Cookbook not found",
			fmt.Sprintf("Cookbook path does not exist: %s", cookbookPath),
		)
		return
	}

	// Check if playbook exists
	playbookPath := filepath.Join(outputPath, recipeName+".yml")
	if _, err := os.Stat(playbookPath); os.IsNotExist(err) {
		resp.Diagnostics.AddError(
			"Playbook not found",
			fmt.Sprintf("Playbook does not exist: %s", playbookPath),
		)
		return
	}

	// Read playbook content
	content, err := os.ReadFile(playbookPath)
	if err != nil {
		resp.Diagnostics.AddError(
			errorReadingPlaybook,
			fmt.Sprintf("Could not read playbook: %s", err),
		)
		return
	}

	// Extract cookbook name from path
	cookbookName := filepath.Base(cookbookPath)

	// Set state
	resp.Diagnostics.Append(resp.State.SetAttribute(ctx, path.Root("cookbook_path"), cookbookPath)...)
	resp.Diagnostics.Append(resp.State.SetAttribute(ctx, path.Root("output_path"), outputPath)...)
	resp.Diagnostics.Append(resp.State.SetAttribute(ctx, path.Root("recipe_name"), recipeName)...)
	resp.Diagnostics.Append(resp.State.SetAttribute(ctx, path.Root("cookbook_name"), cookbookName)...)
	resp.Diagnostics.Append(resp.State.SetAttribute(ctx, path.Root("playbook_content"), string(content))...)
	resp.Diagnostics.Append(resp.State.SetAttribute(ctx, path.Root("id"), fmt.Sprintf("%s-%s", cookbookName, recipeName))...)
}
