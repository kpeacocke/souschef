"""
Ansible repository structure generation.

This module analyses converted Chef cookbooks and generates appropriate
Ansible repository structures with proper organisation, configuration files,
and git initialisation.
"""

import subprocess
from enum import Enum
from pathlib import Path
from typing import Any

from souschef.core.path_utils import _check_symlink_safety, _normalize_path

# Constants
HOSTS_FILE = "hosts.yml"


class RepoType(Enum):
    """Types of Ansible repository structures."""

    INVENTORY_FIRST = "inventory_first"  # Classic inventory-first (infra management)
    PLAYBOOKS_ROLES = "playbooks_roles"  # Simpler playbooks + roles
    COLLECTION = "collection"  # Ansible Collection (reusable automation)
    MONO_REPO = "mono_repo"  # Multi-project mono-repo


def analyse_conversion_output(
    cookbook_path: str,
    num_recipes: int = 0,
    num_roles: int = 0,
    has_multiple_apps: bool = False,
    needs_multi_env: bool = True,
    ai_provider: str = "",
    api_key: str = "",
    model: str = "",
) -> RepoType:
    """
    Analyse conversion output and determine the best repo type.

    Uses AI assessment if credentials are provided to make smarter decisions
    based on cookbook complexity, otherwise falls back to heuristic rules.

    Args:
        cookbook_path: Path to the Chef cookbook
        num_recipes: Number of recipes converted
        num_roles: Number of roles that would be created
        has_multiple_apps: Whether multiple applications are being managed
        needs_multi_env: Whether multiple environments are needed
        ai_provider: AI provider name (anthropic, openai, watson) optional
        api_key: API key for AI provider optional
        model: AI model to use optional

    Returns:
        The recommended RepoType

    """
    # Try AI-enhanced analysis if credentials provided
    if ai_provider and api_key:
        repo_type_ai = _analyse_with_ai(
            cookbook_path, num_recipes, num_roles, ai_provider, api_key, model
        )
        if repo_type_ai is not None:
            return repo_type_ai

    # Fall back to heuristic-based analysis
    return _analyse_with_heuristics(
        num_recipes, num_roles, has_multiple_apps, needs_multi_env
    )


def _analyse_with_heuristics(
    num_recipes: int,
    num_roles: int,
    has_multiple_apps: bool,
    needs_multi_env: bool,
) -> RepoType:
    """Apply heuristic rules for repository type selection."""
    # Collection layout for reusable automation (3+ roles)
    if num_roles >= 3:
        return RepoType.COLLECTION

    # Mono-repo for multiple applications
    if has_multiple_apps:
        return RepoType.MONO_REPO

    # Simple playbooks + roles for small projects
    if not needs_multi_env and num_recipes <= 3:
        return RepoType.PLAYBOOKS_ROLES

    # Default: inventory-first for infrastructure management
    return RepoType.INVENTORY_FIRST


def _analyse_with_ai(
    cookbook_path: str,
    num_recipes: int,
    num_roles: int,
    ai_provider: str,
    api_key: str,
    model: str,
) -> RepoType | None:
    """
    Analyse cookbook using AI to determine optimal repository type.

    Args:
        cookbook_path: Path to the Chef cookbook
        num_recipes: Number of recipes converted
        num_roles: Number of roles estimate
        ai_provider: AI provider name
        api_key: API key for AI provider
        model: AI model to use

    Returns:
        Recommended RepoType if AI assessment succeeds, None otherwise

    """
    try:
        # Import here to avoid circular dependencies
        from souschef.assessment import assess_single_cookbook_with_ai  # noqa: F401

        # Perform AI assessment
        assessment = assess_single_cookbook_with_ai(
            cookbook_path=cookbook_path,
            ai_provider=ai_provider,
            api_key=api_key,
            model=model or "claude-3-5-sonnet-20241022",
            temperature=0.3,
            max_tokens=2000,
        )

        # Check for errors in assessment
        if "error" in assessment:
            return None

        # Extract complexity score (0-100)
        complexity_score = assessment.get("complexity_score", 0)

        # AI-informed decision making
        # High complexity + multiple roles should be a collection
        if complexity_score > 70 and num_roles >= 2:
            return RepoType.COLLECTION

        # Medium-high complexity with multiple roles
        if complexity_score > 50 and num_roles >= 2:
            return RepoType.COLLECTION

        # High complexity generally benefits from inventory-first
        if complexity_score > 70:
            return RepoType.INVENTORY_FIRST

        # Low complexity recipes with minimal roles
        if complexity_score < 30 and num_roles <= 1 and num_recipes <= 3:
            return RepoType.PLAYBOOKS_ROLES

        # Medium complexity with simple structure
        if complexity_score < 50 and num_roles <= 1:
            return RepoType.PLAYBOOKS_ROLES

        # Default to inventory-first for AI-assessed cookbooks
        return RepoType.INVENTORY_FIRST

    except Exception:
        # If AI fails, return None to fall back to heuristics
        return None


def _create_ansible_cfg(repo_path: Path, repo_type: RepoType) -> None:
    """Create ansible.cfg with appropriate settings."""
    inventory_path = (
        "./inventory" if repo_type == RepoType.PLAYBOOKS_ROLES else "./inventories/prod"
    )
    roles_path = (
        "./roles"
        if repo_type != RepoType.COLLECTION
        else "./ansible_collections/*/*/roles"
    )

    cfg_content = f"""[defaults]
inventory = {inventory_path}
roles_path = {roles_path}
host_key_checking = False
retry_files_enabled = False
gathering = smart
fact_caching = jsonfile
fact_caching_connection = /tmp/ansible_facts
fact_caching_timeout = 3600
callbacks_enabled = profile_tasks, timer

[privilege_escalation]
become = True
become_method = sudo
become_user = root
become_ask_pass = False

[ssh_connection]
pipelining = True
ssh_args = -o ControlMaster=auto -o ControlPersist=60s

[diff]
always = False
context = 3
"""
    (repo_path / "ansible.cfg").write_text(cfg_content)


def _create_requirements_yml(repo_path: Path) -> None:
    """Create requirements.yml for dependencies."""
    requirements_content = """---
# Ansible Collections
collections:
  - name: ansible.posix
    version: ">=1.5.0"
  - name: community.general
    version: ">=8.0.0"

# Ansible Roles (if using Galaxy roles)
roles: []
"""
    (repo_path / "requirements.yml").write_text(requirements_content)


def _create_gitignore(repo_path: Path) -> None:
    """Create .gitignore for Ansible projects."""
    gitignore_content = """# Ansible
*.retry
.ansible/
/tmp/
/temp/

# Vault
vault-password.txt
.vault_pass*

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
ENV/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Logs
*.log
"""
    (repo_path / ".gitignore").write_text(gitignore_content)


def _create_gitattributes(repo_path: Path) -> None:
    """Create .gitattributes for consistent line endings and file handling."""
    gitattributes_content = """# Auto detect text files and perform LF normalisation
* text=auto eol=lf

# Explicitly declare text files
*.py text
*.yml text
*.yaml text
*.ini text
*.cfg text
*.conf text
*.txt text
*.md text
*.rst text
*.j2 text

# Declare files that will always have LF line endings on checkout
*.sh text eol=lf

# Denote binary files
*.png binary
*.jpg binary
*.jpeg binary
*.gif binary
*.ico binary
*.zip binary
*.tar binary
*.gz binary
"""
    (repo_path / ".gitattributes").write_text(gitattributes_content)


def _create_editorconfig(repo_path: Path) -> None:
    """Create .editorconfig for consistent coding styles."""
    editorconfig_content = """# EditorConfig for Ansible projects
# https://editorconfig.org

root = true

# All files
[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
trim_trailing_whitespace = true

# YAML files (Ansible playbooks, vars, etc.)
[*.{yml,yaml}]
indent_style = space
indent_size = 2

# Python files
[*.py]
indent_style = space
indent_size = 4
max_line_length = 88

# Jinja2 templates
[*.j2]
indent_style = space
indent_size = 2

# Shell scripts
[*.sh]
indent_style = space
indent_size = 2

# Markdown
[*.md]
trim_trailing_whitespace = false
max_line_length = off

# Makefile
[Makefile]
indent_style = tab
"""
    (repo_path / ".editorconfig").write_text(editorconfig_content)


def _create_readme(repo_path: Path, repo_type: RepoType, org_name: str) -> None:
    """Create README.md with usage instructions."""
    type_desc = {
        RepoType.INVENTORY_FIRST: (
            "inventory-first structure for infrastructure management"
        ),
        RepoType.PLAYBOOKS_ROLES: "simple playbooks and roles structure",
        RepoType.COLLECTION: "Ansible Collection for reusable automation",
        RepoType.MONO_REPO: "mono-repository for multiple projects",
    }

    readme_content = f"""# {org_name} Ansible Automation

This repository uses a {type_desc.get(repo_type, "standard")} approach.

## Structure

Generated from Chef cookbook conversion using SousChef.

## Quick Start

1. Install dependencies:
   ```bash
   ansible-galaxy install -r requirements.yml
   ```

2. Configure inventory:
   - Update inventory files with your hosts
   - Set environment-specific variables in group_vars/host_vars

3. Run playbooks:
   ```bash
   ansible-playbook playbooks/site.yml
   ```

## Requirements

- Ansible >= 2.15
- Python >= 3.9

## Security

- Never commit secrets to git
- Use Ansible Vault for sensitive data: `ansible-vault encrypt_string`
- Store vault password securely (not in this repo)

## Documentation

- [Ansible Best Practices](https://docs.ansible.com/ansible/latest/user_guide/playbooks_best_practices.html)
- [Ansible Vault](https://docs.ansible.com/ansible/latest/user_guide/vault.html)

---
Generated by [SousChef](https://github.com/kpeacocke/souschef)
"""
    (repo_path / "README.md").write_text(readme_content)


def _create_inventory_first_structure(repo_path: Path) -> None:
    """Create classic inventory-first repo structure."""
    # Top-level directories
    (repo_path / "inventories" / "prod" / "group_vars").mkdir(parents=True)
    (repo_path / "inventories" / "prod" / "host_vars").mkdir(parents=True)
    (repo_path / "inventories" / "nonprod" / "group_vars").mkdir(parents=True)
    (repo_path / "inventories" / "nonprod" / "host_vars").mkdir(parents=True)
    (repo_path / "playbooks").mkdir()
    (repo_path / "roles").mkdir()
    (repo_path / "filter_plugins").mkdir()
    (repo_path / "library").mkdir()

    # Create sample inventory files
    prod_hosts = """---
all:
  children:
    webservers:
      hosts:
        web1.example.com:
        web2.example.com:
    databases:
      hosts:
        db1.example.com:
"""
    (repo_path / "inventories" / "prod" / HOSTS_FILE).write_text(prod_hosts)
    (repo_path / "inventories" / "nonprod" / HOSTS_FILE).write_text(prod_hosts)

    # Create sample group_vars
    all_vars = """---
# Variables for all hosts
ansible_user: ansible
ansible_python_interpreter: /usr/bin/python3
"""
    (repo_path / "inventories" / "prod" / "group_vars" / "all.yml").write_text(all_vars)

    # Create sample playbook
    site_playbook = """---
- name: Site-wide configuration
  hosts: all
  gather_facts: true
  tasks:
    - name: Ensure system is up to date
      ansible.builtin.package:
        name: "*"
        state: latest
      when: ansible_os_family == "RedHat"
"""
    (repo_path / "playbooks" / "site.yml").write_text(site_playbook)


def _create_playbooks_roles_structure(repo_path: Path) -> None:
    """Create simple playbooks + roles structure."""
    (repo_path / "inventory" / "group_vars").mkdir(parents=True)
    (repo_path / "inventory" / "host_vars").mkdir(parents=True)
    (repo_path / "playbooks").mkdir()
    (repo_path / "roles").mkdir()

    # Simple inventory
    hosts = """---
all:
  hosts:
    localhost:
      ansible_connection: local
"""
    (repo_path / "inventory" / "hosts.yml").write_text(hosts)

    # Simple playbook
    deploy_playbook = """---
- name: Deploy application
  hosts: all
  gather_facts: true
  roles:
    - common
"""
    (repo_path / "playbooks" / "deploy.yml").write_text(deploy_playbook)


def _create_collection_structure(repo_path: Path, org_name: str) -> None:
    """Create Ansible Collection layout."""
    collection_name = org_name.lower().replace("-", "_")
    base_path = repo_path / "ansible_collections" / collection_name / "platform"

    (base_path / "plugins" / "modules").mkdir(parents=True)
    (base_path / "plugins" / "filter").mkdir(parents=True)
    (base_path / "roles").mkdir(parents=True)
    (base_path / "playbooks").mkdir(parents=True)
    (base_path / "docs").mkdir(parents=True)
    (base_path / "tests").mkdir(parents=True)

    # Galaxy metadata
    galaxy_yml = f"""---
namespace: {collection_name}
name: platform
version: 1.0.0
readme: README.md
authors:
  - Your Name <you@example.com>
description: Platform automation collection converted from Chef
license:
  - MIT
tags:
  - infrastructure
  - automation
dependencies: {{}}
repository: https://github.com/{org_name}/ansible-platform
"""
    (base_path / "galaxy.yml").write_text(galaxy_yml)

    # Collection README
    collection_readme = f"""# {collection_name}.platform Collection

Ansible Collection for platform automation.

## Installation

```bash
ansible-galaxy collection install {collection_name}.platform
```

## Usage

```yaml
- hosts: all
  collections:
    - {collection_name}.platform
  tasks:
    - import_role:
        name: common
```
"""
    (base_path / "README.md").write_text(collection_readme)


def _create_mono_repo_structure(repo_path: Path) -> None:
    """Create multi-project mono-repo structure."""
    (repo_path / "inventories" / "prod").mkdir(parents=True)
    (repo_path / "inventories" / "nonprod").mkdir(parents=True)
    (repo_path / "projects" / "app1" / "playbooks").mkdir(parents=True)
    (repo_path / "projects" / "app1" / "roles").mkdir(parents=True)
    (repo_path / "shared_roles").mkdir()
    (repo_path / "collections").mkdir()

    # Sample project structure
    app1_playbook = """---
- name: Deploy App1
  hosts: app1_servers
  gather_facts: true
  roles:
    - role: shared_roles/common
    - role: app1_config
"""
    (repo_path / "projects" / "app1" / "playbooks" / "deploy.yml").write_text(
        app1_playbook
    )


def _init_git_repo(repo_path: Path) -> str:
    """Initialise git repository with souschef user configuration."""
    try:
        # Initialize git
        subprocess.run(
            ["git", "init"],
            cwd=repo_path,
            check=True,
            capture_output=True,
            text=True,
        )

        # Configure git user for this repository
        subprocess.run(
            ["git", "config", "user.name", "souschef"],
            cwd=repo_path,
            check=True,
            capture_output=True,
            text=True,
        )

        subprocess.run(
            ["git", "config", "user.email", "souschef@ansible.local"],
            cwd=repo_path,
            check=True,
            capture_output=True,
            text=True,
        )

        # Create initial commit
        subprocess.run(
            ["git", "add", "."],
            cwd=repo_path,
            check=True,
            capture_output=True,
            text=True,
        )

        subprocess.run(
            ["git", "commit", "-m", "Initial commit: Ansible repo structure"],
            cwd=repo_path,
            check=True,
            capture_output=True,
            text=True,
        )

        return "Git repository initialised with initial commit"
    except subprocess.CalledProcessError as e:
        return f"Git initialisation failed: {e.stderr}"
    except FileNotFoundError:
        return "Git not found - skipped repository initialisation"


def _create_repo_structure(repo_path: Path, repo_type: RepoType, org_name: str) -> None:
    """
    Create repository structure based on type.

    Args:
        repo_path: Path to repository root
        repo_type: Type of repository to create
        org_name: Organisation name for the repository

    """
    if repo_type == RepoType.INVENTORY_FIRST:
        _create_inventory_first_structure(repo_path)
    elif repo_type == RepoType.PLAYBOOKS_ROLES:
        _create_playbooks_roles_structure(repo_path)
    elif repo_type == RepoType.COLLECTION:
        _create_collection_structure(repo_path, org_name)
    elif repo_type == RepoType.MONO_REPO:
        _create_mono_repo_structure(repo_path)


def generate_ansible_repository(
    output_path: str,
    repo_type: RepoType | str,
    org_name: str = "myorg",
    init_git: bool = True,
) -> dict[str, Any]:
    """
    Generate a complete Ansible repository structure.

    Args:
        output_path: Path where the repository should be created
        repo_type: Type of repository structure to generate
        org_name: Organisation name for the repository
        init_git: Whether to initialise a git repository

    Returns:
        Dictionary with generation results including:
        - success: Whether generation succeeded
        - repo_path: Path to the created repository
        - repo_type: Type of repository created
        - files_created: List of files created
        - git_status: Git initialisation status

    """
    # Convert string to enum if needed
    if isinstance(repo_type, str):
        try:
            repo_type = RepoType(repo_type)
        except ValueError:
            return {
                "success": False,
                "error": f"Invalid repo_type: {repo_type}. "
                f"Valid types: {[t.value for t in RepoType]}",
            }

    try:
        # Check for symlinks before normalisation to detect attacks
        _check_symlink_safety(_normalize_path(output_path), Path(output_path))

        # Validate and normalise the output path
        repo_path = _normalize_path(output_path)
    except ValueError as e:
        return {
            "success": False,
            "error": f"Invalid output path: {e}",
        }

    # Check if path already exists
    if repo_path.exists():
        return {
            "success": False,
            "error": f"Path already exists: {output_path}",
        }

    try:
        # Create base directory
        repo_path.mkdir(parents=True)

        # Create common files
        _create_ansible_cfg(repo_path, repo_type)
        _create_requirements_yml(repo_path)
        _create_gitignore(repo_path)
        _create_gitattributes(repo_path)
        _create_editorconfig(repo_path)
        _create_readme(repo_path, repo_type, org_name)

        # Create structure based on repo type
        _create_repo_structure(repo_path, repo_type, org_name)

        # Collect created files
        files_created = [
            str(p.relative_to(repo_path)) for p in repo_path.rglob("*") if p.is_file()
        ]

        # Initialize git if requested
        git_status = ""
        if init_git:
            git_status = _init_git_repo(repo_path)

        return {
            "success": True,
            "repo_path": str(repo_path),
            "repo_type": repo_type.value,
            "files_created": sorted(files_created),
            "git_status": git_status,
            "message": f"Successfully created {repo_type.value} repository structure",
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to generate repository: {e}",
        }
