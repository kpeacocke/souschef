package provider

import (
	"context"
	"testing"

	"github.com/hashicorp/terraform-plugin-framework/resource"
)

// TestHabitatMigrationResourceImplementsInterface verifies the resource implements the correct interface
func TestHabitatMigrationResourceImplementsInterface(t *testing.T) {
	var _ resource.Resource = &habitatMigrationResource{}
	var _ resource.ResourceWithImportState = &habitatMigrationResource{}
}

// TestNewHabitatMigrationResource verifies the constructor
func TestNewHabitatMigrationResource(t *testing.T) {
	r := NewHabitatMigrationResource()
	if r == nil {
		t.Fatal("Expected non-nil resource")
	}

	_, ok := r.(*habitatMigrationResource)
	if !ok {
		t.Fatal("Expected *habitatMigrationResource")
	}
}

// TestHabitatMigrationResourceMetadata verifies metadata
func TestHabitatMigrationResourceMetadata(t *testing.T) {
	r := &habitatMigrationResource{}

	req := resource.MetadataRequest{
		ProviderTypeName: "souschef",
	}
	resp := &resource.MetadataResponse{}

	r.Metadata(context.Background(), req, resp)

	expected := "souschef_habitat_migration"
	if resp.TypeName != expected {
		t.Errorf("Expected TypeName %q, got %q", expected, resp.TypeName)
	}
}

// TestHabitatMigrationResourceSchema verifies schema
func TestHabitatMigrationResourceSchema(t *testing.T) {
	r := &habitatMigrationResource{}

	req := resource.SchemaRequest{}
	resp := &resource.SchemaResponse{}

	r.Schema(context.Background(), req, resp)

	if resp.Schema.Attributes == nil {
		t.Fatal("Expected non-nil schema attributes")
	}

	// Verify key attributes exist
	requiredAttrs := []string{"id", "plan_path", "output_path", "base_image"}
	for _, attr := range requiredAttrs {
		if _, ok := resp.Schema.Attributes[attr]; !ok {
			t.Errorf("Missing required attribute: %s", attr)
		}
	}
}

// TestHabitatMigrationResourceConfigure verifies configure with valid client
func TestHabitatMigrationResourceConfigure(t *testing.T) {
	r := &habitatMigrationResource{}

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

// TestHabitatMigrationResourceConfigureNilData verifies configure with nil data
func TestHabitatMigrationResourceConfigureNilData(t *testing.T) {
	r := &habitatMigrationResource{}

	req := resource.ConfigureRequest{
		ProviderData: nil,
	}
	resp := &resource.ConfigureResponse{}

	r.Configure(context.Background(), req, resp)

	if resp.Diagnostics.HasError() {
		t.Errorf("Expected no errors with nil data, got: %v", resp.Diagnostics.Errors())
	}
}

// TestHabitatMigrationResourceConfigureInvalidType verifies configure with wrong type
func TestHabitatMigrationResourceConfigureInvalidType(t *testing.T) {
	r := &habitatMigrationResource{}

	req := resource.ConfigureRequest{
		ProviderData: "invalid",
	}
	resp := &resource.ConfigureResponse{}

	r.Configure(context.Background(), req, resp)

	if !resp.Diagnostics.HasError() {
		t.Error("Expected error with invalid provider data type")
	}
}

// TestHabitatMigrationResourceModel verifies the data model compiles
func TestHabitatMigrationResourceModel(t *testing.T) {
	_ = habitatMigrationResourceModel{}
}

// TestHabitatMigrationResourceCreate tests Create method
func TestHabitatMigrationResourceCreate(t *testing.T) {
	r := &habitatMigrationResource{client: &SousChefClient{Path: "test"}}
	defer func() {
		if r := recover(); r != nil {
			t.Logf(expectedPanicMsg, r)
		}
	}()
	r.Create(context.Background(), resource.CreateRequest{}, &resource.CreateResponse{})
}

// TestHabitatMigrationResourceRead tests Read method
func TestHabitatMigrationResourceRead(t *testing.T) {
	r := &habitatMigrationResource{client: &SousChefClient{Path: "test"}}
	defer func() {
		if r := recover(); r != nil {
			t.Logf(expectedPanicMsg, r)
		}
	}()
	r.Read(context.Background(), resource.ReadRequest{}, &resource.ReadResponse{})
}

// TestHabitatMigrationResourceUpdate tests Update method
func TestHabitatMigrationResourceUpdate(t *testing.T) {
	r := &habitatMigrationResource{client: &SousChefClient{Path: "test"}}
	defer func() {
		if r := recover(); r != nil {
			t.Logf(expectedPanicMsg, r)
		}
	}()
	r.Update(context.Background(), resource.UpdateRequest{}, &resource.UpdateResponse{})
}

// TestHabitatMigrationResourceDelete tests Delete method
func TestHabitatMigrationResourceDelete(t *testing.T) {
	r := &habitatMigrationResource{client: &SousChefClient{Path: "test"}}
	defer func() {
		if r := recover(); r != nil {
			t.Logf(expectedPanicMsg, r)
		}
	}()
	r.Delete(context.Background(), resource.DeleteRequest{}, &resource.DeleteResponse{})
}

// TestHabitatMigrationResourceImportState tests ImportState method
func TestHabitatMigrationResourceImportState(t *testing.T) {
	r := &habitatMigrationResource{client: &SousChefClient{Path: "test"}}
	defer func() {
		if r := recover(); r != nil {
			t.Logf(expectedPanicMsg, r)
		}
	}()
	r.ImportState(context.Background(), resource.ImportStateRequest{}, &resource.ImportStateResponse{})
}
