# TODO

- [ ] **Perform a clean installation of the latest Intel graphics drivers.**
  -   Download and run the Intel Driver & Support Assistant (DSA) from [https://www.intel.com/content/www/us/en/support/detect.html](https://www.intel.com/content/www/us/en/support/detect.html).
  -   It is highly recommended to first uninstall the existing Intel graphics driver from **Windows Apps & Features**.
  -   Reboot your system after the driver installation is complete.
- [ ] **Run the `run_debug.bat` script.**
  -   This will start the Ollama server and run the diagnostics script.
  -   If the server starts successfully, the diagnostics script will show that GPU offload is active.
- [ ] **If the server still fails to start, review the `logs/ollama_server.log` file.**
  -   This file will contain detailed error messages that can help diagnose the problem.
