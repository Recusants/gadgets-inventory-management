' ==============================================================================
' 21 Void Technologies - Silent Background Server Launcher
' Runs run_server.bat completely hidden in the background without any CMD window.
' ==============================================================================
Dim WshShell, fso, scriptDir

Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)

WshShell.CurrentDirectory = scriptDir
WshShell.Run "cmd.exe /c run_server.bat", 0, False

Set WshShell = Nothing
Set fso = Nothing
