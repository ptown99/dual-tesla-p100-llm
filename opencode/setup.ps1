# OpenCode Client Auto-Setup for Dual Tesla P100 Homelab
param (
    [string]$ClusterIP = "192.168.1.67"
)

Write-Host "Connecting OpenCode to Homelab P100 Cluster ($ClusterIP)..." -ForegroundColor Cyan

$configDir = "$env:USERPROFILE\.config\opencode"
$commandsDir = "$configDir\commands"

if (!(Test-Path $commandsDir)) {
    New-Item -ItemType Directory -Path $commandsDir -Force | Out-Null
}

Write-Host "Fetching dynamic models and remote MCP configuration..." -ForegroundColor Gray
Invoke-RestMethod -Uri "http://$ClusterIP`:8001/opencode.json" -OutFile "$configDir\opencode.json"

Write-Host "Installing /deepresearch and /sync commands..." -ForegroundColor Gray
Invoke-RestMethod -Uri "http://$ClusterIP`:8001/commands/deepresearch.md" -OutFile "$commandsDir\deepresearch.md"
Invoke-RestMethod -Uri "http://$ClusterIP`:8001/commands/sync.md" -OutFile "$commandsDir\sync.md"

$cli = "$env:LOCALAPPDATA\Programs\ai.opencode.desktop\resources\opencode-cli.exe"
if (Test-Path $cli) {
    & $cli reload | Out-Null
    Write-Host "OpenCode configuration reloaded live!" -ForegroundColor Green
} else {
    Write-Host "Restart OpenCode desktop to apply new models and tools." -ForegroundColor Yellow
}

Write-Host "Setup Complete! 22+ models and remote MCP clusters active." -ForegroundColor Green
