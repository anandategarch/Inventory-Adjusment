Option Explicit

Dim shell, fso, folder, bat
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

folder = fso.GetParentFolderName(WScript.ScriptFullName)
bat = """" & folder & "\launch.bat" & """"

shell.Run "cmd.exe /k " & bat, 1, False

Set fso = Nothing
Set shell = Nothing
