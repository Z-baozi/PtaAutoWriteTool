[Setup]
AppId={{E6B16C64-4CF5-4F04-B425-C9CE6B3A7336}
AppName=PTA 自动代码写入工具
AppVersion=4.2
AppPublisher=Z-baozi
AppPublisherURL=mailto:scholartime@qq.com
AppSupportURL=mailto:scholartime@qq.com
DefaultDirName={autopf}\PTAAutoType
DefaultGroupName=PTA 自动代码写入工具
DisableProgramGroupPage=yes
OutputDir=installer_dist
OutputBaseFilename=PTA自动代码写入工具-安装包-v4.2
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\PTAAutoType.exe
SetupIconFile=favicon.ico

[Languages]
Name: "chinesesimplified"; MessagesFile: "ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加任务:"; Flags: unchecked

[Files]
Source: "dist\PTAAutoType\PTAAutoType.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\PTAAutoType\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\PTA 自动代码写入工具"; Filename: "{app}\PTAAutoType.exe"; IconFilename: "{app}\PTAAutoType.exe"
Name: "{autodesktop}\PTA 自动代码写入工具"; Filename: "{app}\PTAAutoType.exe"; Tasks: desktopicon; IconFilename: "{app}\PTAAutoType.exe"

[Run]
Filename: "{app}\PTAAutoType.exe"; Description: "启动 PTA 自动代码写入工具"; Flags: nowait postinstall skipifsilent
