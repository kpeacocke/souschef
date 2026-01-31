# AI-Based Repository Type Selection

## Overview

The SousChef repository generation now supports intelligent repository structure selection using AI analysis of cookbook complexity. This feature enables tailored repository structures based on actual cookbook characteristics rather than simple heuristics.

## Feature Description

### Smart Repository Determination

When AI credentials are provided, the `analyse_conversion_output()` function now:

1. **Evaluates cookbook complexity** using AI assessment
2. **Maps complexity scores** to optimal repository types
3. **Falls back gracefully** to heuristic rules if AI is unavailable

### Supported Repository Types

- **INVENTORY_FIRST**: Classic infrastructure management (complex cookbooks)
- **COLLECTION**: Ansible Collections for reusable automation (3+ roles or high complexity)
- **PLAYBOOKS_ROLES**: Simple playbooks with basic roles (low complexity, few recipes)
- **MONO_REPO**: Multi-project repository structure

## Architecture

### Decision Logic

The AI-based analysis uses complexity_score (0-100) to determine optimal structure:

```
Complexity Score | Num Roles | Decision
> 70             | >= 2      → COLLECTION (reusable automation)
> 70             | 1         → INVENTORY_FIRST (enterprise infra)
50-70            | >= 2      → COLLECTION
< 30             | <= 1      → PLAYBOOKS_ROLES (simple projects)
Default          |           → INVENTORY_FIRST
```

### Module Structure

**Location**: [souschef/generators/repo.py](../souschef/generators/repo.py)

#### Key Functions

- `analyse_conversion_output()` - Main entry point
- `_analyse_with_ai()` - AI-based analysis
- `_analyse_with_heuristics()` - Fallback heuristic rules

#### Parameters

```python
def analyse_conversion_output(
    cookbook_path: str,
    num_recipes: int = 0,
    num_roles: int = 0,
    has_multiple_apps: bool = False,
    needs_multi_env: bool = True,
    ai_provider: str = "",           # NEW: anthropic, openai, watson
    api_key: str = "",              # NEW: AI provider API key
    model: str = "",                # NEW: AI model to use
) -> RepoType:
```

## Integration Points

### UI Integration

The Streamlit UI ([souschef/ui/pages/cookbook_analysis.py](../souschef/ui/pages/cookbook_analysis.py)) can pass AI credentials:

```python
repo_type = analyse_conversion_output(
    cookbook_path=cookbook_path,
    num_recipes=num_recipes,
    num_roles=num_roles,
    has_multiple_apps=has_multiple_apps,
    needs_multi_env=True,
    ai_provider="anthropic",          # Optional
    api_key=st.session_state.get("ai_key", ""),  # Optional
    model="claude-3-5-sonnet-20241022",  # Optional
)
```

### MCP Server Integration

The MCP server ([souschef/server.py](../souschef/server.py)) can accept AI parameters:

```python
determined_type = analyse_conversion_output(
    cookbook_path=cookbook_path,
    num_recipes=num_recipes,
    num_roles=num_roles,
    has_multiple_apps=has_multiple_apps,
    needs_multi_env=True,
    ai_provider="anthropic",  # Optional
    api_key=api_key,          # Optional
    model=model,              # Optional
)
```

## AI Assessment Details

### Complexity Score Interpretation

- **0-30**: Simple, single-purpose cookbooks
  - Few recipes
  - No nested resources
  - Standard patterns
  - Recommendation: PLAYBOOKS_ROLES

- **30-70**: Medium complexity
  - Multiple recipes with dependencies
  - Some nested resources
  - Custom logic
  - Recommendation: Compatible with most structures

- **70-100**: High complexity
  - Enterprise-scale cookbooks
  - Multiple interdependent components
  - Custom resources and providers
  - Recommendation: INVENTORY_FIRST or COLLECTION

### Fallback Behavior

If AI assessment is unavailable or fails:

1. **Missing credentials**: Use heuristic rules
2. **API error**: Log error and fallback to heuristics
3. **Timeout**: Return None and use heuristics
4. **Malformed response**: Return None and use heuristics

## Testing

### Unit Tests

Located in [tests/unit/test_generators_repo.py](../tests/unit/test_generators_repo.py):

```python
# Test AI-based analysis with mock assessment
def test_ai_analysis_high_complexity_multiple_roles():
    mock_assessment = {"complexity_score": 75, ...}
    result = analyse_conversion_output(..., ai_provider="anthropic")
    assert result == RepoType.COLLECTION

# Test fallback when AI unavailable
def test_no_ai_credentials_uses_heuristics():
    result = analyse_conversion_output(...)
    assert result == RepoType.COLLECTION  # Heuristic-based
```

### Integration Tests

Located in [tests/integration/test_integration.py](../tests/integration/test_integration.py):

- `test_analyse_with_mock_ai_assessment` - AI decision logic
- `test_analyse_falls_back_without_ai_credentials` - Heuristic fallback
- `test_analyse_uses_heuristics_on_ai_error` - Error handling

## Performance Considerations

- **AI assessment**: ~1-3 seconds per cookbook (depends on size and provider)
- **Caching**: Consider caching assessment results for known cookbooks
- **Timeout**: Default 30 seconds, configurable via model parameter

## Security

- **API Keys**: Passed as parameters, never logged
- **Sensitive data**: Assessment results don't contain cookbook content
- **Provider validation**: Supports authenticated providers (Anthropic, OpenAI, Watson, Red Hat Lightspeed)
- **Local models**: Supports local model servers (Ollama, llama.cpp, vLLM, LM Studio) without requiring API keys

## Future Enhancements

- [ ] Cache AI assessments per cookbook
- [ ] Provide assessment reasoning in repository metadata
- [ ] UI option to override AI recommendation
- [ ] Integration with existing CI/CD assessment tools

## Examples

### Example 1: High Complexity Cookbook

```python
# Input
analyse_conversion_output(
    cookbook_path="/path/to/enterprise_cookbook",
    num_recipes=15,
    num_roles=3,
    has_multiple_apps=False,
    needs_multi_env=True,
    ai_provider="anthropic",
    api_key="sk-ant-...",
)

# AI Assessment: complexity_score = 85
# Decision: COLLECTION (high complexity + 3 roles)
# Recommendation: Organize as Ansible Collection for reusability
```

### Example 2: Simple Cookbook, No AI

```python
# Input (no AI credentials)
analyse_conversion_output(
    cookbook_path="/path/to/simple_cookbook",
    num_recipes=2,
    num_roles=1,
    has_multiple_apps=False,
    needs_multi_env=False,
)

# Falls back to heuristics
# Decision: PLAYBOOKS_ROLES (small, simple project)
# Recommendation: Simple playbooks + roles structure
```

### Example 3: AI Assessment Fails

```python
# Input (AI credentials provided, service unavailable)
analyse_conversion_output(
    cookbook_path="/path/to/cookbook",
    num_recipes=8,
    num_roles=2,
    ai_provider="anthropic",
    api_key="invalid_key",
)

# AI assessment fails: logs error
# Falls back to heuristics
# Decision: INVENTORY_FIRST (default fallback)
```

## Related Components

- [souschef/assessment.py](../souschef/assessment.py) - AI assessment functions
- [souschef/generators/repo.py](../souschef/generators/repo.py) - Repository generation
- [souschef/ui/pages/cookbook_analysis.py](../souschef/ui/pages/cookbook_analysis.py) - UI integration
- [souschef/server.py](../souschef/server.py) - MCP server integration

## References

- [Repository Architecture](./ARCHITECTURE.md)
- [Cookbook Assessment Guide](api-reference/assessment.md)
- [Testing Guide](./contributing.md#testing-requirements)
