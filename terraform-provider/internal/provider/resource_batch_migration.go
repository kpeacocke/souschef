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

const errorReadingBatchPlaybook = "Error reading playbook"

// Ensure the implementation satisfies the expected interfaces
var (
	_ resource.Resource                = &batchMigrationResource{}
	_ resource.ResourceWithImportState = &batchMigrationResource{}
)

// NewBatchMigrationResource creates a new batch migration resource
func NewBatchMigrationResource() resource.Resource {
	return &batchMigrationResource{}
}

// batchMigrationResource is the resource implementation
type batchMigrationResource struct {
	client *SousChefClient
}

// batchMigrationResourceModel describes the resource data model
type batchMigrationResourceModel struct {
	ID            types.String   `tfsdk:"id"`
	CookbookPath  types.String   `tfsdk:"cookbook_path"`
	OutputPath    types.String   `tfsdk:"output_path"`
	RecipeNames   []types.String `tfsdk:"recipe_names"`
	CookbookName  types.String   `tfsdk:"cookbook_name"`
	PlaybookCount types.Int64    `tfsdk:"playbook_count"`
	Playbooks     types.Map      `tfsdk:"playbooks"`
}

// Metadata returns the resource type name
func (r *batchMigrationResource) Metadata(ctx context.Context, req resource.MetadataRequest, resp *resource.MetadataResponse) {
	resp.TypeName = req.ProviderTypeName + "_batch_migration"
}

// Schema defines the schema for the resource
func (r *batchMigrationResource) Schema(ctx context.Context, req resource.SchemaRequest, resp *resource.SchemaResponse) {
	resp.Schema = schema.Schema{
		MarkdownDescription: "Manages batch migration of multiple Chef recipes to Ansible playbooks from a single cookbook.",

		Attributes: map[string]schema.Attribute{
			"id": schema.StringAttribute{
				Computed:            true,
				MarkdownDescription: "Unique identifier for the batch migration",
			},
			"cookbook_path": schema.StringAttribute{
				Required:            true,
				MarkdownDescription: "Path to the Chef cookbook directory",
			},
			"output_path": schema.StringAttribute{
				Required:            true,
				MarkdownDescription: "Directory where Ansible playbooks will be written",
			},
			"recipe_names": schema.ListAttribute{
				Required:            true,
				ElementType:         types.StringType,
				MarkdownDescription: "List of recipe names to convert",
			},
			"cookbook_name": schema.StringAttribute{
				Computed:            true,
				MarkdownDescription: "Name of the cookbook",
			},
			"playbook_count": schema.Int64Attribute{
				Computed:            true,
				MarkdownDescription: "Number of playbooks generated",
			},
			"playbooks": schema.MapAttribute{
				Computed:            true,
				ElementType:         types.StringType,
				MarkdownDescription: "Map of recipe names to playbook content",
			},
		},
	}
}

// Configure adds the provider configured client to the resource
func (r *batchMigrationResource) Configure(ctx context.Context, req resource.ConfigureRequest, resp *resource.ConfigureResponse) {
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
func (r *batchMigrationResource) Create(ctx context.Context, req resource.CreateRequest, resp *resource.CreateResponse) {
	var plan batchMigrationResourceModel
	diags := req.Plan.Get(ctx, &plan)
	resp.Diagnostics.Append(diags...)
	if resp.Diagnostics.HasError() {
		return
	}

	cookbookPath := plan.CookbookPath.ValueString()
	outputPath := plan.OutputPath.ValueString()
	recipeNames := make([]string, len(plan.RecipeNames))
	for i, name := range plan.RecipeNames {
		recipeNames[i] = name.ValueString()
	}

	// Create output directory
	if err := os.MkdirAll(outputPath, 0755); err != nil {
		resp.Diagnostics.AddError(
			"Error creating output directory",
			fmt.Sprintf("Could not create directory %s: %s", outputPath, err),
		)
		return
	}

	// Convert each recipe
	playbooks := make(map[string]string)
	for _, recipeName := range recipeNames {
		// Call souschef CLI to convert recipe
		cmd := exec.CommandContext(ctx, r.client.Path, "convert-recipe",
			"--cookbook-path", cookbookPath,
			"--recipe-name", recipeName,
			"--output-path", outputPath)

		output, err := cmd.CombinedOutput()
		if err != nil {
			resp.Diagnostics.AddError(
				"Error converting recipe",
				fmt.Sprintf("Could not convert recipe %s: %s\nOutput: %s", recipeName, err, string(output)),
			)
			return
		}

		// Read generated playbook
		playbookPath := filepath.Join(outputPath, recipeName+".yml")
		content, err := os.ReadFile(playbookPath)
		if err != nil {
			resp.Diagnostics.AddError(
				errorReadingBatchPlaybook,
				fmt.Sprintf("Could not read generated playbook %s: %s", recipeName, err),
			)
			return
		}

		playbooks[recipeName] = string(content)
	}

	// Extract cookbook name from path
	cookbookName := filepath.Base(cookbookPath)

	// Convert playbooks map to types.Map
	playbooksMap, mapDiags := types.MapValueFrom(ctx, types.StringType, playbooks)
	resp.Diagnostics.Append(mapDiags...)
	if resp.Diagnostics.HasError() {
		return
	}

	// Set state
	plan.ID = types.StringValue(fmt.Sprintf("%s-batch", cookbookName))
	plan.CookbookName = types.StringValue(cookbookName)
	plan.PlaybookCount = types.Int64Value(int64(len(playbooks)))
	plan.Playbooks = playbooksMap

	diags = resp.State.Set(ctx, plan)
	resp.Diagnostics.Append(diags...)
}

// Read refreshes the Terraform state with the latest data
func (r *batchMigrationResource) Read(ctx context.Context, req resource.ReadRequest, resp *resource.ReadResponse) {
	var state batchMigrationResourceModel
	diags := req.State.Get(ctx, &state)
	resp.Diagnostics.Append(diags...)
	if resp.Diagnostics.HasError() {
		return
	}

	outputPath := state.OutputPath.ValueString()
	recipeNames := make([]string, len(state.RecipeNames))
	for i, name := range state.RecipeNames {
		recipeNames[i] = name.ValueString()
	}

	// Check if any playbook exists
	anyExists := false
	playbooks := make(map[string]string)
	for _, recipeName := range recipeNames {
		playbookPath := filepath.Join(outputPath, recipeName+".yml")
		if _, err := os.Stat(playbookPath); err == nil {
			anyExists = true
			content, err := os.ReadFile(playbookPath)
			if err != nil {
				resp.Diagnostics.AddError(
					errorReadingBatchPlaybook,
					fmt.Sprintf("Could not read playbook %s: %s", recipeName, err),
				)
				return
			}
			playbooks[recipeName] = string(content)
		}
	}

	if !anyExists {
		resp.State.RemoveResource(ctx)
		return
	}

	// Update state with current content
	playbooksMap, mapDiags := types.MapValueFrom(ctx, types.StringType, playbooks)
	resp.Diagnostics.Append(mapDiags...)
	if resp.Diagnostics.HasError() {
		return
	}

	state.Playbooks = playbooksMap
	state.PlaybookCount = types.Int64Value(int64(len(playbooks)))

	diags = resp.State.Set(ctx, state)
	resp.Diagnostics.Append(diags...)
}

// Update updates the resource and sets the updated Terraform state on success
func (r *batchMigrationResource) Update(ctx context.Context, req resource.UpdateRequest, resp *resource.UpdateResponse) {
	var plan batchMigrationResourceModel
	diags := req.Plan.Get(ctx, &plan)
	resp.Diagnostics.Append(diags...)
	if resp.Diagnostics.HasError() {
		return
	}

	// Re-run conversion for all recipes
	cookbookPath := plan.CookbookPath.ValueString()
	outputPath := plan.OutputPath.ValueString()
	recipeNames := make([]string, len(plan.RecipeNames))
	for i, name := range plan.RecipeNames {
		recipeNames[i] = name.ValueString()
	}

	playbooks := make(map[string]string)
	for _, recipeName := range recipeNames {
		cmd := exec.CommandContext(ctx, r.client.Path, "convert-recipe",
			"--cookbook-path", cookbookPath,
			"--recipe-name", recipeName,
			"--output-path", outputPath)

		output, err := cmd.CombinedOutput()
		if err != nil {
			resp.Diagnostics.AddError(
				"Error converting recipe",
				fmt.Sprintf("Could not convert recipe %s: %s\nOutput: %s", recipeName, err, string(output)),
			)
			return
		}

		playbookPath := filepath.Join(outputPath, recipeName+".yml")
		content, err := os.ReadFile(playbookPath)
		if err != nil {
			resp.Diagnostics.AddError(
				errorReadingBatchPlaybook,
				fmt.Sprintf("Could not read updated playbook %s: %s", recipeName, err),
			)
			return
		}

		playbooks[recipeName] = string(content)
	}

	playbooksMap, mapDiags := types.MapValueFrom(ctx, types.StringType, playbooks)
	resp.Diagnostics.Append(mapDiags...)
	if resp.Diagnostics.HasError() {
		return
	}

	plan.Playbooks = playbooksMap
	plan.PlaybookCount = types.Int64Value(int64(len(playbooks)))

	diags = resp.State.Set(ctx, plan)
	resp.Diagnostics.Append(diags...)
}

// Delete deletes the resource and removes the Terraform state on success
func (r *batchMigrationResource) Delete(ctx context.Context, req resource.DeleteRequest, resp *resource.DeleteResponse) {
	var state batchMigrationResourceModel
	diags := req.State.Get(ctx, &state)
	resp.Diagnostics.Append(diags...)
	if resp.Diagnostics.HasError() {
		return
	}

	outputPath := state.OutputPath.ValueString()
	recipeNames := make([]string, len(state.RecipeNames))
	for i, name := range state.RecipeNames {
		recipeNames[i] = name.ValueString()
	}

	// Delete generated playbooks
	for _, recipeName := range recipeNames {
		playbookPath := filepath.Join(outputPath, recipeName+".yml")
		if err := os.Remove(playbookPath); err != nil && !os.IsNotExist(err) {
			resp.Diagnostics.AddWarning(
				"Error deleting playbook",
				fmt.Sprintf("Could not delete playbook %s: %s", recipeName, err),
			)
		}
	}
}

// ImportState imports an existing resource into Terraform
func (r *batchMigrationResource) ImportState(ctx context.Context, req resource.ImportStateRequest, resp *resource.ImportStateResponse) {
	// Import ID format: cookbook_path|output_path|recipe1,recipe2,recipe3
	parts := strings.Split(req.ID, "|")
	if len(parts) != 3 {
		resp.Diagnostics.AddError(
			"Invalid import ID",
			"Import ID must be in format: cookbook_path|output_path|recipe1,recipe2,recipe3",
		)
		return
	}

	cookbookPath := parts[0]
	outputPath := parts[1]
	recipeNamesStr := parts[2]

	// Validate that the cookbook directory exists
	if _, err := os.Stat(cookbookPath); os.IsNotExist(err) {
		resp.Diagnostics.AddError(
			"Cookbook not found",
			fmt.Sprintf("Cookbook path does not exist: %s", cookbookPath),
		)
		return
	}

	// Parse recipe names
	recipeNames := strings.Split(recipeNamesStr, ",")
	if len(recipeNames) == 0 {
		resp.Diagnostics.AddError(
			"Invalid import ID",
			"At least one recipe name must be specified",
		)
		return
	}

	// Read all playbooks and validate they exist
	playbooks := make(map[string]string)
	for _, recipeName := range recipeNames {
		playbookPath := filepath.Join(outputPath, recipeName+".yml")
		if _, err := os.Stat(playbookPath); os.IsNotExist(err) {
			resp.Diagnostics.AddError(
				"Playbook not found",
				fmt.Sprintf("Playbook does not exist: %s", playbookPath),
			)
			return
		}

		content, err := os.ReadFile(playbookPath)
		if err != nil {
			resp.Diagnostics.AddError(
				errorReadingBatchPlaybook,
				fmt.Sprintf("Could not read playbook %s: %s", recipeName, err),
			)
			return
		}

		playbooks[recipeName] = string(content)
	}

	// Extract cookbook name from path
	cookbookName := filepath.Base(cookbookPath)

	// Convert recipe names to types
	recipeNamesTypes := make([]types.String, len(recipeNames))
	for i, name := range recipeNames {
		recipeNamesTypes[i] = types.StringValue(name)
	}

	// Convert playbooks map to types.Map
	playbooksMap, mapDiags := types.MapValueFrom(ctx, types.StringType, playbooks)
	resp.Diagnostics.Append(mapDiags...)
	if resp.Diagnostics.HasError() {
		return
	}

	// Set state
	resp.Diagnostics.Append(resp.State.SetAttribute(ctx, path.Root("cookbook_path"), cookbookPath)...)
	resp.Diagnostics.Append(resp.State.SetAttribute(ctx, path.Root("output_path"), outputPath)...)
	resp.Diagnostics.Append(resp.State.SetAttribute(ctx, path.Root("recipe_names"), recipeNamesTypes)...)
	resp.Diagnostics.Append(resp.State.SetAttribute(ctx, path.Root("cookbook_name"), cookbookName)...)
	resp.Diagnostics.Append(resp.State.SetAttribute(ctx, path.Root("playbook_count"), int64(len(playbooks)))...)
	resp.Diagnostics.Append(resp.State.SetAttribute(ctx, path.Root("playbooks"), playbooksMap)...)
	resp.Diagnostics.Append(resp.State.SetAttribute(ctx, path.Root("id"), fmt.Sprintf("%s-batch", cookbookName))...)
}
