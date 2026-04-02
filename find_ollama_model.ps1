param (
    [string]$ModelName = "deepseek-r1:7b"
)

$modelParts = $ModelName -split ":"
$name = $modelParts[0]
$tag = if ($modelParts.Length -gt 1) { $modelParts[1] } else { "latest" }

$ollamaBase = Join-Path $env:USERPROFILE ".ollama\models\manifests\registry.ollama.ai\library"
$manifestPath = Join-Path (Join-Path $ollamaBase $name) $tag

if (-not (Test-Path $manifestPath)) {
    # Try generic library if not found
    $manifestPath = Join-Path (Join-Path $ollamaBase "library") (Join-Path $name $tag)
}

if (-not (Test-Path $manifestPath)) {
    Write-Error "Ollama manifest not found for $ModelName at $manifestPath"
    exit 1
}

$manifest = Get-Content $manifestPath | ConvertFrom-Json
# GGUF models usually have the largest layer as the model blob
$modelLayer = $manifest.layers | Sort-Object -Property size -Descending | Select-Object -First 1

if (-not $modelLayer) {
    Write-Error "No model layer found in manifest for $ModelName"
    exit 1
}

$digest = $modelLayer.digest -replace "sha256:", "sha256-"
$blobPath = Join-Path $env:USERPROFILE ".ollama\models\blobs\$digest"

if (Test-Path $blobPath) {
    Write-Output $blobPath
} else {
    Write-Error "Model blob not found at $blobPath"
    exit 1
}
