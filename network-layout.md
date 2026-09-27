# 🌐 PIOTR NETWORK LAYOUT

## Serveur

Hostname: piotr

IPv4:
67.215.13.169

IPv6 Tunnel (/64):
2001:470:b2af::/64

---

# ⚠️ RÈGLE ABSOLUE

NE JAMAIS UTILISER L'IPv4 POUR IRC.

Tous les bots IRC doivent utiliser IPv6.

L'adresse IPv4 du serveur est réservée aux services système,
web, administration et compatibilité.

---

# Assignation IPv6 des bots

| Bot | IPv6 |
|------|------|
| Azriel | 2001:470:b2af::1 |
| jade14 | 2001:470:b2af::2 |
| christine24 | 2001:470:b2af::3 |
| Tanya24 | 2001:470:b2af::4 |
| Réservé | 2001:470:b2af::5 |
| Anya | 2001:470:b2af::6 |

---

# Réseau IRC

Undernet:
irc6.undernet.org

Connexion requise:
IPv6

Authentification:
X / cloaks lorsque applicable

---

# Développement Python

Méthodes recommandées

```python
sock = socket.create_connection((SERVER, PORT))
```

ou

```python
reader, writer = await asyncio.open_connection(
    SERVER,
    PORT
)
```

Méthodes à éviter

```python
sock = socket.socket()
sock.connect((SERVER, PORT))
```

---

# Déploiement sécurisé

Avant chaque déploiement :

1. git pull --rebase
2. Vérifier les conflits
3. Vérifier la compatibilité IPv6
4. git push
5. rsync vers Piotr
6. systemctl restart <bot>

Exemple :

```bash
rsync -avz \
  --exclude='venv' \
  --exclude='.git' \
  --exclude='__pycache__' \
  ~/anya/ \
  piotr:/home/alxd/anya/
```

Puis :

```bash
ssh piotr "systemctl restart anya"
```

---

# Historique

Septembre 2026

Migration complète des bots IRC vers IPv6.

Cause:
- Bots connectés via IPv4
- Correctifs réseau appliqués sur Piotr
- Correctifs Python pour compatibilité IPv4/IPv6
- Standardisation des adresses IPv6 par bot

Objectif:
Ne jamais revenir à une connexion IRC IPv4.
