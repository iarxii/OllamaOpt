Get-Command cmake, cl, vulkaninfo -ErrorAction SilentlyContinue

---

Here is what you need to do:
1. **Download CMake**: Go to [https://cmake.org/download/](https://cmake.org/download/) and download the Windows x64 Installer (e.g., `cmake-3.31.5-windows-x86_64.msi`).
2. **Install CMake**: Run the installer. **CRITICAL:** During installation, make sure you select the option to **"Add CMake to the system PATH for all users"** (or for the current user).
3. **Restart your Terminal**: Once installed, close your current PowerShell window and open a new one so that your system recognizes the `cmake` command.
4. **Run the script again**:
```powershell
cd c:\your\developer_folder\projects\ghusr\OllamaOpt
.\install_rotorquant.ps1
```