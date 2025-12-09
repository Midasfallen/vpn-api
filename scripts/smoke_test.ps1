# Smoke test for VPN API
# Usage: .\smoke_test.ps1 -BaseUrl http://localhost:8000
param(
    [string]$BaseUrl = "http://localhost:8000",
    [string]$Email = "smoketest+user@example.com",
    [string]$Password = "S3curePassw0rd!"
)

Write-Host "Running smoke test against $BaseUrl"

$headers = @{"Content-Type" = "application/json"}

# 1) Register
$regPayload = @{ email = $Email; password = $Password } | ConvertTo-Json
Write-Host "Registering user $Email"
try {
    $reg = Invoke-RestMethod -Uri "$BaseUrl/auth/register" -Method Post -Headers $headers -Body $regPayload
    Write-Host "Register response:"; $reg | ConvertTo-Json -Depth 3
} catch {
    Write-Host "Register failed:" $_.Exception.Response.StatusCode.Value__
    Write-Host $_.Exception.Response.Content.ReadAsStringAsync().Result
    exit 1
}

# 2) Login
$loginPayload = @{ email = $Email; password = $Password } | ConvertTo-Json
Write-Host "Logging in"
$tokenResp = Invoke-RestMethod -Uri "$BaseUrl/auth/login" -Method Post -Headers $headers -Body $loginPayload
$token = $tokenResp.access_token
if (-not $token) { Write-Host "Login did not return token"; exit 1 }
Write-Host "Received token (truncated): $($token.Substring(0,20))..."
$authHeaders = @{ Authorization = "Bearer $token"; "Content-Type" = "application/json" }

# 3) Create peer (self)
$peerPayload = @{ device_name = "smoke-pwsh" } | ConvertTo-Json
Write-Host "Creating peer for self"
$peer = Invoke-RestMethod -Uri "$BaseUrl/vpn_peers/self" -Method Post -Headers $authHeaders -Body $peerPayload
Write-Host "Peer created:"; $peer | ConvertTo-Json -Depth 3

# 4) Get config
Write-Host "Fetching wg-quick config"
$config = Invoke-RestMethod -Uri "$BaseUrl/vpn_peers/self/config" -Method Get -Headers $authHeaders
Write-Host "Config received:"; $config.wg_quick.Substring(0, (if ($config.wg_quick.Length -gt 200) {200} else {$config.wg_quick.Length}))

Write-Host "Smoke test completed successfully"
