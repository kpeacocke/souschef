#!/usr/bin/env python3
"""
Demo script showing how to use mock Chef Server for testing.

This demonstrates testing Chef Server integration WITHOUT a real Chef Server
using the responses library to mock HTTP responses.
"""

import responses
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from souschef.core.chef_server import ChefServerClient, ChefServerConfig

CHEF_SERVER_URL = "https://chef.example.com"
CHEF_ORG = "demo-org"
CHEF_SEARCH_URL = f"{CHEF_SERVER_URL}/organizations/{CHEF_ORG}/search/node"
CHEF_COOKBOOKS_URL = f"{CHEF_SERVER_URL}/organizations/{CHEF_ORG}/cookbooks"


def generate_test_key() -> str:
    """Generate a test RSA key for demo purposes."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    key_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return key_pem.decode("utf-8")


@responses.activate
def demo_connection_test():
    """Demo: Test Chef Server connection with mock response."""
    print("\n=== Demo 1: Connection Test ===")

    # Step 1: Setup mock response
    responses.add(
        responses.GET,
        CHEF_SEARCH_URL,
        json={"rows": [], "total": 0, "start": 0},
        status=200,
    )

    # Step 2: Create client config with test key
    config = ChefServerConfig(
        server_url=CHEF_SERVER_URL,
        organisation=CHEF_ORG,
        client_name="demo-client",
        client_key=generate_test_key(),
        timeout=10,
    )

    # Step 3: Test connection
    client = ChefServerClient(config)
    success, message = client.test_connection()

    # Step 4: Verify results
    print(f"✅ Connection: {success}")
    print(f"   Message: {message}")
    print(f"   Requests made: {len(responses.calls)}")

    # Step 5: Inspect auth headers
    headers = responses.calls[0].request.headers
    print("   Auth headers sent:")
    print(f"   - X-Ops-Userid: {headers.get('X-Ops-Userid')}")
    print(f"   - X-Ops-Sign: {headers.get('X-Ops-Sign')}")
    auth_header = headers.get("X-Ops-Authorization-1")
    if auth_header:
        print(f"   - X-Ops-Authorization-1: {auth_header[:30]}...")


@responses.activate
def demo_node_search():
    """Demo: Search for nodes with mock data."""
    print("\n=== Demo 2: Node Search ===")

    # Mock node data
    mock_nodes = {
        "rows": [
            {
                "name": "web-server-01",
                "run_list": ["role[webserver]", "role[monitoring]"],
                "chef_environment": "production",
                "platform": "ubuntu",
                "ipaddress": "10.0.1.10",  # NOSONAR - S1313: mock data for demo
                "fqdn": "web-server-01.example.com",
                "automatic": {"platform_version": "22.04"},
            },
            {
                "name": "db-server-01",
                "run_list": ["role[database]"],
                "chef_environment": "production",
                "platform": "centos",
                "ipaddress": "10.0.1.20",  # NOSONAR - S1313: mock data for demo
                "fqdn": "db-server-01.example.com",
                "automatic": {"platform_version": "8"},
            },
        ],
        "total": 2,
        "start": 0,
    }

    # Setup mock
    responses.add(
        responses.GET,
        CHEF_SEARCH_URL,
        json=mock_nodes,
        status=200,
    )

    # Search nodes
    config = ChefServerConfig(
        server_url=CHEF_SERVER_URL,
        organisation=CHEF_ORG,
        client_name="demo-client",
        client_key=generate_test_key(),
        timeout=10,
    )
    client = ChefServerClient(config)
    nodes = client.search_nodes("role:webserver")

    # Display results
    print(f"✅ Found {len(nodes)} nodes:")
    for node in nodes:
        print(f"   - {node['name']}: {node['platform']} @ {node['ipaddress']}")
        print(f"     Environment: {node['environment']}")
        print(f"     Roles: {', '.join(node['roles'])}")


@responses.activate
def demo_list_roles():
    """Demo: List Chef Server roles."""
    print("\n=== Demo 3: List Roles ===")

    # Mock roles
    mock_roles = {
        "webserver": {"url": f"{CHEF_SERVER_URL}/roles/webserver"},
        "database": {"url": f"{CHEF_SERVER_URL}/roles/database"},
        "monitoring": {"url": f"{CHEF_SERVER_URL}/roles/monitoring"},
    }

    responses.add(
        responses.GET,
        f"{CHEF_SERVER_URL}/organizations/{CHEF_ORG}/roles",
        json=mock_roles,
        status=200,
    )

    # List roles
    config = ChefServerConfig(
        server_url=CHEF_SERVER_URL,
        organisation=CHEF_ORG,
        client_name="demo-client",
        client_key=generate_test_key(),
        timeout=10,
    )
    client = ChefServerClient(config)
    roles = client.list_roles()

    # Display results
    print(f"✅ Found {len(roles)} roles:")
    for role in roles:
        print(f"   - {role['name']}: {role['url']}")


@responses.activate
def demo_auth_failure():
    """Demo: Handle authentication failure."""
    print("\n=== Demo 4: Authentication Failure ===")

    # Mock 401 authentication failure
    responses.add(
        responses.GET,
        CHEF_SEARCH_URL,
        json={"error": "Invalid signature"},
        status=401,
    )

    # Test connection (should fail)
    config = ChefServerConfig(
        server_url=CHEF_SERVER_URL,
        organisation=CHEF_ORG,
        client_name="demo-client",
        client_key=generate_test_key(),
        timeout=10,
    )
    client = ChefServerClient(config)
    success, message = client.test_connection()

    # Display results
    print(f"❌ Connection: {success}")
    print(f"   Message: {message}")
    status_code = getattr(responses.calls[0].response, "status_code", None)
    if status_code is not None:
        print(f"   Status code: {status_code}")


@responses.activate
def demo_list_cookbooks():
    """Demo: List cookbooks with versions."""
    print("\n=== Demo 5: List Cookbooks ===")

    # Mock cookbooks
    mock_cookbooks = {
        "apache2": {
            "url": f"{CHEF_SERVER_URL}/cookbooks/apache2",
            "versions": [
                {"url": f"{CHEF_SERVER_URL}/cookbooks/apache2/8.6.0"},
                {"url": f"{CHEF_SERVER_URL}/cookbooks/apache2/8.5.0"},
            ],
        },
        "mysql": {
            "url": f"{CHEF_SERVER_URL}/cookbooks/mysql",
            "versions": [{"url": f"{CHEF_SERVER_URL}/cookbooks/mysql/10.5.0"}],
        },
        "nginx": {
            "url": f"{CHEF_SERVER_URL}/cookbooks/nginx",
            "versions": [{"url": f"{CHEF_SERVER_URL}/cookbooks/nginx/12.4.0"}],
        },
    }

    responses.add(
        responses.GET,
        CHEF_COOKBOOKS_URL,
        json=mock_cookbooks,
        status=200,
    )

    # List cookbooks
    config = ChefServerConfig(
        server_url=CHEF_SERVER_URL,
        organisation=CHEF_ORG,
        client_name="demo-client",
        client_key=generate_test_key(),
        timeout=10,
    )
    client = ChefServerClient(config)
    cookbooks = client.list_cookbooks()

    # Display results
    print(f"✅ Found {len(cookbooks)} cookbooks:")
    for cookbook in cookbooks:
        print(f"   - {cookbook['name']}")
        if "versions" in cookbook:
            print(f"     Versions: {len(cookbook['versions'])}")


def main():
    """Run all demos."""
    print("=" * 60)
    print("Chef Server Mock Testing Demo")
    print("=" * 60)
    print("\nThis demo shows how to test Chef Server integration")
    print("WITHOUT a real Chef Server using mocked HTTP responses.\n")

    demo_connection_test()
    demo_node_search()
    demo_list_roles()
    demo_auth_failure()
    demo_list_cookbooks()

    print("\n" + "=" * 60)
    print("✅ All demos completed successfully!")
    print("=" * 60)
    print("\nNext steps:")
    print(
        "  1. Run mock tests: poetry run pytest tests/integration/test_chef_server_mock.py -v"
    )
    print("  2. Read the guide: docs/testing/MOCK_CHEF_SERVER.md")
    print("  3. Write your own mock tests!")
    print()


if __name__ == "__main__":
    main()
