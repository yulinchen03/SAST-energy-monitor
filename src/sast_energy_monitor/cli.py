import argparse
import subprocess
import sys
import os
from pathlib import Path
import importlib.resources
import tempfile
import shlex  # <-- Added for safe command splitting
from colorama import init as colorama_init, Fore, Style

# --- Package/Config Info ---
# Ensure these match your actual package structure and config file names
PACKAGE_NAME = "sast_energy_monitor"
CONFIG_DIR_NAME = "configs"
BANDIT_CONFIG_FILES = {
    "loose": ".bandit_basic",
    "strict": ".bandit",
}
SEMGREP_CONFIG_FILES = {
    "loose": "semgrep.yml",
    "strict": "p/bandit",  # Using Semgrep registry path for strict
}
# ---

# Initialize colorama
colorama_init(autoreset=True)


def get_package_config_path(config_filename: str) -> importlib.resources.abc.Traversable:
    """Gets a traversable object for a config file bundled within the package."""
    try:
        package_files = importlib.resources.files(PACKAGE_NAME)
        config_path = package_files / CONFIG_DIR_NAME / config_filename
        if not config_path.is_file():
            raise FileNotFoundError(f"Bundled config file '{config_filename}' not found.")
        return config_path
    except (ModuleNotFoundError, FileNotFoundError, NotADirectoryError) as e:
        raise FileNotFoundError(
            f"Could not find bundled config file '{config_filename}' within "
            f"'{PACKAGE_NAME}/{CONFIG_DIR_NAME}'. "
            f"Package installed correctly? Error: {e}"
        ) from e


def build_scan_command(tool: str, config_level: str, repo_path: Path) -> str:
    """
    Builds the static analysis command string using bundled or registry configurations.

    Args:
        tool: 'bandit' or 'semgrep'.
        config_level: 'strict' or 'loose'.
        repo_path: Path to the repository to scan.

    Returns:
        The command string for the scanner.

    Raises:
        FileNotFoundError: If a required bundled config file is not found.
        ValueError: If the tool or config_level is invalid.
    """
    scan_command = ""
    repo_path_str = str(repo_path.resolve())  # Ensure absolute path as string

    if tool == "bandit":
        if config_level not in BANDIT_CONFIG_FILES:
            raise ValueError(f"Invalid config level '{config_level}' for bandit.")

        config_filename = BANDIT_CONFIG_FILES[config_level]
        print(Fore.CYAN + f"Info: Using bandit {config_level} config ('{config_filename}')")

        bundled_config_ref = get_package_config_path(config_filename)
        # Use 'with' to ensure temporary file (if created by as_file) is handled
        with importlib.resources.as_file(bundled_config_ref) as config_file_path:
            config_path_str = str(config_file_path.resolve())
            print(Fore.CYAN + f"Using config file resolved to: {config_path_str}")
            # Ensure paths are quoted within the command string itself for clarity,
            # though shlex.split should handle them correctly later.
            scan_command = f'bandit -c "{config_path_str}" -r "{repo_path_str}"'

    elif tool == "semgrep":
        if config_level not in SEMGREP_CONFIG_FILES:
            raise ValueError(f"Invalid config level '{config_level}' for semgrep.")

        config_identifier = SEMGREP_CONFIG_FILES[config_level]

        if config_level == "loose":  # Loose uses a bundled file
            print(Fore.CYAN + f"Info: Using semgrep loose config ('{config_identifier}')")
            bundled_config_ref = get_package_config_path(config_identifier)
            with importlib.resources.as_file(bundled_config_ref) as config_file_path:
                config_path_str = str(config_file_path.resolve())
                print(Fore.CYAN + f"Using config file resolved to: {config_path_str}")
                scan_command = f'semgrep scan "{repo_path_str}" --verbose --config={config_path_str}'

        elif config_level == "strict":  # Strict uses a registry path
            print(Fore.CYAN + f"Info: Using semgrep strict config ('{config_identifier}' from registry)")
            # Need to quote the registry path if it contains special chars, though 'p/bandit' is safe.
            # Using f-string quoting ensures it's treated as one argument by shlex.split.
            scan_command = f'semgrep scan "{repo_path_str}" --verbose --config={config_identifier}'
        else:
            raise ValueError(f"Unhandled semgrep config level: {config_level}")

    else:
        raise ValueError(f"Unsupported tool: {tool}. Use 'bandit' or 'semgrep'.")

    return scan_command


# Corrected function using list-based command execution
def run_measurement(energibridge_path: Path, scan_cmd: str, tool_name: str, config_level: str):
    """
    Runs the scan command wrapped by energibridge, using list-based execution
    to avoid shell interpretation issues. Handles expected exit codes, redirects
    periodic data, and prints results/summary with colors.
    """
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=True) as temp_output_file:
        temp_file_path = Path(temp_output_file.name).resolve() # Ensure temp path is absolute Path object
        print(Fore.CYAN + f"Redirecting Energibridge periodic data to temporary file: {temp_file_path}")

        # --- Prepare Command List ---
        energibridge_abs_path = str(energibridge_path.resolve())
        temp_file_abs_str = str(temp_file_path)

        # Base command parts for Energibridge
        base_command_list = [
            energibridge_abs_path,
            "-o", temp_file_abs_str,
            "--summary"
            # The actual scan command will be appended here
        ]

        # Safely split the scan_cmd generated by build_scan_command.
        try:
            # Use posix=False on Windows for better handling of backslashes in paths
            # shlex should correctly handle the quotes we put in build_scan_command
            scan_cmd_parts = shlex.split(scan_cmd, posix=(os.name != 'nt'))
            scan_cmd_parts = [arg.strip('"') for arg in scan_cmd_parts]

            # print(Fore.CYAN + f"DEBUG: Split scan command parts: {scan_cmd_parts}")
        except Exception as e:
             print(Fore.RED + Style.BRIGHT + f"Internal Error: Could not split scan command '{scan_cmd}'. Error: {e}", file=sys.stderr)
             sys.exit(1)

        # Combine Energibridge command with the split scan command parts
        command_list = base_command_list + scan_cmd_parts

        print(Style.DIM + "-" * 60)
        print(f"Starting {tool_name} scan ({config_level} config)...")
        # Print the list clearly for debugging
        # print(Fore.BLUE + f"Executing list: {command_list}")
        print(Style.DIM + "-" * 60)

        try:
            # Run the command as a list, shell=False is the default and safer
            result = subprocess.run(
                command_list,
                check=True, # Still check for errors initially
                capture_output=True,
                text=True,
                encoding='utf-8',
                # Add current working directory if necessary, but shouldn't be needed here
                # cwd=...
            )

            # --- Process successful run (exit code 0) ---
            print(Fore.GREEN + Style.BRIGHT + f"\n--- {tool_name.capitalize()} Scan Successful & Energy Summary (Exit Code 0) ---")
            if result.stdout:
                lines = result.stdout.strip().splitlines()
                for line in lines:
                    if "Energy consumption in joules:" in line:
                        print(Fore.MAGENTA + Style.BRIGHT + line) # Highlight energy summary
                    else:
                        print(line) # Print normal tool output
            if result.stderr:
                # stderr might contain warnings even on success
                print(Fore.YELLOW + "\n--- Standard Error Output (Warnings/Info) ---")
                print(result.stderr.strip())

        except subprocess.CalledProcessError as e:
            # --- Handle known non-zero exit codes ---
            expected_findings_exit_code = 1 # Common for bandit findings
            bandit_config_error_code = 2    # Common for Bandit config/arg errors

            # Check for Bandit's specific config error first
            if tool_name == 'bandit' and e.returncode == bandit_config_error_code:
                 print(Fore.RED + Style.BRIGHT + f"Error: {tool_name.capitalize()} failed with Exit Code {e.returncode}. This often indicates a configuration file issue or command argument error.", file=sys.stderr)
                 print(Fore.RED + Style.BRIGHT + "Please check the scanner's error message below.", file=sys.stderr)
                 # Print output and exit as it's an actual execution error
                 print(Fore.RED + "\n--- Tool/Energibridge Output (stderr) ---", file=sys.stderr)
                 print(e.stderr.strip() if e.stderr else "[No stderr]", file=sys.stderr)
                 print(Fore.RED + "\n--- Tool/Energibridge Output (stdout) ---", file=sys.stderr)
                 print(e.stdout.strip() if e.stdout else "[No stdout]", file=sys.stderr)
                 print("\n" + Style.DIM + "-" * 60, file=sys.stderr)
                 print(Fore.RED + f"Measurement failed due to tool error. Temp file was: {temp_file_path}", file=sys.stderr)
                 sys.exit(1) # Exit with error status

            # Check for expected "findings detected" exit code
            elif tool_name in ['bandit', 'semgrep'] and e.returncode == expected_findings_exit_code:
                print(Fore.YELLOW + Style.BRIGHT + f"\n--- {tool_name.capitalize()} Scan Found Issues (Exit Code {e.returncode}) ---")
                output_found = False
                if e.stdout:
                    output_found = True
                    print(Style.BRIGHT + "--- Standard Output & Energibridge Summary ---")
                    lines = e.stdout.strip().splitlines()
                    for line in lines:
                         if "Energy consumption in joules:" in line:
                              print(Fore.MAGENTA + Style.BRIGHT + line) # Highlight energy summary
                         else:
                              print(line) # Print normal tool output
                if e.stderr:
                    # Avoid duplicate headers if stderr also contains the summary line (less likely)
                    print_stderr_header = True
                    if e.stdout and "Energy consumption in joules:" in e.stdout:
                        if "Energy consumption in joules:" in e.stderr:
                             print_stderr_header = False # Already shown via stdout
                    if print_stderr_header:
                         print(Style.BRIGHT + "\n--- Standard Error Output ---")
                    print(e.stderr.strip())
                    output_found = True

                if not output_found:
                    print("[No output captured on stdout or stderr]")

                print(Fore.CYAN + f"\nNote: {tool_name.capitalize()} exit code {e.returncode} usually indicates findings were detected. Treated as successful scan for energy measurement.")

            # --- Handle *other* unexpected non-zero exit codes ---
            else:
                 print(e)
                 print(Fore.RED + Style.BRIGHT + f"Error: Command execution failed with unexpected exit code {e.returncode}", file=sys.stderr)
                 print(Fore.RED + "\n--- Tool/Energibridge Output (stderr) ---", file=sys.stderr)
                 print(e.stderr.strip() if e.stderr else "[No stderr]", file=sys.stderr)
                 print(Fore.RED + "\n--- Tool/Energibridge Output (stdout) ---", file=sys.stderr)
                 print(e.stdout.strip() if e.stdout else "[No stdout]", file=sys.stderr)
                 print("\n" + Style.DIM + "-" * 60, file=sys.stderr)
                 print(Fore.RED + f"Measurement failed. Check logs. Temp file was: {temp_file_path}", file=sys.stderr)
                 sys.exit(1) # Exit with error status

        except FileNotFoundError:
            # This error means the *first element* of command_list (energibridge) wasn't found
            print(Fore.RED + Style.BRIGHT + f"Error: Command failed. Could not find executable: '{command_list[0]}'.", file=sys.stderr)
            print(Fore.RED + Style.BRIGHT + f"Ensure the Energibridge path argument is correct.", file=sys.stderr)
            # It *could* also be the scanner tool if energibridge tried to run it and failed,
            # but that would likely be a CalledProcessError from energibridge itself.
            # Checking the scanner path is still good advice.
            print(Fore.RED + Style.BRIGHT + f"Also ensure '{tool_name}' is installed and accessible in the system PATH.", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            # Catch any other unexpected Python errors during execution
            print(Fore.RED + Style.BRIGHT + f"An unexpected Python error occurred during measurement execution: {e}", file=sys.stderr)
            print(f"(Command attempted: {command_list})", file=sys.stderr)
            print(f"Temporary data file was: {temp_file_path}", file=sys.stderr)
            sys.exit(1)

    print(Style.DIM + "-" * 60)
     # Use GREEN for the final success message (reached if no sys.exit happened)
    print(Fore.GREEN + "Measurement process finished.")


def main():
    parser = argparse.ArgumentParser(
        description="Run Bandit or Semgrep scans with specific configurations and measure energy consumption using Energibridge."
    )
    # --- Arguments ---
    parser.add_argument("--energibridge-path", type=Path, required=True, help="Path to the energibridge executable.")
    parser.add_argument("--repo-path", type=Path, required=True, help="Path to the code repository to scan.")
    parser.add_argument("--tool", choices=["bandit", "semgrep"], required=True, help="Static analysis tool to use.")
    parser.add_argument("--config-level", choices=["strict", "loose"], required=True, help="Configuration level ('strict' or 'loose'). Uses predefined configurations.")
    args = parser.parse_args()

    # --- Input Validation ---
    if not args.energibridge_path.is_file():
        print(Fore.RED + Style.BRIGHT + f"Error: Energibridge executable not found at '{args.energibridge_path}'", file=sys.stderr)
        sys.exit(1)
    # Add execute permission check if needed (e.g., on Linux/macOS)
    # if os.name != 'nt' and not os.access(args.energibridge_path, os.X_OK):
    #     print(Fore.RED + Style.BRIGHT + f"Error: Energibridge file does not have execute permissions: '{args.energibridge_path}'", file=sys.stderr)
    #     sys.exit(1)

    if not args.repo_path.is_dir():
        print(Fore.RED + Style.BRIGHT + f"Error: Repository path not found or is not a directory: '{args.repo_path}'", file=sys.stderr)
        sys.exit(1)

    try:
        # --- Build Scan Command ---
        repo_path_abs = args.repo_path.resolve()
        print(Fore.CYAN + "Building scan command...")
        scan_cmd_str = build_scan_command(args.tool, args.config_level, repo_path_abs)
        print(Fore.CYAN + "Scan command string built.")

        # --- Run Measurement ---
        run_measurement(args.energibridge_path.resolve(), scan_cmd_str, args.tool, args.config_level)

    except FileNotFoundError as e: # Errors during command *building* (e.g., finding bundled config)
        print(Fore.RED + Style.BRIGHT + f"Error: Required file not found during setup. {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e: # Errors during command *building* (e.g., invalid tool/level)
        print(Fore.RED + Style.BRIGHT + f"Error: Configuration issue during setup. {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e: # Other unexpected errors during setup
        print(Fore.RED + Style.BRIGHT + f"An unexpected Python error occurred during setup: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()