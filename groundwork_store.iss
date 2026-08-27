; Groundwork — Inno Setup installer script (STORE / Path 2 variant)
; ---------------------------------------------------------------------------
; Purpose: Microsoft Store certification (10.2.9.2) requires a Win32 installer
; that installs SILENTLY and completes promptly. groundwork.iss / _offline.iss
; RUN OllamaSetup.exe during install (a 1.4GB nested installer, waituntil-
; terminated) — which risks a cert timeout on a fresh machine.
;
; This variant runs NOTHING during install. It places the Ollama runtime AND
; the phi3.5 model as plain FILE COPIES — the same "just files on disk" trick
; groundwork_offline.iss already uses for the model — so the whole install is
; a fast, deterministic copy that certifies silently. Groundwork then starts
; Ollama itself on launch (see _ensure_ollama_running in launch.py), since the
; file copy does not configure Ollama's usual autostart.
;
; Produces: Groundwork_Setup_Store.exe
;
; PREREQUISITE staging (one-time, before building):
;   Copy a full Ollama runtime into  C:\Groundwork\vendor\ollama_runtime\
;   (i.e. the contents of  %LOCALAPPDATA%\Programs\Ollama\  from a machine
;   that has Ollama installed: ollama.exe, "ollama app.exe", lib\, app.ico).
;   The phi3.5 model is already staged at C:\Groundwork\vendor\phi3.5_model\.
;
; NOTE: NOT YET VERIFIED on a clean machine. Portable Ollama (runtime copied
; rather than installed) + app-started `ollama serve` must be tested on a box
; with no prior Ollama before submitting.
; ---------------------------------------------------------------------------

#define AppName "Groundwork"
#define AppVersion "1.1.0"
#define AppPublisher "Groundwork"
#define AppURL "https://groundworkfinance.app"
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
LicenseFile=C:\Groundwork\EULA.txt
OutputDir=C:\Groundwork\installer_output
OutputBaseFilename=Groundwork_Setup_Store
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
; The app itself.
Source: "C:\Groundwork\dist\Groundwork\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; Ollama RUNTIME as plain files (no nested installer). Copied to Ollama's fixed
; per-user location so the app (and NeedsOllamaInstall) find it exactly where an
; installed Ollama would be. Skipped when Ollama is already present.
Source: "C:\Groundwork\vendor\ollama_runtime\*"; DestDir: "{localappdata}\Programs\Ollama"; Flags: onlyifdoesntexist recursesubdirs createallsubdirs; Check: NeedsOllamaInstall

; phi3.5 model, written straight into Ollama's content-addressed store — same
; approach as groundwork_offline.iss. Ollama does not need to be running for this.
Source: "C:\Groundwork\vendor\phi3.5_model\blobs\*"; DestDir: "{%USERPROFILE}\.ollama\models\blobs"; Flags: onlyifdoesntexist; Check: NeedsModelInstall
Source: "C:\Groundwork\vendor\phi3.5_model\manifests\registry.ollama.ai\library\phi3.5\latest"; DestDir: "{%USERPROFILE}\.ollama\models\manifests\registry.ollama.ai\library\phi3.5"; Flags: onlyifdoesntexist; Check: NeedsModelInstall

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
; NOTHING is run during install (that is the whole point of this variant).
; Only the post-install app launch, which is skipped for silent/Store installs.
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Code]
// Skip the runtime copy if Ollama is already installed here.
function NeedsOllamaInstall(): Boolean;
begin
  Result := not FileExists(ExpandConstant('{localappdata}\Programs\Ollama\ollama.exe'));
end;

// Skip the ~2.2GB model copy if the manifest (Ollama's presence marker) exists.
function NeedsModelInstall(): Boolean;
begin
  Result := not FileExists(ExpandConstant('{%USERPROFILE}\.ollama\models\manifests\registry.ollama.ai\library\phi3.5\latest'));
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  // Guard against UninstallSilent(): unattended uninstall must never block on a MsgBox.
  if (CurUninstallStep = usUninstall) and not UninstallSilent() then begin
    MsgBox(
      'Groundwork will be uninstalled.' + #13#10 + #13#10 +
      'Your financial data will NOT be deleted.' + #13#10 +
      'It stays safe at:' + #13#10 +
      ExpandConstant('{localappdata}') + '\Groundwork\' + #13#10 + #13#10 +
      'The local AI runtime and model were also left in place — delete' + #13#10 +
      '~\.ollama\ and %LOCALAPPDATA%\Programs\Ollama\ manually to reclaim space.',
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
  // Silent/Store installs must never block on a MsgBox — skip the prompt.
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
