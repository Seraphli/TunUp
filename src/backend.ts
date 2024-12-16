import { ServerAPI, ToastData, Router } from 'decky-frontend-lib';
import {
    LogInfo,
    LogErrorInfo,
    BackendReturn,
    DefaultSettings,
    Settings,
    BackendInfo,
    DefaultBackendInfo,
} from './interfaces';

export class Backend {
    public backendInfo: BackendInfo = DefaultBackendInfo;
    public settings: Settings = DefaultSettings;

    private serverAPI: ServerAPI;
    private token = '';
    constructor(serverAPI: ServerAPI) {
        this.serverAPI = serverAPI;
    }
    async setup() {
        await this.getToken();
        if (!(await this.checkToken())) {
            return false;
        }
        await this.loadSettings();
        await this.saveSettings();
        await this.updateInfo();
        return true;
    }
    async updateInfo() {
        await this.getVersion();
        await this.checkServices();
        await this.getProfiles();
        await this.updateProfileMeta();
        await this.checkServer();
    }

    // Avoid repeated setup after reload
    async getToken() {
        this.token = await this.bridge('get_token');
    }
    async checkToken() {
        return await this.bridge('check_token', { token: this.token });
    }

    async getVersion() {
        this.backendInfo.version = await this.bridge('get_version');
    }
    async checkServices() {
        this.backendInfo.serviceStatus = await this.bridge('check_services');
    }
    async getProfiles() {
        this.backendInfo.profiles = await this.bridge('get_profiles');
    }
    async getProfileMeta(profile_name: string) {
        return await this.bridge('get_profile_meta', { profile_name });
    }
    async checkServer() {
        this.backendInfo.serverStatus = await this.bridge('check_server');
    }
    async updateProfileMeta() {
        if (this.settings.profile !== '') {
            this.backendInfo.profile_meta = await this.getProfileMeta(
                this.settings.profile,
            );
        }
    }

    async startServer() {
        return await this.bridge('start_server');
    }
    async stopServer() {
        return await this.bridge('stop_server');
    }

    async checkIfServiceExists(service: string) {
        return await this.bridge('check_if_service_exists', { service });
    }
    async installService() {
        return await this.bridge('install_service');
    }
    async uninstallService() {
        return await this.bridge('uninstall_service');
    }
    async startService(service: string) {
        return await this.bridge('start_service', { service });
    }
    async stopService(service: string) {
        return await this.bridge('stop_service', { service });
    }

    async checkResolved() {
        return await this.bridge('check_resolved');
    }
    async restoreResolved() {
        return await this.bridge('restore_resolved');
    }
    async disableResolved() {
        return await this.bridge('disable_resolved');
    }

    async updateProfile(profile_name: string) {
        return await this.bridge('update_profile', { profile_name });
    }

    async getSettings(key: string, defaultValue: any) {
        const result = await this.bridge('get_settings', {
            key,
            default: defaultValue,
        });
        return result;
    }
    async setSettings(key: string, value: any) {
        await this.bridge('set_settings', { key, value });
    }
    async commitSettings() {
        await this.bridge('commit_settings');
    }

    async loadSettings() {
        await this.applySettings(this.settings, DefaultSettings);
    }
    // Recursive function to handle all settings
    private async applySettings(
        currentSettings: any,
        defaultSettings: any,
        prefix = '',
    ) {
        for (const key of Object.keys(defaultSettings)) {
            const currentKey = prefix ? `${prefix}.${key}` : key;
            if (
                typeof defaultSettings[key] === 'object' &&
                defaultSettings[key] !== null
            ) {
                // Object type and not null, handle recursively
                await this.applySettings(
                    currentSettings[key],
                    defaultSettings[key],
                    currentKey,
                );
            } else {
                // Base type, load setting
                currentSettings[key] = await this.getSettings(
                    currentKey,
                    defaultSettings[key],
                );
            }
        }
    }

    // Function to save settings recursively
    async saveSettings() {
        await this.saveNestedSettings(this.settings, '');
        await this.commitSettings();
    }
    private async saveNestedSettings(currentSettings: any, prefix = '') {
        for (const key of Object.keys(currentSettings)) {
            const currentKey = prefix ? `${prefix}.${key}` : key;
            if (
                typeof currentSettings[key] === 'object' &&
                currentSettings[key] !== null
            ) {
                // Object type and not null, handle recursively
                await this.saveNestedSettings(currentSettings[key], currentKey);
            } else {
                // Base type, save setting
                await this.setSettings(currentKey, currentSettings[key]);
            }
        }
    }

    async log(info: LogInfo) {
        console.log(`[${info.sender}] ${info.message}`);
        await this.serverAPI.callPluginMethod<{ message: string }, any>('log', {
            message: `[${info.sender}] ${info.message}`,
        });
    }

    async logError(info: LogErrorInfo) {
        let msg = `[${info.sender}] ${info.message}`;
        if (info.stack) {
            msg += `\n-->\n${info.stack}`;
        }
        await this.serverAPI.callPluginMethod<{ message: string }, any>(
            'log_err',
            {
                message: msg,
            },
        );
    }

    async bridge(functionName: string, namedArgs?: any) {
        if (
            functionName !== 'check_token' &&
            functionName !== 'get_token' &&
            !(await this.checkToken())
        ) {
            return null;
        }
        namedArgs = namedArgs ? namedArgs : {};
        // const error = new Error('Stack trace');
        // await this.log({
        // 	sender: 'bridge',
        // 	message: `${functionName} call with ${JSON.stringify(
        // 		namedArgs,
        // 	)} from ${error.stack}`,
        // });
        await this.log({
            sender: 'bridge',
            message: `${functionName} call with ${JSON.stringify(
                namedArgs,
            )}, token: ${this.token}`,
        });
        const ret = await this.serverAPI.callPluginMethod<any, BackendReturn>(
            functionName,
            namedArgs,
        );
        await this.log({
            sender: 'bridge',
            message: `${functionName} return ${JSON.stringify(ret)}, token: ${
                this.token
            }`,
        });
        if (ret.success) {
            if (ret.result == null) {
                return null;
            }
            const payload = ret.result as BackendReturn;
            if (payload.code == 0) {
                return payload.data;
            }
            const errMessage = `${functionName} return fail: ${JSON.stringify(
                ret,
            )}`;
            await this.logError({ sender: 'bridge', message: errMessage });
        }
        const errMessage = `${functionName} fail: ${JSON.stringify(ret)}`;
        await this.logError({ sender: 'bridge', message: errMessage });
        return null;
    }
}
