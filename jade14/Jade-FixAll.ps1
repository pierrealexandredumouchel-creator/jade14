# ============================================================
# #  Jade-FixAll.ps1 — alxd 2026
# #  Fusion AutoFix + Gallery + Monitor
# # ============================================================
#
# $root = "/opt/jade14"
# $log = "$root/logs/fixall.log"
# $assets = "$root/html/assets/famille"
# $galerie = "$root/html/galerie"
# $uploads = "$root/uploads"
#
# function Log($msg) {
#     $timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
#         Add-Content -Path $log -Value "$timestamp  $msg"
#         }
#
#         # Vérification Nginx
#         if (Get-Process nginx -ErrorAction SilentlyContinue) {
#             Log "Nginx actif."
#             } else {
#                 Log "Nginx inactif — redémarrage..."
#                     systemctl restart nginx
#                     }
#
#                     # Vérification Cloudflared
#                     if (Get-Process cloudflared -ErrorAction SilentlyContinue) {
#                         Log "Cloudflared actif."
#                         } else {
#                             Log "Cloudflared inactif — redémarrage..."
#                                 systemctl restart cloudflared
#                                 }
#
#                                 # Vérification Jade14 API
#                                 try {
#                                     $api = Invoke-WebRequest -Uri "http://127.0.0.1:5000/api/jade14/xrdp" -UseBasicParsing -TimeoutSec 3
#                                         Log "Jade14 API répond: $($api.StatusCode)"
#                                         } catch {
#                                             Log "Jade14 API ne répond pas — redémarrage..."
#                                                 systemctl restart jade14
#                                                 }
#
#                                                 # Galerie auto-update
#                                                 New-Item -ItemType Directory -Force -Path $assets | Out-Null
#                                                 New-Item -ItemType Directory -Force -Path $galerie | Out-Null
#                                                 New-Item -ItemType Directory -Force -Path $uploads | Out-Null
#
#                                                 $images = Get-ChildItem $uploads -Include *.jpg,*.jpeg,*.png -ErrorAction SilentlyContinue
#                                                 if ($images.Count -gt 0) {
#                                                     Log "Nouvelles images détectées : $($images.Count)"
#                                                         foreach ($img in $images) {
#                                                                 Copy-Item $img.FullName -Destination $assets -Force
#                                                                         Remove-Item $img.FullName -Force
#                                                                             }
#                                                                                 @"
#                                                                                 <!DOCTYPE html>
#                                                                                 <html lang='fr'>
#                                                                                 <head>
#                                                                                 <meta charset='UTF-8'>
#                                                                                 <title>Souvenirs du Royaume</title>
#                                                                                 <link rel='stylesheet' href='../assets/style-galerie.css'>
#                                                                                 </head>
#                                                                                 <body>
#                                                                                 <h1>Souvenirs du Royaume</h1>
#                                                                                 <div class='galerie'>
#                                                                                 "@ | Set-Content "$galerie/index.html"
#                                                                                     Get-ChildItem $assets -Include *.jpg,*.jpeg,*.png | ForEach-Object {
#                                                                                             Add-Content "$galerie/index.html" "<img src='../assets/famille/$($_.Name)' alt='Souvenir du Royaume'>"
#                                                                                                 }
#                                                                                                     Add-Content "$galerie/index.html" "</div></body></html>"
#                                                                                                         Log "Galerie régénérée."
#                                                                                                         }
#
#                                                                                                         Log "Cycle terminé."
#
