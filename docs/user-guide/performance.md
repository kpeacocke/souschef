# Performance Benchmarks

SousChef includes comprehensive performance benchmarks to ensure fast and efficient cookbook conversions. This guide explains the benchmarking framework, current performance characteristics, and optimisation strategies.

## Benchmark Suite

SousChef uses pytest-benchmark to measure performance across key operations. Benchmarks run automatically in CI/CD and can be executed locally for performance validation.

### Running Benchmarks

```bash
# Run all benchmarks with detailed output
poetry run pytest tests/ -v --benchmark-only

# Run benchmarks with comparison
poetry run pytest tests/ --benchmark-only --benchmark-compare

# Save benchmark results
poetry run pytest tests/ --benchmark-only --benchmark-save=baseline

# Compare against saved baseline
poetry run pytest tests/ --benchmark-only --benchmark-compare=baseline

# Generate histogram visualizations
poetry run pytest tests/ --benchmark-only --benchmark-histogram
```

## Current Performance Metrics

All benchmarks measured on: Linux, Python 3.13, single-threaded execution.

### Parsing Operations

| Operation | Mean Time | Min Time | Max Time | Throughput |
|-----------|-----------|----------|----------|------------|
| Recipe parsing | 174.5 µs | 126.9 µs | 302.8 µs | 5,732 ops/sec |
| Attribute parsing | 150.8 µs | 107.7 µs | 384.2 µs | 6,633 ops/sec |
| Template parsing | 149.9 µs | 107.2 µs | 719.8 µs | 6,672 ops/sec |
| Metadata parsing | 182.3 µs | 122.2 µs | 2,025 ms | 5,486 ops/sec |
| Custom resource | 144.3 µs | 96.0 µs | 565.7 µs | 7,442 ops/sec |

**Key Insights:**
- Consistent sub-200µs performance for standard Chef artifacts
- Over 5,000 operations per second for all parsing tasks
- Metadata parsing has occasional outliers (max 2ms) due to file I/O

### Conversion Operations

| Operation | Mean Time | Min Time | Max Time | Throughput |
|-----------|-----------|----------|----------|------------|
| Basic conversion | 906 ns | 791 ns | 42.5 µs | 1,103,644 ops/sec |
| Resource conversion | 3.2 µs | 1.9 µs | 1,118 ms | 312,166 ops/sec |
| InSpec conversion | 170.5 µs | 119.0 µs | 4,663 ms | 5,864 ops/sec |
| Playbook generation | 1.4 ms | 721.1 µs | 15.8 ms | 717 ops/sec |

**Key Insights:**
- Nanosecond-level performance for basic conversions
- Resource conversion highly parallelizable
- Playbook generation is the most expensive operation (millisecondsrange)

### Structure Analysis

| Operation | Mean Time | Min Time | Max Time | Throughput |
|-----------|-----------|----------|----------|------------|
| Cookbook structure | 1.5 ms | 926.0 µs | 20.7 ms | 672 ops/sec |
| Large cookbook | 1.4 ms | 1.2 ms | 2.9 ms | 708 ops/sec |
| InSpec profiles | 632.6 µs | 443.0 µs | 3,256 ms | 1,581 ops/sec |

**Key Insights:**
- Consistent low-millisecond performance for structure analysis
- Large cookbooks (100+ resources) maintain similar performance
- File I/O dominates structure analysis time

## Performance Characteristics

### Scalability

SousChef scales linearly with cookbook size:

```python
# Small cookbook (10 resources): ~1.4ms
# Medium cookbook (50 resources): ~1.5ms  
# Large cookbook (100 resources): ~1.4ms
# Very large cookbook (500 resources): ~7-10ms (estimated)
```

**Why it scales well:**
- Parsing is single-pass with minimal backtracking
- No recursive tree transformations
- Lazy evaluation of optional fields
- Efficient path normalization caching

### Memory Usage

Typical memory footprint:

- **Small cookbook** (10 recipes): ~5-10 MB
- **Medium cookbook** (50 recipes): ~15-30 MB
- **Large cookbook** (100+ recipes): ~50-100 MB

Memory is linear with:
- Number of resources parsed
- Template file sizes
- Attribute complexity

**Memory optimization tips:**
- Process cookbooks in batches for large migrations
- Use streaming for template conversion
- Clear cached results between cookbook conversions

### CPU Utilization

SousChef is primarily CPU-bound during:
1. **Ruby parsing** (30-40% of time)
2. **YAML generation** (20-30% of time)
3. **Validation** (15-25% of time)
4. **AI API calls** (varies, network-bound)

I/O-bound operations:
- Reading Chef files from disk
- Writing Ansible playbooks
- Network requests to AI providers

## Optimization Strategies

### For Large Cookbooks

```python
# Process cookbooks in parallel
from concurrent.futures import ProcessPoolExecutor
from souschef.assessment import assess_cookbook

cookbooks = ["cookbook1", "cookbook2", "cookbook3"]

with ProcessPoolExecutor(max_workers=4) as executor:
    results = list(executor.map(assess_cookbook, cookbooks))
```

**Benefits:**
- 3-4x speedup on multi-core systems
- Reduced wall-clock time for batch conversions
- Each cookbook isolated in separate process

### For Incremental Conversions

```python
# Only convert changed recipes
from souschef.converters.playbook import convert_recipe_to_playbook

changed_recipes = get_changed_files()  # Your VCS diff logic
for recipe in changed_recipes:
    playbook = convert_recipe_to_playbook(recipe)
    save_playbook(playbook)
```

**Benefits:**
- Only process what changed
- Ideal for CI/CD pipelines
- Maintains conversion consistency

### For Template-Heavy Cookbooks

```python
# Pre-compile templates in batch
from souschef.parsers.template import parse_template

templates = find_all_templates(cookbook_path)
parsed_templates = {
    t: parse_template(t) for t in templates
}

# Reuse parsed templates during conversion
for recipe in recipes:
    playbook = convert_with_templates(recipe, parsed_templates)
```

**Benefits:**
- Avoid re-parsing templates
- Better cache locality
- 30-50% faster for template-heavy cookbooks

### For AI-Powered Conversions

```python
# Batch AI requests to reduce latency
from souschef.converters.playbook import generate_playbook_with_ai

# Collect all conversion requests
conversion_requests = prepare_batch(recipes)

# Send in batches of 10
for batch in chunks(conversion_requests, size=10):
    results = asyncio.run(batch_convert_with_ai(batch))
```

**Benefits:**
- Amortize network overhead
- Respect API rate limits
- Better error handling

## Performance Tuning

### Environment Variables

```bash
# Disable AI-assisted conversion for speed
export SOUSCHEF_DISABLE_AI=1

# Increase parser timeout for complex files
export SOUSCHEF_PARSER_TIMEOUT=60

# Enable performance profiling
export SOUSCHEF_PROFILE=1
```

### Configuration Options

```python
# In your conversion script
config = {
    "max_workers": 4,           # Parallel workers
    "cache_templates": True,    # Cache parsed templates
    "validate_output": False,   # Skip validation for speed
    "ai_batch_size": 10,       # AI request batch size
}

convert_cookbook(path, **config)
```

## Profiling and Diagnostics

### Built-in Profiler

```bash
# Profile a conversion
poetry run souschef convert --profile cookbook/ output/

# View profiling results
# Results saved to souschef_profile.prof
poetry run python -m pstats souschef_profile.prof
```

### Custom Profiling

```python
import cProfile
import pstats
from souschef.assessment import assess_cookbook

# Profile cookbook assessment
profiler = cProfile.Profile()
profiler.enable()

result = assess_cookbook("path/to/cookbook")

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(20)  # Top 20 functions
```

### Memory Profiling

```bash
# Install memory profiler
poetry add --dev memory-profiler

# Profile memory usage
poetry run python -m memory_profiler souschef/cli.py convert cookbook/
```

## Performance Regression Testing

Benchmarks run automatically in CI/CD to detect performance regressions:

```yaml
# .github/workflows/ci.yml
- name: Run benchmarks
  run: |
    poetry run pytest --benchmark-only \
      --benchmark-compare=main \
      --benchmark-compare-fail=mean:10%
```

**Regression thresholds:**
- Fail if mean time increases by >10%
- Warn if max time increases by >25%
- Alert if throughput drops by >15%

## Troubleshooting Slow Conversions

### Symptom: Parsing taking >1 second per file

**Possible causes:**
- Very complex Chef Ruby code
- Large template files (>100KB)
- Deep attribute nesting (>10 levels)

**Solutions:**
- Simplify Chef code before conversion
- Split large templates
- Flatten attribute structures

### Symptom: High memory usage (>500MB)

**Possible causes:**
- Processing too many cookbooks simultaneously
- Not clearing caches between conversions
- Very large attribute files

**Solutions:**
```python
import gc

for cookbook in large_cookbook_list:
    result = convert_cookbook(cookbook)
    process_result(result)
    
    # Manual garbage collection
    gc.collect()
```

### Symptom: Slow AI-powered conversions

**Possible causes:**
- Network latency to AI provider
- API rate limits
- Large prompts (>4000 tokens)

**Solutions:**
- Use regional AI endpoints
- Implement request caching
- Batch API calls
- Reduce prompt size

## Best Practices

1. **Measure first**: Profile before optimizing
2. **Batch operations**: Process cookbooks in logical groups
3. **Cache aggressively**: Reuse parsed templates and attributes
4. **Parallel processing**: Use multiple workers for independent cookbooks
5. **Monitor memory**: Clear caches for long-running processes
6. **Set timeouts**: Prevent hanging on complex files
7. **Use benchmarks**: Compare before/after optimization

## Future Performance Improvements

Planned optimizations:

- **Incremental parsing**: Only re-parse changed sections
- **Native parsing**: Cython extensions for hot paths
- **Streaming output**: Write playbooks as they're generated
- **Distributed processing**: Celery task queue for large migrations
- **Smart caching**: Persistent cache across runs
- **GPU acceleration**: For AI-powered conversions

## Contributing Benchmarks

When adding new features, include benchmarks:

```python
def test_benchmark_my_new_feature(benchmark):
    """Benchmark the new feature."""
    result = benchmark(my_new_feature, input_data)
    
    # Assert performance requirements
    assert benchmark.stats['mean'] < 0.001  # <1ms mean
    assert benchmark.stats['max'] < 0.010   # <10ms max
```

See [tests/test_integration.py](../../tests/test_integration.py) for examples.

## Resources

- **pytest-benchmark docs**: https://pytest-benchmark.readthedocs.io/
- **Python profiling**: https://docs.python.org/3/library/profile.html
- **Performance best practices**: https://wiki.python.org/moin/PythonSpeed

---

For questions about performance, open an issue: https://github.com/kpeacocke/souschef/issues
