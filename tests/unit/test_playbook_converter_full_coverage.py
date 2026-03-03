"""Targeted unit tests for converters/playbook.py."""

import json
import tempfile
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

from souschef.converters import playbook as pb
from souschef.core.constants import ERROR_PREFIX

# Test AI Client Initialisation


class TestRecipeConversion:
    """Test playbook generation entry points."""

    def test_generate_playbook_from_recipe_parse_error(self) -> None:
        """It returns parser errors early."""
        with patch("souschef.converters.playbook.parse_recipe") as mock_parse:
            mock_parse.return_value = f"{ERROR_PREFIX} parse"
            result = pb.generate_playbook_from_recipe("recipe.rb")
            assert result.startswith(ERROR_PREFIX)

    def test_generate_playbook_from_recipe_missing_file(self) -> None:
        """It reports missing recipes inside the workspace root."""
        with tempfile.TemporaryDirectory() as tmpdir:
            recipe_path = Path(tmpdir) / "missing.rb"
            with (
                patch("souschef.converters.playbook._get_workspace_root") as mock_root,
                patch("souschef.converters.playbook._normalize_path") as mock_norm,
                patch(
                    "souschef.converters.playbook._ensure_within_base_path"
                ) as mock_safe,
                patch("souschef.converters.playbook.safe_exists") as mock_exists,
                patch("souschef.converters.playbook.parse_recipe") as mock_parse,
            ):
                mock_root.return_value = Path(tmpdir)
                mock_norm.return_value = recipe_path
                mock_safe.return_value = recipe_path
                mock_exists.return_value = False
                mock_parse.return_value = "parsed"

                result = pb.generate_playbook_from_recipe(str(recipe_path))
                assert "does not exist" in result

    def test_generate_playbook_from_recipe_path_traversal(self) -> None:
        """It reports traversal attempts from read errors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            recipe_path = Path(tmpdir) / "recipe.rb"
            with (
                patch("souschef.converters.playbook._get_workspace_root") as mock_root,
                patch("souschef.converters.playbook._normalize_path") as mock_norm,
                patch(
                    "souschef.converters.playbook._ensure_within_base_path"
                ) as mock_safe,
                patch("souschef.converters.playbook.safe_exists") as mock_exists,
                patch("souschef.converters.playbook.safe_read_text") as mock_read,
                patch("souschef.converters.playbook.parse_recipe") as mock_parse,
            ):
                mock_root.return_value = Path(tmpdir)
                mock_norm.return_value = recipe_path
                mock_safe.return_value = recipe_path
                mock_exists.return_value = True
                mock_read.side_effect = ValueError("traversal")
                mock_parse.return_value = "parsed"

                result = pb.generate_playbook_from_recipe(str(recipe_path))
                assert "Path traversal" in result

    def test_generate_playbook_from_recipe_success(self) -> None:
        """It builds a playbook with generated structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            recipe_path = Path(tmpdir) / "recipe.rb"
            recipe_path.write_text("package 'vim'", encoding="utf-8")
            with (
                patch("souschef.converters.playbook._get_workspace_root") as mock_root,
                patch(
                    "souschef.converters.playbook._generate_playbook_structure"
                ) as mock_gen,
                patch("souschef.converters.playbook.parse_recipe") as mock_parse,
            ):
                mock_root.return_value = Path(tmpdir)
                mock_parse.return_value = "parsed"
                mock_gen.return_value = "---\n- name: ok"

                result = pb.generate_playbook_from_recipe(str(recipe_path))
                assert result.startswith("---")

    def test_generate_playbook_from_recipe_with_ai_parse_error(self) -> None:
        """It returns parse errors for AI conversion too."""
        with patch("souschef.converters.playbook.parse_recipe") as mock_parse:
            mock_parse.return_value = f"{ERROR_PREFIX} parse"
            with tempfile.TemporaryDirectory() as tmpdir:
                recipe_path = Path(tmpdir) / "recipe.rb"
                recipe_path.write_text("package 'vim'", encoding="utf-8")
                with patch(
                    "souschef.converters.playbook._get_workspace_root"
                ) as mock_root:
                    mock_root.return_value = Path(tmpdir)
                    result = pb.generate_playbook_from_recipe_with_ai(str(recipe_path))
                    assert result.startswith(ERROR_PREFIX)

    def test_generate_playbook_from_recipe_with_ai_missing_file(self) -> None:
        """It reports missing AI recipe files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            recipe_path = Path(tmpdir) / "missing.rb"
            with (
                patch("souschef.converters.playbook._get_workspace_root") as mock_root,
                patch("souschef.converters.playbook._normalize_path") as mock_norm,
                patch(
                    "souschef.converters.playbook._ensure_within_base_path"
                ) as mock_safe,
                patch("souschef.converters.playbook.safe_exists") as mock_exists,
            ):
                mock_root.return_value = Path(tmpdir)
                mock_norm.return_value = recipe_path
                mock_safe.return_value = recipe_path
                mock_exists.return_value = False

                result = pb.generate_playbook_from_recipe_with_ai(str(recipe_path))
                assert "does not exist" in result

    def test_generate_playbook_from_recipe_with_ai_success(self) -> None:
        """It returns an AI-generated playbook when dependencies are mocked."""
        with tempfile.TemporaryDirectory() as tmpdir:
            recipe_path = Path(tmpdir) / "recipe.rb"
            recipe_path.write_text("package 'vim'", encoding="utf-8")
            with (
                patch("souschef.converters.playbook._get_workspace_root") as mock_root,
                patch("souschef.converters.playbook.parse_recipe") as mock_parse,
                patch(
                    "souschef.converters.playbook._generate_playbook_with_ai"
                ) as mock_ai,
            ):
                mock_root.return_value = Path(tmpdir)
                mock_parse.return_value = "parsed"
                mock_ai.return_value = "---\n- name: ai"

                result = pb.generate_playbook_from_recipe_with_ai(str(recipe_path))
                assert result.startswith("---")

    def test_generate_playbook_with_ai_client_error(self) -> None:
        """It returns client errors from AI initialisation."""
        with patch("souschef.converters.playbook._initialize_ai_client") as mock_init:
            mock_init.return_value = f"{ERROR_PREFIX} bad client"
            result = pb._generate_playbook_with_ai(
                "raw",
                "parsed",
                "recipe.rb",
                "openai",
                "key",
                "model",
                0.1,
                200,
            )
            assert result.startswith(ERROR_PREFIX)

    def test_generate_playbook_with_ai_success(self) -> None:
        """It returns the cleaned and validated AI playbook."""
        with (
            patch("souschef.converters.playbook._initialize_ai_client") as mock_init,
            patch(
                "souschef.converters.playbook._create_ai_conversion_prompt"
            ) as mock_prompt,
            patch("souschef.converters.playbook._call_ai_api") as mock_call,
            patch(
                "souschef.converters.playbook._clean_ai_playbook_response"
            ) as mock_clean,
            patch(
                "souschef.converters.playbook._validate_and_fix_playbook"
            ) as mock_validate,
        ):
            mock_init.return_value = object()
            mock_prompt.return_value = "prompt"
            mock_call.return_value = "raw"
            mock_clean.return_value = "---\n- name: ok"
            mock_validate.return_value = "---\n- name: ok"

            result = pb._generate_playbook_with_ai(
                "raw",
                "parsed",
                "recipe.rb",
                "openai",
                "key",
                "model",
                0.1,
                200,
            )
            assert result.startswith("---")


# Test AI API Calling Functions


class TestAiHelpers:
    """Test AI helper utilities."""

    def test_initialize_ai_client_github_copilot(self) -> None:
        """It blocks unsupported GitHub Copilot provider."""
        result = pb._initialize_ai_client("github_copilot", "key")
        assert "public REST API" in result

    def test_initialize_ai_client_unsupported(self) -> None:
        """It rejects unknown providers."""
        result = pb._initialize_ai_client("unknown", "key")
        assert "Unsupported" in result

    def test_initialize_ai_client_lightspeed_invalid_url(self) -> None:
        """It returns URL validation errors for Lightspeed."""
        with patch(
            "souschef.converters.playbook.validate_user_provided_url"
        ) as mock_url:
            mock_url.side_effect = ValueError("bad url")
            result = pb._initialize_ai_client(
                "lightspeed",
                "key",
                base_url="http://x",  # NOSONAR
            )
            assert "Invalid" in result

    def test_initialize_ai_client_lightspeed_requests_missing(self) -> None:
        """It reports missing requests for Lightspeed."""
        with patch("souschef.converters.playbook.requests", None):
            result = pb._initialize_ai_client("lightspeed", "key")
            assert "not available" in result.lower()

    def test_call_anthropic_api_tool_response(self) -> None:
        """It extracts tool output for structured responses."""
        mock_client = MagicMock()
        tool_block = MagicMock()
        tool_block.type = "tool_use"
        tool_block.input = {"response": "structured"}
        mock_client.messages.create.return_value.content = [tool_block]

        result = pb._call_anthropic_api(
            mock_client,
            "prompt",
            "model",
            0.1,
            200,
            response_format={"type": "json_object"},
        )
        assert result == "structured"

    def test_call_lightspeed_api_error(self) -> None:
        """It returns error text for non-200 responses."""
        mock_client = {"api_key": "key", "base_url": "https://api.redhat.com"}
        with patch("souschef.converters.playbook.requests") as mock_requests:
            mock_response = MagicMock()
            mock_response.status_code = 403
            mock_response.text = "Forbidden"
            mock_requests.post.return_value = mock_response

            result = pb._call_lightspeed_api(mock_client, "prompt", "model", 0.1, 10)
            assert "error" in result.lower()

    def test_call_github_copilot_api_error(self) -> None:
        """It returns error text for non-200 responses."""
        mock_client = {"api_key": "key", "base_url": "https://api.github.com"}
        with patch("souschef.converters.playbook.requests") as mock_requests:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.text = "Boom"
            mock_requests.post.return_value = mock_response

            result = pb._call_github_copilot_api(
                mock_client, "prompt", "model", 0.1, 10
            )
            assert "error" in result.lower()

    def test_call_ai_api_dispatch_openai(self) -> None:
        """It dispatches to OpenAI when provider is not matched."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value.choices = [
            MagicMock(message=MagicMock(content="ok"))
        ]

        result = pb._call_ai_api(mock_client, "openai", "prompt", "model", 0.1, 10)
        assert result == "ok"


# Test AI Prompt Building


class TestAiValidation:
    """Test AI playbook validation paths."""

    def test_clean_ai_playbook_response_empty(self) -> None:
        """It returns an error for empty responses."""
        assert pb._clean_ai_playbook_response("  ").startswith(ERROR_PREFIX)

    def test_validate_and_fix_playbook_short_circuit_error_prefix(self) -> None:
        """It returns error-prefixed content without changes."""
        result = pb._validate_and_fix_playbook(
            f"{ERROR_PREFIX} bad", object(), "openai", "m", 0.1, 10
        )
        assert result.startswith(ERROR_PREFIX)

    def test_validate_and_fix_playbook_fix_fails_returns_original(self) -> None:
        """It falls back when fixed response is invalid."""
        with (
            patch("souschef.converters.playbook._validate_playbook_yaml") as mock_yaml,
            patch("souschef.converters.playbook._run_ansible_lint") as mock_lint,
            patch("souschef.converters.playbook._call_ai_api") as mock_ai,
        ):
            mock_yaml.return_value = None
            mock_lint.return_value = "lint error"
            mock_ai.return_value = "not yaml"

            original = "---\n- name: test\n  hosts: all\n  tasks: []"
            result = pb._validate_and_fix_playbook(
                original, object(), "openai", "m", 0.1, 10
            )
            assert result == original

    def test_validate_and_fix_playbook_fix_success(self) -> None:
        """It returns corrected YAML from AI."""
        with (
            patch("souschef.converters.playbook._validate_playbook_yaml") as mock_yaml,
            patch("souschef.converters.playbook._run_ansible_lint") as mock_lint,
            patch("souschef.converters.playbook._call_ai_api") as mock_ai,
        ):
            mock_yaml.return_value = None
            mock_lint.return_value = "lint error"
            mock_ai.return_value = "---\n- name: fixed\n  hosts: all\n  tasks: []"

            result = pb._validate_and_fix_playbook(
                "---\n- name: bad\n  hosts: all\n  tasks: []",
                object(),
                "openai",
                "m",
                0.1,
                10,
            )
            assert "fixed" in result

    def test_run_ansible_lint_missing_binary(self) -> None:
        """It skips lint when ansible-lint is missing."""
        with patch("souschef.converters.playbook.shutil.which", return_value=None):
            assert pb._run_ansible_lint("---\n- name: t") is None

    def test_run_ansible_lint_returns_error_output(self) -> None:
        """It returns lint output when ansible-lint fails."""
        with (
            patch(
                "souschef.converters.playbook.shutil.which",
                return_value="/bin/ansible-lint",
            ),
            patch("souschef.converters.playbook.subprocess.run") as mock_run,
        ):
            mock_run.return_value = types.SimpleNamespace(
                returncode=2, stdout="fail", stderr="bad"
            )
            result = pb._run_ansible_lint("---\n- name: t")
            assert result and "fail" in result


# Test AI Response Cleaning


class TestSearchParsing:
    """Test Chef search parsing and inventory conversion."""

    def test_parse_search_condition_equal(self) -> None:
        """It parses equal conditions."""
        result = pb._parse_search_condition("role:web")
        assert result["operator"] == "equal"

    def test_parse_search_condition_wildcard(self) -> None:
        """It parses wildcard conditions."""
        result = pb._parse_search_condition("role:web*")
        assert result["operator"] == "wildcard"

    def test_parse_search_condition_regex(self) -> None:
        """It parses regex conditions."""
        result = pb._parse_search_condition("role:~web.*")
        assert result["operator"] == "regex"

    def test_parse_search_condition_not_equal(self) -> None:
        """It parses not-equal conditions."""
        result = pb._parse_search_condition("role:!db")
        assert result["operator"] == "not_equal"

    def test_parse_search_condition_range(self) -> None:
        """It parses range conditions."""
        result = pb._parse_search_condition("memory:(>1 AND <2)")
        assert result["operator"] == "range"

    def test_parse_search_condition_tag(self) -> None:
        """It parses tag conditions."""
        result = pb._parse_search_condition("tags:blue")
        assert result["operator"] == "contains"

    def test_parse_search_condition_unknown(self) -> None:
        """It handles unknown conditions."""
        result = pb._parse_search_condition("not a query")
        assert result["type"] == "unknown"

    def test_determine_search_index_role(self) -> None:
        """It maps role searches to node index."""
        assert pb._determine_search_index("role:web") == "node"

    def test_extract_query_parts_operators(self) -> None:
        """It extracts conditions and operators."""
        conditions, operators = pb._extract_query_parts("role:web AND env:prod")
        assert conditions
        assert operators == ["AND"]

    def test_determine_query_complexity_intermediate(self) -> None:
        """It marks regex or not-equal as intermediate."""
        complexity = pb._determine_query_complexity([{"operator": "~"}], [])
        assert complexity == "intermediate"

    def test_should_use_dynamic_inventory_with_regex(self) -> None:
        """It requests dynamic inventory for regex conditions."""
        info = {
            "complexity": "simple",
            "conditions": [{"operator": "regex"}],
        }
        assert pb._should_use_dynamic_inventory(info) is True

    def test_process_search_condition_role_sets_variable(self) -> None:
        """It adds role variables to inventory config."""
        inventory = {"groups": {}, "variables": {}, "dynamic_script_needed": False}
        pb._process_search_condition(
            {"key": "role", "value": "web", "operator": "equal"}, 0, inventory
        )
        assert inventory["variables"]["role_web_role"] == "web"

    def test_process_search_condition_pattern_sets_dynamic(self) -> None:
        """It marks dynamic inventory for wildcard patterns."""
        inventory = {"groups": {}, "variables": {}, "dynamic_script_needed": False}
        pb._process_search_condition(
            {"key": "role", "value": "web*", "operator": "wildcard"}, 1, inventory
        )
        assert inventory["dynamic_script_needed"] is True

    def test_generate_ansible_inventory_from_search_combined_group(self) -> None:
        """It creates a combined group for logical operators."""
        info = {
            "original_query": "role:web AND env:prod",
            "conditions": [{"key": "role", "value": "web", "operator": "equal"}],
            "logical_operators": ["AND"],
            "complexity": "complex",
        }
        inventory = pb._generate_ansible_inventory_from_search(info)
        assert "combined_search_results" in inventory["groups"]

    def test_generate_group_name_for_not_equal(self) -> None:
        """It prefixes not-equal group names."""
        name = pb._generate_group_name_from_condition(
            {"key": "role", "value": "db", "operator": "not_equal"},
            1,
        )
        assert name.startswith("not_role")


# Test Chef Search Query Parsing


class TestSearchPatternExtraction:
    """Test Chef search pattern extraction and recommendations."""

    def test_find_search_patterns_in_content_mixed(self) -> None:
        """It finds search, data bag, and node attribute patterns."""
        content = (
            "search(:node, 'role:web')\n"
            "partial_search(:node, 'environment:prod')\n"
            "data_bag_item('secrets', 'db')\n"
            "node['platform']['version']\n"
        )
        patterns = pb._find_search_patterns_in_content(content, "recipe.rb")
        types = {pattern["type"] for pattern in patterns}
        assert "search" in types
        assert "data_bag_access" in types
        assert "node_attribute" in types

    def test_extract_search_patterns_from_file_reads_content(self) -> None:
        """It reads patterns from a single file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "default.rb"
            file_path.write_text("search(:node, 'role:web')", encoding="utf-8")
            patterns = pb._extract_search_patterns_from_file(file_path, Path(tmpdir))
            assert patterns

    def test_extract_search_patterns_from_cookbook_collects_all(self) -> None:
        """It aggregates patterns from recipes, libraries, and resources."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            recipes_dir = base / "recipes"
            libraries_dir = base / "libraries"
            resources_dir = base / "resources"
            recipes_dir.mkdir()
            libraries_dir.mkdir()
            resources_dir.mkdir()
            (recipes_dir / "default.rb").write_text(
                "search(:node, 'role:web')", encoding="utf-8"
            )
            (libraries_dir / "helpers.rb").write_text(
                "partial_search(:node, 'environment:prod')", encoding="utf-8"
            )
            (resources_dir / "thing.rb").write_text(
                "data_bag_item('secrets', 'db')", encoding="utf-8"
            )
            patterns = pb._extract_search_patterns_from_cookbook(base)
            assert len(patterns) == 4

    def test_generate_inventory_recommendations_dynamic(self) -> None:
        """It recommends dynamic inventory for many searches."""
        patterns = [
            {"type": "search", "query": "role:web"},
            {"type": "search", "query": "role:db"},
            {"type": "search", "query": "role:cache"},
        ]
        recommendations = pb._generate_inventory_recommendations(patterns)
        assert recommendations["structure"] == "dynamic"

    def test_add_general_recommendations_data_bag(self) -> None:
        """It adds data bag notes when detected."""
        recommendations = {
            "notes": [],
            "groups": {},
            "structure": "static",
            "variables": {},
        }
        pb._add_general_recommendations(
            recommendations,
            [{"type": "data_bag_access"}],
        )
        assert any("Data bag" in note for note in recommendations["notes"])

    def test_extract_role_and_environment_groups(self) -> None:
        """It extracts role and environment sets from patterns."""
        patterns = [{"type": "search", "query": "role:web AND environment:prod"}]
        roles, envs = pb._extract_role_and_environment_groups(patterns)
        assert roles == {"web"}
        assert envs == {"prod"}


# Test Inventory Generation


class TestVariablesAndValues:
    """Test variable extraction and Ruby conversions."""

    def test_extract_mode_variables_multiple(self) -> None:
        """It uses defaults when multiple modes are present."""
        content = "mode '0644'\nmode '0755'"
        result = pb._extract_mode_variables(content)
        assert "directory_mode" in result

    def test_convert_chef_attr_path_number_words(self) -> None:
        """It converts leading digits to words."""
        assert pb._convert_chef_attr_path_to_ansible_var("301.version").startswith(
            "threezeroone_"
        )

    def test_extract_attribute_variables_value(self) -> None:
        """It collects attribute values from parsed content."""
        content = "Attribute: test.attr\nValue: 1"
        result = pb._extract_attribute_variables(content)
        assert result

    def test_extract_recipe_variables_combines(self) -> None:
        """It merges all recipe variable extractors."""
        content = "version '1.2.3'\nmode '0644'"
        result = pb._extract_recipe_variables(content)
        assert "package_version" in result

    def test_find_and_collect_value_lines_no_value(self) -> None:
        """It returns no values when Value: is missing."""
        lines = ["attr", "Precedence: default"]
        values, index = pb._find_and_collect_value_lines(lines, 0)
        assert values == []
        assert index >= 0


# Test Guard Condition Conversion


class TestGuards:
    """Test guard conversion and parsing."""

    def test_extract_guard_patterns_all(self) -> None:
        """It extracts all guard patterns from a block."""
        block = (
            "only_if 'test -f /a'\n"
            "not_if 'test -f /b'\n"
            "only_if do File.exist?('/c') end\n"
            "not_if do File.exist?('/d') end\n"
            "only_if { File.exist?('/e') }\n"
            "not_if { File.exist?('/f') }\n"
            "only_if ['test -f /g', 'test -f /h']\n"
            "not_if ['test -f /i', 'test -f /j']\n"
        )
        parts = pb._extract_guard_patterns(block)
        assert all(parts)

    def test_parse_guard_array_with_lambda_and_block(self) -> None:
        """It handles mixed lambda and block guards."""
        array_content = (
            "'test -f /a', { File.exist?('/b') }, lambda { File.exist?('/c') }"
        )
        result = pb._parse_guard_array(array_content, negate=False)
        assert len(result) == 3

    def test_convert_chef_condition_to_ansible_fallback_command(self) -> None:
        """It falls back to command checks when no mapping exists."""
        condition = pb._convert_chef_condition_to_ansible("custom_command")
        assert "ansible_facts.env" in condition

    def test_convert_chef_condition_to_ansible_systemctl(self) -> None:
        """It maps systemctl checks to service facts."""
        condition = pb._convert_chef_condition_to_ansible(
            "system('systemctl is-active nginx')"
        )
        assert "services" in condition

    def test_convert_chef_block_to_ansible_manual_review(self) -> None:
        """It requests manual review for Ruby-specific syntax."""
        result = pb._convert_chef_block_to_ansible("Object.new")
        assert "REVIEW" in result

    def test_handle_file_existence_block_interpolation(self) -> None:
        """It replaces Ruby interpolation with Jinja2."""
        result = pb._handle_file_existence_block(
            "File.exist?(\"#{node['path']}\")",
            positive=True,
        )
        assert result is not None
        assert "{{" in result

    def test_handle_command_execution_block_non_which_returns_review(self) -> None:
        """It falls back to review for non-which system calls."""
        result = pb._handle_command_execution_block("system('echo hi')", True)
        assert result and "REVIEW" in result


# Test Resource and Task Conversion


class TestResourcesAndNotifications:
    """Test resource parsing and notification handling."""

    def test_parse_resource_block_include_recipe(self) -> None:
        """It parses include_recipe blocks."""
        block = "Include Recipe 1:\nRecipe: web"
        result = pb._parse_resource_block(block)
        assert result and result["type"] == "include_recipe"

    def test_extract_resources_from_parsed_content_preserves_order(self) -> None:
        """It sorts resources by raw content order."""
        parsed = (
            "Resource 1:\nType: service\nName: nginx\nAction: start\n"
            "Resource 2:\nType: package\nName: nginx\nAction: install\n"
        )
        raw = "package 'nginx'\nservice 'nginx'"
        resources = pb._extract_resources_from_parsed_content(parsed, raw)
        assert resources[0]["type"] == "package"

    def test_extract_nodejs_npm_version_found(self) -> None:
        """It extracts version from nodejs_npm blocks."""
        raw = "nodejs_npm 'express' do\n  version '1.0.0'\nend"
        assert pb._extract_nodejs_npm_version(raw, "express") == "'1.0.0'"

    def test_convert_resource_to_task_dict_adds_notify_and_handlers(self) -> None:
        """It adds notifications and handlers for resources."""
        raw = (
            "template 'config' do\n"
            "  notifies :restart, 'service[nginx]', :delayed\n"
            "end\n"
            "service 'nginx' do\n"
            "  subscribes :restart, 'template[config]'\n"
            "end\n"
        )
        resource = {
            "type": "template",
            "name": "config",
            "action": "create",
            "properties": "",
        }
        with patch(
            "souschef.converters.playbook._convert_chef_resource_to_ansible"
        ) as mock_convert:
            mock_convert.return_value = {"name": "Task"}
            result = pb._convert_resource_to_task_dict(resource, raw)
            assert result["handlers"]
            assert "notify" in result["task"]

    def test_process_subscribes_matches_resource(self) -> None:
        """It creates handlers for matching subscribes."""
        raw = "service 'nginx' do\n  subscribes :restart, 'template[config]'\nend"
        resource = {"type": "template", "name": "config"}
        task: dict[str, object] = {}
        handlers = pb._process_subscribes(
            resource,
            [("restart", "template[config]", "")],
            raw,
            task,
        )
        assert handlers

    def test_extract_enhanced_notifications_default_timing(self) -> None:
        """It defaults timing to delayed when missing."""
        raw = "template 'config' do\n  notifies :restart, 'service[nginx]'\nend"
        resource = {"type": "template", "name": "config"}
        result = pb._extract_enhanced_notifications(resource, raw)
        assert result[0]["timing"] == "delayed"

    def test_create_handler_with_timing_immediate(self) -> None:
        """It annotates immediate timing metadata."""
        handler = pb._create_handler_with_timing(
            "restart", "service", "nginx", "immediate"
        )
        assert handler.get("_priority") == "immediate"


# Test Notification Handling


class TestPlaybookBuilder:
    """Test playbook formatting helpers."""

    def test_add_playbook_variables_adds_attr_vars(self) -> None:
        """It appends attribute variables when present."""
        lines = []
        raw = "version '1.0'"
        with (
            patch("souschef.converters.playbook.parse_attributes") as mock_parse,
            patch("souschef.converters.playbook.safe_exists") as mock_exists,
        ):
            mock_exists.return_value = True
            mock_parse.return_value = "Attribute: cookbook.attr\nValue: 1"
            pb._add_playbook_variables(lines, raw, Path("/tmp/recipe.rb"))  # NOSONAR
            assert any("cookbook_attr" in line for line in lines)

    def test_add_playbook_variables_no_vars(self) -> None:
        """It leaves a placeholder when no variables found."""
        lines = []
        raw = ""
        with patch("souschef.converters.playbook.safe_exists", return_value=False):
            pb._add_playbook_variables(lines, raw, Path("/tmp/recipe.rb"))  # NOSONAR
            assert any("No variables" in line for line in lines)

    def test_generate_playbook_structure_includes_handlers(self) -> None:
        """It renders handlers when present."""
        with patch(
            "souschef.converters.playbook._convert_and_collect_resources"
        ) as mock_convert:
            mock_convert.return_value = ([{"name": "task"}], [{"name": "handler"}])
            with patch(
                "souschef.converters.playbook._format_ansible_task",
                return_value="- name: ok",
            ):
                result = pb._generate_playbook_structure(
                    "parsed",
                    "raw",
                    Path("/tmp/recipe.rb"),  # NOSONAR
                )
                assert "handlers" in result


# Test Variable Extraction


class TestDynamicInventoryScript:
    """Test dynamic inventory script generation."""

    def test_generate_dynamic_inventory_script_invalid_json(self) -> None:
        """It reports invalid JSON input."""
        result = pb.generate_dynamic_inventory_script("not json")
        assert result.startswith("Error:")

    def test_generate_dynamic_inventory_script_success(self) -> None:
        """It returns a script for valid query JSON."""
        queries = json.dumps([{"group_name": "web", "search_query": "role:web"}])
        result = pb.generate_dynamic_inventory_script(queries)
        assert result.startswith("#!/usr/bin/env python3")

    def test_generate_inventory_script_content_includes_group(self) -> None:
        """It embeds group names in the script."""
        content = pb._generate_inventory_script_content(
            [{"group_name": "db", "search_query": "role:db"}]
        )
        assert "db" in content


# Test Ruby Value Conversion


class TestAnalyseSearchPatterns:
    """Test analyse_chef_search_patterns for file and directory."""

    def test_analyse_chef_search_patterns_file(self) -> None:
        """It analyses single recipes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            recipe_path = Path(tmpdir) / "default.rb"
            recipe_path.write_text("search(:node, 'role:web')", encoding="utf-8")
            with patch(
                "souschef.converters.playbook._get_workspace_root",
                return_value=Path(tmpdir),
            ):
                result = pb.analyse_chef_search_patterns(str(recipe_path))
                data = json.loads(result)
                assert data["discovered_searches"]

    def test_analyse_chef_search_patterns_dir(self) -> None:
        """It analyses cookbook directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cookbook = Path(tmpdir)
            (cookbook / "recipes").mkdir()
            (cookbook / "recipes" / "default.rb").write_text(
                "search(:node, 'role:web')", encoding="utf-8"
            )
            with patch(
                "souschef.converters.playbook._get_workspace_root",
                return_value=cookbook,
            ):
                result = pb.analyse_chef_search_patterns(str(cookbook))
                data = json.loads(result)
                assert data["discovered_searches"]

    def test_analyse_chef_search_patterns_missing(self) -> None:
        """It reports missing paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            missing = Path(tmpdir) / "nope"
            with patch(
                "souschef.converters.playbook._get_workspace_root",
                return_value=Path(tmpdir),
            ):
                result = pb.analyse_chef_search_patterns(str(missing))
                assert result.startswith("Error:")


# Test Utility Helper Functions


class TestInventoryConversion:
    """Test public inventory conversion helpers."""

    def test_convert_chef_search_to_inventory_json(self) -> None:
        """It returns JSON for search conversion."""
        result = pb.convert_chef_search_to_inventory("role:web")
        data = json.loads(result)
        assert "inventory_type" in data


# Test Playbook Building


class TestInventoryScriptContent:
    """Test inventory script content builder."""

    def test_generate_inventory_script_content_includes_helpers(self) -> None:
        """It embeds helper functions in script output."""
        content = pb._generate_inventory_script_content(
            [{"group_name": "web", "search_query": "role:web"}]
        )
        assert "validate_chef_server_url" in content


# Test Search Pattern Analysis


class TestConvertAndCollectResources:
    """Test convert-and-collect pipeline."""

    def test_convert_and_collect_resources(self) -> None:
        """It aggregates tasks and handlers from resources."""
        with (
            patch(
                "souschef.converters.playbook._extract_resources_from_parsed_content"
            ) as mock_extract,
            patch(
                "souschef.converters.playbook._convert_resource_to_task_dict"
            ) as mock_convert,
        ):
            mock_extract.return_value = [
                {
                    "type": "package",
                    "name": "nginx",
                    "action": "install",
                    "properties": "",
                }
            ]
            mock_convert.return_value = {
                "task": {"name": "task"},
                "handlers": [{"name": "handler"}],
            }

            tasks, handlers = pb._convert_and_collect_resources("parsed", "raw")
            assert tasks and handlers


# Test Full Integration


class TestHelpersForStrings:
    """Test small string utility helpers."""

    def test_split_by_commas_with_nesting(self) -> None:
        """It respects nested braces when splitting."""
        parts = pb._split_by_commas_with_nesting("{a: 1}, {b: 2}")
        assert len(parts) == 2

    def test_convert_ruby_value_to_yaml_hash(self) -> None:
        """It converts Ruby hashes to flow YAML."""
        result = pb._convert_ruby_value_to_yaml('{"a" => 1}')
        assert result.startswith("{")

    def test_convert_ruby_value_to_yaml_array(self) -> None:
        """It converts Ruby arrays to flow YAML."""
        result = pb._convert_ruby_value_to_yaml("[1, 2]")
        assert result.startswith("[")

    def test_convert_primitive_value_nil(self) -> None:
        """It converts nil to null."""
        assert pb._convert_primitive_value("nil") == "null"
