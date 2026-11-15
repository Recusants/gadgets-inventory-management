' ============================================================
' Gadget Store System - Silent Background Docker Runner
' Launches Docker Desktop completely hidden/minimized on Windows login
' without opening the main dashboard window on screen.
' ============================================================
Dim WshShell, FSO, dockerPath
Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")

dockerPath = "C:\Program Files\Docker\Docker\Docker Desktop.exe"

If FSO.FileExists(dockerPath) Then
    ' Run minimized (window style 7 = Minimized without taking focus)
    WshShell.Run """" & dockerPath & """ --minimize", 7, False
End If
