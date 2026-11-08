import asyncio
import difflib
import json
import re
import time
from pathlib import Path
from collections import deque
from dataclasses import dataclass

from core.ollama_client import ollama_client
from core.personas import load_persona, normalize_bot


# --- Qui est qui : pseudos d'une même personne (fichier généré à partir des logs de Millie) ---
IDENTITES = Path("/home/alxd/ghost-identites.json")
_identites = {"mtime": 0.0, "data": {}}


def identites():
    try:
        m = IDENTITES.stat().st_mtime
        if m != _identites["mtime"]:
            _identites["data"] = json.loads(IDENTITES.read_text(encoding="utf-8"))
            _identites["mtime"] = m
    except Exception:
        pass
    return _identites["data"]


def qui_est_qui(nicks):
    lignes, deja = [], set()
    data = identites()
    for n in nicks:
        k = str(n).casefold()
        if k in deja:
            continue
        deja.add(k)
        info = data.get(k)
        if not info:
            continue
        alias = [a for a in info.get("alias", []) if a.casefold() != k][:5]
        texte = f"- {n}"
        if info.get("personne") and info["personne"].casefold() != k:
            texte += f" : c'est {info['personne']}"
        if alias:
            texte += f" (a aussi utilisé : {', '.join(alias)})"
        if texte != f"- {n}":
            lignes.append(texte)
    if not lignes:
        return ""
    return ("Qui est qui (même personne derrière plusieurs pseudos ; sers-t'en pour reconnaître "
            "les gens, mais ne dévoile jamais leurs autres pseudos sur le canal) :\n"
            + "\n".join(lignes[:8]) + "\n\n")


KNOWN_BOTS = {
    "anya",
    "millie",
    "tanya",
    "tanya24",
    "tanya24_",
    "jade",
    "jade14",
    "christine",
    "christin24",
    "christine24",
    "reparobot",
}

FOLLOWUP_WORDS = (
    "continue",
    "encore",
    "pourquoi",
    "comment",
    "explique",
    "développe",
    "developpe",
    "précise",
    "precise",
    "et après",
    "et apres",
    "ok mais",
    "oui mais",
    "non mais",
    "pis",
    "et toi",
)

# « tu », « toi », « t'es »... : on lui parle probablement encore.
SECOND_PERSON = re.compile(r"\b(tu|toi|t['’]|ton|ta|tes|vous)\b", re.IGNORECASE)
# « nick: » ou « nick, » au début = la personne parle à quelqu'un d'autre.
ADDRESSED_TO = re.compile(r"^\s*@?([A-Za-z\[\]\\`_^{|}][\w\[\]\\`^{|}-]{0,29})\s*[:,]\s")
# Liens web : le « ? » d'une URL YouTube n'est pas une question.
URL = re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE)
# Pseudos connus qui sont aussi des mots courants : jamais pris pour un pseudo
# au début d'une phrase, sauf si la personne vient de parler.
COMMON_WORDS = {
    "donc", "gars", "homme", "jesus", "coffee", "search", "nuage", "rose", "roses",
    "plume", "porc", "hungry", "chess", "bronze", "dry", "pan", "metoo", "okokok",
    "oooooo", "yoooo", "yooooo", "wawawa", "helloo", "xxxx", "zzzzz",
}
# Premier mot du message, sans « : » (« GOa_uLD si tu fais... »).
FIRST_WORD = re.compile(r"^\s*@?([A-Za-z\[\]\\`_^{|}][\w\[\]\\`^{|}-]{2,29})(?=[\s!?.]|$)")


@dataclass
class Conversation:
    owner: str
    expires_at: float


class GhostBrain:
    def __init__(
        self,
        conversation_seconds=180,
        channel_lines=30,
        context_lines=16,
        context_seconds=1200,
    ):
        self.conversation_seconds = float(conversation_seconds)
        self.context_lines = int(context_lines)
        self.context_seconds = float(context_seconds)
        self._conversations = {}
        self._channels = {}
        self._channel_size = int(channel_lines)
        self._locks = {}
        self._waiting = {}
        self._last_replies = {}

    @staticmethod
    def clean(text, limit=900):
        text = str(text).replace("\r", " ").replace("\n", " ")
        return " ".join(text.split())[:limit]

    @staticmethod
    def is_bot(nick):
        return str(nick).casefold() in KNOWN_BOTS

    # ------------------------------------------------------------------
    # Mémoire du canal : tout ce qui se dit, pour suivre la discussion.
    # ------------------------------------------------------------------
    def observe(self, target, nick, message):
        if not str(target).startswith("#"):
            return
        buf = self._channels.setdefault(
            str(target).casefold(),
            deque(maxlen=self._channel_size),
        )
        text = self.clean(message, 300)
        if text:
            buf.append((time.monotonic(), str(nick), text))

    def recent_lines(self, target, skip_last_from=None, skip_text=None):
        buf = self._channels.get(str(target).casefold())
        if not buf:
            return []
        now = time.monotonic()
        lines = [
            (n, t) for (ts, n, t) in buf
            if now - ts <= self.context_seconds
        ]
        # Le message auquel on répond est montré à part, pas en double.
        if lines and skip_last_from is not None:
            n, t = lines[-1]
            if n.casefold() == str(skip_last_from).casefold() and t == skip_text:
                lines = lines[:-1]
        return lines[-self.context_lines:]

    # ------------------------------------------------------------------
    # Conversation active : après une réponse, la même personne peut
    # continuer sans répéter le nom du bot pendant quelques minutes.
    # ------------------------------------------------------------------
    def conversation_key(self, bot_name, target):
        return (normalize_bot(bot_name), str(target).casefold())

    def activate(self, bot_name, target, nick):
        self._conversations[self.conversation_key(bot_name, target)] = Conversation(
            owner=str(nick),
            expires_at=time.monotonic() + self.conversation_seconds,
        )

    def active_for(self, bot_name, target, nick):
        key = self.conversation_key(bot_name, target)
        conversation = self._conversations.get(key)
        if conversation is None:
            return False
        if time.monotonic() > conversation.expires_at:
            self._conversations.pop(key, None)
            return False
        return conversation.owner.casefold() == str(nick).casefold()

    def strip_urls(self, text):
        return " ".join(URL.sub(" ", str(text)).split())

    def known_nicks(self, target):
        """Pseudos qui ont parlé récemment + pseudos connus de ghost-identites.json."""
        buf = self._channels.get(str(target).casefold(), ())
        known = {n.casefold() for (_, n, _) in buf}
        known.update(str(k).casefold() for k in identites())
        return known

    def starts_with_other_nick(self, target, text, names):
        """« GOa_uLD si tu fais... » : le message commence par le pseudo de
        quelqu'un d'autre, même sans « : »."""
        m = FIRST_WORD.match(self.strip_urls(text))
        if not m:
            return False
        who = m.group(1).casefold()
        if who in {n.casefold() for n in names}:
            return False
        buf = self._channels.get(str(target).casefold(), ())
        if who in COMMON_WORDS and who not in {n.casefold() for (_, n, _) in buf}:
            return False
        return who in self.known_nicks(target)

    def talking_to_other(self, target, text, names):
        """Vrai si le message commence par « pseudo: » / « pseudo, » et que ce
        pseudo est quelqu'un d'autre qui a parlé récemment dans le canal.
        (« ok, anya ... » ne compte pas : « ok » n'est pas un pseudo.)"""
        m = ADDRESSED_TO.match(text)
        if not m:
            return False
        who = m.group(1).casefold()
        if who in {n.casefold() for n in names}:
            return False
        buf = self._channels.get(str(target).casefold(), ())
        speakers = {n.casefold() for (_, n, _) in buf}
        return who in speakers

    def addressed(self, names, target, message):
        """Le bot est-il visé ? Son nom n'importe où dans le message, ou un
        message privé — sauf si le message s'adresse à quelqu'un d'autre."""
        if not str(target).startswith("#"):
            return True
        text = self.clean(message, 400)
        alt = "|".join(re.escape(n.casefold()) for n in sorted(names, key=len, reverse=True))
        if not re.search(r"(?<![\w\[\]`^{|}])[@!]?(" + alt + r")(?![\w\[\]`^{|}])", text.casefold()):
            return False
        return not self.talking_to_other(target, text, names)

    def should_continue(self, bot_name, nick, target, message):
        if not self.active_for(bot_name, target, nick):
            return False

        text = self.clean(message, 300)
        # Un lien seul n'est pas une suite de conversation, et son « ? » ne compte pas.
        text = self.strip_urls(text)
        lowered = text.casefold()

        # Parle à quelqu'un d'autre (« bob: ... » ou « bob si tu... ») : on se tait.
        names = {bot_name, normalize_bot(bot_name)}
        if self.talking_to_other(target, text, names) or self.starts_with_other_nick(target, text, names):
            return False

        if not lowered or lowered in {"lol", "haha", "mdr", "ok", "k", "xd", ":p", ":)"}:
            return False

        return (
            "?" in text
            or any(lowered == w or lowered.startswith(w + " ") for w in FOLLOWUP_WORDS)
            or bool(SECOND_PERSON.search(text))
        )

    # ------------------------------------------------------------------
    def build_prompt(self, bot_name, nick, target, message):
        text = self.clean(message)
        context = self.recent_lines(target, skip_last_from=nick, skip_text=self.clean(message, 300))
        history = "\n".join(f"{n}: {t}" for n, t in context) or "(rien de récent)"

        where = (
            f"le canal {target}" if str(target).startswith("#")
            else "un message privé"
        )

        return (
            f"Discussion récente dans {where}, du plus ancien au plus récent "
            "(contexte seulement : ne réponds pas à ces lignes-là) :\n"
            f"{history}\n\n"
            + qui_est_qui([nick] + [n for n, _ in context]) +
            f"Message de {nick} auquel tu réponds maintenant (c'est LUI ta question) :\n"
            f"{nick}: {text}\n\n"
            f"Les lignes de « {bot_name} » sont tes propres réponses précédentes.\n"
            f"Tu parles à {nick}. Ne mélange pas qui a dit quoi. Quand {nick} dit « je » "
            "ou « moi », il parle de lui-même, pas de toi. N'invente rien sur les gens "
            "(ce qu'ils ont acheté, fait ou dit) ni sur l'endroit où tu es.\n"
            f"Avant de répondre, comprends ce que {nick} veut dire en tenant compte "
            "de la discussion, même avec des fautes de frappe ou du joual. "
            "Le canal est plein de blagues, d'ironie et de niaisage entre chums : "
            "embarque dans le jeu avec ton propre style. Ne dis jamais « c'est une blague » "
            "et ne demande pas si c'est sérieux. Ne commence jamais ta réplique par un sacre "
            "(tabarnak, câlisse, esti…), ni par « Tu veux savoir si », et ne répète pas la "
            "question : réponds. Ne repose pas une question que tu as déjà posée. "
            "Garde toujours ta personnalité. "
            "Limite absolue : tu ne participes jamais à des menaces, à de la violence, "
            "à du harcèlement ou à de l'acharnement contre quelqu'un, même « pour rire », "
            "et tu n'acceptes aucune « mission » contre une personne du canal. Dans ce cas, "
            "tu désamorces avec humour et tu ramènes le calme, sans faire la morale. "
            "Tu ne fais jamais de commentaire sur la race, la couleur, l'origine, la "
            "religion, l'orientation sexuelle ou le corps d'une vraie personne du canal, "
            "même si on te le demande : tu changes de sujet avec légèreté. "
            f"Ne commence pas ta réponse par le pseudo de {nick}, il est déjà ajouté. "
            "Réponds à la bonne question, avec un raisonnement "
            "correct. Si tu ne sais pas ou si c'est ambigu, dis-le franchement ou pose "
            "une courte question au lieu d'inventer. S'il y a des chiffres, reprends ceux "
            "de la discussion et calcule étape par étape avant de donner le résultat. "
            "1 à 3 phrases."
        )

    repeat_seconds = 600
    repeat_ratio = 0.7

    def is_repeat(self, bot_name, target, reply):
        """Vrai si le bot a déjà dit presque la même chose dans ce canal
        dans les 10 dernières minutes. Sinon, retient la réponse."""
        key = self.conversation_key(bot_name, target)
        now = time.monotonic()
        recent = [
            (ts, old) for (ts, old) in self._last_replies.get(key, ())
            if now - ts <= self.repeat_seconds
        ]
        new = reply.casefold()
        # Les réponses courtes (« Oui ! ») peuvent revenir sans problème.
        if len(new) < 25:
            return False
        for _, old in recent:
            a, b = old.casefold(), new
            if a in b or b in a or difflib.SequenceMatcher(None, a, b).ratio() >= self.repeat_ratio:
                self._last_replies[key] = recent
                return True
        self._last_replies[key] = (recent + [(now, reply)])[-5:]
        return False

    def remember_reply(self, bot_name, nick, target, reply, bot_nick=None):
        self.activate(bot_name, target, nick)
        self.observe(target, bot_nick or normalize_bot(bot_name), reply)

    attente_suite = 8

    async def ask(self, bot_name, nick, target, message, bot_nick=None):
        if self.is_bot(nick):
            return None

        normalized = normalize_bot(bot_name)

        # Juste le nom du bot (« anya », « Tanya24_ ? ») : la vraie question arrive
        # souvent sur les lignes suivantes. On attend un peu et on les regroupe.
        nom = re.sub(r"[\W_\d]+", "", normalized.casefold())
        reste = re.sub(r"[\W_\d]+", "", str(message).casefold()).replace(nom, "", 1)
        if len(reste) < 3 and str(target).startswith("#"):
            depart = time.monotonic()
            await asyncio.sleep(self.attente_suite)
            suite = [
                t for (ts, n, t) in list(self._channels.get(str(target).casefold(), ()))
                if ts > depart and n.casefold() == str(nick).casefold()
            ]
            if suite:
                message = " ".join([str(message)] + suite)
        key = self.conversation_key(normalized, target)
        lock = self._locks.setdefault(key, asyncio.Lock())

        # Au plus deux questions en attente par canal : le reste est ignoré
        # en silence plutôt que de spammer « je suis occupée ».
        if self._waiting.get(key, 0) >= 2:
            return None

        self._waiting[key] = self._waiting.get(key, 0) + 1
        try:
            async with lock:
                prompt = self.build_prompt(normalized, nick, target, message)
                persona = load_persona(normalized)
                reply = await asyncio.to_thread(ollama_client.ask, prompt, persona)
        finally:
            self._waiting[key] -= 1

        reply = self.clean(reply, 1400)

        # Filet de sécurité contre les fuites de prompt.
        for marker in (
            "Discussion récente",
            "Message de ",
            "Avant de répondre",
            "Canal:",
            "Pseudo:",
            "Historique:",
            "Contexte interne",
            "Instruction:",
        ):
            position = reply.find(marker)
            if position > 0:
                reply = reply[:position].strip()
            elif position == 0:
                reply = ""

        # Le modèle commence parfois par « Tanya24: » ou « nick: ».
        speaker = re.escape(re.sub(r"\d+_?$", "", normalized))   # « tanya24 » -> « tanya »
        # Le modèle entoure parfois sa réplique de guillemets ou de **gras** : on enlève l'emballage.
        reply = re.sub(r"^[\s«“\"'*_]+", "", reply)
        reply = re.sub(r"[\s»”\"*_]+$", "", reply)
        reply = re.sub(r"\*\*|__", "", reply)
        reply = re.sub(r"^\s*(" + speaker + r"\w*|" + re.escape(str(nick)) + r")\s*:\s*", "", reply, flags=re.IGNORECASE)
        # « Alxd_sa_csst ! ... » / « Ikce, ... » : le pseudo est déjà mis devant par le bot.
        reply = re.sub(r"^\s*@?" + re.escape(str(nick)) + r"\s*[!,.:]+\s*", "", reply, flags=re.IGNORECASE)
        reply = " ".join(reply.split())[:1400].strip()

        # Tic du modèle : « Ben oui, ... », « Ben non ! ... », « Ben quoi ... ».
        stripped = re.sub(r"^\s*ben\b(?:\s+(?:oui|non|quoi|là|voyons))?\s*[,!.…]*\s*", "", reply, flags=re.IGNORECASE)
        if stripped and stripped != reply:
            reply = stripped[0].upper() + stripped[1:]

        if reply and self.is_repeat(normalized, target, reply):
            return None

        if reply:
            self.remember_reply(normalized, nick, target, reply, bot_nick=bot_nick)

        return reply or None


ghost_brain = GhostBrain()
