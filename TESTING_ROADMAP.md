# Testing Improvement Roadmap

## Current State
- **Coverage**: 84% (souschef/server.py: 84%, souschef/cli.py: 88%)
- **Test Count**: 355 tests across 12,000 lines
- **Test Types**: Unit, Integration, Property-Based, CLI
- **Missing Lines**: 435 statements uncovered

---

## High Priority (Do These Next)

### 1. Mutation Testing Configuration ⚠️
**Status**: mutmut installed but not configured
**Effort**: 2-3 days
**Impact**: Reveals weak tests that pass even when code is broken

**Tasks**:
- [ ] Add mutmut configuration to pyproject.toml
- [ ] Run initial mutation scan: `poetry run mutmut run`
- [ ] Analyze survivors: `poetry run mutmut results`
- [ ] Fix weak tests (expect 60-70% initial mutation score)
- [ ] Add GitHub workflow for mutation testing on PRs

**Config to add**:
```toml
[tool.mutmut]
paths_to_mutate = "souschef/"
backup = false
runner = "poetry run pytest -x --assert=plain -q"
tests_dir = "tests/"
```

---

### 2. MCP Protocol Testing ⚠️
**Status**: Missing entirely
**Effort**: 1 day
**Impact**: Critical for production readiness

**Tasks**:
- [ ] Test MCP server initialization and startup
- [ ] Test tool registration with FastMCP
- [ ] Test tool invocation via MCP protocol
- [ ] Test error serialization over MCP
- [ ] Test concurrent MCP requests
- [ ] Add tests/test_mcp.py with MCP client tests

**Tests to add**:
```python
def test_mcp_server_starts()
def test_mcp_tool_registration()
def test_mcp_tool_invocation_parse_recipe()
def test_mcp_error_handling()
def test_mcp_concurrent_requests()
```

---

### 3. Error Recovery Testing
**Status**: 435 uncovered lines, mostly error paths
**Effort**: 3-5 days
**Impact**: Improves robustness and gets to 95%+ coverage

**Uncovered Error Paths**:
- [ ] Lines 1706-1711: Malformed cookbook metadata
- [ ] Lines 2962-2991: AWX workflow generation errors (30 lines)
- [ ] Lines 4303-4313: Resource attribute extraction edge cases
- [ ] Lines 4417-4427: Chef search conversion errors
- [ ] Lines 4883-4922: Deployment pattern errors (40 lines)
- [ ] Lines 5013-5034: Migration assessment edge cases
- [ ] Lines 6757-6773: Data bag encryption errors

**Tests to add**:
```python
# Malformed/corrupted files
def test_parse_recipe_with_syntax_errors()
def test_parse_recipe_with_invalid_utf8()
def test_parse_recipe_with_mixed_encodings()

# Resource limits
def test_parse_recipe_with_10000_resources()
def test_parse_template_with_deeply_nested_erb()
def test_parse_recipe_with_circular_dependencies()

# Chef version edge cases
def test_parse_chef_13_vs_14_vs_15_syntax()
def test_parse_policyfile_vs_berkshelf()
def test_custom_resource_with_multiple_inheritance()
```

---

## Medium Priority (Next Sprint)

### 4. Snapshot Testing 📸
**Status**: Missing entirely
**Effort**: 2 days
**Impact**: Prevents regressions in complex output formats

**Tasks**:
- [ ] Install syrupy: `poetry add --group dev syrupy`
- [ ] Add snapshot tests for playbook generation
- [ ] Add snapshot tests for Jinja2 template conversion
- [ ] Add snapshot tests for InSpec control output
- [ ] Add snapshot tests for markdown reports
- [ ] Add snapshot tests for AWX job templates (~20 tests total)

**Tests to add**:
```python
def test_playbook_generation_snapshot(snapshot)
def test_template_conversion_snapshot(snapshot)
def test_inspec_control_snapshot(snapshot)
def test_migration_report_snapshot(snapshot)
def test_awx_workflow_snapshot(snapshot)
```

---

### 5. Integration Accuracy Testing
**Status**: Have parsing tests, missing validation tests
**Effort**: 3-4 days
**Impact**: Validates conversion correctness

**Tasks**:
- [ ] Install ansible-lint: `poetry add --group dev ansible-lint`
- [ ] Add round-trip validation tests
- [ ] Validate generated Ansible YAML is syntactically correct
- [ ] Validate generated Jinja2 templates compile
- [ ] Test Chef → Ansible → execution equivalence
- [ ] Add 15-20 accuracy validation tests

**Tests to add**:
```python
def test_nginx_recipe_generates_valid_ansible()
def test_template_conversion_produces_valid_jinja2()
def test_converted_playbook_passes_ansible_lint()
def test_chef_package_to_ansible_package_equivalence()
def test_chef_template_vars_match_jinja2_vars()
```

---

### 6. Test Fixture Diversity
**Status**: Limited to 1 sample cookbook
**Effort**: 1-2 days
**Impact**: Tests against real-world Chef code

**Current Fixtures**:
- tests/fixtures/sample_cookbook/ (1 cookbook)
- tests/fixtures/sample_inspec_profile/ (1 profile)
- tests/fixtures/*.rb (2-3 simple recipes)

**Tasks**:
- [ ] Create tests/fixtures/real_world_cookbooks/
- [ ] Add Chef Supermarket cookbooks: nginx, mysql, postgresql, apache2, docker
- [ ] Add examples for Chef 12, 13, 14, 15, 16, 17 syntax variations
- [ ] Add Policyfile-based cookbooks
- [ ] Add Berkshelf-based cookbooks
- [ ] Add complex LWRP examples
- [ ] Add malformed/corrupted Chef files for error testing
- [ ] Add Windows Chef cookbook examples

**Cookbooks to add**:
- [ ] nginx (community cookbook)
- [ ] mysql (official cookbook)
- [ ] postgresql (complex resources)
- [ ] apache2 (multiple platforms)
- [ ] docker (modern Chef patterns)

---

## Lower Priority (Nice to Have)

### 7. Performance & Load Testing 📈
**Status**: 7 basic benchmarks exist
**Effort**: 1-2 days
**Impact**: Ensures scale handling

**Current Benchmarks**:
- ✅ test_benchmark_conversion
- ✅ test_benchmark_parse_attributes
- ✅ test_benchmark_inspec_conversion
- ✅ test_benchmark_custom_resource_parsing
- ✅ test_benchmark_template_parsing
- ✅ test_benchmark_parse_recipe
- ✅ test_benchmark_inspec_profile_parsing

**Missing Tests**:
- [ ] Memory usage tests (large cookbooks)
- [ ] Concurrent tool invocation tests
- [ ] Streaming output tests for huge files
- [ ] Parse 500MB cookbook without OOM
- [ ] 1000 concurrent MCP requests

**Tests to add**:
```python
def test_parse_500mb_cookbook_memory_usage(benchmark)
def test_memory_usage_stays_under_100mb()
def test_concurrent_mcp_tool_invocations()
def test_streaming_large_output()
```

---

## Testing Metrics Goals

**Current State**:
- Line Coverage: 84%
- Test Count: 355
- Mutation Score: Unknown (not configured)
- Snapshot Tests: 0

**Target State**:
- Line Coverage: 95%+
- Test Count: 450+
- Mutation Score: 80%+
- Snapshot Tests: 20+
- MCP Tests: 10+
- Accuracy Tests: 20+

---

## Quick Wins (Next 2 Hours)

Want immediate impact? Start here:

1. **Add mutmut config** (5 minutes)
   - Add to pyproject.toml
   - Run first scan

2. **Test MCP server startup** (30 minutes)
   - Add tests/test_mcp.py
   - Test basic server initialization

3. **Test one error path** (30 minutes)
   - Pick lines 1706-1711 (metadata errors)
   - Add test_parse_metadata_with_syntax_error()

4. **Add one snapshot test** (30 minutes)
   - Install syrupy
   - Add test_playbook_generation_snapshot()

5. **Test memory usage** (30 minutes)
   - Add test_parse_large_cookbook_memory()
   - Use tracemalloc

---

## Implementation Order

**Week 1**: Foundation
- Day 1-2: Mutation testing setup + initial scan
- Day 3: MCP protocol tests
- Day 4-5: Error recovery tests (cover 200+ uncovered lines)

**Week 2**: Quality Improvements
- Day 1-2: Snapshot testing setup + 20 tests
- Day 3-4: Integration accuracy tests + ansible-lint validation
- Day 5: Test fixture diversity (add 5 real cookbooks)

**Week 3**: Performance & Polish
- Day 1-2: Performance/load testing
- Day 3-4: Fix remaining mutation test failures
- Day 5: Documentation and CI/CD integration

---

## CI/CD Integration

After implementing tests, add workflows:

1. **Mutation Testing** (.github/workflows/mutation-testing.yml)
   - Run on PRs to main/develop
   - Fail if mutation score drops below threshold

2. **Snapshot Testing**
   - Auto-update snapshots on main branch merges
   - Require manual review for snapshot changes in PRs

3. **Performance Regression**
   - Track benchmark trends
   - Alert on >10% performance degradation

---

## Success Criteria

✅ **Phase 1 Complete** (Weeks 1-2):
- Mutation score ≥ 70%
- Line coverage ≥ 90%
- MCP tests passing
- 20+ snapshot tests
- All error paths tested

✅ **Phase 2 Complete** (Week 3):
- Mutation score ≥ 80%
- Line coverage ≥ 95%
- 10+ real cookbook fixtures
- Performance benchmarks passing
- CI/CD fully integrated

✅ **Production Ready**:
- Mutation score ≥ 85%
- Line coverage ≥ 95%
- All test types implemented
- Zero known test gaps
- Comprehensive fixture library
