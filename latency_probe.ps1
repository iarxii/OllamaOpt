param(
    [string]$Model = "qwen3.5:8B",
    [string]$OutputFile = "curl-latency.log"
)

$url = "http://localhost:11434/api/generate"
$payload = @{
    model  = $Model
    prompt = "Return OK only."
    stream = $false
} | ConvertTo-Json

Write-Host "Running latency test for model: $Model"
Write-Host "Output: $OutputFile"

try {
    $duration = Measure-Command {
        $response = Invoke-WebRequest -UseBasicParsing -Uri $url `
            -Method Post `
            -Headers @{"Content-Type" = "application/json" } `
            -Body $payload `
            -TimeoutSec 30 `
            -ErrorAction Stop
    }
    
    $result = @{
        timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        model     = $Model
        duration  = $duration.TotalMilliseconds
        unit      = "ms"
    } | ConvertTo-Json
    
    Write-Host "Result: $result"
    Add-Content -Path $OutputFile -Value $result
    Write-Host "[OK] Latency test complete"
}
catch {
    Write-Host "[FAIL] Error during latency test: $_"
    Write-Error $_
    exit 1
}
