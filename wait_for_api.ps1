param(
    [int]$MaxRetries = 30,
    [int]$TimeoutSec = 2
)

$port = 11434
$url = "http://127.0.0.1:$port/api/tags"

Write-Host "Waiting for Ollama API to respond at $url..."

for ($i = 0; $i -lt $MaxRetries; $i++) {
    try {
        $response = Invoke-WebRequest -UseBasicParsing $url -TimeoutSec $TimeoutSec -Proxy $null -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            Write-Host "[OK] Ollama is up."
            exit 0
        }
    }
    catch {
        # API not ready, keep trying
    }
    
    Start-Sleep -Seconds 1
}

Write-Host "[FAIL] Ollama did not respond in time."
exit 1
