# CodeQL Analysis Structure

This directory contains all CodeQL-related files and artifacts for security and quality analysis of the souschef project.

## Directory Layout

```
.codeql/
├── config/              # CodeQL configuration (COMMITTED)
│   ├── .codeqlignore    # Patterns to exclude from analysis
│   ├── config.yml       # CodeQL configuration
│   └── qlpack.yml       # Query pack definitions
├── databases/           # CodeQL databases (IGNORED - rebuilt locally)
│   └── python-db/       # Python analysis database (largest file)
├── reports/             # SARIF analysis reports (COMMITTED)
│   ├── latest.sarif     # Most recent analysis results
│   ├── archive/         # Historical SARIF files
│   └── *.sarif          # Individual analysis snapshots
└── queries/             # Custom query definitions (COMMITTED)
    └── [future: custom queries]
```

## What Gets Committed vs Ignored

### ✅ Committed to Git
- **config/.codeqlignore** - Specifies which files to exclude from analysis
- **config/config.yml** - CodeQL analysis parameters
- **config/qlpack.yml** - Query pack configuration
- **reports/latest.sarif** - Current analysis results
- **reports/archive/** - Historical analysis results (for tracking trends)
- **queries/** - Custom security queries

### ❌ Ignored (Local Build Artifacts)
- **databases/** - CodeQL databases are large (~600MB) and rebuilt per machine
  - Rebuilt with: `codeql database create .codeql/databases/python-db --language=python --source-root=.`
  - Contents include extracted code representations, not source code
  - Machine-specific and should be regenerated locally

## Using CodeQL on Your Machine

### Initial Setup
```bash
# Install CodeQL CLI if not already installed
# https://github.com/github/codeql-cli-binaries/releases

# Create the CodeQL database (one-time per machine)
codeql database create .codeql/databases/python-db \
  --language=python \
  --source-root=. \
  --codescanning-config=.codeql/config/config.yml \
  --source-map-filters=.codeql/config/.codeqlignore
```

### Running Analysis
```bash
# Analyze and generate SARIF report
codeql database analyze .codeql/databases/python-db \
  --format=sarif-latest \
  --output=.codeql/reports/latest.sarif \
  codeql/python-queries:codeql-suites/python-security-and-quality.qls
```

### After Code Changes
If source code changes, rebuild the database:
```bash
rm -rf .codeql/databases/python-db
# Then run "Create CodeQL database" command above
# Then run analysis command above
```

## Platform Compatibility

This structure works on:
- ✅ macOS (Intel and Apple Silicon)
- ✅ Linux
- ✅ Windows (Git Bash, WSL, or PowerShell)

All paths use forward slashes and work across platforms.

## SARIF Reports

SARIF (Static Analysis Results Format) files capture analysis results:
- **latest.sarif** - Most recent analysis (tracked in git)
- **archive/** - Previous analyses for trend tracking
- Reports can be viewed in:
  - GitHub Security tab (when committed and pushed)
  - VS Code CodeQL extension
  - SARIF viewers

## Current Findings

See [/CODEQL_STATUS.md](/CODEQL_STATUS.md) for analysis summary:
- 17 findings in source code
- All documented and safe (intentional patterns)
- Inline suppressions in code explain each finding

## CI/CD Integration

In GitHub Actions workflows:
```yaml
- name: Initialize CodeQL database
  run: codeql database create .codeql/databases/python-db --language=python --source-root=.

- name: Run CodeQL analysis
  run: codeql database analyze .codeql/databases/python-db --format=sarif-latest --output=.codeql/reports/latest.sarif codeql/python-queries:codeql-suites/python-security-and-quality.qls
```

## Troubleshooting

### Database creation fails
- Delete the database directory and try again:  `rm -rf .codeql/databases/python-db`
- Check .codeqlignore syntax

### Analysis runs very slowly
- Database exists but is outdated; rebuild it
- Check for very large files in the source tree that should be ignored

### SARIF file is huge
- This is normal for comprehensive analysis
- Archive old reports to keep git history manageable:  `mv .codeql/reports/latest.sarif .codeql/reports/archive/$(date +%Y%m%d-%H%M%S).sarif`
