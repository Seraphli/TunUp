import { ServerAPI, ToastData, Router } from 'decky-frontend-lib';
import { LogInfo, LogErrorInfo, BackendReturn, DefaultSettings, Settings } from './interfaces';

export class Backend {
	public settings: Settings = DefaultSettings;

	private serverAPI: ServerAPI;
	constructor(serverAPI: ServerAPI) {
		this.serverAPI = serverAPI;
	}
	async setup() {
		await this.loadSettings();
		await this.saveSettings();
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
		this.settings.enabled = await this.getSettings(
			'enabled',
			DefaultSettings.enabled,
		);
	}

	async saveSettings() {
		await this.setSettings('enabled', this.settings.enabled);
		await this.commitSettings();
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
		namedArgs = namedArgs ? namedArgs : {};
		await this.log({
			sender: 'bridge',
			message: `${functionName} call with ${JSON.stringify(namedArgs)}`,
		});
		const ret = await this.serverAPI.callPluginMethod<any, BackendReturn>(
			functionName,
			namedArgs,
		);
		await this.log({
			sender: 'bridge',
			message: `${functionName} return ${JSON.stringify(ret)}`,
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
