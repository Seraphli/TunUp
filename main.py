import os
import subprocess
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# The decky plugin module is located at decky-loader/plugin
# For easy intellisense checkout the decky-loader code one directory up
# or add the `decky-loader/plugin` path to `python.analysis.extraPaths` in `.vscode/settings.json`
import decky_plugin
from settings import SettingsManager

from py_modules.func import (
    check_service_status,
    kill_process_on_port,
    list_profiles,
    wrap_return,
)

server_process = None


class Plugin:
    VERSION = decky_plugin.DECKY_PLUGIN_VERSION
    settingsManager = SettingsManager("TunUp", os.environ["DECKY_PLUGIN_SETTINGS_DIR"])

    async def get_version(self):
        return wrap_return(self.VERSION)

    async def check_services(self):
        tunup = check_service_status("tunup")
        await Plugin.log_py(self, tunup.pop("debug", None))
        resolved = check_service_status("systemd-resolved")
        await Plugin.log_py(self, resolved.pop("debug", None))
        return wrap_return(
            {
                "tunup": tunup,
                "resolved": resolved,
            }
        )

    async def get_profiles(self):
        return wrap_return(
            list_profiles(
                os.path.join(os.environ["DECKY_PLUGIN_SETTINGS_DIR"], "profiles")
            )
        )

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
        global server_process
        if server_process is None:
            await Plugin.log_py(self, "Server is not running.")
            if kill_process_on_port(12345):
                await Plugin.log_py(self, "Killed another process using port 12345.")
            return wrap_return(True)
        server_process.terminate()  # Send termination signal
        server_process.wait()  # Wait for the process to finish
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

    # Asyncio-compatible long-running code, executed in a task when the plugin is loaded
    async def _main(self):
        decky_plugin.logger.info(f"TunUp {self.VERSION} backend loaded.")

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
