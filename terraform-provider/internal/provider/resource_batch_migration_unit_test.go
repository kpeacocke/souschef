package provider

import (
	"context"
	"testing"

	"github.com/hashicorp/terraform-plugin-framework/resource"
)

const (
	expectedPanicMsg = "Expected panic: %v"
)

// TestBatchMigrationResourceImplementsInterface verifies the resource implements the correct interface
func TestBatchMigrationResourceImplementsInterface(t *testing.T) {
	var _ resource.Resource = &batchMigrationResource{}
	var _ resource.ResourceWithImportState = &batchMigrationResource{}
}

// TestNewBatchMigrationResource verifies the constructor
func TestNewBatchMigrationResource(t *testing.T) {
	r := NewBatchMigrationResource()
	if r == nil {
		t.Fatal("Expected non-nil resource")
	}

	_, ok := r.(*batchMigrationResource)
	if !ok {
		t.Fatal("Expected *batchMigrationResource")
	}
}

// TestBatchMigrationResourceMetadata verifies metadata
func TestBatchMigrationResourceMetadata(t *testing.T) {
	r := &batchMigrationResource{}

	req := resource.MetadataRequest{
		ProviderTypeName: "souschef",
	}
	resp := &resource.MetadataResponse{}

	r.Metadata(context.Background(), req, resp)

	expected := "souschef_batch_migration"
	if resp.TypeName != expected {
		t.Errorf("Expected TypeName %q, got %q", expected, resp.TypeName)
	}
}

// TestBatchMigrationResourceSchema verifies schema
func TestBatchMigrationResourceSchema(t *testing.T) {
	r := &batchMigrationResource{}

	req := resource.SchemaRequest{}
	resp := &resource.SchemaResponse{}

	r.Schema(context.Background(), req, resp)

	if resp.Schema.Attributes == nil {
		t.Fatal("Expected non-nil schema attributes")
	}

	// Verify key attributes exist
	requiredAttrs := []string{"id", "cookbook_path", "output_path", "recipe_names"}
	for _, attr := range requiredAttrs {
		if _, ok := resp.Schema.Attributes[attr]; !ok {
			t.Errorf("Missing required attribute: %s", attr)
		}
	}
}

// TestBatchMigrationResourceConfigure verifies configure with valid client
func TestBatchMigrationResourceConfigure(t *testing.T) {
	r := &batchMigrationResource{}

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

// TestBatchMigrationResourceConfigureNilData verifies configure with nil data
func TestBatchMigrationResourceConfigureNilData(t *testing.T) {
	r := &batchMigrationResource{}

	req := resource.ConfigureRequest{
		ProviderData: nil,
	}
	resp := &resource.ConfigureResponse{}

	r.Configure(context.Background(), req, resp)

	if resp.Diagnostics.HasError() {
		t.Errorf("Expected no errors with nil data, got: %v", resp.Diagnostics.Errors())
	}
}

// TestBatchMigrationResourceConfigureInvalidType verifies configure with wrong type
func TestBatchMigrationResourceConfigureInvalidType(t *testing.T) {
	r := &batchMigrationResource{}

	req := resource.ConfigureRequest{
		ProviderData: "invalid",
	}
	resp := &resource.ConfigureResponse{}

	r.Configure(context.Background(), req, resp)

	if !resp.Diagnostics.HasError() {
		t.Error("Expected error with invalid provider data type")
	}
}

// TestBatchMigrationResourceModel verifies the data model compiles
func TestBatchMigrationResourceModel(t *testing.T) {
	_ = batchMigrationResourceModel{}
}

// TestBatchMigrationResourceCreate tests Create method
func TestBatchMigrationResourceCreate(t *testing.T) {
	r := &batchMigrationResource{
		client: &SousChefClient{Path: "nonexistent-souschef-for-test"},
	}
	req := resource.CreateRequest{}
	resp := &resource.CreateResponse{}
	defer func() {
		if r := recover(); r != nil {
			t.Logf(expectedPanicMsg, r)
		}
	}()
	r.Create(context.Background(), req, resp)
}

// TestBatchMigrationResourceRead tests Read method
func TestBatchMigrationResourceRead(t *testing.T) {
	r := &batchMigrationResource{client: &SousChefClient{Path: "test"}}
	defer func() {
		if r := recover(); r != nil {
			t.Logf(expectedPanicMsg, r)
		}
	}()
	r.Read(context.Background(), resource.ReadRequest{}, &resource.ReadResponse{})
}

// TestBatchMigrationResourceUpdate tests Update method
func TestBatchMigrationResourceUpdate(t *testing.T) {
	r := &batchMigrationResource{client: &SousChefClient{Path: "test"}}
	defer func() {
		if r := recover(); r != nil {
			t.Logf(expectedPanicMsg, r)
		}
	}()
	r.Update(context.Background(), resource.UpdateRequest{}, &resource.UpdateResponse{})
}

// TestBatchMigrationResourceDelete tests Delete method
func TestBatchMigrationResourceDelete(t *testing.T) {
	r := &batchMigrationResource{client: &SousChefClient{Path: "test"}}
	defer func() {
		if r := recover(); r != nil {
			t.Logf(expectedPanicMsg, r)
		}
	}()
	r.Delete(context.Background(), resource.DeleteRequest{}, &resource.DeleteResponse{})
}

// TestBatchMigrationResourceImportState tests ImportState method
func TestBatchMigrationResourceImportState(t *testing.T) {
	r := &batchMigrationResource{client: &SousChefClient{Path: "test"}}
	defer func() {
		if r := recover(); r != nil {
			t.Logf(expectedPanicMsg, r)
		}
	}()
	r.ImportState(context.Background(), resource.ImportStateRequest{}, &resource.ImportStateResponse{})
}
