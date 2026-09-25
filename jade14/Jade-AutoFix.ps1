# ============================================================
# #  Jade‑AutoFix.ps1 — alxd 2026
# #  Répare le dashboard Jade14 sur le VPS
# # ============================================================
#
# $log = "/opt/jade14/logs/autofix.log"
# function Log($msg) {
#     $timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
#         Add-Content -Path $log -Value "$timestamp  $msg"
#             Write-Host $msg
#             }
#
#             Log "=== DÉBUT DU SCRIPT JADE‑AUTOFIX ==="
#
#             # ------------------------------------------------------------
#             # 1. Vérification NGINX
#             # ------------------------------------------------------------
#             Log "=== Vérification Nginx ==="
#             $nginxPath = "/usr/sbin/nginx"
#
#             if (-not (Test-Path $nginxPath)) {
#                 Log "ERREUR: nginx introuvable."
#                 } else {
#                     $test = & $nginxPath -t 2>&1
#                         if ($test -match "successful") {
#                                 Log "Nginx configuration OK."
#                                     } else {
#                                             Log "Nginx configuration cassée: $test"
#                                                     Log "Redémarrage forcé..."
#                                                             systemctl restart nginx
#                                                                 }
#
#                                                                     Start-Sleep -Seconds 2
#                                                                         if ((Get-Process nginx -ErrorAction SilentlyContinue)) {
#                                                                                 Log "Nginx actif."
#                                                                                     } else {
#                                                                                             Log "ERREUR: Nginx ne démarre pas."
#                                                                                                 }
#                                                                                                 }
#
#                                                                                                 # ------------------------------------------------------------
#                                                                                                 # 2. Vérification Cloudflared
#                                                                                                 # ------------------------------------------------------------
#                                                                                                 Log "=== Vérification Cloudflared ==="
#                                                                                                 $cf = Get-Process cloudflared -ErrorAction SilentlyContinue
#                                                                                                 if ($cf) {
#                                                                                                     Log "Cloudflared actif."
#                                                                                                     } else {
#                                                                                                         Log "Cloudflared inactif — redémarrage..."
#                                                                                                             systemctl restart cloudflared
#                                                                                                                 Start-Sleep -Seconds 3
#                                                                                                                     if (Get-Process cloudflared -ErrorAction SilentlyContinue) {
#                                                                                                                             Log "Cloudflared démarré."
#                                                                                                                                 } else {
#                                                                                                                                         Log "ERREUR: Cloudflared ne démarre pas."
#                                                                                                                                             }
#                                                                                                                                             }
#
#                                                                                                                                             # ------------------------------------------------------------
#                                                                                                                                             # 3. Vérification du Dashboard Jade14
#                                                                                                                                             # ------------------------------------------------------------
#                                                                                                                                             Log "=== Vérification du Dashboard Jade14 ==="
#                                                                                                                                             try {
#                                                                                                                                                 $api = Invoke-WebRequest -Uri "http://127.0.0.1:5000/api/jade14/xrdp" -UseBasicParsing -TimeoutSec 3
#                                                                                                                                                     Log "Dashboard Jade14 répond: $($api.StatusCode)"
#                                                                                                                                                     } catch {
#                                                                                                                                                         Log "ERREUR: Dashboard Jade14 ne répond pas — redémarrage du service."
#                                                                                                                                                             systemctl restart jade14
#                                                                                                                                                             }
#
#                                                                                                                                                             # ------------------------------------------------------------
#                                                                                                                                                             # FIN
#                                                                                                                                                             # ------------------------------------------------------------
#                                                                                                                                                             Log "=== FIN DU SCRIPT JADE‑AUTOFIX ==="
#
