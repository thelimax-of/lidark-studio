' Para o motor do Lidark (supervisor + servidor). Produções em andamento são interrompidas.
Option Explicit
Dim wmi, procs, p, n, resp
resp = MsgBox("Parar o Lidark agora?" & vbCrLf & "Vídeos sendo produzidos serão interrompidos e retomados quando você abrir de novo.", 36, "Parar Lidark")
If resp <> 6 Then WScript.Quit
Set wmi = GetObject("winmgmts:\.\root\cimv2")
n = 0
Set procs = wmi.ExecQuery("SELECT * FROM Win32_Process WHERE CommandLine LIKE '%lidark.supervisor%' OR CommandLine LIKE '%uvicorn%lidark%' OR CommandLine LIKE '%lidark_app.py%'")
For Each p In procs
  p.Terminate
  n = n + 1
Next
MsgBox "Lidark parado (" & n & " processo(s) encerrado(s)).", 64, "Parar Lidark"
