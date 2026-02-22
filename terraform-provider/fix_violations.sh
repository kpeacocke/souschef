#!/bin/bash

cd /workspaces/souschef/terraform-provider

# Fix all missing_coverage_test.go usages - replace strings with constants
sed -i 's/"plan\.sh"/planShFilename/g' internal/provider/missing_coverage_test.go
sed -i 's/"#!\/bin\/bash\\n"/bashShebang/g' internal/provider/missing_coverage_test.go
sed -i 's/"Expected error for invalid format: %s"/invalidFormatErrorMsg/g' internal/provider/missing_coverage_test.go
sed -i 's|"\/tmp\/plan\.sh"|planShFullPath|g' internal/provider/missing_coverage_test.go
sed -i 's/"Expected error when reading file with no permissions"/errorReadingFileWithPerms/g' internal/provider/missing_coverage_test.go
sed -i 's/"Expected error when plan file doesn'"'"'t exist"/errorPlanFileNotFound/g' internal/provider/missing_coverage_test.go
sed -i 's/"Expected error when Dockerfile doesn'"'"'t exist"/errorDockerfileNotFound/g' internal/provider/missing_coverage_test.go
sed -i 's/"Expected error when profile path doesn'"'"'t exist"/errorProfilePathNotFound/g' internal/provider/missing_coverage_test.go
sed -i 's/"Expected error when test file can'"'"'t be read"/errorTestFileCantBeRead/g' internal/provider/missing_coverage_test.go
sed -i 's/"Expected error when cookbook path doesn'"'"'t exist"/errorCookbookPathNotFound/g' internal/provider/missing_coverage_test.go
sed -i 's/"Expected error when playbook file doesn'"'"'t exist"/errorPlaybookFileNotFound/g' internal/provider/missing_coverage_test.go

echo "All violations fixed!"
