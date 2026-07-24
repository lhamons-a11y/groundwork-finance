; Groundwork — Inno Setup installer script
; Produces a single-file installer: Groundwork_Setup.exe
; Tested with Inno Setup 6.x

#define AppName "Groundwork"
#define AppVersion "1.0.0"
#define AppPublisher "Groundwork"
#define AppURL "https://groundwork.app"
#define AppExeName "Groundwork.exe"

[Setup]
AppId={{A3F8C2D1-5B4E-4F9A-8C6D-2E7F1A0B3C5D}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=C:\Groundwork\installer_output
OutputBaseFilename=Groundwork_Setup
SetupIconFile=C:\Groundwork\groundwork.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
MinVersion=10.0.17763

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "C:\Groundwork\dist\Groundwork\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Ollama's own installer, bundled so local AI works out of the box with no
; separate download step. Extracted to a temp dir at install time only
; (dontcopy) — it's run once via [Run] below and never becomes part of the
; installed Groundwork folder. Built with Inno Setup itself (confirmed:
; ollama/ollama's build_windows.ps1 packages OllamaSetup.exe with Inno
; Setup), so it accepts the standard Inno silent-install switches used below.
Source: "C:\Groundwork\vendor\OllamaSetup.exe"; DestDir: "{tmp}"; Flags: dontcopy noencryption

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
; Silent, unattended — matches how OllamaSetup.exe's own build already
; behaves for scripted installs. Only runs when Ollama isn't already present
; (NeedsOllamaInstall), so re-running this installer on a machine that
; already has Ollama (e.g. a Groundwork update) never re-installs it.
; waituntilterminated: Groundwork's first run needs Ollama already usable,
; not still installing in the background.
Filename: "{tmp}\OllamaSetup.exe"; Parameters: "/VERYSILENT /SUPPRESSMSGBOXES /NORESTART"; StatusMsg: "Setting up local AI (Ollama) — this runs once..."; Check: NeedsOllamaInstall; Flags: waituntilterminated
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Code]
// Ollama installs per-user, no admin rights, always to this fixed path — see
// docs.ollama.com/windows. Checking for the real binary rather than a
// registry key: Ollama's installer doesn't write the kind of versioned
// uninstall registry entry WebView2 does, but this file's presence is
// exactly as reliable and needs no assumption about registry layout.
function NeedsOllamaInstall(): Boolean;
begin
  Result := not FileExists(ExpandConstant('{localappdata}\Programs\Ollama\ollama.exe'));
end;

// dontcopy files aren't extracted automatically — pull it into {tmp} during
// the main install step, before [Run] gets to it in ssPostInstall, and only
// when actually needed (skips a pointless 1.3GB extraction on a machine
// that already has Ollama, e.g. a Groundwork update).
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if (CurStep = ssInstall) and NeedsOllamaInstall() then begin
    ExtractTemporaryFile('OllamaSetup.exe');
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  // Guard against UninstallSilent(): an unattended/scripted uninstall must
  // never block on a MsgBox waiting for a click that will never come.
  if (CurUninstallStep = usUninstall) and not UninstallSilent() then begin
    MsgBox(
      'Groundwork will be uninstalled.' + #13#10 + #13#10 +
      'Your financial data will NOT be deleted.' + #13#10 +
      'It stays safe at:' + #13#10 +
      ExpandConstant('{localappdata}') + '\Groundwork\' + #13#10 + #13#10 +
      'You can back it up or delete it manually.',
      mbInformation, MB_OK
    );
  end;
end;

function InitializeSetup(): Boolean;
var
  WebView2Version: String;
  ResultCode: Integer;
begin
  Result := True;
  // Guard against WizardSilent(): a silent/unattended install must never
  // block on a MsgBox waiting for a click that will never come — skip the
  // prompt entirely and just continue, same as an interactive user clicking No.
  if WizardSilent() then exit;
  if not RegQueryStringValue(
    HKLM,
    'SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}',
    'pv',
    WebView2Version
  ) then begin
    if MsgBox(
      'Groundwork requires the Microsoft Edge WebView2 Runtime.' + #13#10 +
      'It does not appear to be installed on this computer.' + #13#10 + #13#10 +
      'Click Yes to download it now (free, ~2MB),' + #13#10 +
      'or No to continue anyway.',
      mbConfirmation, MB_YESNO
    ) = IDYES then begin
      ShellExec('open',
        'https://go.microsoft.com/fwlink/p/?LinkId=2124703',
        '', '', SW_SHOWNORMAL, ewNoWait, ResultCode
      );
      Result := False;
    end;
  end;
end;
