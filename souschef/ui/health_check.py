#!/usr/bin/env python3
"""Health check endpoint for SousChef UI Docker container."""

import json
import sys
from pathlib import Path

# Add the parent directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def main():
    """Run health check."""
    try:
        # Try to import a core module to verify the environment is working
        from souschef.core.constants import VERSION

        sys.stdout.write(
            json.dumps(
                {"status": "healthy", "service": "souschef-ui", "version": VERSION}
            )
        )
        sys.exit(0)
    except Exception as e:
        sys.stdout.write(
            json.dumps(
                {"status": "unhealthy", "service": "souschef-ui", "error": str(e)}
            )
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
