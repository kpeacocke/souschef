#!/bin/bash
# Script to regenerate Go test results after container rebuild
set -e

echo "🔄 Regenerating Go test results..."

cd /workspaces/souschef/terraform-provider

# Ensure test environment is set up
if [[ ! -f ".env.test" ]]; then
    echo "📋 Setting up test environment..."
    cp .env.test.example .env.test
fi

# Run tests with coverage to regenerate output files
echo "🧪 Running Go tests with coverage..."
export TF_ACC=1
go test -v -cover -coverprofile=coverage.out ./... > test-output.txt 2>&1

# Generate HTML coverage report
echo "📊 Generating coverage report..."
go tool cover -html=coverage.out -o coverage.html

# Extract test results summary
echo "📋 Extracting test results..."
grep -E "(PASS|FAIL|RUN)" test-output.txt > test-results.txt || true
grep -A 10 -B 2 "Test" test-output.txt > test-results-full.txt || true

# Create acceptance test summary (placeholder)
echo "✅ Tests completed at $(date)" > test-acceptance.txt
echo "Coverage: $(go tool cover -func=coverage.out | grep total | awk '{print $3}')" >> test-acceptance.txt

# Create latest test summary
echo "📅 Latest test run: $(date)" > test-latest.txt
echo "Results: $(tail -5 test-output.txt)" >> test-latest.txt

echo "✅ Go test results regenerated!"
echo "Files created:"
echo "  - coverage.out (coverage profile)"
echo "  - coverage.html (HTML coverage report)"
echo "  - test-output.txt (full test output)"
echo "  - test-results.txt (test summary)"
echo "  - test-results-full.txt (detailed results)"
echo "  - test-acceptance.txt (acceptance summary)"
echo "  - test-latest.txt (latest run summary)"
