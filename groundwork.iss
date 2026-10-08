; Groundwork — Inno Setup installer script
; Produces a single-file installer: Groundwork_Setup.exe
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
OutputBaseFilename=Groundwork_Setup
SetupIconFile=groundwork.ico
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
Source: "dist\Groundwork\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; The local AI model (ENGINE_REPLACEMENT.md, item 31): the exact tested file, inside Groundwork's own folder,
; where core/engine.py looks for it and checks its SHA-256 before loading. No Ollama, no second program, no
; download, and nothing written outside {app}. Already compressed, so it is stored as-is.
Source: "vendor\phi3.5_model\blobs\sha256-b5374915da534cb93df39f03bd4f2cd5a0c533df0d5e21957dc9556c260be9eb"; DestDir: "{app}\models"; DestName: "phi3.5-mini-instruct-q4.gguf"; Flags: ignoreversion nocompression

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Code]
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
  // block on a MsgBox waiting for a click that will never come — skip the
  // prompt entirely and just continue, same as an interactive user clicking No.
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
