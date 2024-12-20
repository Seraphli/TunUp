import {
    Router,
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
import { BackendInfo, Settings } from './interfaces';

const Content: VFC<{ backend: Backend }> = ({ backend }) => {
    const [backendInfo, setBackendInfo] = useState<BackendInfo>(
        backend.backendInfo,
    );
    const [settings, setSettings] = useState<Settings>(backend.settings);
    const [working, setWorking] = useState(false);
    const [options, setOptions] = useState<DropdownOption[]>(
        (() => {
            let subs_option: DropdownOption[] = [];
            backend.backendInfo.profiles.map((x) => {
                subs_option.push({ data: x, label: x });
            });
            return subs_option;
        })(),
    );
    const [currentSub, setCurrentSub] = useState<string>(
        backend.settings.profile,
    );
    const [profileMeta, setProfileMeta] = useState<{
        type: string;
        update_time: number;
    }>(backend.backendInfo.profile_meta);

    useEffect(() => {}, []);
    return (
        <div>
            <PanelSection title="Profile Select">
                <Field focusable={true} childrenContainerWidth="max">
                    Select a profile and enable it on your SteamDeck.
                    <br />
                    <strong>Change profile need to re-enable</strong>
                </Field>
                <DropdownItem
                    strDefaultLabel={
                        currentSub === '' ? 'Select a Profile' : currentSub
                    }
                    rgOptions={options}
                    selectedOption={currentSub}
                    disabled={working}
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
                        setWorking(true);
                        if (x.data === currentSub || x.data === '') {
                            return;
                        }
                        backend.settings.profile = x.data;
                        await backend.saveSettings();
                        setCurrentSub(x.data);
                        await backend.updateProfileMeta();
                        setProfileMeta(backend.backendInfo.profile_meta);
                        setWorking(false);
                    }}
                />
                {currentSub !== '' ? (
                    <PanelSectionRow>
                        <Field focusable={false} label="Last Update: ">
                            {new Date(
                                profileMeta.update_time * 1000,
                            ).toLocaleString()}
                        </Field>
                        <ButtonItem
                            layout="below"
                            disabled={working || profileMeta.type === 'upload'}
                            onClick={async () => {
                                setWorking(true);
                                await backend.updateProfile(currentSub);
                                await backend.updateProfileMeta();
                                setProfileMeta(
                                    backend.backendInfo.profile_meta,
                                );
                                setWorking(false);
                            }}
                        >
                            Update Profile
                        </ButtonItem>
                        {/* <ToggleField
                            label="Auto Update"
                            description="Auto update profile"
                            disabled={working || profileMeta.type === 'upload'}
                            checked={settings.auto_update}
                            onChange={async (value) => {
                                backend.settings.auto_update = value;
                                await backend.saveSettings();
                                setSettings({
                                    ...settings,
                                    auto_update: value,
                                });
                            }}
                        /> */}
                    </PanelSectionRow>
                ) : null}
                <ToggleField
                    label="Enable Service"
                    description="Enable TunUp"
                    disabled={working}
                    checked={backend.backendInfo.serviceStatus.tunup.enabled}
                    onChange={async (value) => {
                        setWorking(true);
                        if (value) {
                            await backend.installService();
                        } else {
                            await backend.uninstallService();
                        }
                        await backend.checkServices();
                        setBackendInfo({ ...backend.backendInfo });
                        setWorking(false);
                    }}
                />
                <ButtonItem
                    layout="below"
                    onClick={() => {
                        Router.CloseSideMenus();
                        Navigation.NavigateToExternalWeb(
                            'http://127.0.0.1:9090/ui',
                        );
                    }}
                    disabled={
                        !backend.backendInfo.serviceStatus.tunup.active ||
                        working
                    }
                >
                    Open Dashboard
                </ButtonItem>
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
                    disabled={backend.backendInfo.serverStatus}
                    onClick={async () => {
                        await backend.startServer();
                        await backend.checkServer();
                        setBackendInfo({ ...backend.backendInfo });
                    }}
                >
                    Start Server
                </ButtonItem>
                <ButtonItem
                    layout="below"
                    disabled={!backend.backendInfo.serverStatus}
                    onClick={async () => {
                        await backend.stopServer();
                        await backend.checkServer();
                        setBackendInfo({ ...backend.backendInfo });
                    }}
                >
                    Stop Server
                </ButtonItem>
            </PanelSection>
            <PanelSection title="Service Status">
                <PanelSectionRow>
                    <Field label="tunup" focusable={true}>
                        Active: {`${backendInfo.serviceStatus.tunup.active}`}
                        <br />
                        Enabled: {`${backendInfo.serviceStatus.tunup.enabled}`}
                    </Field>
                    <ToggleField
                        label="Active"
                        description="Activate TunUp"
                        disabled={!backendInfo.serviceStatus.tunup.exists}
                        checked={backendInfo.serviceStatus.tunup.active}
                        onChange={async (value) => {
                            if (value) {
                                await backend.startService('tunup');
                            } else {
                                await backend.stopService('tunup');
                            }
                            await backend.checkServices();
                            setBackendInfo({ ...backend.backendInfo });
                        }}
                    />
                </PanelSectionRow>
                <PanelSectionRow>
                    <Field label="resolved" focusable={true}>
                        Active: {`${backendInfo.serviceStatus.resolved.active}`}
                        <br />
                        Enabled:{' '}
                        {`${backendInfo.serviceStatus.resolved.enabled}`}
                    </Field>
                    <ToggleField
                        label="Active"
                        description="Activate Resolved"
                        disabled={!backendInfo.serviceStatus.resolved.exists}
                        checked={backendInfo.serviceStatus.resolved.active}
                        onChange={async (value) => {
                            if (value) {
                                await backend.restoreResolved();
                            } else {
                                await backend.disableResolved();
                            }
                            await backend.checkServices();
                            setBackendInfo({ ...backend.backendInfo });
                        }}
                    />
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
