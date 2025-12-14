#!/bin/bash

echo "Validating cross-platform setup scripts using containers..."

# Validate Linux setup.sh
echo "Validating Linux setup.sh..."
docker run --rm -v "$(pwd)/linux:/scripts" koalaman/shellcheck:stable /scripts/setup.sh
if [ $? -eq 0 ]; then
    echo "Linux setup.sh: PASSED"
else
    echo "Linux setup.sh: FAILED"
fi

# Validate macOS setup.fish
echo "Validating macOS setup.fish..."
if [ -f macos/setup.fish ]; then
    echo "macOS setup.fish: PASSED"
else
    echo "macOS setup.fish: FAILED"
fi

# Validate Windows setup.ps1
echo "Validating Windows setup.ps1..."
# Use a container with PowerShell
docker run --rm -v "$(pwd)/windows:/scripts" mcr.microsoft.com/powershell:latest pwsh -Command "
Install-Module -Name PSScriptAnalyzer -RequiredVersion 1.21.0 -Force -SkipPublisherCheck
Import-Module PSScriptAnalyzer
\$results = Invoke-ScriptAnalyzer -Path /scripts/setup.ps1 -ExcludeRule PSAvoidUsingWriteHost
if (\$results) {
    Write-Host 'Windows setup.ps1: FAILED'
    \$results | ForEach-Object { Write-Host \$_.Message }
} else {
    Write-Host 'Windows setup.ps1: PASSED'
}
"

echo "Validation complete."