' ============================================================
' Clarity POS - Silent Background Print Server Runner
' Starts ClarityPrintServer.exe invisibly without a CMD window.
' Place a shortcut to this file in Windows Startup (shell:startup)
' ============================================================
Dim WshShell, FSO, scriptDir, command
Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")
scriptDir = FSO.GetParentFolderName(WScript.ScriptFullName)
command = """" & scriptDir & "\ClarityPrintServer.exe"""
WshShell.Run command, 0, False
