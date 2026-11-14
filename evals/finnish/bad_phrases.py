"""
Known bad Finnish from the coach: add a line whenever a reviewer finds one.

Each entry is (regex, code, severity, hint). Regexes are case-insensitive;
use ``\\w*`` after a stem so every inflected form matches. Keep the hint in
Finnish with the better wording, so the report shows how to fix it.

The first entries are real Gemma answers from 14 Nov 2026.
"""

ERROR = "error"
WARNING = "warning"

BAD_PHRASES = [
    # English idioms or words with Finnish endings
    (r"\brails\w*", "anglicism", ERROR,
     "Englannin 'on the rails'. Esim. 'taloutesi on hyvällä mallilla'."),
    (r"\btehdä\s+järkeä\b|\btekee\s+järkeä\b", "anglicism", ERROR,
     "Englannin 'make sense'. Esim. 'on järkevää'."),
    (r"\bottaa\s+paikkaa\b|\botti\s+paikkaa\b", "anglicism", ERROR,
     "Englannin 'take place'. Esim. 'tapahtui'."),

    # Wrong words
    (r"\bulkoilma-ateri\w*", "wrong_word", ERROR,
     "'Ulkoilma-ateria' on ulkona syöty ateria. Tarkoitettu: 'ravintola-ateria'."),
    (r"\btiliasi\w*", "wrong_word", ERROR,
     "Ei tarkoita tilin saldoa. Esim. 'tilisi saldo' tai 'tililläsi oleva raha'."),
    (r"\bviihkke\w*", "typo", ERROR, "Kirjoitusvirhe: 'viihde', 'viihteeseen'."),
    (r"\bviihdee(?:n|seen|ssä|stä)\b", "typo", ERROR, "Väärä taivutus: 'viihteen', 'viihteeseen', 'viihteessä'."),

    # Grammar
    (r"\bikäisissä\b", "grammar", ERROR,
     "Väärä sijamuoto. Esim. 'ikäisilläsi' tai 'ikäistesi joukossa'."),
    (r"\bkulutuksia(?:si)?\s+oli\b", "grammar", ERROR,
     "Kongruenssi: 'Kulutuksesi oli yhteensä …' tai luontevammin 'Kulutit yhteensä …'."),
    # Found by a native reviewer, 14 Nov 2026 (coach-review-gemma, baskets-fi-1).
    (r"\beräitä\b", "grammar", ERROR,
     "Väärä monikko: 'eriä' (esim. 'Suurimpia eriä olivat …')."),
    (r"\bmihin\b[^.?!\n]{0,60}\bmuodostu\w*", "wrong_word", ERROR,
     "Esim. 'mistä arjen kulutus koostuu' (ei 'mihin … muodostuu')."),
    (r"\b\d+\s?[–-]\s?\d+\s+vuotta\b", "age_range", WARNING,
     "Ikäryhmä adjektiivina: '18–24-vuotiaat' tai '18–24-vuotiaiden'."),
]
