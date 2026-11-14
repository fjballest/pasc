; Inno Setup script for the pasc Windows installer.
; Built by .github/workflows/release.yml:  iscc /DVersion=1.0 pasc.iss
; Installs for the current user only (no administrator rights needed)
; and adds the install directory to the user's PATH.

#ifndef Version
  #define Version "0.0"
#endif

[Setup]
AppName=pasc
AppVersion={#Version}
AppPublisher=pasc
DefaultDirName={localappdata}\Programs\pasc
DisableDirPage=yes
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\..\dist
OutputBaseFilename=pasc-{#Version}-windows-setup
Compression=lzma2
SolidCompression=yes
ChangesEnvironment=yes
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayName=pasc {#Version}
MinVersion=6.1

[Files]
Source: "..\..\dist\pasc\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion
Source: "..\..\README.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{userprograms}\pasc\Guía de instalación y uso de pasc"; Filename: "{app}\INSTALAR.pdf"
Name: "{userprograms}\pasc\Desinstalar pasc"; Filename: "{uninstallexe}"

[Registry]
Root: HKCU; Subkey: "Environment"; ValueType: expandsz; ValueName: "Path"; \
	ValueData: "{olddata};{app}"; Check: NeedsAddPath(ExpandConstant('{app}'))

[Code]
function NeedsAddPath(Dir: string): boolean;
var
	Path: string;
begin
	if not RegQueryStringValue(HKEY_CURRENT_USER, 'Environment', 'Path', Path) then
	begin
		Result := True;
		exit;
	end;
	Result := Pos(';' + Uppercase(Dir) + ';', ';' + Uppercase(Path) + ';') = 0;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
	Path, Dir: string;
	P: Integer;
begin
	if CurUninstallStep <> usPostUninstall then
		exit;
	if not RegQueryStringValue(HKEY_CURRENT_USER, 'Environment', 'Path', Path) then
		exit;
	Dir := ExpandConstant('{app}');
	P := Pos(';' + Uppercase(Dir), Uppercase(Path));
	if P > 0 then
	begin
		Delete(Path, P, Length(Dir) + 1);
		RegWriteExpandStringValue(HKEY_CURRENT_USER, 'Environment', 'Path', Path);
	end;
end;
