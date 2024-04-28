export interface LogInfo {
	sender: string;
	message: string;
}

export interface LogErrorInfo {
	sender: string;
	message: string;
	stack?: string;
}

export interface Settings {
	enabled: boolean;
}
export const DefaultSettings: Settings = {
	enabled: false,
};

export interface BackendReturn {
	code: number;
	data: any;
}

// From https://github.com/popsUlfr/SDH-PauseGames.git
// SteamClient Doc https://github.com/SteamDeckHomebrew/decky-frontend-lib/pull/92

/**
 * @prop unAppID is not properly set by Steam for non-steam game shortcuts, so it defaults to 0 for them
 */
export interface AppLifetimeNotification {
	unAppID: number;
	nInstanceID: number;
	bRunning: boolean;
}

export interface Unregisterable {
	/**
	 * Unregister the callback.
	 */
	unregister(): void;
}

// only the needed subset of the SteamClient
export interface SteamClient {
	GameSessions: {
		/**
		 * Registers a callback function to be called when an app lifetime notification is received.
		 * @param {function} callback - The callback function to be called.
		 * @returns {Unregisterable | any} - An object that can be used to unregister the callback.
		 */
		RegisterForAppLifetimeNotifications(
			callback: (
				appLifetimeNotification: AppLifetimeNotification,
			) => void,
		): Unregisterable | any;
	};
	Apps: {
		/**
		 * Registers a callback function to be called when a game action starts.
		 * @param {function} callback - The callback function to be called.
		 * @returns {Unregisterable | any} - An object that can be used to unregister the callback.
		 */
		RegisterForGameActionStart(
			callback: (
				gameActionIdentifier: number,
				appId: string,
				action: string,
				param3: number,
			) => void,
		): Unregisterable | any;
		/**
		 * Registers a callback function to be called when a game action ends.
		 * @param {function} callback - The callback function to be called.
		 * @returns {Unregisterable | any} - An object that can be used to unregister the callback.
		 */
		RegisterForGameActionEnd(
			callback: (gameActionIdentifier: number) => void,
		): Unregisterable | any;
	};
	System: {
		RegisterForOnSuspendRequest: (cb: () => Promise<any> | void) => {
			unregister: () => void;
		};
		RegisterForOnResumeFromSuspend: (cb: () => Promise<any> | void) => {
			unregister: () => void;
		};
	};
}
