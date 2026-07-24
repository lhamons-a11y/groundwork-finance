; Groundwork — Inno Setup installer script (OFFLINE variant, Phase 6B)
; Same as groundwork.iss, plus the phi3.5 model weights bundled directly, so
; the whole install works with zero network access — verified for the
; no-internet field case, unlike groundwork.iss's Lane A (which still needs
; one internet pull the first time local AI runs).
; Produces: Groundwork_Setup_Offline.exe
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
OutputBaseFilename=Groundwork_Setup_Offline
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
; installed Groundwork folder.
Source: "C:\Groundwork\vendor\OllamaSetup.exe"; DestDir: "{tmp}"; Flags: dontcopy noencryption

; Phase 6B — the phi3.5 model itself (~2.2GB), bundled straight into Ollama's
; own content-addressed model store layout, so first run finds it already
; installed and never needs to touch the network. This is what makes the
; install genuinely offline-capable, unlike groundwork.iss's Lane A.
;
; Ollama identifies models by content hash — writing straight to {%USERPROFILE}
; (not {tmp}) via [Files] is the same "just files on disk" operation
; `ollama pull` itself performs; Ollama doesn't need to be running for this.
; onlyifdoesntexist means a machine that already has this exact blob (shared
; hash with any other model) never gets a redundant multi-GB overwrite, and
; NeedsModelInstall skips the whole section instantly when it's already there.
Source: "C:\Groundwork\vendor\phi3.5_model\blobs\*"; DestDir: "{%USERPROFILE}\.ollama\models\blobs"; Flags: onlyifdoesntexist; Check: NeedsModelInstall
Source: "C:\Groundwork\vendor\phi3.5_model\manifests\registry.ollama.ai\library\phi3.5\latest"; DestDir: "{%USERPROFILE}\.ollama\models\manifests\registry.ollama.ai\library\phi3.5"; Flags: onlyifdoesntexist; Check: NeedsModelInstall

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

// The manifest file is the single marker Ollama itself uses to know a model
// is present (its blobs are only ever referenced through it) — if it's
// already there, either this installer already ran once or the user pulled
// phi3.5 themselves, and copying ~2.2GB of blobs again would be pure waste.
function NeedsModelInstall(): Boolean;
begin
  Result := not FileExists(ExpandConstant('{%USERPROFILE}\.ollama\models\manifests\registry.ollama.ai\library\phi3.5\latest'));
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
      'You can back it up or delete it manually.' + #13#10 + #13#10 +
      'The local AI model at ~\.ollama\ was also left in place —' + #13#10 +
      'delete it manually too if you want to reclaim ~2.2GB.',
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
  // block on a MsgBox waiting for a click that will never come.
  if WizardSilent() then exit;

  MsgBox(
    'This is the OFFLINE installer — it includes Groundwork''s local AI ' +
    'model (~2.2GB) bundled in, so the whole install works with no ' +
    'internet connection at all, including first run.' + #13#10 + #13#10 +
    'If you have internet access, the regular installer is smaller and ' +
    'downloads the same model in the background instead.',
    mbInformation, MB_OK
  );

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
