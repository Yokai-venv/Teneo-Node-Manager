Set FSO = CreateObject("Scripting.FileSystemObject")
Set WShell = CreateObject("WScript.Shell")
strPath = FSO.GetParentFolderName(WScript.ScriptFullName)

' Проверяем наличие виртуального окружения
If Not FSO.FolderExists(strPath & "\venv") Then
    WScript.Echo "Error: Virtual environment not found!" & vbCrLf & _
                 "Please run setup.bat first."
    WScript.Quit
End If

WShell.CurrentDirectory = strPath
WShell.Run "cmd /c ""venv\Scripts\activate.bat && pythonw main.py""", 0, False 