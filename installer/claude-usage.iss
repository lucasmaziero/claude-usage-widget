; Inno Setup script for the Claude Usage Widget.
; Built by installer/build.ps1, which passes MyAppVersion in from pyproject.toml.
;
; Per-user install on purpose: PrivilegesRequired=lowest keeps it out of
; Program Files, so no UAC prompt and no admin needed for a tray utility that
; only ever touches the current user's %APPDATA%.

#define MyAppName "Claude Usage Widget"
#define MyAppPublisher "Lucas Maziero"
#define MyAppExeName "ClaudeUsage.exe"
#define MyAppUrl "https://github.com/lucasmaziero/claude-usage-widget"
#ifndef MyAppVersion
  #define MyAppVersion "1.0.0"
#endif
#ifndef SourceDir
  #define SourceDir "..\build\dist\ClaudeUsage"
#endif

[Setup]
; Never change AppId: it is what ties an upgrade to the existing install.
AppId={{7B3F2C41-9E5A-4C7D-8F26-2A0D5E9B4C13}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppUrl}
AppSupportURL={#MyAppUrl}
AppUpdatesURL={#MyAppUrl}
VersionInfoVersion={#MyAppVersion}
VersionInfoDescription={#MyAppName} Setup

DefaultDirName={autopf}\Claude Usage Widget
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
LicenseFile=..\LICENSE

OutputDir=..\build
OutputBaseFilename=ClaudeUsage-{#MyAppVersion}
SetupIconFile=claude-usage.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern

; The tray app holds its own files open; let Restart Manager close it instead of
; failing the copy or leaving a stale process behind after an upgrade.
CloseApplications=yes
CloseApplicationsFilter=*.exe
RestartApplications=no

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "autostart"; Description: "{cm:AutoStartDesc}"; GroupDescription: "{cm:AutoStartGroup}"

[Files]
Source: "{#SourceDir}\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceDir}\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
; Same key and value name the app's own "Iniciar com o Windows" menu item uses,
; so the two never disagree about the current state.
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; \
    ValueType: string; ValueName: "ClaudeUsageWidget"; \
    ValueData: """{app}\{#MyAppExeName}"""; Flags: uninsdeletevalue; Tasks: autostart

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; \
    Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Sweep the whole install folder. Anything that survives the file list (a lock
; released late, a file dropped in by hand) would otherwise keep it alive.
Type: filesandordirs; Name: "{app}\_internal"
Type: filesandordirs; Name: "{app}"

[CustomMessages]
brazilianportuguese.AutoStartDesc=Iniciar o widget junto com o Windows
brazilianportuguese.AutoStartGroup=Inicializacao:
english.AutoStartDesc=Start the widget with Windows
english.AutoStartGroup=Startup:

[Code]
// CloseApplications (Restart Manager) covers Setup, but NOT the uninstaller:
// uninstalling with the widget running left every locked file behind - the exe,
// python313.dll, the Qt DLLs - roughly 57 MB of orphans, plus a folder that
// outlived its own uninstall entry. So the process is closed explicitly on both
// paths. A hard kill costs nothing here: preferences are written the moment
// they change, never at exit.
procedure StopWidget;
var
  ResultCode: Integer;
begin
  Exec(ExpandConstant('{sys}\taskkill.exe'), '/F /T /IM ClaudeUsage.exe',
       '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Sleep(800);   // let Windows release the file handles before we touch them
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  StopWidget;
  Result := '';
end;

function InitializeUninstall(): Boolean;
begin
  StopWidget;
  Result := True;
end;

// Settings live outside {app}; ask before throwing them away, and only when a
// person is watching (a silent uninstall keeps them).
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  SettingsDir: String;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    SettingsDir := ExpandConstant('{userappdata}\ClaudeUsageWidget');
    if DirExists(SettingsDir) and not UninstallSilent then
      if SuppressibleMsgBox('Remover tambem as preferencias do widget (posicao, intervalo)?',
                            mbConfirmation, MB_YESNO, IDNO) = IDYES then
        DelTree(SettingsDir, True, True, True);
  end;
end;
