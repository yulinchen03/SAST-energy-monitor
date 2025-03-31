# SAST (Static application security testing) Energy Monitor

[![PyPI version](https://badge.fury.io/py/sast-energy-monitor.svg)](https://pypi.org/project/sast-energy-monitor/)

A command-line tool to measure the energy consumption of static analysis scans (Bandit, Semgrep) on your codebase using Energibridge, with clear, colored output.

## What it Does

This tool wraps `bandit` or `semgrep` scans within an `energibridge` measurement process. It runs the specified scan using predefined configurations bundled with the tool and displays:

*   The findings reported by Bandit or Semgrep.
*   The total energy consumed during the scan execution, as reported by Energibridge.
*   Colored output for better readability (errors in red, findings in yellow, success/summary in green/magenta).

## Prerequisites

- **Python:** Version 3.8 or higher.

- **Energibridge:**
    *   You must have the `energibridge.exe` (or your OS equivalent) executable installed and know its path. Energibridge needs to be obtained separately from its source.
    *   **Windows Setup (RAPL Service):** Energibridge often relies on the RAPL (Running Average Power Limit) service to access energy data on Windows. If you haven't configured this before, you may need to install and start the service using **Administrator privileges**:
        ```powershell
        # Open PowerShell or Command Prompt as Administrator

        # Create the service (Replace path if LibreHardwareMonitor.sys is elsewhere)
        sc create rapl type=kernel binPath="C:\path\to\your\LibreHardwareMonitor.sys"

        # Start the service
        sc start rapl
        ```
        * Download LibreHardwareMonitor.sys from here: https://github.com/LibreHardwareMonitor/LibreHardwareMonitor/releases
        *   **Note:** You only need to do this *once*. Verify the path to `LibreHardwareMonitor.sys` (which often comes with tools like LibreHardwareMonitor or potentially Energibridge's dependencies).
        *   You can test if Energibridge is working correctly by running a simple command like `energibridge.exe --summary timeout 5` in your terminal (as Admin if needed).

- **Bandit / Semgrep:**
    *   The specific scanner (`bandit` or `semgrep`) you intend to use must be installed in your Python environment and accessible from your system's PATH.
    *   Install them if needed:
  
        ```bash
        pip install bandit semgrep
        ```

## Installation

**From PyPI:**

```bash
pip install sast_energy_monitor
```

## Usage
Run the tool from your command line:
```bash
sast_energy_monitor --energibridge-path /path/to/energibridge.exe \
            --repo-path /path/to/your/code/repository \
            --tool [bandit|semgrep] \
            --config-level [strict|loose]
```

Arguments:

- energibridge-path: (Required) Absolute or relative path to your energibridge executable.

- repo-path: (Required) Path to the root directory of the code repository you want to scan.

- tool: (Required) Choose bandit or semgrep.

- config-level: (Required) Choose strict or loose. This selects a predefined configuration file bundled with the tool.

Example:
```bash
# On Windows
sast_energy_monitor --energibridge-path C:\Tools\energibridge.exe
            --repo-path C:\MyProjects\MyApp
            --tool bandit
            --config-level strict

# On Linux/macOS
sast_energy_monitor --energibridge-path /usr/local/bin/energibridge \
            --repo-path ~/projects/my_app \
            --tool semgrep \
            --config-level loose
```
The tool will execute the scan, display the scanner's findings, and print the final energy consumption summary from Energibridge. Non-zero exit codes from scanners (indicating findings) are handled gracefully.

## Bundled Configurations
This tool uses internal configuration files:

- Bandit:

    - loose: Uses the bundled configs/.bandit_basic file.

    - strict: Uses the bundled configs/.bandit file.

- Semgrep:

    - loose: Uses the bundled configs/.semgrep.yml file.

    - strict: Uses the Semgrep Registry ruleset p/bandit.

Currently it is not possible to override these configurations via command-line arguments.

## Important Notes
- Administrator Privileges: You need to run the sast-energy-monitor command itself with Administrator/root privileges for Energibridge to function correctly.

- The accuracy of energy measurements depends heavily on Energibridge's capabilities and the underlying hardware support (like Intel RAPL).

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributors
Sustainable Software Engineering Group 10, TU Delft:
- Yulin Chen
- Ayush Kuruvilla
- Sahar Marossi
- Andrea Onofrei