# OllamaOpt - GPU Offload Troubleshooting

## Problem

GPU offload is not working for the local LLM. The model is running entirely on the CPU.

## Diagnostics

The `gpu_diagnostics.ps1` script was run to analyze the state of the GPU, drivers, and Ollama configuration. The results showed that critical Intel compute libraries are missing:

- **SYCL support (igcsycl.dll):** NOT FOUND
- **Level Zero support (ze_intel_gpu.dll):** NOT FOUND

This indicates that the installed Intel graphics driver is either not the correct version or the installation is incomplete. These libraries are essential for GPU compute and offload.

## Solution

The recommended solution is to perform a clean installation of the latest Intel graphics drivers.

### Steps

1.  **Download the Intel Driver & Support Assistant (DSA)**
    -   [https://www.intel.com/content/www/us/en/support/detect.html](https://www.intel.com/content/www/us/en/support/detect.html)
2.  **Perform a Clean Installation**
    -   It is highly recommended to first uninstall the existing Intel graphics driver from **Windows Apps & Features**.
    -   Run the Intel DSA to download and install the latest drivers.
3.  **Reboot**
    -   After the driver installation is complete, reboot your system.
4.  **Restart the Ollama Server**
    -   Run the `start_clean.bat` script to clear any old configurations.
    -   Run the `start_dev.bat` script to start the Ollama server with the new drivers.
5.  **Verify the Fix**
    -   Run the `gpu_diagnostics.ps1` script again to confirm that the critical libraries are found and that GPU offload is active.

## Additional Notes

-   The `gpu_diagnostics.ps1` script was updated to include checks for these critical libraries.
-   The model used for testing was changed to `qwen:0.5b` for faster analysis. If this model is not present, you can pull it by running `ollama pull qwen:0.5b`.
