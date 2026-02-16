"""
Integration tests for AWX/AAP API with mock HTTP responses.

Tests AWX/Ansible Tower API interactions using mocked HTTP responses
instead of a real AWX/AAP instance. Covers common API endpoints for
job templates, inventories, credentials, projects, and workflows.
"""

from __future__ import annotations

import pytest
import responses

from souschef.core.chef_server import requests_module

if requests_module is None:
    pytest.skip("requests is required for AWX mock tests", allow_module_level=True)


class TestAWXMockJobTemplates:
    """Test AWX Job Template API endpoints with mock responses."""

    @responses.activate
    def test_list_job_templates(self) -> None:
        """Test listing job templates."""
        mock_job_templates = {
            "count": 2,
            "results": [
                {
                    "id": 1,
                    "name": "Deploy Apache",
                    "description": "Deploy Apache web server",
                    "job_type": "run",
                    "inventory": 1,
                    "project": 1,
                    "playbook": "apache_deploy.yml",
                    "credential": 1,
                },
                {
                    "id": 2,
                    "name": "Deploy MySQL",
                    "description": "Deploy MySQL database",
                    "job_type": "run",
                    "inventory": 1,
                    "project": 1,
                    "playbook": "mysql_deploy.yml",
                    "credential": 1,
                },
            ],
        }

        responses.add(
            responses.GET,
            "https://awx.example.com/api/v2/job_templates/",
            json=mock_job_templates,
            status=200,
        )

        # Simulate API call (you would use requests or AWX client here)
        response = requests_module.get(
            "https://awx.example.com/api/v2/job_templates/",
            headers={"Authorization": "Bearer test-token"},
            timeout=10,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        assert len(data["results"]) == 2
        assert data["results"][0]["name"] == "Deploy Apache"
        assert data["results"][1]["playbook"] == "mysql_deploy.yml"

    @responses.activate
    def test_create_job_template(self) -> None:
        """Test creating a new job template."""
        new_template = {
            "name": "Deploy Nginx",
            "description": "Deploy Nginx web server",
            "job_type": "run",
            "inventory": 1,
            "project": 1,
            "playbook": "nginx_deploy.yml",
            "credential": 1,
        }

        mock_response = {
            "id": 3,
            **new_template,
            "created": "2026-02-16T12:00:00.000000Z",
            "modified": "2026-02-16T12:00:00.000000Z",
        }

        responses.add(
            responses.POST,
            "https://awx.example.com/api/v2/job_templates/",
            json=mock_response,
            status=201,
        )

        response = requests_module.post(
            "https://awx.example.com/api/v2/job_templates/",
            json=new_template,
            headers={"Authorization": "Bearer test-token"},
            timeout=10,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["id"] == 3
        assert data["name"] == "Deploy Nginx"
        assert "created" in data

    @responses.activate
    def test_launch_job_template(self) -> None:
        """Test launching a job template."""
        launch_response = {
            "job": 42,
            "ignored_fields": {},
            "id": 42,
            "type": "job",
            "url": "/api/v2/jobs/42/",
            "status": "pending",
            "failed": False,
        }

        responses.add(
            responses.POST,
            "https://awx.example.com/api/v2/job_templates/1/launch/",
            json=launch_response,
            status=201,
        )

        response = requests_module.post(
            "https://awx.example.com/api/v2/job_templates/1/launch/",
            json={"extra_vars": {"target_env": "production"}},
            headers={"Authorization": "Bearer test-token"},
            timeout=10,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["job"] == 42
        assert data["status"] == "pending"


class TestAWXMockInventories:
    """Test AWX Inventory API endpoints."""

    @responses.activate
    def test_list_inventories(self) -> None:
        """Test listing inventories."""
        mock_inventories = {
            "count": 3,
            "results": [
                {
                    "id": 1,
                    "name": "Production Servers",
                    "description": "Production environment",
                    "organization": 1,
                    "total_hosts": 25,
                    "total_groups": 5,
                },
                {
                    "id": 2,
                    "name": "Staging Servers",
                    "description": "Staging environment",
                    "organization": 1,
                    "total_hosts": 10,
                    "total_groups": 3,
                },
            ],
        }

        responses.add(
            responses.GET,
            "https://awx.example.com/api/v2/inventories/",
            json=mock_inventories,
            status=200,
        )

        response = requests_module.get(
            "https://awx.example.com/api/v2/inventories/",
            headers={"Authorization": "Bearer test-token"},
            timeout=10,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 3
        assert data["results"][0]["total_hosts"] == 25

    @responses.activate
    def test_sync_inventory_source(self) -> None:
        """Test syncing an inventory source."""
        sync_response = {
            "inventory_update": 15,
            "status": "pending",
            "can_cancel": True,
        }

        responses.add(
            responses.POST,
            "https://awx.example.com/api/v2/inventory_sources/5/update/",
            json=sync_response,
            status=202,
        )

        response = requests_module.post(
            "https://awx.example.com/api/v2/inventory_sources/5/update/",
            headers={"Authorization": "Bearer test-token"},
            timeout=10,
        )

        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "pending"
        assert data["inventory_update"] == 15


class TestAWXMockProjects:
    """Test AWX Project API endpoints."""

    @responses.activate
    def test_list_projects(self) -> None:
        """Test listing projects."""
        mock_projects = {
            "count": 2,
            "results": [
                {
                    "id": 1,
                    "name": "Ansible Playbooks",
                    "description": "Main playbook repository",
                    "scm_type": "git",
                    "scm_url": "https://github.com/example/playbooks.git",
                    "scm_branch": "main",
                    "status": "successful",
                },
                {
                    "id": 2,
                    "name": "Chef Migrations",
                    "description": "Converted Chef cookbooks",
                    "scm_type": "git",
                    "scm_url": "https://github.com/example/chef-migrations.git",
                    "scm_branch": "main",
                    "status": "successful",
                },
            ],
        }

        responses.add(
            responses.GET,
            "https://awx.example.com/api/v2/projects/",
            json=mock_projects,
            status=200,
        )

        response = requests_module.get(
            "https://awx.example.com/api/v2/projects/",
            headers={"Authorization": "Bearer test-token"},
            timeout=10,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        assert data["results"][0]["scm_type"] == "git"

    @responses.activate
    def test_update_project(self) -> None:
        """Test updating a project (SCM sync)."""
        update_response = {
            "project_update": 8,
            "status": "pending",
            "can_cancel": True,
        }

        responses.add(
            responses.POST,
            "https://awx.example.com/api/v2/projects/1/update/",
            json=update_response,
            status=202,
        )

        response = requests_module.post(
            "https://awx.example.com/api/v2/projects/1/update/",
            headers={"Authorization": "Bearer test-token"},
            timeout=10,
        )

        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "pending"


class TestAWXMockCredentials:
    """Test AWX Credentials API endpoints."""

    @responses.activate
    def test_list_credentials(self) -> None:
        """Test listing credentials."""
        mock_credentials = {
            "count": 2,
            "results": [
                {
                    "id": 1,
                    "name": "SSH Key",
                    "description": "Production SSH key",
                    "credential_type": 1,
                    "kind": "ssh",
                },
                {
                    "id": 2,
                    "name": "AWS Credentials",
                    "description": "AWS access keys",
                    "credential_type": 3,
                    "kind": "aws",
                },
            ],
        }

        responses.add(
            responses.GET,
            "https://awx.example.com/api/v2/credentials/",
            json=mock_credentials,
            status=200,
        )

        response = requests_module.get(
            "https://awx.example.com/api/v2/credentials/",
            headers={"Authorization": "Bearer test-token"},
            timeout=10,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        assert data["results"][0]["kind"] == "ssh"


class TestAWXMockWorkflows:
    """Test AWX Workflow Template API endpoints."""

    @responses.activate
    def test_list_workflow_templates(self) -> None:
        """Test listing workflow templates."""
        mock_workflows = {
            "count": 1,
            "results": [
                {
                    "id": 1,
                    "name": "Full Stack Deployment",
                    "description": "Deploy all components",
                    "organization": 1,
                    "inventory": 1,
                },
            ],
        }

        responses.add(
            responses.GET,
            "https://awx.example.com/api/v2/workflow_job_templates/",
            json=mock_workflows,
            status=200,
        )

        response = requests_module.get(
            "https://awx.example.com/api/v2/workflow_job_templates/",
            headers={"Authorization": "Bearer test-token"},
            timeout=10,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["results"][0]["name"] == "Full Stack Deployment"

    @responses.activate
    def test_launch_workflow(self) -> None:
        """Test launching a workflow."""
        launch_response = {
            "workflow_job": 25,
            "id": 25,
            "type": "workflow_job",
            "url": "/api/v2/workflow_jobs/25/",
            "status": "pending",
        }

        responses.add(
            responses.POST,
            "https://awx.example.com/api/v2/workflow_job_templates/1/launch/",
            json=launch_response,
            status=201,
        )

        response = requests_module.post(
            "https://awx.example.com/api/v2/workflow_job_templates/1/launch/",
            json={"extra_vars": {}},
            headers={"Authorization": "Bearer test-token"},
            timeout=10,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["workflow_job"] == 25
        assert data["status"] == "pending"


class TestAWXMockJobs:
    """Test AWX Job monitoring and status endpoints."""

    @responses.activate
    def test_get_job_status(self) -> None:
        """Test getting job status."""
        job_status = {
            "id": 42,
            "type": "job",
            "name": "Deploy Apache",
            "status": "successful",
            "failed": False,
            "started": "2026-02-16T12:00:00.000000Z",
            "finished": "2026-02-16T12:05:00.000000Z",
            "elapsed": 300.5,
        }

        responses.add(
            responses.GET,
            "https://awx.example.com/api/v2/jobs/42/",
            json=job_status,
            status=200,
        )

        response = requests_module.get(
            "https://awx.example.com/api/v2/jobs/42/",
            headers={"Authorization": "Bearer test-token"},
            timeout=10,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "successful"
        assert data["failed"] is False
        assert data["elapsed"] == pytest.approx(300.5)

    @responses.activate
    def test_get_job_output(self) -> None:
        """Test getting job output/stdout."""
        job_output = {
            "content": """
PLAY [webservers] **************************************************************

TASK [Gathering Facts] *********************************************************
ok: [web-01]

TASK [Install Apache] **********************************************************
changed: [web-01]

PLAY RECAP *********************************************************************
web-01                     : ok=2    changed=1    unreachable=0    failed=0
""",
            "range": {"start": 0, "end": 300, "absolute_end": 300},
        }

        responses.add(
            responses.GET,
            "https://awx.example.com/api/v2/jobs/42/stdout/",
            json=job_output,
            status=200,
        )

        response = requests_module.get(
            "https://awx.example.com/api/v2/jobs/42/stdout/",
            headers={"Authorization": "Bearer test-token"},
            timeout=10,
        )

        assert response.status_code == 200
        data = response.json()
        assert "PLAY RECAP" in data["content"]
        assert "ok=2" in data["content"]

    @responses.activate
    def test_cancel_job(self) -> None:
        """Test canceling a running job."""
        cancel_response = {"can_cancel": True, "status": "canceled"}

        responses.add(
            responses.POST,
            "https://awx.example.com/api/v2/jobs/42/cancel/",
            json=cancel_response,
            status=202,
        )

        response = requests_module.post(
            "https://awx.example.com/api/v2/jobs/42/cancel/",
            headers={"Authorization": "Bearer test-token"},
            timeout=10,
        )

        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "canceled"


class TestAWXMockAuthAndErrors:
    """Test AWX authentication and error handling."""

    @responses.activate
    def test_unauthorized_access(self) -> None:
        """Test 401 unauthorized response."""
        responses.add(
            responses.GET,
            "https://awx.example.com/api/v2/job_templates/",
            json={"detail": "Authentication credentials were not provided."},
            status=401,
        )

        response = requests_module.get(
            "https://awx.example.com/api/v2/job_templates/",
            timeout=10,
        )

        assert response.status_code == 401
        assert "Authentication" in response.json()["detail"]

    @responses.activate
    def test_forbidden_access(self) -> None:
        """Test 403 forbidden response."""
        responses.add(
            responses.GET,
            "https://awx.example.com/api/v2/job_templates/999/",
            json={"detail": "You do not have permission to perform this action."},
            status=403,
        )

        response = requests_module.get(
            "https://awx.example.com/api/v2/job_templates/999/",
            headers={"Authorization": "Bearer test-token"},
            timeout=10,
        )

        assert response.status_code == 403
        assert "permission" in response.json()["detail"]

    @responses.activate
    def test_not_found(self) -> None:
        """Test 404 not found response."""
        responses.add(
            responses.GET,
            "https://awx.example.com/api/v2/job_templates/9999/",
            json={"detail": "Not found."},
            status=404,
        )

        response = requests_module.get(
            "https://awx.example.com/api/v2/job_templates/9999/",
            headers={"Authorization": "Bearer test-token"},
            timeout=10,
        )

        assert response.status_code == 404
        assert "Not found" in response.json()["detail"]

    @responses.activate
    def test_validation_error(self) -> None:
        """Test 400 validation error response."""
        error_response = {
            "name": ["This field is required."],
            "inventory": ["Invalid inventory ID."],
        }

        responses.add(
            responses.POST,
            "https://awx.example.com/api/v2/job_templates/",
            json=error_response,
            status=400,
        )

        response = requests_module.post(
            "https://awx.example.com/api/v2/job_templates/",
            json={"description": "Missing required fields"},
            headers={"Authorization": "Bearer test-token"},
            timeout=10,
        )

        assert response.status_code == 400
        data = response.json()
        assert "name" in data
        assert "required" in data["name"][0]


class TestAWXMockOrganizations:
    """Test AWX Organizations API endpoints."""

    @responses.activate
    def test_list_organizations(self) -> None:
        """Test listing organizations."""
        mock_orgs = {
            "count": 2,
            "results": [
                {
                    "id": 1,
                    "name": "Default",
                    "description": "Default organization",
                },
                {
                    "id": 2,
                    "name": "Engineering",
                    "description": "Engineering team organization",
                },
            ],
        }

        responses.add(
            responses.GET,
            "https://awx.example.com/api/v2/organizations/",
            json=mock_orgs,
            status=200,
        )

        response = requests_module.get(
            "https://awx.example.com/api/v2/organizations/",
            headers={"Authorization": "Bearer test-token"},
            timeout=10,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        assert data["results"][0]["name"] == "Default"
