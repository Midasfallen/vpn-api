<#
Remote diagnostic script for a deployed host.
Usage: .\remote_diag.ps1 -BaseUrl http://62.84.98.109:8588
This script performs read-only checks (no modifications):
 - fetch root page
 - fetch /openapi.json and /docs
 - try WG-Easy API endpoints commonly exposed by the UI
 - show quick guidance about whether the UI is wg-easy or the vpn-api
#>
param(
    [string]$BaseUrl = "http://62.84.98.109:8588"
)

function TryGet($url) {
    try {
        Write-Host "GET $url"
        $r = Invoke-RestMethod -Uri $url -Method Get -TimeoutSec 10 -ErrorAction Stop
        if ($r -is [string]) {
            # HTML or text
            $head = $r.Substring(0, [Math]::Min(400, $r.Length))
            Write-Host "(text/html) head:"
            Write-Host $head
        } else {
            # JSON
            $json = $r | ConvertTo-Json -Depth 3
            Write-Host $json
        }
    } catch {
        Write-Host "Request failed: $_"
    }
}

Write-Host "Remote diagnostic starting for $BaseUrl`n"

# 1) root
TryGet "$BaseUrl/"

# 2) openapi (typical for FastAPI)
TryGet "$BaseUrl/openapi.json"

# 3) docs (Swagger UI)
TryGet "$BaseUrl/docs"
TryGet "$BaseUrl/redoc"

# 4) Try the common vpn-api endpoints (may require auth)
TryGet "$BaseUrl/vpn_peers"
TryGet "$BaseUrl/vpn_peers/self"

# 5) WG-Easy API endpoints (UI observed might be wg-easy)
TryGet "$BaseUrl/api/wireguard/clients"
TryGet "$BaseUrl/api/wireguard/backup"

Write-Host "`nDiagnostic finished. Interpretation tips:`n"
Write-Host "- If root served HTML that looks like 'WireGuard' or 'WireGuard Easy', this host is running wg-easy UI."
Write-Host "- If /openapi.json returned JSON describing 'paths' with /auth or /vpn_peers, this host is running vpn-api."
Write-Host "- Our vpn-api stores peers in its database; the wg-easy UI shows clients managed by wg-easy. If you expected the new peer to appear in the wg-easy UI, ensure vpn-api was configured to talk to that wg-easy instance (env WG_KEY_POLICY=wg-easy and WG_EASY_URL pointing to this host)."
Write-Host "- To further debug: check docker compose on the deploy host, environment variables (WG_EASY_URL/WG_EASY_PASSWORD), and database records (select from vpn_peers). If you want, I can prepare remote commands to run on the server (ssh) to inspect containers and DB (you'll need to run them or provide access)."
