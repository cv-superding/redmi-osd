Option Explicit
Dim fso, shell, base, pythonw, main
Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")

base = fso.GetParentFolderName(WScript.ScriptFullName)
pythonw = base & "\.venv\Scripts\pythonw.exe"
main = base & "\main.pyw"

If Not fso.FileExists(pythonw) Then
    MsgBox "Runtime not found: " & pythonw & vbCrLf & "Rebuild .venv first (see README).", 48, "Redmi OSD"
    WScript.Quit 1
End If
If Not fso.FileExists(main) Then
    MsgBox "Main script not found: " & main, 48, "Redmi OSD"
    WScript.Quit 1
End If

shell.CurrentDirectory = base
shell.Run """" & pythonw & """ """ & main & """", 0, False
