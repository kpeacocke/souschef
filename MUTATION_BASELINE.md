# Mutation Testing Baseline Report

**Date**: January 3, 2026
**Issue**: #22 - Implement mutation testing with mutmut

## Summary

Mutation testing configured and baseline scan completed successfully.

### Results
- **Total Mutants**: 6,861
- **Killed** (🎉): 5,975 (87.1%)
- **Survived** (🙁): 542 (7.9%)
- **Timeout** (⏰): 20 (0.3%)
- **No Tests** (🔇): 324 (4.7%)

### Mutation Score: **87.1%**

This is an excellent baseline! The project already has strong test coverage with 87% of mutations caught by tests.

## Key Findings

### Functions with No Test Coverage (324 mutants)
These functions have zero tests and need immediate attention:

1. **`_convert_chef_block_to_ansible`** - 53 mutants (Chef conditional blocks)
2. **`_extract_resource_subscriptions`** - 40 mutants (Resource subscription parsing)
3. **`_analyze_environments_structure`** - 55 mutants (Environment analysis)
4. **`_analyze_databag_structure`** - 58 mutants (Data bag analysis)
5. **`_extract_cookbook_attributes`** - 22 mutants (Attribute extraction for AWX)
6. **`_generate_survey_fields_from_attributes`** - 46 mutants (AWX survey generation)
7. **`_generate_blue_green_conversion_playbook`** - 22 mutants (Blue-green deployment)
8. **`_generate_canary_conversion_playbook`** - 22 mutants (Canary deployment)
9. **`_generate_big_bang_phases`** - 4 mutants (Migration phases)
10. **`main` in cli.py** - 2 mutants (CLI entry point)

### Functions with Weak Tests (542 survived mutants)
Functions where tests exist but don't catch all mutations:

**High Priority (10+ survived mutants each)**:
- `_find_search_patterns_in_content` - 29 survived
- `_extract_context` - 11 survived
- `_convert_chef_condition_to_ansible` - 12 survived
- `_generate_group_name_from_condition` - 11 survived
- `_create_group_config_for_equal_condition` - 9 survived
- `_extract_attributes_block` - 11 survived
- `_generate_complete_inventory_from_environments` - 19 survived
- `_assess_single_cookbook` - 20 survived

### Timeout Issues (20 mutants)
Some mutations cause tests to hang - these indicate potential infinite loops or performance issues in edge cases.

## Next Steps

Per issue #22 task list:

- [x] Add mutmut configuration to pyproject.toml
- [x] Run initial mutation scan
- [x] Document baseline mutation score (87.1%)
- [ ] Fix weak tests to improve mutation score to 90%+
- [ ] Add GitHub workflow for mutation testing on PRs
- [ ] Add mutation score badge to README

## Recommendations

1. **Priority 1**: Add tests for the 10 completely untested functions (324 mutants)
2. **Priority 2**: Strengthen tests for high-survivor functions (29+ survived each)
3. **Priority 3**: Investigate and fix timeout issues (20 mutants)
4. **Target**: Achieve 90%+ mutation score (currently 87.1%)

## How to Run

```bash
# Run mutation testing (takes ~15 minutes)
poetry run mutmut run

# View results summary
poetry run mutmut results

# View specific mutant details
poetry run mutmut show <mutant_id>

# Apply a surviving mutant to see what changed
poetry run mutmut apply <mutant_id>
```

## Configuration

Mutation testing configuration in `pyproject.toml`:

```toml
[tool.mutmut]
backup = false
```

Additional configuration in `.mutmut.toml`:

```toml
paths_to_mutate = "souschef/"
tests_dir = "tests/"
backup = false
```
