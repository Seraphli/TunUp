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
} from 'decky-frontend-lib';
import { VFC, useState } from 'react';
import { FaRegPaperPlane } from 'react-icons/fa';
import { Backend } from './backend';

const Content: VFC<{ backend: Backend }> = ({ backend }) => {
	const [enabled, setEnabled] = useState<boolean>(backend.settings.enabled);

	return (
		<PanelSection title="Settings">
			<ToggleField
				label="Enabled"
				checked={enabled}
				onChange={(value) => {
					setEnabled(value);
					backend.settings.enabled = value;
					backend.saveSettings();
				}}
			/>
		</PanelSection>
	);
};

export default definePlugin((serverApi: ServerAPI) => {
	const backend = new Backend(serverApi);

	return {
		title: <div className={staticClasses.Title}>TunUp</div>,
		content: <Content backend={backend} />,
		icon: <FaRegPaperPlane />,
		onDismount() {},
	};
});
