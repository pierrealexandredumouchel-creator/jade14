import asyncio
import re
import time
from collections import deque
from dataclasses import dataclass

from core.ollama_client import ollama_client
from core.personas import load_persona, normalize_bot


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
        lowered = text.casefold()

        # Parle à quelqu'un d'autre (« bob: ... ») : on se tait.
        if self.talking_to_other(target, text, {bot_name, normalize_bot(bot_name)}):
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
            f"Message de {nick} auquel tu réponds maintenant (c'est LUI ta question) :\n"
            f"{nick}: {text}\n\n"
            f"Les lignes de « {bot_name} » sont tes propres réponses précédentes.\n"
            f"Avant de répondre, comprends ce que {nick} veut dire en tenant compte "
            "de la discussion, même avec des fautes de frappe ou du joual. "
            "Le canal est plein de blagues, d'ironie et de niaisage entre chums : "
            "si c'est une blague, embarque dans le jeu avec ton propre style au lieu "
            "de la prendre au pied de la lettre. Garde toujours ta personnalité. "
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

    def remember_reply(self, bot_name, nick, target, reply, bot_nick=None):
        self.activate(bot_name, target, nick)
        self.observe(target, bot_nick or normalize_bot(bot_name), reply)

    async def ask(self, bot_name, nick, target, message, bot_nick=None):
        if self.is_bot(nick):
            return None

        normalized = normalize_bot(bot_name)
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
        reply = re.sub(r"^\s*(" + speaker + r"\w*|" + re.escape(str(nick)) + r")\s*:\s*", "", reply, flags=re.IGNORECASE)
        # « Alxd_sa_csst ! ... » / « Ikce, ... » : le pseudo est déjà mis devant par le bot.
        reply = re.sub(r"^\s*@?" + re.escape(str(nick)) + r"\s*[!,.:]+\s*", "", reply, flags=re.IGNORECASE)
        reply = " ".join(reply.split())[:1400].strip()

        # Tic du modèle : « Ben oui, ... », « Ben non ! ... », « Ben quoi ... ».
        stripped = re.sub(r"^\s*ben\b(?:\s+(?:oui|non|quoi|là|voyons))?\s*[,!.…]*\s*", "", reply, flags=re.IGNORECASE)
        if stripped and stripped != reply:
            reply = stripped[0].upper() + stripped[1:]

        if reply:
            self.remember_reply(normalized, nick, target, reply, bot_nick=bot_nick)

        return reply or None


ghost_brain = GhostBrain()
