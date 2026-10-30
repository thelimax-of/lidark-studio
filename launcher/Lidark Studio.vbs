' Lidark Studio — liga o motor e abre o painel como aplicativo em TELA CHEIA (sem barra de título).
Option Explicit
Dim sh, fso, root, py, pyw, app, http, i, ok, edge, chrome, url
Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
root = fso.GetParentFolderName(fso.GetParentFolderName(WScript.ScriptFullName))
py = root & "\backend\.venv\Scripts\pythonw.exe"
app = root & "\launcher\lidark_app.py"
url = "http://localhost:8765"

' 1) liga o motor (o supervisor garante uma única instância e reinicia se travar)
sh.CurrentDirectory = root & "\backend"
sh.Run """" & py & """ -m lidark.supervisor", 0, False

' 2) espera o motor responder (até ~60s)
Set http = CreateObject("MSXML2.ServerXMLHTTP")
ok = False
For i = 1 To 60
  On Error Resume Next
  http.Open "GET", "http://127.0.0.1:8765/api/health", False
  http.Send
  If Err.Number = 0 Then
    If http.Status = 200 Then ok = True
  End If
  Err.Clear
  On Error GoTo 0
  If ok Then Exit For
  WScript.Sleep 1000
Next
If Not ok Then
  MsgBox "O motor do Lidark não respondeu. Veja data\logs\server.log", 48, "Lidark Studio"
  WScript.Quit
End If

' 3) abre o app nativo (pywebview/WebView2) em tela cheia total.
'    Ele mesmo cai para o Edge/Chrome se o WebView2 falhar.
If fso.FileExists(py) And fso.FileExists(app) Then
  sh.Run """" & py & """ """ & app & """ --no-wait --url " & url, 1, False
  WScript.Quit
End If

' 4) reserva: Edge/Chrome em modo app, tela cheia
edge = sh.ExpandEnvironmentStrings("%ProgramFiles(x86)%") & "\Microsoft\Edge\Application\msedge.exe"
chrome = sh.ExpandEnvironmentStrings("%ProgramFiles%") & "\Google\Chrome\Application\chrome.exe"
If fso.FileExists(edge) Then
  sh.Run """" & edge & """ --app=" & url & " --start-fullscreen", 1, False
ElseIf fso.FileExists(chrome) Then
  sh.Run """" & chrome & """ --app=" & url & " --start-fullscreen", 1, False
Else
  sh.Run url
End If
