' Roda "servidor.ps1 vigiar" sem abrir janela nenhuma (usado pela tarefa agendada ChatbotTutor-Vigia).
' Chamar o powershell.exe direto, mesmo com -WindowStyle Hidden, pisca um console e tira o foco de
' jogos em tela cheia; pelo wscript o processo já nasce oculto (estilo 0).
Dim pasta
pasta = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
CreateObject("WScript.Shell").Run "powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File """ & _
    pasta & "\servidor.ps1"" vigiar", 0, False
