package provider

import (
	"context"
	"testing"

	"github.com/hashicorp/terraform-plugin-framework/resource"
)

// TestInSpecMigrationResourceImplementsInterface verifies the resource implements the correct interface
func TestInSpecMigrationResourceImplementsInterface(t *testing.T) {
	var _ resource.Resource = &inspecMigrationResource{}
	var _ resource.ResourceWithImportState = &inspecMigrationResource{}
}

// TestNewInSpecMigrationResource verifies the constructor
func TestNewInSpecMigrationResource(t *testing.T) {
	r := NewInSpecMigrationResource()
	if r == nil {
		t.Fatal("Expected non-nil resource")
	}
	
	_, ok := r.(*inspecMigrationResource)
	if !ok {
		t.Fatal("Expected *inspecMigrationResource")
	}
}

// TestInSpecMigrationResourceMetadata verifies metadata
func TestInSpecMigrationResourceMetadata(t *testing.T) {
	r := &inspecMigrationResource{}
	
	req := resource.MetadataRequest{
		ProviderTypeName: "souschef",
	}
	resp := &resource.MetadataResponse{}
	
	r.Metadata(context.Background(), req, resp)
	
	expected := "souschef_inspec_migration"
	if resp.TypeName != expected {
		t.Errorf("Expected TypeName %q, got %q", expected, resp.TypeName)
	}
}

// TestInSpecMigrationResourceSchema verifies schema
func TestInSpecMigrationResourceSchema(t *testing.T) {
	r := &inspecMigrationResource{}
	
	req := resource.SchemaRequest{}
	resp := &resource.SchemaResponse{}
	
	r.Schema(context.Background(), req, resp)
	
	if resp.Schema.Attributes == nil {
		t.Fatal("Expected non-nil schema attributes")
	}
	
	// Verify key attributes exist
	requiredAttrs := []string{"id", "profile_path", "output_path", "output_format"}
	for _, attr := range requiredAttrs {
		if _, ok := resp.Schema.Attributes[attr]; !ok {
			t.Errorf("Missing required attribute: %s", attr)
		}
	}
}

// TestInSpecMigrationResourceConfigure verifies configure with valid client
func TestInSpecMigrationResourceConfigure(t *testing.T) {
	r := &inspecMigrationResource{}
	
	client := &SousChefClient{Path: "souschef"}
	
	req := resource.ConfigureRequest{
		ProviderData: client,
	}
	resp := &resource.ConfigureResponse{}
	
	r.Configure(context.Background(), req, resp)
	
	if resp.Diagnostics.HasError() {
		t.Errorf("Expected no errors, got: %v", resp.Diagnostics.Errors())
	}
	
	if r.client != client {
		t.Error("Expected client to be set")
	}
}

// TestInSpecMigrationResourceConfigureNilData verifies configure with nil data
func TestInSpecMigrationResourceConfigureNilData(t *testing.T) {
	r := &inspecMigrationResource{}
	
	req := resource.ConfigureRequest{
		ProviderData: nil,
	}
	resp := &resource.ConfigureResponse{}
	
	r.Configure(context.Background(), req, resp)
	
	if resp.Diagnostics.HasError() {
		t.Errorf("Expected no errors with nil data, got: %v", resp.Diagnostics.Errors())
	}
}

// TestInSpecMigrationResourceConfigureInvalidType verifies configure with wrong type
func TestInSpecMigrationResourceConfigureInvalidType(t *testing.T) {
	r := &inspecMigrationResource{}
	
	req := resource.ConfigureRequest{
		ProviderData: "invalid",
	}
	resp := &resource.ConfigureResponse{}
	
	r.Configure(context.Background(), req, resp)
	
	if !resp.Diagnostics.HasError() {
		t.Error("Expected error with invalid provider data type")
	}
}

// TestInSpecMigrationResourceModel verifies the data model compiles
func TestInSpecMigrationResourceModel(t *testing.T) {
	_ = inspecMigrationResourceModel{}
}
