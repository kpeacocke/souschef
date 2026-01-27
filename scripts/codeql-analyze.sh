#!/usr/bin/env bash
# CodeQL Database Build and Analysis Script
# Works on macOS, Linux, and Windows (Git Bash / WSL)
# Usage: ./scripts/codeql-analyze.sh [build|analyze|clean|rebuild]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Paths
PROJECT_ROOT="."
CODEQL_DIR=".codeql"
DB_DIR="${CODEQL_DIR}/databases/python-db"
CONFIG_DIR="${CODEQL_DIR}/config"
REPORTS_DIR="${CODEQL_DIR}/reports"
export CODEQLIGNORE="${CONFIG_DIR}/.codeqlignore"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[CodeQL]${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Function to check if codeql is installed
check_codeql() {
    if ! command -v codeql &> /dev/null; then
        print_error "CodeQL CLI is not installed or not in PATH"
        echo "Install from: https://github.com/github/codeql-cli-binaries/releases"
        exit 1
    fi
    local version
    version=$(codeql version)
    print_success "CodeQL CLI found: ${version}"
}

# Function to build CodeQL database
build_database() {
    print_status "Building CodeQL database for Python..."

    if [ -d "${DB_DIR}" ]; then
        print_warning "Database already exists at ${DB_DIR}"
        read -p "Delete and rebuild? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf "${DB_DIR}"
            print_status "Removed existing database"
        else
            print_warning "Skipping database rebuild"
            return 0
        fi
    fi

    mkdir -p "${DB_DIR}"

    codeql database create "${DB_DIR}" \
        --language=python \
        --source-root="${PROJECT_ROOT}" || {
        print_error "Failed to create CodeQL database"
        rm -rf "${DB_DIR}"
        exit 1
    }

    print_success "CodeQL database created successfully"
}

# Function to run analysis
analyze() {
    print_status "Running CodeQL analysis..."

    if [ ! -d "${DB_DIR}" ]; then
        print_error "Database not found. Run 'build' first."
        exit 1
    fi

    mkdir -p "${REPORTS_DIR}/archive"

    # Archive previous latest.sarif if it exists
    if [ -f "${REPORTS_DIR}/latest.sarif" ]; then
        timestamp=$(date +%Y%m%d-%H%M%S)
        mv "${REPORTS_DIR}/latest.sarif" "${REPORTS_DIR}/archive/${timestamp}.sarif"
        print_status "Archived previous report to archive/${timestamp}.sarif"
    fi

    codeql database analyze "${DB_DIR}" \
        --format=sarif-latest \
        --output="${REPORTS_DIR}/latest.sarif" \
        codeql/python-queries:codeql-suites/python-security-and-quality.qls || {
        print_error "CodeQL analysis failed"
        exit 1
    }

    print_success "Analysis complete"

    # Count findings
    if command -v jq &> /dev/null; then
        local find_count
        find_count=$(jq '.runs[].results | length' "${REPORTS_DIR}/latest.sarif" | paste -sd+ - | bc)
        echo "Total findings: ${find_count}"
    fi
}

# Function to clean databases
clean_databases() {
    print_status "Cleaning CodeQL databases..."

    if [ -d "${DB_DIR}" ]; then
        rm -rf "${DB_DIR}"
        print_success "Removed database at ${DB_DIR}"
    fi

    mkdir -p "${DB_DIR}"
    touch "${DB_DIR}/.gitkeep"
    print_success "Database directory reset"
}

# Function to show help
show_help() {
    cat << EOF
CodeQL Analysis Tool

Usage: $0 [COMMAND]

Commands:
  build       Build the CodeQL database (from scratch)
  analyze     Run CodeQL analysis on existing database
  rebuild     Clean and rebuild everything (build + analyze)
  clean       Remove CodeQL databases (keeps configuration and reports)
  help        Show this help message

Examples:
  # First time setup
  $0 build
  $0 analyze

  # After code changes
  $0 analyze

  # Start fresh
  $0 rebuild

Environment:
  CODEQL_THREADS   Number of parallel threads (default: auto)

The directory structure:
  .codeql/
    ├── config/        Configuration files (committed)
    ├── databases/     CodeQL databases (local only, ignored)
    ├── reports/       SARIF analysis results (committed)
    └── queries/       Custom queries (committed)

EOF
}

# Main script
main() {
    local command="${1:-analyze}"

    case "${command}" in
        build)
            check_codeql
            build_database
            ;;
        analyze)
            check_codeql
            analyze
            ;;
        rebuild)
            check_codeql
            clean_databases
            build_database
            analyze
            ;;
        clean)
            clean_databases
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            print_error "Unknown command: ${command}"
            show_help
            exit 1
            ;;
    esac
}

main "$@"
