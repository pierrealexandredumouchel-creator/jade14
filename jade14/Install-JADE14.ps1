$pythonPath = (where.exe python)[0]
$botPath = "E:\Kracken2\tools\python\jade14"

sc.exe delete JADE14

sc.exe create JADE14 binPath= "\"$pythonPath\" $botPath\jade14.py" start= auto

Start-Service JADE14
