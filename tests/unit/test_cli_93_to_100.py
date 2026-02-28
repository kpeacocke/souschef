"""Targeted tests for remaining souschef.cli coverage gaps from 93% to 100%."""

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

import souschef.cli as cli_module


def _invoke(cmd: str, **kwargs: Any) -> Any:
    """Invoke a top-level CLI command callback directly."""
    return cli_module.cli.commands[cmd].callback(**kwargs)  # type: ignore


def _invoke_group(group: str, cmd: str, **kwargs: Any) -> Any:
    """Invoke a grouped CLI command callback directly."""
    return cli_module.cli.commands[group].commands[cmd].callback(**kwargs)  # type: ignore


def test_line_405_template_summary_more(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Cover template summary '...and N more' branch."""
    f = tmp_path / "a.erb"
    f.write_text("x")
    with patch.object(
        cli_module,
        "parse_template",
        return_value='{"variables": ["a", "b", "c", "d", "e", "f"]}',
    ):
        cli_module._display_template_summary(f)
    assert "... and 1 more" in capsys.readouterr().out


def test_line_405_template_summary_json_decode(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Cover template summary JSON decode fallback branch."""
    f = tmp_path / "a.erb"
    f.write_text("x")
    with patch.object(cli_module, "parse_template", return_value="not-json"):
        cli_module._display_template_summary(f)
    assert "not-json" in capsys.readouterr().out


def test_line_559_template_failure(tmp_path: Path) -> None:
    """Cover cookbook template conversion failure branch."""
    cookbook = tmp_path / "cookbook"
    (cookbook / "recipes").mkdir(parents=True)
    (cookbook / "templates" / "default").mkdir(parents=True)
    (cookbook / "templates" / "default" / "x.erb").write_text("<%= @x %>")
    out = tmp_path / "out"
    with patch(
        "souschef.converters.template.convert_template_file",
        return_value={"success": False},
    ):
        cli_module._save_cookbook_conversion(cookbook, str(out))


def test_profile_and_profile_operation_lines(tmp_path: Path) -> None:
    """Cover profile exception and profile_operation non-detailed branch."""
    cookbook = tmp_path / "cookbook"
    cookbook.mkdir()

    with (
        patch.object(
            cli_module,
            "generate_cookbook_performance_report",
            side_effect=RuntimeError("boom"),
        ),
        pytest.raises(SystemExit),
    ):
        _invoke("profile", cookbook_path=str(cookbook), output=None)

    recipe = tmp_path / "r.rb"
    recipe.write_text("package 'nginx' do\nend\n")
    with patch.object(cli_module, "profile_function", return_value=(None, "ok-report")):
        _invoke(
            "profile-operation", operation="recipe", path=str(recipe), detailed=False
        )


def test_output_text_and_profile_output_branches(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Cover lines 914 and 961-963 branches."""
    cli_module._output_text_format("[1,2,3]")
    assert "[1,2,3]" in capsys.readouterr().out

    cookbook = tmp_path / "cookbook"
    cookbook.mkdir()
    out_file = tmp_path / "report.txt"
    with patch.object(
        cli_module, "generate_cookbook_performance_report", return_value={"k": "v"}
    ):
        _invoke("profile", cookbook_path=str(cookbook), output=str(out_file))
        _invoke("profile", cookbook_path=str(cookbook), output=None)


def test_convert_recipe_line_1064(tmp_path: Path) -> None:
    """Cover convert-recipe output path OSError branch."""
    cookbook = tmp_path / "cookbook"
    (cookbook / "recipes").mkdir(parents=True)
    (cookbook / "recipes" / "default.rb").write_text("x")

    real_resolve = Path.resolve

    def _resolve_side_effect(path_self: Path, *args, **kwargs):
        if str(path_self).endswith("out"):
            raise OSError("bad path")
        return real_resolve(path_self, *args, **kwargs)

    with (
        patch("pathlib.Path.resolve", autospec=True, side_effect=_resolve_side_effect),
        pytest.raises(SystemExit),
    ):
        _invoke(
            "convert-recipe",
            cookbook_path=str(cookbook),
            recipe_name="default",
            output_path=str(tmp_path / "out"),
        )


def test_assessment_complexity_branches(tmp_path: Path) -> None:
    """Cover low/medium/high complexity recommendation branches."""
    empty = tmp_path / "empty"
    empty.mkdir()
    low = cli_module._analyse_cookbook_for_assessment(empty)
    assert low["complexity"] == "Low"

    medium = tmp_path / "medium"
    (medium / "recipes").mkdir(parents=True)
    for i in range(5):
        (medium / "recipes" / f"r{i}.rb").write_text("package 'x' do\nend\n")
    med = cli_module._analyse_cookbook_for_assessment(medium)
    assert med["complexity"] == "Medium"

    high = tmp_path / "high"
    (high / "recipes").mkdir(parents=True)
    for i in range(11):
        (high / "recipes" / f"r{i}.rb").write_text("package 'x' do\nend\n")
    hi = cli_module._analyse_cookbook_for_assessment(high)
    assert hi["complexity"] == "High"


def test_convert_habitat_and_inspec_path_validation(tmp_path: Path) -> None:
    """Cover convert-habitat and convert-inspec path validation branches."""
    plan = tmp_path / "plan.sh"
    plan.write_text("pkg_name=test")

    real_resolve = Path.resolve

    def _resolve_side_effect(path_self: Path, *args, **kwargs):
        if str(path_self).endswith("bad-out"):
            raise OSError("resolve bad")
        return real_resolve(path_self, *args, **kwargs)

    with (
        patch("pathlib.Path.resolve", autospec=True, side_effect=_resolve_side_effect),
        pytest.raises(SystemExit),
    ):
        _invoke(
            "convert-habitat",
            plan_path=str(plan),
            output_path=str(tmp_path / "bad-out"),
            base_image="ubuntu:latest",
        )

    file_not_dir = tmp_path / "not_dir"
    file_not_dir.write_text("x")
    with pytest.raises(SystemExit):
        _invoke(
            "convert-inspec",
            profile_path=str(file_not_dir),
            output_path=str(tmp_path / "o"),
            output_format="testinfra",
        )

    profile_dir = tmp_path / "profile"
    profile_dir.mkdir()
    with pytest.raises(SystemExit):
        _invoke(
            "convert-inspec",
            profile_path=str(profile_dir),
            output_path=str(tmp_path / "missing" / "out"),
            output_format="testinfra",
        )


def test_convert_cookbook_validation_and_assessment_file(tmp_path: Path) -> None:
    """Cover convert-cookbook output-parent and assessment-file branches."""
    cookbook = tmp_path / "cookbook"
    cookbook.mkdir()

    with pytest.raises(SystemExit):
        _invoke(
            "convert-cookbook",
            cookbook_path=str(cookbook),
            output_path=str(tmp_path / "missing" / "role"),
            assessment_file=None,
            role_name=None,
            skip_templates=False,
            skip_attributes=False,
            skip_recipes=False,
        )

    assessment_file = tmp_path / "a.json"
    assessment_file.write_text('{"k":1}')
    with patch("souschef.server.convert_cookbook_comprehensive", return_value="ok"):
        _invoke(
            "convert-cookbook",
            cookbook_path=str(cookbook),
            output_path=str(tmp_path / "role"),
            assessment_file=str(assessment_file),
            role_name=None,
            skip_templates=False,
            skip_attributes=False,
            skip_recipes=False,
        )

    with (
        patch(
            "pathlib.Path.resolve", autospec=True, side_effect=OSError("resolve bad")
        ),
        pytest.raises(SystemExit),
    ):
        _invoke(
            "convert-cookbook",
            cookbook_path=str(cookbook),
            output_path=str(tmp_path / "any"),
            assessment_file=None,
            role_name=None,
            skip_templates=False,
            skip_attributes=False,
            skip_recipes=False,
        )


def test_simulate_validate_query_convert_ai_history_and_main(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cover remaining command branches: simulate, validate, query, ai, history, main."""
    cb_dir = tmp_path / "cbs"
    cb_dir.mkdir()

    with patch("souschef.server.simulate_chef_to_awx_migration", return_value="sim-ok"):
        _invoke(
            "simulate-migration",
            cookbooks_path=str(cb_dir),
            output_path=str(tmp_path / "out"),
            target_platform="awx",
            chef_server_url="https://chef.example.com",
            organisation="default",
            include_repo=True,
            include_tar=True,
        )

    with patch(
        "souschef.core.chef_server._validate_chef_server_connection",
        return_value=(True, "ok"),
    ):
        _invoke(
            "validate-chef-server",
            server_url="https://chef.example.com",
            organisation="default",
            client_name="admin",
            client_key_path="",
        )

    monkeypatch.setenv("CHEF_SERVER_URL", "https://chef.example.com")
    monkeypatch.delenv("CHEF_CLIENT_NAME", raising=False)
    with pytest.raises(SystemExit):
        _invoke(
            "query-chef-nodes",
            search_query="*:*",
            server_url="",
            organisation="default",
            client_name="",
            client_key_path="",
            output_json=False,
        )

    monkeypatch.setenv("CHEF_CLIENT_NAME", "admin")
    monkeypatch.delenv("CHEF_CLIENT_KEY_PATH", raising=False)
    with pytest.raises(SystemExit):
        _invoke(
            "query-chef-nodes",
            search_query="*:*",
            server_url="",
            organisation="default",
            client_name="",
            client_key_path="",
            output_json=False,
        )

    erb = tmp_path / "t.erb"
    erb.write_text("<%= @a %>")
    with (
        patch(
            "souschef.converters.template.convert_template_with_ai",
            side_effect=RuntimeError("boom"),
        ),
        pytest.raises(SystemExit),
    ):
        _invoke("convert-template-ai", erb_path=str(erb), ai=True, output=None)

    class _Storage:
        def delete_analysis(self, _record_id):
            return False

        def delete_conversion(self, _record_id):
            raise RuntimeError("db")

    with (
        patch("souschef.storage.get_storage_manager", return_value=_Storage()),
        patch("click.confirm", return_value=False),
    ):
        _invoke_group(
            "history", "delete", history_type="analysis", record_id=1, yes=False
        )

    class _StorageSuccess:
        def delete_analysis(self, _record_id):
            return True

        def delete_conversion(self, _record_id):
            return True

    with patch("souschef.storage.get_storage_manager", return_value=_StorageSuccess()):
        _invoke_group(
            "history", "delete", history_type="conversion", record_id=2, yes=True
        )

    with (
        patch("souschef.storage.get_storage_manager", return_value=_Storage()),
        pytest.raises(SystemExit),
    ):
        _invoke_group(
            "history", "delete", history_type="analysis", record_id=1, yes=True
        )

    with (
        patch("souschef.storage.get_storage_manager", return_value=_Storage()),
        pytest.raises(SystemExit),
    ):
        _invoke_group(
            "history", "delete", history_type="conversion", record_id=2, yes=True
        )

    with (
        patch.object(cli_module, "configure_logging"),
        patch.object(cli_module, "cli"),
        patch("sys.exit", side_effect=SystemExit),
        pytest.raises(SystemExit),
    ):
        cli_module.main()


def test_parse_collections_file_error_branches(tmp_path: Path) -> None:
    """Cover parse-collections error and helper branches."""
    req = tmp_path / "requirements.yml"
    req.write_text("collections:\n  - community.general: '>=1.0.0'\n")

    # 2315-2320 import error branch
    import builtins

    real_import = builtins.__import__

    def _fake_import(name, *args, **kwargs):
        if name == "yaml":
            raise ImportError("no yaml")
        return real_import(name, *args, **kwargs)

    with (
        patch("builtins.__import__", side_effect=_fake_import),
        pytest.raises(ValueError),
    ):
        cli_module._parse_collections_file(str(req))

    # 2326 / 2328 / 2329-2330 validation branches
    with pytest.raises(ValueError):
        cli_module._parse_collections_file(str(tmp_path / "missing.yml"))

    dir_path = tmp_path / "dir"
    dir_path.mkdir()
    with pytest.raises(ValueError):
        cli_module._parse_collections_file(str(dir_path))

    with (
        patch("pathlib.Path.open", side_effect=OSError("cant read")),
        pytest.raises(ValueError),
    ):
        cli_module._parse_collections_file(str(req))

    # 2337 invalid structure + 2395/2398-2400 + 2414-2415 helper branches
    out: dict[str, str] = {}
    cli_module._add_dict_collections({1: "x", "a": None, "b": "1.2.3"}, out)  # type: ignore[dict-item]
    cli_module._add_string_collections("ns.col:2.0.0", out)
    assert out["a"] == "*"
    assert out["b"] == "1.2.3"
    assert out["ns.col"] == "2.0.0"


def test_main_and_convert_habitat_success_and_convert_inspec_oserror(
    tmp_path: Path,
) -> None:
    """Cover lines 1254, 1319-1322 and main() lines 2517-2519."""
    plan = tmp_path / "plan.sh"
    plan.write_text("pkg_name=test")

    with (
        patch(
            "pathlib.Path.resolve", autospec=True, side_effect=OSError("bad resolve")
        ),
        pytest.raises(SystemExit),
    ):
        _invoke(
            "convert-habitat",
            plan_path=str(plan),
            output_path=str(tmp_path / "o"),
            base_image="ubuntu:latest",
        )

    profile = tmp_path / "profile"
    profile.mkdir()
    with (
        patch(
            "pathlib.Path.resolve", autospec=True, side_effect=OSError("bad resolve")
        ),
        pytest.raises(SystemExit),
    ):
        _invoke(
            "convert-inspec",
            profile_path=str(profile),
            output_path=str(tmp_path / "o"),
            output_format="testinfra",
        )


def test_convert_cookbook_and_parse_collections_oserror_branches(
    tmp_path: Path,
) -> None:
    """Cover final OSError branches at lines 1322, 1423 and 2330."""
    cookbook = tmp_path / "cookbook"
    cookbook.mkdir()

    real_resolve = Path.resolve

    def _resolve_side_effect(path_self: Path, *args, **kwargs):
        path_str = str(path_self)
        if path_str.endswith("out-inspec") or path_str.endswith("out-cookbook"):
            raise OSError("resolve boom")
        return real_resolve(path_self, *args, **kwargs)

    profile = tmp_path / "profile"
    profile.mkdir()

    with (
        patch("pathlib.Path.resolve", autospec=True, side_effect=_resolve_side_effect),
        pytest.raises(SystemExit),
    ):
        _invoke(
            "convert-inspec",
            profile_path=str(profile),
            output_path=str(tmp_path / "out-inspec"),
            output_format="testinfra",
        )

    with (
        patch("pathlib.Path.resolve", autospec=True, side_effect=_resolve_side_effect),
        pytest.raises(SystemExit),
    ):
        _invoke(
            "convert-cookbook",
            cookbook_path=str(cookbook),
            output_path=str(tmp_path / "out-cookbook"),
            assessment_file=None,
            role_name=None,
            skip_templates=False,
            skip_attributes=False,
            skip_recipes=False,
        )

    with (
        patch(
            "pathlib.Path.resolve", autospec=True, side_effect=OSError("resolve bad")
        ),
        pytest.raises(ValueError),
    ):
        cli_module._parse_collections_file(str(tmp_path / "requirements.yml"))
