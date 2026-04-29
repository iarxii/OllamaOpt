<#
.SYNOPSIS
Installs a custom llama-cpp-turboquant build for RotorQuant KV cache compression.

.DESCRIPTION
This script clones a community fork of llama.cpp that supports RotorQuant (e.g., planar3/iso3 KV quantizations).
It compiles the engine with Vulkan support, which is ideal for Intel iGPUs, providing significant speedups for long-context generation.

.EXAMPLE
.\install_rotorquant.ps1
#>

param(
    [switch]$ForceRebuild = $false
)

$RepoUrl = "https://github.com/johndpope/llama-cpp-turboquant.git"
$Branch = "feature/planarquant-kv-cache"
$InstallDir = "llama-cpp-turboquant"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " RotorQuant (llama-cpp-turboquant) Installer for Intel iGPU " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""

if (Test-Path $InstallDir) {
    if ($ForceRebuild) {
        Write-Host "Force rebuild requested. Removing existing directory..." -ForegroundColor Yellow
        Remove-Item -Recurse -Force $InstallDir
        Write-Host "Cloning repository..." -ForegroundColor Green
        git clone $RepoUrl $InstallDir
    } else {
        Write-Host "Directory '$InstallDir' already exists. Skipping clone." -ForegroundColor Yellow
        Write-Host "To rebuild, use: .\install_rotorquant.ps1 -ForceRebuild"
    }
} else {
    Write-Host "Cloning repository..." -ForegroundColor Green
    git clone $RepoUrl $InstallDir
}
if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to clone repository. Ensure git is installed and accessible." -ForegroundColor Red
    exit 1
}

cd $InstallDir
git checkout $Branch

Write-Host "Configuring CMake with Vulkan support (optimal for Intel iGPU)..." -ForegroundColor Green
# Using Vulkan backend as it provides the most stable performance across iGPUs
cmake -B build -DGGML_VULKAN=ON
if ($LASTEXITCODE -ne 0) {
    Write-Host "CMake configuration failed. Ensure CMake and Vulkan SDK are installed." -ForegroundColor Red
    exit 1
}

Write-Host "Building project (this may take a few minutes)..." -ForegroundColor Green
cmake --build build --config Release
if ($LASTEXITCODE -ne 0) {
    Write-Host "Build failed." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Installation Complete!" -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "The custom engine is built at: .\$InstallDir\build\bin\Release\llama-server.exe (or similar depending on MSVC generator)."
Write-Host "To use this engine, start the server with your model:"
Write-Host "  .\$InstallDir\build\bin\Release\llama-server.exe -m path/to/model.gguf --port 11434 --ctx-size 8192 -ngl 99"
Write-Host "Note: You can pass custom RotorQuant KV cache flags (like --ctk planar3 --ctv planar3) if supported by the fork."
Write-Host "AICodex / OllamaOpt will seamlessly connect to port 11434."
