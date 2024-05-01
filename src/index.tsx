import {
    ButtonItem,
    definePlugin,
    Navigation,
    PanelSection,
    PanelSectionRow,
    ServerAPI,
    staticClasses,
    ToggleField,
    Field,
    DropdownItem,
    DropdownOption,
} from 'decky-frontend-lib';
import { VFC, useState, useEffect } from 'react';
import { FaRegPaperPlane } from 'react-icons/fa';
import { Backend } from './backend';
import { BackendInfo, DefaultBackendInfo, Settings } from './interfaces';

let current_sub = '';

const Content: VFC<{ backend: Backend }> = ({ backend }) => {
    const [backendInfo, setBackendInfo] = useState<BackendInfo>(
        backend.backendInfo,
    );
    const [settings, setSettings] = useState<Settings>(backend.settings);
    const [serverOnline, setServerOnline] = useState(false);
    const [options, setOptions] = useState<DropdownOption[]>(
        (() => {
            let subs_option: DropdownOption[] = [];
            backend.backendInfo.profiles.map((x) => {
                subs_option.push({ data: x, label: x });
            });
            return subs_option;
        })(),
    );
    const [currentSub, setCurrentSub] = useState<string>(backend.settings.profile);

    useEffect(() => {}, []);
    return (
        <div>
            <PanelSection title="Profile Select">
                <Field focusable={true} childrenContainerWidth="max">
                    Select a profile and install it on your SteamDeck.
                    <br />
                    <strong>Change profile need to reinstall</strong>
                </Field>
                <DropdownItem
                    strDefaultLabel={
                        currentSub === '' ? 'Select a Profile' : currentSub
                    }
                    rgOptions={options}
                    selectedOption={currentSub}
                    onMenuWillOpen={async () => {
                        await backend.getProfiles();
                        if (backend.backendInfo.profiles.length === 0) {
                            return;
                        }
                        setOptions(
                            (() => {
                                let subs_option: DropdownOption[] = [];
                                backend.backendInfo.profiles.map((x) => {
                                    subs_option.push({ data: x, label: x });
                                });
                                return subs_option;
                            })(),
                        );
                    }}
                    onChange={async (x) => {
                        if (x.data === currentSub || x.data === '') {
                            return;
                        }
                        backend.settings.profile = x.data;
                        await backend.saveSettings();
                        setCurrentSub(x.data);
                    }}
                />
            </PanelSection>
            <PanelSection title="Profile Update">
                <Field focusable={true} childrenContainerWidth="max">
                    Start the server and visit
                    <br />
                    <strong>http://[steamdeck_ip]:12345</strong>
                    <br />
                    to update profiles. <br />
                    You can get SteamDeck's IP in the settings.
                </Field>
                <ButtonItem
                    layout="below"
                    disabled={serverOnline}
                    onClick={async () => {
                        await backend.startServer();
                        setServerOnline(true);
                    }}
                >
                    Start Server
                </ButtonItem>
                <ButtonItem
                    layout="below"
                    disabled={!serverOnline}
                    onClick={async () => {
                        await backend.stopServer();
                        setServerOnline(false);
                    }}
                >
                    Stop Server
                </ButtonItem>
            </PanelSection>
            <PanelSection title="Service Status">
                {Object.entries(backendInfo.serviceStatus).map(
                    ([key, { active, enabled }]) => (
                        <Field label={key} focusable={true}>
                            Active: {`${active}`}
                            <br />
                            Enabled: {`${enabled}`}
                        </Field>
                    ),
                )}
            </PanelSection>
            {/* <PanelSection title="Actions">
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
			</PanelSection> */}
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
