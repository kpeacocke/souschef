package provider

import (
	"context"
	"testing"

	"github.com/hashicorp/terraform-plugin-framework/resource"
)

// TestMigrationResourceImplementsInterface verifies interface implementation
func TestMigrationResourceImplementsInterface(t *testing.T) {
	var _ resource.Resource = &migrationResource{}
	var _ resource.ResourceWithConfigure = &migrationResource{}
	var _ resource.ResourceWithImportState = &migrationResource{}
}

// TestNewMigrationResource verifies factory function
func TestNewMigrationResource(t *testing.T) {
	r := NewMigrationResource()
	if r == nil {
		t.Fatal("Expected resource, got nil")
	}
	
	_, ok := r.(*migrationResource)
	if !ok {
		t.Fatal("Expected *migrationResource")
	}
}

// TestMigrationResourceMetadata verifies metadata is correctly set
func TestMigrationResourceMetadata(t *testing.T) {
	r := &migrationResource{}
	
	req := resource.MetadataRequest{
		ProviderTypeName: "souschef",
	}
	resp := &resource.MetadataResponse{}
	
	r.Metadata(context.Background(), req, resp)
	
	expected := "souschef_migration"
	if resp.TypeName != expected {
		t.Errorf("Expected type name '%s', got '%s'", expected, resp.TypeName)
	}
}

// TestMigrationResourceSchema verifies schema is defined correctly
func TestMigrationResourceSchema(t *testing.T) {
	r := &migrationResource{}
	
	req := resource.SchemaRequest{}
	resp := &resource.SchemaResponse{}
	
	r.Schema(context.Background(), req, resp)
	
	if resp.Schema.Attributes == nil {
		t.Fatal("Expected schema attributes to be defined")
	}
	
	// Verify required attributes
	requiredAttrs := []string{"cookbook_path", "output_path"}
	for _, attr := range requiredAttrs {
		if _, exists := resp.Schema.Attributes[attr]; !exists {
			t.Errorf("Expected required attribute '%s' in schema", attr)
		}
	}
	
	// Verify optional attributes
	optionalAttrs := []string{"recipe_name"}
	for _, attr := range optionalAttrs {
		if _, exists := resp.Schema.Attributes[attr]; !exists {
			t.Errorf("Expected optional attribute '%s' in schema", attr)
		}
	}
	
	// Verify computed attributes
	computedAttrs := []string{"id", "cookbook_name", "playbook_content"}
	for _, attr := range computedAttrs {
		if _, exists := resp.Schema.Attributes[attr]; !exists {
			t.Errorf("Expected computed attribute '%s' in schema", attr)
		}
	}
}

// TestMigrationResourceConfigure verifies configuration
func TestMigrationResourceConfigure(t *testing.T) {
	r := &migrationResource{}
	
	client := &SousChefClient{Path: "souschef"}
	
	req := resource.ConfigureRequest{
		ProviderData: client,
	}
	resp := &resource.ConfigureResponse{}
	
	r.Configure(context.Background(), req, resp)
	
	if resp.Diagnostics.HasError() {
		t.Errorf("Expected no errors, got: %v", resp.Diagnostics.Errors())
	}
	
	if r.client == nil {
		t.Error("Expected client to be configured")
	}
	
	if r.client.Path != "souschef" {
		t.Errorf("Expected client path 'souschef', got '%s'", r.client.Path)
	}
}

// TestMigrationResourceConfigureNilData verifies nil provider data is handled
func TestMigrationResourceConfigureNilData(t *testing.T) {
	r := &migrationResource{}
	
	req := resource.ConfigureRequest{
		ProviderData: nil,
	}
	resp := &resource.ConfigureResponse{}
	
	r.Configure(context.Background(), req, resp)
	
	if resp.Diagnostics.HasError() {
		t.Errorf("Expected no errors with nil provider data, got: %v", resp.Diagnostics.Errors())
	}
}

// TestMigrationResourceConfigureInvalidType verifies invalid provider data type is handled
func TestMigrationResourceConfigureInvalidType(t *testing.T) {
	r := &migrationResource{}
	
	req := resource.ConfigureRequest{
		ProviderData: "invalid",
	}
	resp := &resource.ConfigureResponse{}
	
	r.Configure(context.Background(), req, resp)
	
	if !resp.Diagnostics.HasError() {
		t.Error("Expected error with invalid provider data type")
	}
}

// TestMigrationResourceModel verifies model struct
func TestMigrationResourceModel(t *testing.T) {
	model := migrationResourceModel{}
	
	// Verify struct has expected fields
	_ = model.ID
	_ = model.CookbookPath
	_ = model.OutputPath
	_ = model.CookbookName
	_ = model.RecipeName
	_ = model.PlaybookContent
}
