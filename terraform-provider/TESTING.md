# Terraform Provider Testing Guide

## Test Coverage Summary

**Current Coverage:** 10.4% (55 passing unit tests)  
**Starting Coverage:** 0.3% (6 acceptance tests only)  
**Improvement:** 34x increase

### Coverage Breakdown

#### ✅ Fully Covered (100%)
- **Provider Core** (8 functions)
  - Factory methods (`New()`)
  - Metadata configuration
  - Schema definitions
  - Resource/DataSource registration
  
- **All 4 Resources** (24 functions)
  - `NewMigrationResource()`, `NewBatchMigrationResource()`, `NewHabitatMigrationResource()`, `NewInSpecMigrationResource()`
  - Metadata(), Schema(), Configure() for each resource
  - Interface compliance verification
  - Error handling for invalid provider data

- **All 2 Data Sources** (16 functions)
  - `NewAssessmentDataSource()`, `NewCostEstimateDataSource()`
  - Metadata(), Schema(), Configure() for each data source
  - Interface compliance verification
  - Error handling for invalid provider data

#### ⚠️ Not Covered (0% - 23 functions)

**Provider Configuration** (1 function)
- `(*SousChefProvider).Configure()` - Requires valid Config object with schema

**Data Source Read Operations** (2 functions)
- `(*assessmentDataSource).Read()` - Calls `souschef assess-cookbook` CLI
- `(*costEstimateDataSource).Read()` - Performs cost calculations

**Resource CRUD Operations** (20 functions)
- `Create()` - 4 resources (calls CLI, writes files)
- `Read()` - 4 resources (reads state from files)
- `Update()` - 4 resources (updates existing resources)
- `Delete()` - 4 resources (removes files/state)
- `ImportState()` - 4 resources (imports existing resources)

### Why This Coverage Level is Appropriate

#### Unit Tests Cover: ✅
1. **Interface Compliance** - Verify all resources/data sources implement correct Terraform interfaces
2. **Metadata & Schema** - Ensure proper type registration and attribute definitions
3. **Configuration Logic** - Validate provider data handling and error cases
4. **Type Safety** - Confirm all models compile and have expected fields
5. **Error Handling** - Test invalid provider data, nil checks, type mismatches

#### Acceptance Tests Cover: 🔬
1. **CRUD Operations** - Full lifecycle testing with real CLI execution
2. **File I/O** - Actual file reading/writing operations
3. **External Dependencies** - SousChef CLI integration
4. **End-to-End Workflows** - Complete Terraform apply/destroy cycles

**Note:** Acceptance tests require `TF_ACC=1` environment variable and full test infrastructure.

## Test Organization

```
internal/provider/
├── *_test.go                        # Acceptance tests (require TF_ACC=1)
│   ├── data_source_assessment_test.go
│   ├── data_source_cost_estimate_test.go
│   ├── resource_migration_test.go
│   ├── resource_batch_migration_test.go
│   ├── resource_habitat_migration_test.go
│   └── resource_inspec_migration_test.go
│
└── *_unit_test.go                   # Unit tests (run by default)
    ├── provider_unit_test.go
    ├── data_source_assessment_unit_test.go
    ├── data_source_cost_estimate_unit_test.go
    ├── resource_migration_unit_test.go
    ├── resource_batch_migration_unit_test.go
    ├── resource_habitat_migration_unit_test.go
    └── resource_inspec_migration_unit_test.go
```

## Running Tests

### Unit Tests Only (Default)
```bash
cd terraform-provider
go test -v ./internal/provider
```

**Output:** 55 passing tests, 6 skipped acceptance tests

### With Coverage Report
```bash
cd terraform-provider
go test -v -cover ./internal/provider
go test -coverprofile=coverage.out ./internal/provider
go tool cover -html=coverage.out -o coverage.html
```

### Acceptance Tests (Full Integration)
```bash
cd terraform-provider
export TF_ACC=1
go test -v ./internal/provider
```

**Requirements:**
- `TF_ACC=1` environment variable
- SousChef CLI installed and in PATH
- Test fixtures in place
- Write permissions for output directories

### Specific Test Patterns
```bash
# Run only schema tests
go test -v ./internal/provider -run Schema

# Run only configure tests
go test -v ./internal/provider -run Configure

# Run tests for specific resource
go test -v ./internal/provider -run Migration
```

## Test Coverage Goals

### Current: 10.4% ✅
**Rationale:** Unit tests cover all provider framework integration code (metadata, schema, configuration). This is the code most likely to break from Terraform framework upgrades.

### Target: 15-20% (Optional Enhancement)
**Additional Coverage:**
- Mock-based tests for CLI execution error paths
- Validation logic for input parameters
- Edge cases in state management

### What NOT to Target with Unit Tests

❌ **Full CRUD Operations**
- Reason: Requires mocking `exec.CommandContext`, file I/O, complex Terraform state
- Better Tested By: Acceptance tests with real infrastructure

❌ **File System Operations**  
- Reason: Hard to mock reliably across platforms
- Better Tested By: Integration tests with temporary directories

❌ **CLI Output Parsing**
- Reason: Requires real CLI output fixtures
- Better Tested By: Acceptance tests or dedicated integration tests

## Test Patterns

### Unit Test Pattern
```go
func TestResourceMetadata(t *testing.T) {
    r := &migrationResource{}
    
    req := resource.MetadataRequest{
        ProviderTypeName: "souschef",
    }
    resp := &resource.MetadataResponse{}
    
    r.Metadata(context.Background(), req, resp)
    
    expected := "souschef_migration"
    if resp.TypeName != expected {
        t.Errorf("Expected %q, got %q", expected, resp.TypeName)
    }
}
```

### Acceptance Test Pattern
```go
func TestAccMigrationResource(t *testing.T) {
    if os.Getenv("TF_ACC") == "" {
        t.Skip("Acceptance tests skipped unless env 'TF_ACC' set")
        return
    }
    
    resource.Test(t, resource.TestCase{
        PreCheck:                 func() { testAccPreCheck(t) },
        ProtoV6ProviderFactories: testAccProtoV6ProviderFactories,
        Steps: []resource.TestStep{
            {
                Config: testAccMigrationResourceConfig,
                Check: resource.ComposeTestCheckFunc(
                    resource.TestCheckResourceAttr("souschef_migration.test", "recipe_name", "default"),
                ),
            },
        },
    })
}
```

## Security Testing

### Fixed Issues
- ✅ Replaced 4 hardcoded `/tmp/` paths with workspace-relative paths
- ✅ Added `.env.test` to gitignore
- ✅ All security warnings resolved in Go provider code

### Test Fixtures
All test output paths use `/workspaces/souschef/test-output/` to:
1. Avoid `/tmp/` security warnings
2. Enable debugging (output persists)
3. Maintain workspace isolation

## Continuous Integration

### GitHub Actions Workflow
```yaml
- name: Run Go Tests
  run: |
    cd terraform-provider
    go test -v -cover ./internal/provider
```

**Note:** Acceptance tests (`TF_ACC=1`) are NOT run in CI due to:
- Require SousChef CLI installation
- Need significant test infrastructure
- Longer execution time (minutes vs seconds)

## Contributing

When adding new resources or data sources:

1. **Create unit test file** (`*_unit_test.go`)
   - Test interface compliance
   - Test metadata and schema
   - Test configure with valid/invalid data
   - Test model struct compilation

2. **Create acceptance test file** (`*_test.go`)
   - Test full Create operation
   - Test Read/Update/Delete if applicable
   - Test import functionality
   - Add `TF_ACC` skip check

3. **Update this documentation**
   - Add new test file to organization section
   - Update coverage numbers after testing
   - Document any special test requirements

## Troubleshooting

### "Acceptance tests skipped unless env 'TF_ACC' set"
**Solution:** This is expected behavior. Acceptance tests are opt-in via `export TF_ACC=1`.

### "souschef: command not found" during acceptance tests
**Solution:** Install SousChef CLI or run unit tests only (default behavior).

### Coverage seems low compared to other projects
**Context:** Terraform providers typically have low unit test coverage because:
- Most code interacts with external systems (CLI, APIs, files)
- Proper testing requires acceptance tests with real infrastructure
- Framework integration code (metadata/schema) is what unit tests cover
- Industry standard is 10-30% unit coverage + comprehensive acceptance tests

### Tests fail with "nil pointer dereference"
**Likely Cause:** Resource/data source methods called without Configure() being invoked first.  
**Solution:** Ensure test calls Configure() with valid client before calling Read/Create/Update/Delete.

## References

- [Terraform Provider Testing Docs](https://developer.hashicorp.com/terraform/plugin/testing)
- [terraform-plugin-framework Testing Guide](https://developer.hashicorp.com/terraform/plugin/framework/acctests)
- [SousChef Project Documentation](../README.md)
