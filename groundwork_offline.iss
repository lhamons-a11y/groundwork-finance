; Groundwork — Inno Setup installer script (OFFLINE variant, Phase 6B)
; Since item 31 (ENGINE_REPLACEMENT.md) every installer ships the model inside Groundwork, so
; groundwork.iss is already fully offline. This variant is kept as its own output name
; for the release scripts that build it; its contents now match groundwork.iss.
; Produces: Groundwork_Setup_Offline.exe
; Tested with Inno Setup 6.x

#define AppName "Groundwork"
#define AppVersion "1.1.1"
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
LicenseFile=EULA.txt
OutputDir=installer_output
OutputBaseFilename=Groundwork_Setup_Offline
SetupIconFile=groundwork.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
; Groundwork open while installing is closed first, so its files can be replaced
CloseApplications=yes
RestartApplications=no
MinVersion=10.0.17763

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\Groundwork\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; The local AI model (ENGINE_REPLACEMENT.md, item 31): the exact tested file, inside Groundwork's own folder,
; where core/engine.py looks for it and checks its SHA-256 before loading. No Ollama, no second program, no
; download, and nothing written outside {app}. Already compressed, so it is stored as-is.
Source: "vendor\phi3.5_model\blobs\sha256-b5374915da534cb93df39f03bd4f2cd5a0c533df0d5e21957dc9556c260be9eb"; DestDir: "{app}\models"; DestName: "phi3.5-mini-instruct-q4.gguf"; Flags: ignoreversion nocompression
; Item 113: the voice model, when staged (scripts/fetch_whisper_model.py); without it voice reports unavailable
Source: "vendor\whisper\ggml-base.en.bin"; DestDir: "{app}\models"; Flags: ignoreversion nocompression skipifsourcedoesntexist
; Groundwork's own voice (core/speak.py), when staged (scripts/fetch_kokoro_model.py); without it read aloud uses the computer's voices
Source: "vendor\kokoro\kokoro-v1.0.int8.onnx"; DestDir: "{app}\models"; Flags: ignoreversion nocompression skipifsourcedoesntexist
Source: "vendor\kokoro\voices-v1.0.bin"; DestDir: "{app}\models"; Flags: ignoreversion nocompression skipifsourcedoesntexist
; Whose voice it is (core/voiceprint.py, item 116 V19), when staged (scripts/fetch_voiceprint_model.py)
Source: "vendor\voiceprint\voxceleb_resnet34_LM.onnx"; DestDir: "{app}\models"; Flags: ignoreversion nocompression skipifsourcedoesntexist

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Code]
// Rob 2026-10-31: "the installer should check for previous versions and uninstall them for the user and then install
// 2.0". An earlier Groundwork (this same AppId, any version) is removed silently before the new files go in. Its
// uninstaller removes only the program folder - your records in %LOCALAPPDATA%\Groundwork are never touched - and
// skips its own message box when run silently.
const
  UninstKey = 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{A3F8C2D1-5B4E-4F9A-8C6D-2E7F1A0B3C5D}_is1';

function EarlierGroundwork(var Version: String): String;
var
  S: String;
begin
  Result := '';
  Version := '';
  if RegQueryStringValue(HKCU, UninstKey, 'UninstallString', S) or
     RegQueryStringValue(HKLM, UninstKey, 'UninstallString', S) or
     (IsWin64 and RegQueryStringValue(HKLM64, UninstKey, 'UninstallString', S)) then begin
    Result := RemoveQuotes(S);
    if not (RegQueryStringValue(HKCU, UninstKey, 'DisplayVersion', Version) or
            RegQueryStringValue(HKLM, UninstKey, 'DisplayVersion', Version) or
            (IsWin64 and RegQueryStringValue(HKLM64, UninstKey, 'DisplayVersion', Version))) then
      Version := 'an earlier version';
  end;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  Uninst, Version: String;
  Code: Integer;
begin
  Result := '';
  Uninst := EarlierGroundwork(Version);
  if (Uninst = '') or not FileExists(Uninst) then exit;
  WizardForm.PreparingLabel.Caption := 'Removing Groundwork ' + Version + ' first. Your records are not touched.';
  if not Exec(Uninst, '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART', '', SW_HIDE, ewWaitUntilTerminated, Code) or (Code <> 0) then
    Result := 'Groundwork ' + Version + ' could not be removed first (code ' + IntToStr(Code) + '). ' +
              'Close Groundwork if it is open, then run this installer again. Your records are not touched.';
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

// Rob, 2026-10-02: warn, don't block. Groundwork holds financial data, so it suggests an operating system that
// still receives security updates - Windows 11 today (Windows 10's consumer updates end 13 October 2026). It still
// installs on Windows 10: on an older computer that stays offline, that's perfectly fine. Shown once, interactive
// installs only.
procedure WarnIfWindowsUnsupported();
var
  V: TWindowsVersion;
begin
  GetWindowsVersionEx(V);
  if (V.Major = 10) and (V.Build < 22000) then
    MsgBox(
      'This computer is running Windows 10, which no longer receives security updates from Microsoft.' + #13#10 + #13#10 +
      'Because Groundwork holds your financial data, we suggest running it on a version of Windows that still' + #13#10 +
      'gets security updates (Windows 11).' + #13#10 + #13#10 +
      'You can still install and use Groundwork here. On an older computer that stays offline, that''s perfectly fine.',
      mbInformation, MB_OK);
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
  WarnIfWindowsUnsupported();

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
