# CodeQL Setup and Usage Guide

This document explains how to run CodeQL security analysis on the souschef project across different platforms.

## Quick Start

### macOS / Linux

```bash
# First time setup - build the database
./scripts/codeql-analyze.sh build

# Run analysis
./scripts/codeql-analyze.sh analyze

# Or build and analyze in one step
./scripts/codeql-analyze.sh rebuild
```

### Windows

```batch
REM First time setup - build the database
scripts\codeql-analyze.bat build

REM Run analysis
scripts\codeql-analyze.bat analyze

REM Or build and analyze in one step
scripts\codeql-analyze.bat rebuild
```

## Prerequisites

1. **CodeQL CLI** must be installed
   - Download from: <https://github.com/github/codeql-cli-binaries/releases>
   - Add to your PATH so `codeql` command is available
   - Verify installation: `codeql version`

2. **Git** (for retrieving CodeQL query packs)

3. **Python 3.x** (already required for souschef development)

## Directory Structure

```text
.codeql/
├── config/                    # Committed to git
│   ├── .codeqlignore         # Files to exclude from analysis
│   ├── config.yml            # CodeQL configuration
│   └── codeql.yml            # Query pack settings
├── databases/                 # Ignored (local build artifacts)
│   └── python-db/            # CodeQL database for Python
│       ├── db-python/        # Extracted code representation
│       └── [other files]     # Database metadata
├── reports/                   # Committed to git
│   ├── latest.sarif          # Most recent analysis
│   └── archive/              # Historical results
└── queries/                   # Committed to git (for custom queries)
    └── .gitkeep
```

### What Gets Committed

- **Configuration** (`config/`) - except `databases/`
- **Reports** (`reports/`) - SARIF files showing analysis results
- **Custom Queries** (`queries/`) - if any are added
- **.codeql/README.md** - This directory's documentation

### What's Ignored

- **Databases** (`databases/`) - Large files (~600MB), rebuilt per machine
- **Build artifacts** - Temporary extraction files and metadata

## Detailed Usage

### Building the Database (First Time or Rebuild)

The database is a pre-processed representation of your code for analysis. It's machine-specific and should be rebuilt locally.

**macOS/Linux:**

```bash
./scripts/codeql-analyze.sh build
```

**Windows:**

```batch
scripts\codeql-analyze.bat build
```

This will:

1. Check that CodeQL CLI is installed
2. Create `~build.codeql/databases/python-db/` directory
3. Extract and process all Python files
4. Create searchable code indexes
5. Store compiled representations for fast analysis

**Expected time:** 2-5 minutes depending on machine speed

### Running Analysis

Once the database exists, run analysis to find security and quality issues:

**macOS/Linux:**

```bash
./scripts/codeql-analyze.sh analyze
```

**Windows:**

```batch
scripts\codeql-analyze.bat analyze
```

This will:

1. Execute 174 queries from the Python security-and-quality suite
2. Save results to `.codeql/reports/latest.sarif`
3. Archive previous results to `archive/` with timestamp
4. Display count of findings

**Expected time:** 1-3 minutes

### Rebuilding Everything

If code changes significantly, rebuild the database:

**macOS/Linux:**

```bash
./scripts/codeql-analyze.sh rebuild
```

**Windows:**

```batch
scripts\codeql-analyze.bat rebuild
```

Equivalent to `build` + `analyze` in sequence.

### Cleaning Up

Remove databases (keeps config and reports):

**macOS/Linux:**

```bash
./scripts/codeql-analyze.sh clean
```

**Windows:**

```batch
scripts\codeql-analyze.bat clean
```

## Understanding Results

### SARIF Reports

Results are in SARIF format (Static Analysis Results Format):

- **latest.sarif** - Most recent analysis results (~1MB)
- **archive/** - Previous runs for tracking trends

View results with:

- **GitHub**: Push to repository → Security tab → Code scanning
- **VS Code**: Install "CodeQL" extension by GitHub
- **Online viewers**: <https://microsoft.github.io/sarif-web-component/>

### Findings

The current analysis identifies 17 findings in source code:

- **16 × py/unused-import** - Intentional re-exports for test backward compatibility
- **1 × py/path-injection** - False positive; code properly sanitizes inputs

See [CODEQL_STATUS.md](CODEQL_STATUS.md) for details on each finding.

## Troubleshooting

### "CodeQL CLI is not installed or not in PATH"

```bash
# Verify CodeQL is installed
which codeql          # macOS/Linux
where codeql          # Windows
codeql version        # Should show version info

# If not found, install from:
# https://github.com/github/codeql-cli-binaries/releases
```

### Database creation is very slow

- This is normal for first build (2-5 minutes)
- Check .codeqlignore for files that should be excluded
- Ensure you're not running other memory-intensive tasks

### Out of disk space

The database can be ~600MB. If space is limited:

```bash
# Remove the database (will be rebuilt on next run)
./scripts/codeql-analyze.sh clean
```

### Analysis produces no results

Ensure the database exists:

```bash
ls .codeql/databases/python-db  # macOS/Linux
dir .codeql\databases\python-db # Windows

# If missing, rebuild:
./scripts/codeql-analyze.sh build  # or .bat on Windows
```

### Different results on different machines

Results may vary slightly due to:

- Different CodeQL CLI versions
- Different Python/environment setup
- Different OS handling of symlinks

Rebuild the database on each machine to ensure consistency.

## Configuration

### Adjusting Analysis Scope

Edit `.codeql/config/.codeqlignore` to exclude more files:

```text
# Example: ignore vendor code
vendor/
third_party/

# Already excluded:
tests/
mutants/
site/
htmlcov/
```

### Using Custom Queries

Place custom `.ql` files in `.codeql/queries/` and reference in analysis command.

### Parallel Processing

CodeQL uses multiple threads by default. Force threads:

```bash
# macOS/Linux
export CODEQL_THREADS=4
./scripts/codeql-analyze.sh analyze

# Windows (PowerShell)
$env:CODEQL_THREADS=4
scripts\codeql-analyze.bat analyze
```

## CI/CD Integration

### GitHub Actions

Add to `.github/workflows/codeql.yml`:

```yaml
name: CodeQL Analysis

on:
  push:
    branches: ['main']
  pull_request:
    branches: ['main']

jobs:
  analyze:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Initialize CodeQL
        uses: github/codeql-action/init@v2
        with:
          languages: python

      - name: Autobuild
        uses: github/codeql-action/autobuild@v2

      - name: Perform CodeQL Analysis
        uses: github/codeql-action/analyze@v2
```

## Additional Resources

- [CodeQL Documentation](https://codeql.github.com/docs/)
- [SARIF Format](https://sarifweb.azurewebsites.net/)
- [Python Security Queries](https://github.com/github/codeql/tree/main/python)
- [Repository CodeQL Configuration](.codeql/README.md)

## Support

For issues with CodeQL:

1. Check [CodeQL documentation](https://codeql.github.com/docs/)
2. Review [.codeql/README.md](.codeql/README.md) for detailed setup info
3. Check [CODEQL_STATUS.md](CODEQL_STATUS.md) for known findings
