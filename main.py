import os
import shlex
import subprocess
import sys
import tempfile
import time
import uuid

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# The decky plugin module is located at decky-loader/plugin
# For easy intellisense checkout the decky-loader code one directory up
# or add the `decky-loader/plugin` path to `python.analysis.extraPaths` in `.vscode/settings.json`
import decky_plugin
from settings import SettingsManager

from py_modules.func import (
    check_if_service_exists,
    check_service_status,
    copy_file,
    copy_folder,
    get_profile_meta,
    kill_process_on_port,
    list_profiles,
    run_command,
    set_profile_meta,
    update_config_file,
    wrap_return,
)

server_process = None


class Plugin:
    VERSION = decky_plugin.DECKY_PLUGIN_VERSION
    settingsManager = SettingsManager("TunUp", os.environ["DECKY_PLUGIN_SETTINGS_DIR"])
    TOKEN = ""

    async def get_version(self):
        return wrap_return(self.VERSION)

    async def check_services(self):
        tunup = check_service_status("tunup")
        await Plugin.log_py(self, tunup.pop("debug", None))
        resolved = check_service_status("systemd-resolved")
        await Plugin.log_py(self, resolved.pop("debug", None))
        return wrap_return(
            {
                "tunup": {"exists": check_if_service_exists("tunup"), **tunup},
                "resolved": {
                    "exists": check_if_service_exists("systemd-resolved"),
                    **resolved,
                },
            }
        )

    async def get_profiles(self):
        return wrap_return(
            list_profiles(
                os.path.join(os.environ["DECKY_PLUGIN_SETTINGS_DIR"], "profiles")
            )
        )

    async def get_profile_meta(self, profile_name):
        ret = get_profile_meta(profile_name)
        if ret is None:
            return wrap_return(False)
        return wrap_return(
            {
                "type": ret["type"],
                "update_time": ret["update_time"],
            }
        )

    async def check_server(self):
        await Plugin.log_py(self, "Checking server")
        global server_process
        if server_process is None:
            await Plugin.log_py(self, "Server is not running.")
            return wrap_return(False)
        await Plugin.log_py(self, "Server is running.")
        return wrap_return(True)

    async def update_profile(self, profile_name):
        profile_meta = get_profile_meta(profile_name)
        if profile_meta is None:
            return wrap_return(False)
        profile_type = profile_meta["type"]
        if profile_type == "upload":
            await Plugin.log_py(self, "Profile is of type upload")
            return wrap_return(False)
        # Download profile
        url = profile_meta["url"]
        update_interval = profile_meta["update_interval"]
        # CURL to temp dir then move to profiles
        safe_url = shlex.quote(url)
        with tempfile.NamedTemporaryFile(suffix=".yml", delete=False) as temp_file:
            filename = shlex.quote(temp_file.name)
        command = f"curl -L {safe_url} -o {filename}"
        profiles_savepath = os.path.join(
            os.environ["DECKY_PLUGIN_SETTINGS_DIR"], "profiles"
        )
        try:
            subprocess.run(command, shell=True, check=True)
            # Move to profiles
            copy_file(
                filename,
                os.path.join(
                    profiles_savepath,
                    f"{profile_name}.yml",
                ),
            )
            update_time = int(time.time())
            meta_filename = os.path.join(
                profiles_savepath,
                f"{profile_name}.meta.yml",
            )
            with open(meta_filename, "w") as meta_file:
                meta_file.write(f"url: {url}\n")
                meta_file.write(f"update_time: {update_time}\n")
                meta_file.write(f"update_interval: {update_interval}\n")
                meta_file.write("type: download\n")
        except Exception as e:
            await Plugin.log_py_err(self, f"Error downloading file: {e}")
            return wrap_return(False)
        update_config_file(profile_name, os.path.dirname(os.path.realpath(__file__)))
        ret = run_command(["systemctl", "restart", "tunup"])
        await Plugin.log_py(self, "Restart tunup: " + str(ret))
        return wrap_return(True)

    async def install_service(self):
        cur_profile = await Plugin.get_settings(self, "profile", "", string=False)
        if cur_profile == "":
            return wrap_return(False)
        dir_path = os.path.dirname(os.path.realpath(__file__))
        clash_path = os.path.join(dir_path, "clash")
        config_path = "/home/deck/.config"
        tunup_path = os.path.join(config_path, "tunup")
        os.makedirs(tunup_path, exist_ok=True)

        copy_file(
            os.path.join(clash_path, "clashpremium-linux-amd64"),
            os.path.join(tunup_path, "clashpremium-linux-amd64"),
        )
        run_command(
            ["chmod", "+x", os.path.join(tunup_path, "clashpremium-linux-amd64")]
        )
        copy_file(
            os.path.join(clash_path, "tunup.service"),
            os.path.join(tunup_path, "tunup.service"),
        )
        copy_file(
            os.path.join(clash_path, "Country.mmdb"),
            os.path.join(tunup_path, "Country.mmdb"),
        )
        copy_folder(
            os.path.join(clash_path, "web"),
            os.path.join(tunup_path, "web"),
        )
        await Plugin.log_py(self, f"Current profile: {cur_profile}")
        ret = update_config_file(cur_profile, dir_path)
        await Plugin.log_py(self, "Update config file: " + str(ret))

        ret = run_command(
            [
                "cp",
                os.path.join(tunup_path, "tunup.service"),
                os.path.join("/etc/systemd/system", "tunup.service"),
            ]
        )
        await Plugin.log_py(self, "Copy service file: " + str(ret))
        # Reload systemctl daemon to recognize new service
        ret = run_command(["systemctl", "daemon-reload"])
        await Plugin.log_py(self, "Reload daemon: " + str(ret))
        ret = run_command(["systemctl", "enable", "tunup"])
        await Plugin.log_py(self, "Enable service: " + str(ret))
        ret = run_command(["systemctl", "restart", "tunup"])
        await Plugin.log_py(self, "Restart tunup: " + str(ret))
        return wrap_return(str(ret))

    async def uninstall_service(self):
        _, _, _ = run_command(["systemctl", "stop", "tunup"])
        _, _, _ = run_command(["systemctl", "disable", "tunup"])
        return wrap_return(True)

    async def start_service(self, service):
        _, _, code = run_command(["systemctl", "start", service])
        return wrap_return(code)

    async def stop_service(self, service):
        _, _, code = run_command(["systemctl", "stop", service])
        return wrap_return(code)

    async def check_if_service_exists(self, service):
        return wrap_return(check_if_service_exists(service))

    async def start_server(self):
        """Start the server process"""
        global server_process
        if server_process is not None:
            await Plugin.log_py(self, "Server is already running.")
            return wrap_return(True)
        # Get the directory of the current script
        dir_path = os.path.dirname(os.path.realpath(__file__))
        profiles_path = os.path.join(dir_path, "clash", "profiles")
        profiles_savepath = os.path.join(
            os.environ["DECKY_PLUGIN_SETTINGS_DIR"], "profiles"
        )
        if not os.path.exists(profiles_savepath):
            # Create the directory if it does not exist
            os.makedirs(profiles_savepath, exist_ok=True)
        server_process = subprocess.Popen(
            ["python", f"{profiles_path}/download_server.py"], cwd=profiles_savepath
        )
        await Plugin.log_py(self, "Server started.")
        return wrap_return(True)

    async def stop_server(self):
        """Stop the server process"""
        await Plugin.log_py(self, "Stopping server.")
        global server_process
        if server_process is None:
            await Plugin.log_py(self, "Server is not running.")
            if kill_process_on_port(12345):
                await Plugin.log_py(self, "Killed another process using port 12345.")
            return wrap_return(True)
        await Plugin.log_py(self, f"Terminating server process: {server_process.pid}")
        server_process.terminate()  # Send termination signal
        try:
            server_process.wait(3)  # Wait for the process to finish
        except subprocess.TimeoutExpired:
            await Plugin.log_py(self, "Server process did not terminate.")
            server_process.kill()
        await Plugin.log_py(self, "Server stopped.")
        server_process = None
        return wrap_return(True)

    async def log(self, message):
        value = await Plugin.get_settings(self, "debug.frontend", True, string=False)
        if value:
            decky_plugin.logger.info("[DeckySpy][F]" + message)

    async def log_err(self, message):
        decky_plugin.logger.error("[DeckySpy][F]" + message)

    async def log_py(self, message):
        value = await Plugin.get_settings(self, "debug.backend", True, string=False)
        if value:
            decky_plugin.logger.info("[DeckySpy][B]" + str(message))

    async def log_py_err(self, message):
        decky_plugin.logger.error("[DeckySpy][B]" + str(message))

    async def get_settings(self, key, default, string=True):
        value = self.settingsManager.getSetting(key, default)
        if string:
            return {"code": 0, "data": value}
        return value

    async def set_settings(self, key, value):
        self.settingsManager.setSetting(key, value)

    async def commit_settings(self):
        self.settingsManager.commit()

    async def get_token(self):
        self.TOKEN = str(uuid.uuid4())[:6]
        await Plugin.log_py(self, f"Generated new token: {self.TOKEN}")
        return wrap_return(self.TOKEN)

    async def check_token(self, token):
        if token == self.TOKEN:
            return wrap_return(True)
        return wrap_return(False)

    # Asyncio-compatible long-running code, executed in a task when the plugin is loaded
    async def _main(self):
        decky_plugin.logger.info(f"TunUp {self.VERSION} backend loaded.")
        self.TOKEN = None

    # Function called first during the unload process, utilize this to handle your plugin being removed
    async def _unload(self):
        if server_process is not None:
            Plugin.stop_server(self)
        decky_plugin.logger.info("TunUp backend unloaded.")

    # Migrations that should be performed before entering `_main()`.
    async def _migration(self):
        decky_plugin.logger.info("Migrating")
        # Here's a migration example for logs:
        # - `~/.config/decky-template/template.log` will be migrated to `decky_plugin.DECKY_PLUGIN_LOG_DIR/template.log`
        decky_plugin.migrate_logs(
            os.path.join(
                decky_plugin.DECKY_USER_HOME,
                ".config",
                "decky-template",
                "template.log",
            )
        )
        # Here's a migration example for settings:
        # - `~/homebrew/settings/template.json` is migrated to `decky_plugin.DECKY_PLUGIN_SETTINGS_DIR/template.json`
        # - `~/.config/decky-template/` all files and directories under this root are migrated to `decky_plugin.DECKY_PLUGIN_SETTINGS_DIR/`
        decky_plugin.migrate_settings(
            os.path.join(decky_plugin.DECKY_HOME, "settings", "template.json"),
            os.path.join(decky_plugin.DECKY_USER_HOME, ".config", "decky-template"),
        )
        # Here's a migration example for runtime data:
        # - `~/homebrew/template/` all files and directories under this root are migrated to `decky_plugin.DECKY_PLUGIN_RUNTIME_DIR/`
        # - `~/.local/share/decky-template/` all files and directories under this root are migrated to `decky_plugin.DECKY_PLUGIN_RUNTIME_DIR/`
        decky_plugin.migrate_runtime(
            os.path.join(decky_plugin.DECKY_HOME, "template"),
            os.path.join(
                decky_plugin.DECKY_USER_HOME, ".local", "share", "decky-template"
            ),
        )
