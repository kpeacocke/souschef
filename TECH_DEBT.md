# Technical Debt Analysis - SousChef

**Analysis Date**: January 9, 2026  
**Branch**: feature/in-progress-improvements  
**Total Functions Analyzed**: 170+  
**Functions >50 lines**: 28  
**High Complexity (C-grade, >10)**: 15

## Executive Summary

The codebase is in **good overall health** with:
- ✅ **100% type hint coverage** on public functions
- ✅ **Zero linting/type errors** (ruff, mypy)
- ✅ **91% test coverage** (913 passing tests)
- ✅ **Comprehensive error handling** (recently completed)

Primary technical debt focuses on:
1. **Function length** - 5 functions >90 lines
2. **Cyclomatic complexity** - 15 functions with C-grade complexity (10+)
3. **Single Responsibility Principle** - Some functions handle multiple concerns

## Priority Matrix

### 🔴 HIGH PRIORITY (Complexity ≥13 or Length ≥100)

#### 1. `converters/playbook.py::_generate_inventory_script_content` (L418)
- **Lines**: 130 (LONGEST FUNCTION)
- **Complexity**: Unknown
- **Issues**: 
  - Generates entire dynamic inventory script in one function
  - Mixes script header, group logic, host vars, and metadata
  - String concatenation makes testing difficult
- **Impact**: Hard to maintain, test, and extend
- **Recommendation**: 
  ```python
  def _generate_inventory_script_content(search_patterns: dict[str, Any]) -> str:
      parts = [
          _build_script_header(),
          _build_group_logic(search_patterns),
          _build_host_vars(search_patterns),
          _build_meta_section()
      ]
      return '\n'.join(parts)
  ```

#### 2. `assessment.py::assess_chef_migration_complexity` (L21)
- **Lines**: 121
- **Complexity**: 13 (C-grade)
- **Issues**: 
  - Validates inputs, analyzes cookbooks, calculates scores, formats results
  - High cognitive load
  - Multiple return paths
- **Impact**: Difficult to unit test individual assessment steps
- **Recommendation**: Extract 4 helper functions:
  - `_validate_migration_inputs()`
  - `_analyze_cookbook_metrics()`
  - `_calculate_complexity_scores()`
  - `_format_assessment_results()`

#### 3. `converters/playbook.py::_split_guard_array_parts` (L1444)
- **Lines**: Unknown
- **Complexity**: 14 (HIGHEST COMPLEXITY)
- **Issues**: 
  - Complex Chef guard condition parsing
  - Nested conditionals for bracket matching
  - State tracking across iterations
- **Impact**: Bug-prone, hard to debug
- **Recommendation**: 
  - Use parser library (e.g., pyparsing) for formal grammar
  - Or: Extract bracket matching into `_match_brackets(text)` helper
  - Add comprehensive property-based tests

#### 4. `deployment.py::_analyze_cookbook_for_awx` (L595)
- **Lines**: 71
- **Complexity**: 14 (HIGHEST COMPLEXITY)
- **Issues**: 
  - Analyzes templates, attributes, resources, patterns in one function
  - Multiple analysis dimensions mixed together
- **Impact**: Difficult to add new analysis types
- **Recommendation**: Strategy pattern:
  ```python
  def _analyze_cookbook_for_awx(cookbook_path: str) -> dict:
      analyzers = [
          TemplateAnalyzer(),
          AttributeAnalyzer(),
          ResourceAnalyzer(),
          PatternDetector()
      ]
      return {name: analyzer.analyze(cookbook_path) for name, analyzer in analyzers}
  ```

#### 5. `converters/resource.py::_convert_chef_resource_to_ansible` (L128)
- **Lines**: 62
- **Complexity**: 13 (C-grade)
- **Issues**: 
  - Giant if/elif chain for 30+ resource types
  - Duplicated parameter mapping logic
  - Hard to add new resource types
- **Impact**: Brittle, error-prone when adding resources
- **Recommendation**: Lookup table + data-driven design:
  ```python
  RESOURCE_MAPPINGS = {
      'package': {'module': 'package', 'params': ['name', 'version', 'state']},
      'service': {'module': 'service', 'params': ['name', 'state', 'enabled']},
      # ... 30+ more
  }
  
  def _convert_chef_resource_to_ansible(resource_type: str, props: dict) -> dict:
      mapping = RESOURCE_MAPPINGS.get(resource_type)
      if not mapping:
          return _handle_unknown_resource(resource_type, props)
      return _build_task(mapping, props)
  ```

---

### 🟡 MEDIUM PRIORITY (Complexity 11-12 or Length 70-90)

#### 6. `server.py::_generate_complete_inventory_from_environments` (L1266)
- **Lines**: 69
- **Complexity**: 13 (C-grade)
- **Issues**: Environment parsing mixed with inventory generation
- **Recommendation**: Extract `_parse_environment_files()` and `_build_inventory_structure()`

#### 7. `server.py::_generate_databag_migration_recommendations` (L1815)
- **Lines**: 60
- **Complexity**: 13 (C-grade)
- **Issues**: Long recommendation text generation
- **Recommendation**: Template-based recommendations or recommendation builder class

#### 8. `deployment.py::generate_canary_deployment_strategy` (L439)
- **Lines**: 95
- **Complexity**: 10 (B-grade)
- **Issues**: Long deployment strategy generation
- **Recommendation**: Extract config building, task creation, strategy formatting

#### 9. `parsers/habitat.py::_update_quote_state` (L208)
- **Lines**: Unknown
- **Complexity**: 12 (C-grade)
- **Issues**: Complex quote state tracking
- **Recommendation**: State machine pattern or simplify logic

#### 10. `parsers/metadata.py::list_cookbook_structure` (L48)
- **Lines**: Unknown
- **Complexity**: 12 (C-grade)
- **Issues**: Complex directory traversal
- **Recommendation**: Break down into smaller traversal steps

---

### 🟢 LOW PRIORITY (Complexity 8-10 and Length 60-90)

These functions work well but could benefit from minor refactoring:

- `assessment.py::_assess_single_cookbook` (93 lines, C-11)
- `server.py::generate_ansible_vault_from_databags` (89 lines, C-11)
- `deployment.py::_generate_chef_inventory_script` (92 lines, Unknown)
- `assessment.py::generate_migration_plan` (91 lines, C-11)
- `deployment.py::generate_blue_green_deployment_playbook` (73 lines, Unknown)

---

## Refactoring Strategy

### Phase 1: Critical Infrastructure (Week 1-2)
1. **Resource converter** (`converters/resource.py`) - Data-driven approach
2. **Inventory script generator** (`converters/playbook.py`) - Extract helpers
3. **Guard parser** (`converters/playbook.py`) - Simplify complexity

### Phase 2: Assessment & Analysis (Week 3)
4. **Migration complexity** (`assessment.py`) - Extract validation & scoring
5. **AWX analyzer** (`deployment.py`) - Strategy pattern

### Phase 3: Polish & Testing (Week 4)
6. Refactor medium-priority functions
7. Add targeted tests for new helper functions
8. Update documentation

---

## Guidelines for Refactoring

### ✅ DO:
- Extract functions that do ONE thing
- Use data-driven designs for mappings (lookup tables vs if/elif chains)
- Add tests BEFORE refactoring (characterization tests)
- Keep commits small and focused
- Run full test suite after each change
- Use descriptive helper function names

### ❌ DON'T:
- Change behavior during refactoring (extract only)
- Skip test coverage for new functions
- Mix refactoring with feature additions
- Disable linting/type checking warnings

---

## Metrics Tracking

| Metric | Current | Target |
|--------|---------|--------|
| Functions >100 lines | 1 | 0 |
| Functions >80 lines | 5 | 2 |
| Complexity grade C (≥13) | 15 | 5 |
| Complexity grade B (6-12) | 45 | 50 |
| Test coverage | 91% | 93% |
| Type hint coverage | 100% | 100% |

---

## Next Steps

1. Review and approve this analysis
2. Create GitHub issues for HIGH priority items
3. Start with `_convert_chef_resource_to_ansible` (highest ROI)
4. Proceed systematically through priorities
5. Track progress in REFACTOR_PROGRESS.md

---

**Status**: 🟡 Analysis Complete - Ready for Phase 1 Implementation
