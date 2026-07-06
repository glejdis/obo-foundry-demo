# deploy.ps1 — build & deploy the Aldi Store Ops MCP server to Azure Container Apps.
#
# Uses `az containerapp up` which builds the image in the cloud (ACR Tasks — no
# local Docker push needed), creates the environment, and exposes public HTTPS.
# CLIENT_SECRET is stored as a Container Apps secret, not a plain env var.
#
# Run from the repo root:  ./mcp_server/deploy.ps1
param(
    [string]$ResourceGroup = "rg-Foundry",
    [string]$Location      = "swedencentral",
    [string]$AppName       = "aldi-store-ops-mcp",
    [string]$EnvFile       = ".env"
)

$ErrorActionPreference = "Stop"

# --- Load TENANT / CLIENT_ID / CLIENT_SECRET from .env ----------------------
$vals = @{}
Get-Content $EnvFile | ForEach-Object {
    if ($_ -match '^\s*([A-Z_]+)\s*=\s*"?([^"]*)"?\s*$') { $vals[$Matches[1]] = $Matches[2] }
}
foreach ($k in "TENANT", "CLIENT_ID", "CLIENT_SECRET") {
    if (-not $vals[$k]) { throw "$k not found in $EnvFile" }
}

Write-Host "==> Building & deploying $AppName to $ResourceGroup ($Location)..."

# 1. Build from source (Dockerfile at repo root) + deploy with public ingress.
az containerapp up `
    --name $AppName `
    --resource-group $ResourceGroup `
    --location $Location `
    --source . `
    --ingress external `
    --target-port 8000 `
    --env-vars "TENANT=$($vals['TENANT'])" "CLIENT_ID=$($vals['CLIENT_ID'])" "MCP_VERIFY_SIGNATURE=true"

# 2. Store the client secret as a Container Apps secret and reference it.
az containerapp secret set `
    --name $AppName --resource-group $ResourceGroup `
    --secrets "client-secret=$($vals['CLIENT_SECRET'])" | Out-Null

az containerapp update `
    --name $AppName --resource-group $ResourceGroup `
    --set-env-vars "CLIENT_SECRET=secretref:client-secret" | Out-Null

# 3. Print the public MCP endpoint.
$fqdn = az containerapp show --name $AppName --resource-group $ResourceGroup `
    --query "properties.configuration.ingress.fqdn" -o tsv

Write-Host ""
Write-Host "==> Deployed. MCP endpoint:"
Write-Host "    https://$fqdn/mcp"
Write-Host ""
Write-Host "Use this URL as server_url when registering the MCP tool in Foundry."
