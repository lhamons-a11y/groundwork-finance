; ============================================================
;  Groundwork v1.0.0.0 - Inno Setup Installer Script
;  Download Inno Setup 6 free from: https://jrsoftware.org
;  Build: ISCC.exe installer\groundwork_setup.iss
; ============================================================

#define AppName      "Groundwork"
#define AppVersion   "1.0.0.0"
#define AppPublisher "Groundwork"
#define AppURL       "https://github.com/your-github-username/groundwork"
#define AppExeName   "Groundwork.exe"

[Setup]
AppId={{A8F3C2D1-4B7E-4A9F-B2C3-1D5E6F7A8B9C}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}/releases
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=installer\Output
OutputBaseFilename=GroundworkSetup
SetupIconFile=..\assets\groundwork.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
UsedUserAreasWarning=no
MinVersion=10.0
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon";   Description: "Create a &desktop shortcut";    GroupDescription: "Additional icons:"; Flags: unchecked
Name: "startmenuicon"; Description: "Create a &Start Menu shortcut"; GroupDescription: "Additional icons:"

[Files]
Source: "..\dist\Groundwork\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}";           Filename: "{app}\{#AppExeName}"
Name: "{group}\Uninstall Groundwork"; Filename: "{uninstallexe}"
Name: "{commondesktop}\{#AppName}";   Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Launch Groundwork now"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\__pycache__"

[Code]
// Check for WebView2 runtime (required by pywebview on Windows)
function IsWebView2Installed(): Boolean;
var
  Version: String;
begin
  Result :=
    RegQueryStringValue(HKLM,
      'SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}',
      'pv', Version) or
    RegQueryStringValue(HKCU,
      'SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}',
      'pv', Version);
end;

procedure InitializeWizard();
var
  Msg: String;
begin
  if not IsWebView2Installed() then
  begin
    Msg := 'Groundwork uses the Microsoft WebView2 runtime, which does not appear to be installed.';
    Msg := Msg + Chr(13) + Chr(10) + Chr(13) + Chr(10);
    Msg := Msg + 'If Groundwork does not open after installation, download WebView2 from:';
    Msg := Msg + Chr(13) + Chr(10);
    Msg := Msg + 'https://developer.microsoft.com/microsoft-edge/webview2/';
    Msg := Msg + Chr(13) + Chr(10) + Chr(13) + Chr(10);
    Msg := Msg + 'Most Windows 10 and 11 machines already have it installed.';
    MsgBox(Msg, mbInformation, MB_OK);
  end;
end;
