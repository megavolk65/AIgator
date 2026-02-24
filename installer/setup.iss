; Inno Setup Script for AI Helper
; Build: 1) pyinstaller build.spec  2) Compile this with Inno Setup

#define MyAppName "AI Helper"
#define MyAppVersion "0.9.6"
#define MyAppPublisher "megavolk65"
#define MyAppURL "https://github.com/megavolk65/ai-helper"
#define MyAppExeName "AI Helper.exe"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=..\dist
OutputBaseFilename=AI_Helper_Setup_{#MyAppVersion}
SetupIconFile=..\assets\icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
DisableProgramGroupPage=yes

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "autostart"; Description: "Запускать при старте Windows / Start with Windows"; GroupDescription: "Дополнительно / Additional:"; Flags: unchecked

[Files]
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\settings.default.json"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
; Автозапуск (если выбран)
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "{#MyAppName}"; ValueData: """{app}\{#MyAppExeName}"""; Flags: uninsdeletevalue; Tasks: autostart

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Удаляем пользовательские файлы при удалении
Type: files; Name: "{app}\settings.json"
Type: dirifempty; Name: "{app}"

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
var
  SettingsFile: string;
  SettingsContent: string;
  Lang: string;
  Provider: string;
begin
  if CurStep = ssPostInstall then
  begin
    // Язык приложения = язык установщика
    if ActiveLanguage = 'russian' then
    begin
      Lang := 'ru';
      Provider := 'aitunnel';
    end
    else
    begin
      Lang := 'en';
      Provider := 'openrouter';
    end;
    
    SettingsFile := ExpandConstant('{app}\settings.json');
    
    SettingsContent := '{' + #13#10 +
      '  "language": "' + Lang + '",' + #13#10 +
      '  "api_key": "",' + #13#10 +
      '  "api_provider": "' + Provider + '",' + #13#10 +
      '  "models": []' + #13#10 +
      '}';
    
    // Только при первой установке
    if not FileExists(SettingsFile) then
      SaveStringToFile(SettingsFile, SettingsContent, False);
  end;
end;
