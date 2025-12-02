; ==============================================
; Instalador Task Reminder
; Autor: MMaffi
; ==============================================

[Setup]
AppName=Task Reminder
AppVersion=2025.12.02.0914
DefaultDirName=C:\Task Reminder
DefaultGroupName=Task Reminder
OutputDir=.
OutputBaseFilename=TaskReminder_Installer
Compression=lzma
SolidCompression=yes
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64
WizardStyle=modern
SetupIconFile=images\icon.ico

[Languages]
Name: "portuguese"; MessagesFile: "compiler:Languages\Portuguese.isl"

[Files]
Source: "dist\TaskReminder.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "images\*"; DestDir: "{app}\images"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Atalho no menu iniciar
Name: "{group}\Task Reminder"; Filename: "{app}\TaskReminder.exe"; WorkingDir: "{app}"; IconFilename: "{app}\images\icon.ico"
; Atalho na Área de Trabalho (opcional)
Name: "{userdesktop}\Task Reminder"; Filename: "{app}\TaskReminder.exe"; WorkingDir: "{app}"; IconFilename: "{app}\images\icon.ico"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na Área de Trabalho"; GroupDescription: "Opções adicionais"; Flags: unchecked

[Run]
Filename: "{app}\TaskReminder.exe"; Description: "Executar Task Reminder"; Flags: nowait postinstall skipifsilent