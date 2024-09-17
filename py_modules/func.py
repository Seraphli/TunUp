import codecs
import glob
import os
import shutil
import subprocess
from pathlib import Path

import yaml


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
        # Reload systemctl daemon to recognize new service
        _, _, _ = run_command(["systemctl", "daemon-reload"])
        return True
    except Exception:
        return False


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


def get_profile_meta(profile_name):
    # Get the path to the profile meta file
    meta_file_path = os.path.join(
        os.environ["DECKY_PLUGIN_SETTINGS_DIR"],
        "profiles",
        f"{profile_name}.meta.yml",
    )

    # Check if the meta file exists
    if not os.path.exists(meta_file_path):
        return None

    # Read the contents of the meta file
    with open(meta_file_path, "r") as file:
        meta_data = yaml.safe_load(file)

    # Return the contents of the meta file
    return meta_data


def set_profile_meta(profile_name, meta_data):
    # Get the path to the profile meta file
    meta_file_path = os.path.join(
        os.environ["DECKY_PLUGIN_SETTINGS_DIR"],
        "profiles",
        f"{profile_name}.meta.yml",
    )

    # Write the meta data to the meta file
    with open(meta_file_path, "w") as file:
        yaml.dump(meta_data, file)

    return True


def update_config_file(profile_name, dir_path):
    profiles_savepath = os.path.join(
        os.environ["DECKY_PLUGIN_SETTINGS_DIR"], "profiles"
    )
    clash_path = os.path.join(dir_path, "clash")
    config_path = "/home/deck/.config"
    tunup_path = os.path.join(config_path, "tunup")
    profile_yml_path = os.path.join(profiles_savepath, f"{profile_name}.yml")
    with codecs.open(profile_yml_path, "r", "utf-8") as file:
        profile_yml = yaml.safe_load(file)
    template_yml_path = os.path.join(clash_path, "template.yml")
    with codecs.open(template_yml_path, "r", "utf-8") as file:
        template_yml = yaml.safe_load(file)
    config_yml = {**template_yml}
    config_yml["proxies"] = profile_yml["proxies"]
    config_yml["proxy-groups"] = profile_yml["proxy-groups"]
    config_yml["rules"] = profile_yml["rules"]
    config_yml_path = os.path.join(tunup_path, "config.yml")
    with codecs.open(config_yml_path, "w", "utf-8") as file:
        yaml.safe_dump(config_yml, file, allow_unicode=True)
    return profile_yml_path, profile_yml["proxies"][:3], config_yml_path


def copy_file(src, dst):
    # Copy the file to the destination and overwrite if it exists
    shutil.copy(src, dst)


def copy_folder(src, dst):
    # Copy entire folder and its contents to the destination, overwrite if necessary
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
