# ============================================================
#  Jade-Gallery-AutoUpdate.ps1 — alxd 2026
#  Surveille /opt/jade14/uploads/ et met à jour la galerie
# ============================================================

$root = "/opt/jade14/html"
$assets = "$root/assets/famille"
$galerie = "$root/galerie"
$uploads = "/opt/jade14/uploads"
$log = "/opt/jade14/logs/gallery-autoupdate.log"

function Log($msg) {
    $timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    Add-Content -Path $log -Value "$timestamp  $msg"
}

# Création des dossiers
New-Item -ItemType Directory -Force -Path $assets | Out-Null
New-Item -ItemType Directory -Force -Path $galerie | Out-Null
New-Item -ItemType Directory -Force -Path $uploads | Out-Null

# Vérifier nouvelles images
$images = Get-ChildItem $uploads -Include *.jpg,*.jpeg,*.png -ErrorAction SilentlyContinue

if ($images.Count -gt 0) {
    Log "Nouvelles images détectées : $($images.Count)"

    foreach ($img in $images) {
        Copy-Item $img.FullName -Destination $assets -Force
        Remove-Item $img.FullName -Force
    }

    # Regénérer la galerie HTML
    @"
<!DOCTYPE html>
<html lang='fr'>
<head>
<meta charset='UTF-8'>
<title>Souvenirs du Royaume</title>
<link rel='stylesheet' href='../assets/style-galerie.css'>
</head>
<body>
<h1>Souvenirs du Royaume</h1>
<div class='galerie'>
"@ | Set-Content "$galerie/index.html"

    Get-ChildItem $assets -Include *.jpg,*.jpeg,*.png | ForEach-Object {
        Add-Content "$galerie/index.html" "<img src='../assets/famille/$($_.Name)' alt='Souvenir du Royaume'>"
    }

    Add-Content "$galerie/index.html" "</div></body></html>"

    Log "Galerie régénérée."

    # Redémarrer Nginx
    systemctl restart nginx
    Log "Nginx redémarré."
} else {
    Log "Aucune nouvelle image."
}

