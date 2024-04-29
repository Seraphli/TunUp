import {
	ButtonItem,
	definePlugin,
	DialogButton,
	Menu,
	MenuItem,
	Navigation,
	PanelSection,
	PanelSectionRow,
	ServerAPI,
	showContextMenu,
	staticClasses,
	ToggleField,
	Field,
} from 'decky-frontend-lib';
import { VFC, useState, useEffect } from 'react';
import { FaRegPaperPlane } from 'react-icons/fa';
import { Backend } from './backend';
import { BackendInfo, DefaultBackendInfo, Settings } from './interfaces';

const Content: VFC<{ backend: Backend }> = ({ backend }) => {
	const [backendInfo, setBackendInfo] = useState<BackendInfo>(
		backend.backendInfo,
	);
	const [settings, setSettings] = useState<Settings>(backend.settings);
	useEffect(() => {}, []);
	return (
		<div>
			<PanelSection title="Display">
				<PanelSectionRow>
					<Field focusable={true}>
						<div>{settings.integer}</div>
					</Field>
				</PanelSectionRow>
			</PanelSection>
			<PanelSection title="Actions">
				<PanelSectionRow>
					<ButtonItem
						layout="below"
						onClick={async () => {
							await backend.incr();
							setSettings({
								...settings,
								integer: backend.settings.integer,
							});
						}}
					>
						Incr
					</ButtonItem>
					<ButtonItem
						layout="below"
						onClick={async () => {
							await backend.decr();
							setSettings({
								...settings,
								integer: backend.settings.integer,
							});
						}}
					>
						Decr
					</ButtonItem>
				</PanelSectionRow>
			</PanelSection>
			<PanelSection title="Debug Info">
				<Field label="Version" focusable={true}>
					{backendInfo.version}
				</Field>
				<ToggleField
					label="Frontend"
					description="Enable Frontend debug"
					checked={settings.debug.frontend}
					onChange={async (value) => {
						backend.settings.debug.frontend = value;
						await backend.saveSettings();
						setSettings({
							...settings,
							debug: { ...settings.debug, frontend: value },
						});
					}}
				/>
				<ToggleField
					label="Backend"
					description="Enable Backend debug"
					checked={settings.debug.backend}
					onChange={async (value) => {
						backend.settings.debug.backend = value;
						await backend.saveSettings();
						setSettings({
							...settings,
							debug: { ...settings.debug, backend: value },
						});
					}}
				/>
			</PanelSection>
		</div>
	);
};

export default definePlugin((serverApi: ServerAPI) => {
	const backend = new Backend(serverApi);
	function regularFunction() {
		(async () => {
			await backend.setup();
		})();
	}
	regularFunction();

	return {
		title: <div className={staticClasses.Title}>TunUp</div>,
		content: <Content backend={backend} />,
		icon: <FaRegPaperPlane />,
		onDismount() {},
	};
});
