"""
Performance and load tests for SousChef MCP server.

This module tests memory usage, concurrent processing, large file handling,
and performance regression prevention.
"""

import asyncio
import json
import tracemalloc
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from souschef.server import (
    convert_bash_to_ansible,
    convert_cookbook_comprehensive,
    convert_habitat_to_dockerfile,
    convert_inspec_to_test,
    convert_powershell,
    convert_puppet_manifest_to_ansible,
    convert_resource_to_task,
    convert_salt_pillar_to_vars,
    convert_salt_to_ansible,
    generate_playbook_from_recipe,
    list_cookbook_structure,
    parse_attributes,
    parse_custom_resource,
    parse_habitat_plan,
    parse_inspec_profile,
    parse_powershell,
    parse_puppet_manifest,
    parse_recipe,
    parse_salt_pillar,
    parse_salt_sls,
    parse_salt_top,
    parse_template,
    read_cookbook_metadata,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"
BENCHMARK_CORPUS_DIR = FIXTURES_DIR / "benchmark_corpus"
BENCHMARK_CASES: list[dict[str, Any]] = json.loads(
    (BENCHMARK_CORPUS_DIR / "cases.json").read_text(encoding="utf-8")
)["cases"]
_CORPUS_OPERATIONS: dict[str, Callable[..., str]] = {
    "convert_bash_to_ansible": convert_bash_to_ansible,
    "convert_habitat_to_dockerfile": convert_habitat_to_dockerfile,
    "convert_inspec_to_test": convert_inspec_to_test,
    "convert_powershell": convert_powershell,
    "convert_puppet_manifest_to_ansible": convert_puppet_manifest_to_ansible,
    "convert_salt_pillar_to_vars": convert_salt_pillar_to_vars,
    "convert_salt_to_ansible": convert_salt_to_ansible,
    "generate_playbook_from_recipe": generate_playbook_from_recipe,
    "parse_attributes": parse_attributes,
    "parse_custom_resource": parse_custom_resource,
    "parse_habitat_plan": parse_habitat_plan,
    "parse_inspec_profile": parse_inspec_profile,
    "parse_powershell": parse_powershell,
    "parse_puppet_manifest": parse_puppet_manifest,
    "parse_recipe": parse_recipe,
    "parse_salt_pillar": parse_salt_pillar,
    "parse_salt_sls": parse_salt_sls,
    "parse_salt_top": parse_salt_top,
    "parse_template": parse_template,
}


def _run_benchmark_corpus_case(case: dict[str, Any]) -> str:
    """Run one manifest-defined parser or converter and check its outcome."""
    source_path = FIXTURES_DIR / case["path"]
    operation = _CORPUS_OPERATIONS[case["operation"]]
    result = operation(str(source_path), **case.get("arguments", {}))
    assert isinstance(result, str)
    assert result.strip()

    if "contains" in case:
        assert case["contains"] in result
    if "json_status" in case:
        assert json.loads(result)["status"] == case["json_status"]
    if "json_key" in case:
        assert case["json_key"] in json.loads(result)
    if "json_expected" in case:
        result_data = json.loads(result)
        for key, value in case["json_expected"].items():
            assert result_data.get(key) == value
    if "json_minimums" in case:
        result_data = json.loads(result)
        for key, minimum in case["json_minimums"].items():
            actual = result_data[key]
            actual_count = actual if isinstance(actual, int) else len(actual)
            assert actual_count >= minimum
    if case["kind"] == "malformed":
        assert "Traceback" not in result
    return result


def _run_benchmark_corpus_family(cases: list[dict[str, Any]]) -> tuple[int, int]:
    """Run a fixed set of cases and return case/output sizes for benchmark use."""
    results = [_run_benchmark_corpus_case(case) for case in cases]
    return len(results), sum(map(len, results))


@pytest.mark.parametrize(
    "case",
    BENCHMARK_CASES,
    ids=[
        f"{case['family']}-{case['version']}-{case['variant']}"
        for case in BENCHMARK_CASES
    ],
)
def test_benchmark_corpus_case_is_handled(
    case: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Exercise every versioned corpus case, including malformed inputs."""
    monkeypatch.setenv("SOUSCHEF_WORKSPACE_ROOT", str(FIXTURES_DIR))
    _run_benchmark_corpus_case(case)


class TestMemoryUsage:
    """Tests for memory usage and efficiency."""

    def test_parse_recipe_memory_stays_reasonable(self) -> None:
        """Test that parsing a recipe doesn't use excessive memory."""
        recipe_path = FIXTURES_DIR / "sample_cookbook" / "recipes" / "default.rb"

        tracemalloc.start()
        parse_recipe(str(recipe_path))
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Should use less than 10MB for a small recipe
        assert peak < 10 * 1024 * 1024, f"Peak memory usage: {peak / 1024 / 1024:.2f}MB"

    def test_parse_multiple_recipes_memory_cleanup(self) -> None:
        """Test that memory is cleaned up between parsing operations."""
        recipe_path = FIXTURES_DIR / "sample_cookbook" / "recipes" / "default.rb"

        tracemalloc.start()

        # Parse the same recipe 100 times
        for _ in range(100):
            parse_recipe(str(recipe_path))

        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Should not accumulate memory excessively
        # Peak should be less than 50MB for 100 parses
        assert peak < 50 * 1024 * 1024, f"Peak memory usage: {peak / 1024 / 1024:.2f}MB"

    def test_parse_custom_resource_memory_usage(self) -> None:
        """Test that custom resource parsing doesn't use excessive memory."""
        resource_path = FIXTURES_DIR / "sample_cookbook" / "resources" / "database.rb"

        tracemalloc.start()
        parse_custom_resource(str(resource_path))
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Should use less than 5MB for a small resource
        assert peak < 5 * 1024 * 1024, f"Peak memory usage: {peak / 1024 / 1024:.2f}MB"

    def test_parse_template_memory_usage(self) -> None:
        """Test that template parsing doesn't use excessive memory."""
        template_path = (
            FIXTURES_DIR
            / "sample_cookbook"
            / "templates"
            / "default"
            / "config.yml.erb"
        )

        tracemalloc.start()
        parse_template(str(template_path))
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Should use less than 5MB for a small template
        assert peak < 5 * 1024 * 1024, f"Peak memory usage: {peak / 1024 / 1024:.2f}MB"

    def test_cookbook_structure_memory_usage(self) -> None:
        """Test that cookbook structure analysis doesn't use excessive memory."""
        cookbook_path = FIXTURES_DIR / "sample_cookbook"

        tracemalloc.start()
        list_cookbook_structure(str(cookbook_path))
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Should use less than 20MB for a full cookbook
        assert peak < 20 * 1024 * 1024, f"Peak memory usage: {peak / 1024 / 1024:.2f}MB"


class TestLargeFileHandling:
    """Tests for handling large files and cookbooks."""

    def test_large_recipe_with_many_resources(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """Test parsing a recipe with many resources."""
        monkeypatch.setenv("SOUSCHEF_WORKSPACE_ROOT", str(tmp_path))

        # Generate a recipe with 1000 resources
        large_recipe = tmp_path / "large_recipe.rb"
        resources = []
        for i in range(1000):
            resources.append(
                f"""
package 'package-{i}' do
  action :install
  version '1.0.{i}'
end
"""
            )

        large_recipe.write_text("\n".join(resources))

        # Should parse without error
        result = parse_recipe(str(large_recipe))
        assert "Resource 1:" in result
        assert "package" in result.lower()

    def test_large_attribute_file(self, tmp_path: Path, monkeypatch) -> None:
        """Test parsing an attribute file with many attributes."""
        monkeypatch.setenv("SOUSCHEF_WORKSPACE_ROOT", str(tmp_path))

        # Generate an attribute file with 1000 attributes
        large_attrs = tmp_path / "large_attributes.rb"
        attributes = []
        for i in range(1000):
            attributes.append(f"default['app']['setting_{i}'] = 'value_{i}'\n")

        large_attrs.write_text("".join(attributes))

        # Should parse without error
        result = parse_attributes(str(large_attrs))
        assert len(result) > 0
        assert "setting_" in result

    def test_deep_nested_attributes(self, tmp_path: Path, monkeypatch) -> None:
        """Test parsing deeply nested attributes."""
        monkeypatch.setenv("SOUSCHEF_WORKSPACE_ROOT", str(tmp_path))

        # Generate deeply nested attributes
        nested_attrs = tmp_path / "nested_attributes.rb"
        nested_attrs.write_text("""
default['level1']['level2']['level3']['level4']['level5']['setting'] = 'value'
default['level1']['level2']['level3']['level4']['level5']['count'] = 100
default['level1']['level2']['level3']['level4']['level5']['enabled'] = true
default['level1']['level2']['level3']['array'] = ['a', 'b', 'c']
default['level1']['level2']['hash'] = { 'key' => 'value' }
""")

        # Should parse without error
        result = parse_attributes(str(nested_attrs))
        assert len(result) > 0
        assert "level1" in result

    def test_large_template_file(self, tmp_path: Path, monkeypatch) -> None:
        """Test parsing a large template file."""
        monkeypatch.setenv("SOUSCHEF_WORKSPACE_ROOT", str(tmp_path))

        # Generate a template with many variables
        large_template = tmp_path / "large_template.erb"
        template_lines = ["# Large Template File\n"]
        for i in range(500):
            template_lines.append(f"setting_{i} = <%= @setting_{i} %>\n")

        large_template.write_text("".join(template_lines))

        # Should parse without error
        result = parse_template(str(large_template))
        assert len(result) > 0
        assert "setting_" in result

    def test_cookbook_with_many_files(self, tmp_path: Path, monkeypatch) -> None:
        """Test analyzing a cookbook with many files."""
        monkeypatch.setenv("SOUSCHEF_WORKSPACE_ROOT", str(tmp_path))

        # Create a cookbook with many recipes and resources
        cookbook = tmp_path / "large_cookbook"
        cookbook.mkdir()

        # Create metadata
        metadata = cookbook / "metadata.rb"
        metadata.write_text("name 'large_cookbook'\nversion '1.0.0'\n")

        # Create many recipes
        recipes_dir = cookbook / "recipes"
        recipes_dir.mkdir()
        for i in range(50):
            recipe = recipes_dir / f"recipe_{i}.rb"
            recipe.write_text(f"package 'package-{i}' do\n  action :install\nend\n")

        # Should analyze without error
        result = list_cookbook_structure(str(cookbook))
        assert len(result) > 0
        assert "recipe_" in result


class TestConcurrentProcessing:
    """Tests for concurrent request handling."""

    @pytest.mark.anyio
    async def test_concurrent_recipe_parsing(self) -> None:
        """Test parsing multiple recipes concurrently."""
        recipe_path = FIXTURES_DIR / "sample_cookbook" / "recipes" / "default.rb"

        # Parse the same recipe 50 times concurrently
        async def parse_async() -> str:
            # Simulate async work by wrapping sync call
            return await asyncio.to_thread(parse_recipe, str(recipe_path))

        tasks = [parse_async() for _ in range(50)]
        results = await asyncio.gather(*tasks)

        # All results should be valid
        assert len(results) == 50
        for result in results:
            assert "Resource" in result
            assert len(result) > 0

    @pytest.mark.anyio
    async def test_concurrent_different_operations(self) -> None:
        """Test different operations running concurrently."""
        recipe_path = FIXTURES_DIR / "sample_cookbook" / "recipes" / "default.rb"
        attrs_path = FIXTURES_DIR / "sample_cookbook" / "attributes" / "default.rb"
        resource_path = FIXTURES_DIR / "sample_cookbook" / "resources" / "database.rb"
        template_path = (
            FIXTURES_DIR
            / "sample_cookbook"
            / "templates"
            / "default"
            / "config.yml.erb"
        )

        # Run different operations concurrently
        async def run_operations() -> tuple[str, str, str, str]:
            recipe_task = asyncio.to_thread(parse_recipe, str(recipe_path))
            attrs_task = asyncio.to_thread(parse_attributes, str(attrs_path))
            resource_task = asyncio.to_thread(parse_custom_resource, str(resource_path))
            template_task = asyncio.to_thread(parse_template, str(template_path))

            result = await asyncio.gather(
                recipe_task, attrs_task, resource_task, template_task
            )
            return result

        (
            recipe_result,
            attrs_result,
            resource_result,
            template_result,
        ) = await run_operations()

        # All results should be valid
        assert "Resource" in recipe_result
        assert len(attrs_result) > 0
        assert "resource_name" in resource_result
        assert "variables" in template_result

    @pytest.mark.anyio
    async def test_concurrent_cookbook_analysis(self) -> None:
        """Test analyzing multiple cookbooks concurrently."""
        cookbook_paths = [
            FIXTURES_DIR / "sample_cookbook",
            FIXTURES_DIR / "apache2_cookbook",
            FIXTURES_DIR / "mysql_cookbook",
            FIXTURES_DIR / "nodejs_cookbook",
        ]

        # Analyze all cookbooks concurrently
        async def analyze_async(path: Path) -> str:
            return await asyncio.to_thread(list_cookbook_structure, str(path))

        tasks = [analyze_async(path) for path in cookbook_paths]
        results = await asyncio.gather(*tasks)

        # All results should be valid
        assert len(results) == 4
        for result in results:
            assert len(result) > 0
            assert isinstance(result, str)

    def test_sequential_vs_memory_accumulation(self) -> None:
        """Test that sequential operations don't accumulate memory."""
        recipe_path = FIXTURES_DIR / "sample_cookbook" / "recipes" / "default.rb"

        tracemalloc.start()

        # First parse
        parse_recipe(str(recipe_path))
        _, first_peak = tracemalloc.get_traced_memory()

        # Parse 10 more times
        for _ in range(10):
            parse_recipe(str(recipe_path))

        _, second_peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Memory shouldn't grow significantly
        # Allow some growth for overhead, but not linear with iterations
        memory_growth = second_peak - first_peak
        assert memory_growth < 10 * 1024 * 1024, (
            f"Memory grew by {memory_growth / 1024 / 1024:.2f}MB"
        )


class TestBenchmarkRegression:
    """Tests to prevent performance regressions."""

    @pytest.mark.parametrize(
        "family",
        sorted({case["family"] for case in BENCHMARK_CASES}),
    )
    def test_benchmark_source_family_corpus(
        self,
        benchmark: Any,
        family: str,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Benchmark all valid, complex, and malformed cases for one source."""
        monkeypatch.setenv("SOUSCHEF_WORKSPACE_ROOT", str(FIXTURES_DIR))
        cases = [case for case in BENCHMARK_CASES if case["family"] == family]
        case_count, output_size = benchmark(_run_benchmark_corpus_family, cases)

        assert case_count == len(cases)
        assert output_size > 0

    def test_benchmark_full_cookbook_conversion(
        self, benchmark: Any, tmp_path: Path
    ) -> None:
        """Benchmark full conversion against a fixed multi-file cookbook fixture."""
        cookbook_path = FIXTURES_DIR / "apache2_cookbook"
        output_path = tmp_path / "converted_roles"
        output_path.mkdir()

        result = benchmark(
            convert_cookbook_comprehensive,
            str(cookbook_path),
            str(output_path),
        )

        assert "Cookbook Conversion Summary" in result

    def test_benchmark_parse_recipe(self, benchmark: Any) -> None:
        """Benchmark recipe parsing for regression detection."""
        recipe_path = FIXTURES_DIR / "sample_cookbook" / "recipes" / "default.rb"
        result = benchmark(parse_recipe, str(recipe_path))
        assert "Resource" in result

    def test_benchmark_parse_attributes(self, benchmark: Any) -> None:
        """Benchmark attribute parsing for regression detection."""
        attrs_path = FIXTURES_DIR / "sample_cookbook" / "attributes" / "default.rb"
        result = benchmark(parse_attributes, str(attrs_path))
        assert len(result) > 0

    def test_benchmark_parse_custom_resource(self, benchmark: Any) -> None:
        """Benchmark custom resource parsing for regression detection."""
        resource_path = FIXTURES_DIR / "sample_cookbook" / "resources" / "database.rb"
        result = benchmark(parse_custom_resource, str(resource_path))
        assert "resource_name" in result

    def test_benchmark_parse_template(self, benchmark: Any) -> None:
        """Benchmark template parsing for regression detection."""
        template_path = (
            FIXTURES_DIR
            / "sample_cookbook"
            / "templates"
            / "default"
            / "config.yml.erb"
        )
        result = benchmark(parse_template, str(template_path))
        assert "variables" in result

    def test_benchmark_cookbook_structure(self, benchmark: Any) -> None:
        """Benchmark cookbook structure analysis for regression detection."""
        cookbook_path = FIXTURES_DIR / "sample_cookbook"
        result = benchmark(list_cookbook_structure, str(cookbook_path))
        assert len(result) > 0

    def test_benchmark_read_metadata(self, benchmark: Any) -> None:
        """Benchmark metadata reading for regression detection."""
        metadata_path = FIXTURES_DIR / "sample_cookbook" / "metadata.rb"
        result = benchmark(read_cookbook_metadata, str(metadata_path))
        assert "Name:" in result or "name" in result.lower()

    def test_benchmark_generate_playbook(self, benchmark: Any) -> None:
        """Benchmark playbook generation for regression detection."""
        recipe_path = FIXTURES_DIR / "sample_cookbook" / "recipes" / "default.rb"
        result = benchmark(generate_playbook_from_recipe, str(recipe_path))
        assert "---" in result  # YAML marker
        assert "name:" in result or "tasks:" in result

    def test_benchmark_convert_resource(self, benchmark: Any) -> None:
        """Benchmark resource conversion for regression detection."""
        result = benchmark(
            convert_resource_to_task,
            resource_type="package",
            resource_name="nginx",
            properties={"action": "install"},
        )
        assert len(result) > 0

    def test_benchmark_large_cookbook_structure(self, benchmark: Any) -> None:
        """Benchmark analyzing a larger cookbook structure."""
        cookbook_path = FIXTURES_DIR / "apache2_cookbook"
        result = benchmark(list_cookbook_structure, str(cookbook_path))
        assert len(result) > 0

    def test_benchmark_complex_custom_resource(self, benchmark: Any) -> None:
        """Benchmark parsing complex custom resources."""
        resource_path = FIXTURES_DIR / "mysql_cookbook" / "resources" / "database.rb"
        result = benchmark(parse_custom_resource, str(resource_path))
        assert "resource_name" in result


class TestScalability:
    """Tests for scalability and edge cases."""

    def test_empty_recipe_parsing(self, tmp_path: Path, monkeypatch) -> None:
        """Test parsing an empty recipe file."""
        monkeypatch.setenv("SOUSCHEF_WORKSPACE_ROOT", str(tmp_path))

        empty_recipe = tmp_path / "empty.rb"
        empty_recipe.write_text("")

        result = parse_recipe(str(empty_recipe))
        # Should not crash and return some result
        assert isinstance(result, str)

    def test_recipe_with_comments_only(self, tmp_path: Path, monkeypatch) -> None:
        """Test parsing a recipe with only comments."""
        monkeypatch.setenv("SOUSCHEF_WORKSPACE_ROOT", str(tmp_path))

        comments_recipe = tmp_path / "comments.rb"
        comments_recipe.write_text("""
# This is a comment
# Another comment
# More comments
""")

        result = parse_recipe(str(comments_recipe))
        # Should not crash
        assert isinstance(result, str)

    def test_recipe_with_very_long_lines(self, tmp_path: Path, monkeypatch) -> None:
        """Test parsing a recipe with very long lines."""
        monkeypatch.setenv("SOUSCHEF_WORKSPACE_ROOT", str(tmp_path))

        long_line_recipe = tmp_path / "long_lines.rb"
        long_value = "x" * 10000  # 10KB line
        long_line_recipe.write_text(f"""
package 'test' do
  action :install
  version '{long_value}'
end
""")

        result = parse_recipe(str(long_line_recipe))
        # Should parse without crashing
        assert "Resource" in result

    def test_recipe_with_unicode_content(self, tmp_path: Path, monkeypatch) -> None:
        """Test parsing a recipe with Unicode characters."""
        monkeypatch.setenv("SOUSCHEF_WORKSPACE_ROOT", str(tmp_path))

        unicode_recipe = tmp_path / "unicode.rb"
        unicode_recipe.write_text("""
package 'café' do
  action :install
  description '日本語 test 中文'
end

file '/tmp/emoji.txt' do
  content '🚀 🎉 ✨'
end
""")

        result = parse_recipe(str(unicode_recipe))
        # Should handle Unicode properly
        assert "Resource" in result

    def test_deeply_nested_conditionals(self, tmp_path: Path, monkeypatch) -> None:
        """Test parsing recipes with deeply nested conditionals."""
        monkeypatch.setenv("SOUSCHEF_WORKSPACE_ROOT", str(tmp_path))

        nested_recipe = tmp_path / "nested.rb"
        nested_recipe.write_text("""
if node['platform'] == 'ubuntu'
  if node['platform_version'].to_f >= 20.04
    if node['environment'] == 'production'
      if node['role'] == 'webserver'
        package 'nginx' do
          action :install
        end
      end
    end
  end
end
""")

        result = parse_recipe(str(nested_recipe))
        # Should parse nested structures
        assert isinstance(result, str)

    @pytest.mark.anyio
    async def test_stress_concurrent_parsing(self) -> None:
        """Stress test with many concurrent parsing operations."""
        recipe_path = FIXTURES_DIR / "sample_cookbook" / "recipes" / "default.rb"

        # 100 concurrent parses
        async def parse_async() -> str:
            return await asyncio.to_thread(parse_recipe, str(recipe_path))

        tasks = [parse_async() for _ in range(100)]
        results = await asyncio.gather(*tasks)

        # All should succeed
        assert len(results) == 100
        for result in results:
            assert len(result) > 0
