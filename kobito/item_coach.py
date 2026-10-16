"""The AI companion reacting to what the player picks up.

Every pickup (a konbini snack, a gift-box prize, the mascot's favourite
food) and every state change (getting sleepy, nodding off) makes the
chosen companion say something in its own voice -- and each item also
teaches its Japanese word, reading and an example sentence, so a snack
becomes a tiny vocabulary lesson.

Two layers:
  * A local line, picked instantly from per-companion templates below.
    Always works, offline, no waiting -- this is what shows first.
  * An optional Claude-written line (same companion personality, aware of
    the character, the item and how sleepy the player is). It's requested
    on a background thread so the game never stalls; if it lands while the
    bubble is still on screen it replaces the local line, otherwise it's
    dropped. No API key, no network, or no threads (the browser build)
    simply means the local line stays.
"""

import random
import threading
from dataclasses import dataclass

SITUATIONS = ("snack", "rescue", "favorite", "rare", "life", "coins", "drowsy", "asleep")

# {item} English name, {jp} Japanese word, {pet} the player's mascot,
# {power} current power out of 10. Short: they sit in a small bubble.
VOICES = {
    "kobito": {
        "snack": ["Nice find, {pet}! {item} keeps you going.", "A little {item} -- gentle on the legs, kind to the heart."],
        "rescue": ["There you are! {item} woke you right up.", "Oh, thank goodness -- {item} came just in time."],
        "favorite": ["Your favourite, {pet}! I can see you smiling.", "{item}! That's the one you love."],
        "rare": ["Oh my -- a {item}! That's a rare treasure.", "Such a lucky find. {item}!"],
        "life": ["A whole new life... how lovely.", "Take care of that one, {pet}."],
        "coins": ["A little shower of coins -- how cheerful.", "Gifts everywhere today."],
        "drowsy": ["Your eyes are drooping, {pet}... find something with a kick.", "Careful -- only {power} power left. Something from the konbini would help."],
        "asleep": ["Zzz... oh dear. Rest a moment, then try again.", "You dozed off, {pet}. A life lost, but you're up again."],
    },
    "ushi": {
        "snack": ["There, there -- {item}. Eat up, dear.", "Mmm, {item}. Good for the road, {pet}."],
        "rescue": ["Oh my, you were fading! {item} will fix that.", "Wake up now, sweetheart -- {item} to the rescue."],
        "favorite": ["Your favourite! Mama knows what you like, {pet}.", "{item} -- of course. Enjoy it, dear."],
        "rare": ["Goodness, a {item}! Lucky child.", "Such a rare one. Don't drop it, dear."],
        "life": ["Another life, dear. Be careful with this one.", "A fresh chance. Take it slow."],
        "coins": ["Coins! Put them away safely, dear.", "A little treat from the box."],
        "drowsy": ["You're so sleepy, dear. Find a snack before you nod off.", "Only {power} power left. Shall we find something warm?"],
        "asleep": ["Oh, you fell asleep. Rest a moment, dear -- here we go again.", "A little nap, and a life gone. Up you get."],
    },
    "hana": {
        "snack": ["Ooh, {item}! Sparkle-time, {pet}!", "Yay, {item}! Energy bloom!"],
        "rescue": ["You're BACK! {item} to the rescue!", "Wheee, {item} woke you up -- bloom, bloom!"],
        "favorite": ["Your FAVOURITE! Look at you glow, {pet}!", "{item}!! My heart is blooming for you!"],
        "rare": ["WOW, a {item}! That's SO rare!", "Sparkles everywhere -- {item}!"],
        "life": ["A new life! Let's bloom again!", "Ooh, a spare life -- petal power!"],
        "coins": ["Coins, coins, coins! Shiny!", "Confetti coins!"],
        "drowsy": ["Don't wilt on me, {pet}! Find a drink, quick!", "Only {power} power -- you're droopy! Konbini time!"],
        "asleep": ["Noooo, you wilted! Up, up, up!", "Zzz... shake it off, {pet}, you've got this!"],
    },
    "umeshu": {
        "snack": ["A modest {item}. Quietly satisfying.", "Mm. {item}. A civilised pause, {pet}."],
        "rescue": ["Ah -- {item}. Just what the evening called for.", "You were fading. {item} sets it right."],
        "favorite": ["Your favourite. One must indulge, {pet}.", "{item}. An excellent choice of fate."],
        "rare": ["Remarkable. A {item}, and a rare one.", "Fortune favours you: {item}."],
        "life": ["A life, freely given. Spend it well.", "How gracious of the box."],
        "coins": ["Pocket change, but pleasant.", "A small, polite shower of coins."],
        "drowsy": ["Your pace slackens, {pet}. Perhaps a refreshment?", "{power} power remains. I would find something stimulating."],
        "asleep": ["Sleep overtook you. It happens to the best of us.", "A life spent on a nap. Gather yourself."],
    },
    "kinoko": {
        "snack": ["{item}? That's snack-tastic, {pet}!", "Gobble gobble -- {item}! Fun-gi to eat!"],
        "rescue": ["I mushroom-ed over to say: {item} woke you up!", "Back from the nap -- {item} did the trick!"],
        "favorite": ["Your fave! I'm spore-ly impressed!", "{item}! That's a truffle-ing good find!"],
        "rare": ["A {item}?! That's mush-have!", "Rare! I'm cap-tivated!"],
        "life": ["One more life -- spore-tunity knocks!", "Extra life! I'm over the moon-gus!"],
        "coins": ["Cha-ching, coins! Spore of the moment!", "Coin shower -- what a fun-gi!"],
        "drowsy": ["Don't nod off, {pet}! Need a pick-me-up -- only {power} power!", "You're getting sleepy... find a drink before you hit the hay-stack!"],
        "asleep": ["You fell asleep! Wake up, sleepy-head -- you lost a life!", "Zzz-mushroom! Time to wake up, {pet}!"],
    },
}

CLAUDE_MAX_TOKENS = 110


@dataclass
class Speech:
    lines: list
    expression: str = "happy"
    seconds_left: float = 4.5
    total: float = 4.5
    token: int = 0

    @property
    def page(self):
        """The bubble is small, so a reaction with a vocabulary lesson
        shows as two pages: the companion's line first, then the lesson."""
        if len(self.lines) < 2:
            return 0
        return 0 if (self.total - self.seconds_left) < 0.42 * self.total else 1


class ItemCoach:
    """Owns the companion's in-level reactions. Game calls react(...) /
    warn_drowsy() / fell_asleep() when things happen, update(dt) each
    frame, and reads `speech` to draw the bubble."""

    def __init__(self, hint_service, character_name, rng=None):
        self.hint_service = hint_service
        self.companion = hint_service.companion
        self.character_name = character_name
        self.rng = rng or random.Random()
        self.speech = None
        self._token = 0
        self._pending = {}   # token -> text from a finished Claude call
        self._lock = threading.Lock()

    # -- Public events ---------------------------------------------------

    def react(self, situation, item=None, power=10, lesson=True):
        text = self._local_line(situation, item, power)
        lines = [text]
        if lesson and item is not None:
            lines.append(self.lesson_line(item))
        self._say(lines, "happy" if situation != "asleep" else "sympathetic",
                  seconds=6.5 if len(lines) > 1 else 4.5)
        if item is not None:
            self._ask_claude(situation, item, power)

    def warn_drowsy(self, power):
        self._say([self._local_line("drowsy", None, power)], "sympathetic", seconds=5.0)

    def fell_asleep(self, power):
        self._say([self._local_line("asleep", None, power)], "sympathetic", seconds=5.0)

    def update(self, dt):
        if self.speech is None:
            return
        with self._lock:
            reply = self._pending.pop(self.speech.token, None)
        if reply:
            self.speech.lines[0] = reply
        self.speech.seconds_left -= dt
        if self.speech.seconds_left <= 0:
            self.speech = None

    # -- Text ------------------------------------------------------------

    @staticmethod
    def lesson_line(item):
        return f"{item.jp} ({item.reading}) = {item.meaning}.  {item.example}  ({item.example_en})"

    def _local_line(self, situation, item, power):
        voice = VOICES.get(self.companion["id"], VOICES["kobito"])
        template = self.rng.choice(voice[situation])
        return template.format(
            item=item.name if item else "", jp=item.jp if item else "",
            pet=self.character_name, power=power,
        )

    def _say(self, lines, expression, seconds=4.5):
        self._token += 1
        self.speech = Speech(lines=list(lines), expression=expression, seconds_left=seconds, total=seconds,
                             token=self._token)

    # -- Optional Claude layer -------------------------------------------

    def _ask_claude(self, situation, item, power):
        client = getattr(self.hint_service, "_client", None)
        if client is None:
            return
        token = self._token
        prompt = "\n".join([
            f"You are {self.companion['name']}, {self.companion['personality']}.",
            f"You're cheering on {self.character_name}, a mascot playing a Japanese-learning platformer.",
            f"They just picked up: {item.name} ({item.jp}, {item.reading} = {item.meaning}).",
            f"Situation: {situation}. Their power is {power}/10 (3 or less means sleepy).",
            "Write ONE short, warm reaction in character (max 20 words, no emoji).",
            "If they were sleepy, say the item perks them up. Mention the Japanese word naturally.",
        ])

        def work():
            try:
                response = client.messages.create(
                    model=self.hint_service.model, max_tokens=CLAUDE_MAX_TOKENS,
                    messages=[{"role": "user", "content": prompt}],
                )
                text = next((b.text.strip() for b in response.content if b.type == "text" and b.text.strip()), None)
            except Exception:
                return
            if text:
                with self._lock:
                    self._pending[token] = text

        try:
            threading.Thread(target=work, daemon=True).start()
        except Exception:
            pass  # threads unavailable (e.g. the browser build): keep the local line
