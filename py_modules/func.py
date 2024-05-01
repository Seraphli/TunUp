import glob
import os
import shutil
import subprocess
from pathlib import Path


def wrap_return(data, code=0):
    return {"code": code, "data": data}


def run_command(command):
    """Executes a system command and returns the output."""
    try:
        result = subprocess.run(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except Exception as e:
        return None, str(e), -1


def check_if_service_exists(service_name):
    """Check if the service is installed by attempting to get its status."""
    _, _, return_code = run_command(["systemctl", "status", service_name])
    # A return code of 4 with systemctl status usually indicates that it could not find the service
    return return_code != 4


def install_service(service_name, service_file_path):
    """Install the service by copying the service file to the systemd directory."""
    destination = Path("/etc/systemd/system") / service_name
    try:
        shutil.copy(service_file_path, destination)
        print("Service file installed successfully.")
        # Reload systemctl daemon to recognize new service
        _, _, _ = run_command(["systemctl", "daemon-reload"])
    except Exception as e:
        print(f"Failed to install service: {e}")


def check_service_status(service_name):
    """Check if the service is active and enabled."""
    is_active, _err0, _code0 = run_command(["systemctl", "is-active", service_name])
    is_enabled, _err1, _code1 = run_command(["systemctl", "is-enabled", service_name])
    return {
        "active": is_active == "active",
        "enabled": is_enabled == "enabled",
        "debug": {
            "service_name": service_name,
            "acitve": (is_active, _err0, _code0),
            "enabled": (is_enabled, _err1, _code1),
        },
    }


def download_file_with_curl(url, filename):
    """Downloads a file using curl from a specified URL and saves it to a specified filename."""
    # Build the curl command
    command = ["curl", "-o", filename, url]

    # Execute the curl command using the previously defined run_command function
    stdout, stderr, return_code = run_command(command)

    if return_code != 0:
        return False
    return True


def kill_process_on_port(port):
    """Kill process on a given port using lsof and kill command on Unix."""
    try:
        # Find PID using port
        result = subprocess.run(
            ["lsof", "-ti", f"tcp:{port}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if result.stdout:
            pid = int(result.stdout.strip())
            # Kill the process using the PID
            subprocess.run(
                ["kill", "-9", str(pid)], stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            return True
        return False
    except Exception:
        return False


def install(service_name, service_file_path):
    if not check_if_service_exists(service_name):
        install_service(service_name, service_file_path)
    else:
        active, enabled = check_service_status(service_name)
        print(f"Service '{service_name}' is {'active' if active else 'inactive'}.")
        print(f"Service '{service_name}' is {'enabled' if enabled else 'disabled'}.")


def check_services():
    return {
        "tunup": check_service_status("tunup"),
        "resolved": check_service_status("systemd-resolved"),
    }


def list_profiles(folder_path):
    # Find all .yml files in the specified folder path
    yml_files = glob.glob(os.path.join(folder_path, "*.yml"))
    # Create a set to store unique profile names
    profiles = set()

    # Iterate over all .yml files found
    for file_path in yml_files:
        # Get the base filename without the extension
        base_name = os.path.basename(file_path)
        name = os.path.splitext(base_name)[0]

        # Remove the '.meta' suffix if it exists
        if name.endswith(".meta"):
            name = name[:-5]

        # Add the profile name to the set
        profiles.add(name)

    # Convert the set to a list and return it
    return list(profiles)
