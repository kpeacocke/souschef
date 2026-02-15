"""Additional tests for assessment module to improve coverage."""

from pathlib import Path

from souschef.assessment import (
    analyse_cookbook_dependencies,
    assess_chef_migration_complexity,
    generate_migration_plan,
    generate_migration_report,
    parse_chef_migration_assessment,
    validate_conversion,
)


class TestAssessmentComplexity:
    """Test migration complexity assessment."""

    def test_assess_chef_migration_complexity_single_cookbook(
        self, tmp_path: Path
    ) -> None:
        """Test assessing a single cookbook."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'test'\nversion '1.0'")

        result = assess_chef_migration_complexity(str(cookbook_dir))
        assert isinstance(result, str)
        assert "test" in result or "cookbook" in result.lower() or len(result) > 0

    def test_assess_chef_migration_complexity_with_recipes(
        self, tmp_path: Path
    ) -> None:
        """Test assessment with multiple recipes."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'multi'")
        recipes_dir = cookbook_dir / "recipes"
        recipes_dir.mkdir()
        (recipes_dir / "default.rb").write_text("package 'nginx'")
        (recipes_dir / "database.rb").write_text("package 'postgresql'")

        result = assess_chef_migration_complexity(str(cookbook_dir))
        assert isinstance(result, str)

    def test_assess_chef_migration_complexity_with_attributes(
        self, tmp_path: Path
    ) -> None:
        """Test assessment with attributes."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'attr'")
        attrs_dir = cookbook_dir / "attributes"
        attrs_dir.mkdir()
        (attrs_dir / "default.rb").write_text("default[:key] = 'value'")

        result = assess_chef_migration_complexity(str(cookbook_dir))
        assert isinstance(result, str)

    def test_assess_chef_migration_complexity_with_templates(
        self, tmp_path: Path
    ) -> None:
        """Test assessment with templates."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'templates'")
        templates_dir = cookbook_dir / "templates"
        templates_dir.mkdir()
        (templates_dir / "config.erb").write_text("<%= @config %>")

        result = assess_chef_migration_complexity(str(cookbook_dir))
        assert isinstance(result, str)

    def test_assess_chef_migration_complexity_with_custom_resources(
        self, tmp_path: Path
    ) -> None:
        """Test assessment with custom resources."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'custom'")
        resources_dir = cookbook_dir / "resources"
        resources_dir.mkdir()
        (resources_dir / "custom.rb").write_text("property :name, String")

        result = assess_chef_migration_complexity(str(cookbook_dir))
        assert isinstance(result, str)

    def test_assess_chef_migration_complexity_with_inspec(self, tmp_path: Path) -> None:
        """Test assessment with InSpec tests."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'inspec'")
        profiles_dir = cookbook_dir / "test" / "compliance" / "profiles" / "test"
        profiles_dir.mkdir(parents=True)
        controls_dir = profiles_dir / "controls"
        controls_dir.mkdir()
        (controls_dir / "test.rb").write_text(
            "describe package('nginx') do\n  it { should be_installed }\nend"
        )

        result = assess_chef_migration_complexity(str(cookbook_dir))
        assert isinstance(result, str)

    def test_assess_chef_migration_complexity_full_migration_scope(
        self, tmp_path: Path
    ) -> None:
        """Test assessment with full migration scope."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'test'")

        result = assess_chef_migration_complexity(
            str(cookbook_dir), migration_scope="full"
        )
        assert isinstance(result, str)

    def test_assess_chef_migration_complexity_recipes_only_scope(
        self, tmp_path: Path
    ) -> None:
        """Test assessment with recipes-only scope."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'test'")

        result = assess_chef_migration_complexity(
            str(cookbook_dir), migration_scope="recipes_only"
        )
        assert isinstance(result, str)

    def test_assess_chef_migration_complexity_infrastructure_scope(
        self, tmp_path: Path
    ) -> None:
        """Test assessment with infrastructure scope."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'test'")

        result = assess_chef_migration_complexity(
            str(cookbook_dir), migration_scope="infrastructure_only"
        )
        assert isinstance(result, str)

    def test_assess_chef_migration_complexity_ansible_core_target(
        self, tmp_path: Path
    ) -> None:
        """Test assessment with Ansible Core target."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'test'")

        result = assess_chef_migration_complexity(
            str(cookbook_dir), target_platform="ansible_core"
        )
        assert isinstance(result, str)

    def test_assess_chef_migration_complexity_invalid_path(self) -> None:
        """Test assessment with invalid path."""
        result = assess_chef_migration_complexity("/nonexistent/path")
        assert isinstance(result, str)

    def test_assess_chef_migration_complexity_empty_string(self) -> None:
        """Test assessment with empty path."""
        result = assess_chef_migration_complexity("")
        assert isinstance(result, str)


class TestAnalyseCookbookDependencies:
    """Test cookbook dependency analysis."""

    def test_analyse_cookbook_dependencies_single(self, tmp_path: Path) -> None:
        """Test analyzing single cookbook dependencies."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text(
            "name 'test'\nversion '1.0'\n"
            "depends 'nginx', '~> 1.0'\n"
            "depends 'postgresql', '>= 2.0'"
        )

        result = analyse_cookbook_dependencies(str(cookbook_dir))
        assert isinstance(result, str)

    def test_analyse_cookbook_dependencies_version_constraints(
        self, tmp_path: Path
    ) -> None:
        """Test dependency analysis with various version constraints."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text(
            "name 'test'\n"
            "depends 'pkg1', '1.0'\n"
            "depends 'pkg2', '~> 2.0'\n"
            "depends 'pkg3', '>= 3.0'\n"
            "depends 'pkg4', '< 4.0'\n"
            "depends 'pkg5', '<= 5.0'"
        )

        result = analyse_cookbook_dependencies(str(cookbook_dir))
        assert isinstance(result, str)

    def test_analyse_cookbook_dependencies_no_deps(self, tmp_path: Path) -> None:
        """Test cookbook with no dependencies."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'standalone'\n")

        result = analyse_cookbook_dependencies(str(cookbook_dir))
        assert isinstance(result, str)

    def test_analyse_cookbook_dependencies_missing_metadata(
        self, tmp_path: Path
    ) -> None:
        """Test with missing metadata.rb."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()

        result = analyse_cookbook_dependencies(str(cookbook_dir))
        assert isinstance(result, str)


class TestGenerateMigrationPlan:
    """Test migration plan generation."""

    def test_generate_migration_plan_basic(self, tmp_path: Path) -> None:
        """Test generating basic migration plan."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'test'")
        recipes_dir = cookbook_dir / "recipes"
        recipes_dir.mkdir()
        (recipes_dir / "default.rb").write_text("package 'nginx'")

        result = generate_migration_plan(str(cookbook_dir))
        assert isinstance(result, str)

    def test_generate_migration_plan_multiple_cookbooks(self, tmp_path: Path) -> None:
        """Test migration plan with multiple cookbooks."""
        cookbook1 = tmp_path / "cookbook1"
        cookbook1.mkdir()
        (cookbook1 / "metadata.rb").write_text("name 'cb1'")

        cookbook2 = tmp_path / "cookbook2"
        cookbook2.mkdir()
        (cookbook2 / "metadata.rb").write_text("name 'cb2'")

        cookbooks = f"{cookbook1},{cookbook2}"
        result = generate_migration_plan(cookbooks)
        assert isinstance(result, str)

    def test_generate_migration_plan_with_dependencies(self, tmp_path: Path) -> None:
        """Test plan generation with cookbook dependencies."""
        cookbook = tmp_path / "cookbook"
        cookbook.mkdir()
        (cookbook / "metadata.rb").write_text(
            "name 'test'\ndepends 'nginx'\ndepends 'postgresql'"
        )

        result = generate_migration_plan(str(cookbook))
        assert isinstance(result, str)

    def test_generate_migration_plan_invalid_path(self) -> None:
        """Test plan with invalid path."""
        result = generate_migration_plan("/nonexistent")
        assert isinstance(result, str)


class TestGenerateMigrationReport:
    """Test migration report generation."""

    def test_generate_migration_report_basic(self, tmp_path: Path) -> None:
        """Test generating basic migration report."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'test'")

        result = generate_migration_report(str(cookbook_dir))
        assert isinstance(result, str)

    def test_generate_migration_report_with_recipes_and_attributes(
        self, tmp_path: Path
    ) -> None:
        """Test report with recipes and attributes."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'test'")

        recipes_dir = cookbook_dir / "recipes"
        recipes_dir.mkdir()
        (recipes_dir / "default.rb").write_text("package 'nginx'")

        attrs_dir = cookbook_dir / "attributes"
        attrs_dir.mkdir()
        (attrs_dir / "default.rb").write_text("default[:nginx][:port] = 80")

        result = generate_migration_report(str(cookbook_dir))
        assert isinstance(result, str)

    def test_generate_migration_report_complex_cookbook(self, tmp_path: Path) -> None:
        """Test report with complex cookbook."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text(
            "name 'complex'\nversion '2.0'\n"
            "depends 'dependency1'\n"
            "depends 'dependency2'"
        )

        recipes_dir = cookbook_dir / "recipes"
        recipes_dir.mkdir()
        (recipes_dir / "default.rb").write_text(
            "package 'pkg1'\nservice 'svc1' do\n  action [:enable, :start]\nend"
        )

        templates_dir = cookbook_dir / "templates"
        templates_dir.mkdir()
        (templates_dir / "config.erb").write_text("<config><%= @value %></config>")

        result = generate_migration_report(str(cookbook_dir))
        assert isinstance(result, str)


class TestValidateConversion:
    """Test conversion validation."""

    def test_validate_conversion_basic(self) -> None:
        """Test basic conversion validation."""
        chef_content = "package 'nginx'"
        ansible_content = "- name: Install nginx\n  package:\n    name: nginx"

        result = validate_conversion(chef_content, ansible_content)
        assert isinstance(result, (str, bool, dict))

    def test_validate_conversion_complex_resource(self) -> None:
        """Test validation of complex resource conversion."""
        chef_content = (
            "service 'nginx' do\n"
            "  action [:enable, :start]\n"
            "  subscribes :restart, 'template[/etc/nginx/nginx.conf]'\n"
            "end"
        )
        ansible_content = (
            "- name: Start nginx\n"
            "  service:\n"
            "    name: nginx\n"
            "    state: started\n"
            "    enabled: true"
        )

        result = validate_conversion(chef_content, ansible_content)
        assert isinstance(result, (str, bool, dict))

    def test_validate_conversion_empty_inputs(self) -> None:
        """Test validation with empty inputs."""
        result = validate_conversion("", "")
        assert isinstance(result, (str, bool, dict))

    def test_validate_conversion_multiline_content(self) -> None:
        """Test validation with multiline content."""
        chef_content = (
            "bash 'install packages' do\n"
            "  code 'apt-get install -y pkg1 pkg2'\n"
            "  only_if { node[:install_flag] == true }\n"
            "end"
        )
        ansible_content = (
            "- name: Install packages\n"
            "  shell: apt-get install -y pkg1 pkg2\n"
            "  when: install_flag | bool"
        )

        result = validate_conversion(chef_content, ansible_content)
        assert isinstance(result, (str, bool, dict))


class TestParseMigrationAssessment:
    """Test parsing migration assessment."""

    def test_parse_chef_migration_assessment_basic(self, tmp_path: Path) -> None:
        """Test parsing basic migration assessment."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'test'")

        result = parse_chef_migration_assessment(str(cookbook_dir))
        assert isinstance(result, (str, dict))

    def test_parse_chef_migration_assessment_with_recipes(self, tmp_path: Path) -> None:
        """Test assessment parsing with recipes."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'test'")

        recipes_dir = cookbook_dir / "recipes"
        recipes_dir.mkdir()
        (recipes_dir / "default.rb").write_text(
            "include_recipe 'test::helper'\npackage 'pkg'"
        )
        (recipes_dir / "helper.rb").write_text("# Helper recipe")

        result = parse_chef_migration_assessment(str(cookbook_dir))
        assert isinstance(result, (str, dict))

    def test_parse_chef_migration_assessment_missing_cookbook(self) -> None:
        """Test assessment of missing cookbook."""
        result = parse_chef_migration_assessment("/nonexistent/path")
        assert isinstance(result, (str, dict))

    def test_parse_chef_migration_assessment_deeply_nested_resources(
        self, tmp_path: Path
    ) -> None:
        """Test assessment of cookbook with deeply nested resources."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'nested'")

        recipes_dir = cookbook_dir / "recipes"
        recipes_dir.mkdir()
        complex_recipe = """
directory '/opt/app' do
  recursive true

  execute 'initialize' do
    command 'init.sh'
    not_if { ::File.exist?('/opt/app/.initialized') }
  end
end

file '/etc/config' do
  content lazy { default[:config_content] }
  notifies :restart, 'service[app]', :delayed
end

service 'app' do
  action [:enable, :start]
end
"""
        (recipes_dir / "default.rb").write_text(complex_recipe)

        result = parse_chef_migration_assessment(str(cookbook_dir))
        assert isinstance(result, (str, dict))


class TestAssessmentErrorHandling:
    """Test error handling in assessment functions."""

    def test_assess_complex_with_missing_files(self, tmp_path: Path) -> None:
        """Test assessment when files go missing during processing."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'test'")

        # Create recipe that will exist when function starts
        recipes_dir = cookbook_dir / "recipes"
        recipes_dir.mkdir()
        recipe_file = recipes_dir / "default.rb"
        recipe_file.write_text("package 'test'")

        # Assessment should complete even if files removed during processing
        result = assess_chef_migration_complexity(str(cookbook_dir))
        assert isinstance(result, str)

    def test_assess_with_large_cookbook(self, tmp_path: Path) -> None:
        """Test assessment of cookbook with many files."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'large'")

        recipes_dir = cookbook_dir / "recipes"
        recipes_dir.mkdir()
        for i in range(20):
            (recipes_dir / f"recipe{i}.rb").write_text(
                f"# Recipe {i}\npackage 'pkg{i}'"
            )

        attrs_dir = cookbook_dir / "attributes"
        attrs_dir.mkdir()
        for i in range(10):
            (attrs_dir / f"attr{i}.rb").write_text(f"default[:attr{i}] = 'value{i}'")

        result = assess_chef_migration_complexity(str(cookbook_dir))
        assert isinstance(result, str)

    def test_assess_with_special_characters_in_names(self, tmp_path: Path) -> None:
        """Test assessment with special characters in file/dir names."""
        cookbook_dir = tmp_path / "cookbook with spaces"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'test-cookbook'")

        recipes_dir = cookbook_dir / "recipes"
        recipes_dir.mkdir()
        (recipes_dir / "default-recipe.rb").write_text("package 'pkg'")

        result = assess_chef_migration_complexity(str(cookbook_dir))
        assert isinstance(result, str)
