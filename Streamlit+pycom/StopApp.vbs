Set objShell = CreateObject("WScript.Shell")
objShell.Run "cmd /c for /f ""tokens=5"" %a in ('netstat -aon ^| findstr :8501') do taskkill /F /PID %a", 0, True