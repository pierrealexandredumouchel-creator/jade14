# ============================================================
#  Jade-Security-PLUS.ps1 — alxd 2026
#  Sécurité avancée du Royaume Jade14
# ============================================================

$log = "/opt/jade14/logs/security-plus.log"
$banlist = "/opt/jade14/logs/banned-ips.txt"

function Log($msg) {
    $timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    Add-Content -Path $log -Value "$timestamp  $msg"
}

Log "=== Cycle Jade-Security-PLUS ==="

# ------------------------------------------------------------
# 1. Vérification des services critiques
# ------------------------------------------------------------
$services = @("nginx", "cloudflared", "jade14")
foreach ($svc in $services) {
    $status = systemctl is-active $svc
    if ($status -ne "active") {
        Log "Service $svc INACTIF — redémarrage..."
        systemctl restart $svc
    } else {
        Log "Service $svc actif."
    }
}

# ------------------------------------------------------------
# 2. Vérification des ports ouverts
# ------------------------------------------------------------
$ports = @(22, 80, 443, 5000)
foreach ($p in $ports) {
    $check = ss -tuln | Select-String ":$p"
    if ($check) {
        Log "Port $p ouvert."
    } else {
        Log "Port $p FERMÉ — possible problème."
    }
}

# ------------------------------------------------------------
# 3. Audit Nginx (erreurs, attaques)
# ------------------------------------------------------------
$nginxErrors = Select-String -Path /var/log/nginx/error.log -Pattern "error|crit|alert|emerg"
if ($nginxErrors) {
    Log "Erreurs Nginx détectées:"
    Log $nginxErrors
}

# ------------------------------------------------------------
# 4. Audit Cloudflare Tunnel
# ------------------------------------------------------------
try {
    $cf = Invoke-WebRequest -Uri "https://alxd.net" -UseBasicParsing -TimeoutSec 3
    Log "Cloudflare Tunnel OK — HTTP $($cf.StatusCode)"
} catch {
    Log "Cloudflare Tunnel ERREUR — redémarrage cloudflared"
    systemctl restart cloudflared
}

# ------------------------------------------------------------
# 5. Audit API Jade14
# ------------------------------------------------------------
try {
    $api = Invoke-WebRequest -Uri "https://jade.alxd.net/api/jade14/xrdp" -UseBasicParsing -TimeoutSec 3
    Log "API Jade14 OK — HTTP $($api.StatusCode)"
} catch {
    Log "API Jade14 ne répond pas — redémarrage jade14"
    systemctl restart jade14
}

# ------------------------------------------------------------
# 6. Détection d’intrusion (fail2ban Jade Edition)
# ------------------------------------------------------------
$accessLog = "/var/log/nginx/access.log"
$badIPs = Select-String -Path $accessLog -Pattern "403|404|401|invalid|malformed" | ForEach-Object {
    ($_ -split " ")[0]
}

foreach ($ip in $badIPs) {
    if ($ip -and ($ip -notin (Get-Content $banlist))) {
        Log "Intrusion détectée — IP bannie : $ip"
        Add-Content -Path $banlist -Value $ip
        sudo ufw deny from $ip
    }
}

# ------------------------------------------------------------
# 7. Vérification SHA256 des fichiers Jade14
# ------------------------------------------------------------
$files = @(
    "/opt/jade14/jade14.py",
    "/opt/jade14/admin.py",
    "/opt/jade14/api",
    "/opt/jade14/rpg"
)

foreach ($f in $files) {
    if (Test-Path $f) {
        $hash = (Get-FileHash $f -Algorithm SHA256).Hash
        Log "SHA256 $f : $hash"
    } else {
        Log "Fichier manquant : $f"
    }
}

Log "=== Fin du cycle Jade-Security-PLUS ==="
