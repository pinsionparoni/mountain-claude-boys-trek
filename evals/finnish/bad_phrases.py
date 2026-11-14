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
    (r"\bmihin\b[^.?!\n]{0,60}\b(?:muodostu|koostu)\w*", "wrong_word", ERROR,
     "Esim. 'mistä arjen kulutus koostuu' (ei 'mihin … muodostuu')."),
    (r"\b\d+\s?[–-]\s?\d+\s+vuotta\b", "age_range", WARNING,
     "Ikäryhmä adjektiivina: '18–24-vuotiaat' tai '18–24-vuotiaiden'."),

    # Found by a native reviewer in the blind rating, 14 Nov 2026.
    # S-Bank's three groups are spending categories, not baskets.
    (r"\w*kori(?:a|en|in|ihin|lle|lla|ssa|sta|si|t|n)?\b", "wrong_word", ERROR,
     "Ei 'kori': 'kuuluu kategoriaan ☕ Arjen kulutus', 'kolme kulutuskategoriaa'."),
    (r"\bkulutuksiasi\b(?!\s+oli)", "wrong_word", ERROR,
     "Esim. 'Katsoin kulujasi' tai 'Katsoin kulutustasi'."),
    (r"\bikävertais\w*", "wrong_word", ERROR, "Esim. 'ikäisistäsi', 'ikäisiisi verrattuna'."),
    (r"\bmenit\b[^.?!\n]{0,40}\d", "wrong_word", ERROR,
     "'Menit' = sinä menit jonnekin. Esim. 'Kulutit elokuussa yhteensä 4 906,69 €.'"),
    (r"\bpääsee\s+nämä\b", "grammar", ERROR, "Kongruenssi. Esim. 'Lähimpänä ovat nämä:'."),
    (r"\bkuukauden\s+väliset\b", "grammar", ERROR,
     "Esim. 'summa, joka kattaa 1–3 kuukauden välttämättömät menot'."),
    (r"\bheit\w*[^.?!\n]{0,20}\bkumppanista\b", "wrong_word", ERROR,
     "Ei suomen sanonta. Esim. 'joka suojaa sinua, kun arki yllättää'."),
    (r"\bkäyt\w*\s+viihdettä\b", "grammar", ERROR, "Esim. 'Käytät viihteeseen vähemmän rahaa kuin …'."),
    (r"\bhelpoimmin\b[^.?!\n]{0,80}\bkuin\b", "grammar", ERROR,
     "Vertailu: 'helpommin … kuin', esim. 'Säästät helpommin käymällä ravintoloissa vähemmän kuin …'."),
    (r"\bsuurin\s+osa\b[^.?!\n]{0,20}\boli\s+(?:kaksi|kolme|neljä|viisi)\b", "grammar", ERROR,
     "Esim. 'Kahteen lääkärikäyntiin meni eniten rahaa, yhteensä 117,53 €.'"),
    (r"\bconcrete\s+suggestion\b|\bsuggestion\s*:", "anglicism", ERROR,
     "Englantia suomenkielisessä vastauksessa. Esim. 'Ehdotus:' tai 'Vinkki:'."),
    (r"\w*ostokks\w*", "typo", ERROR, "Kirjoitusvirhe: 'ostoksiin', 'ruokaostoksiin'."),
    # Gemma, 14 Nov 2026: a Thai vowel sign inside "herkkuostokset".
    (r"[Ѐ-ӿ؀-ۿ฀-๿぀-ヿ一-鿿]", "foreign_script", ERROR,
     "Vieraan kirjoitusjärjestelmän merkki keskellä tekstiä."),
    # The reviewer's style preferences: no dashes between clauses, no quote marks.
    (r"\s[–—]\s", "style", WARNING, "Vältä ajatusviivaa: jaa kahdeksi lauseeksi tai käytä pilkkua."),
    (r"[\"“”][^\"“”\n]{1,80}[\"“”]", "style", WARNING, "Vältä lainausmerkkejä vastauksessa."),
]
