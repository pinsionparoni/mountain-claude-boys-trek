"""Finnish and English formatting and S-Pankki terminology helpers for training data."""

from __future__ import annotations

from datetime import date

FI_MONTH_IN = {
    1: "tammikuussa", 2: "helmikuussa", 3: "maaliskuussa", 4: "huhtikuussa",
    5: "toukokuussa", 6: "kesäkuussa", 7: "heinäkuussa", 8: "elokuussa",
    9: "syyskuussa", 10: "lokakuussa", 11: "marraskuussa", 12: "joulukuussa",
}
FI_MONTH_PART = {
    1: "tammikuuta", 2: "helmikuuta", 3: "maaliskuuta", 4: "huhtikuuta",
    5: "toukokuuta", 6: "kesäkuuta", 7: "heinäkuuta", 8: "elokuuta",
    9: "syyskuuta", 10: "lokakuuta", 11: "marraskuuta", 12: "joulukuuta",
}
FI_MONTH_NOM = {
    1: "tammikuu", 2: "helmikuu", 3: "maaliskuu", 4: "huhtikuu",
    5: "toukokuu", 6: "kesäkuu", 7: "heinäkuu", 8: "elokuu",
    9: "syyskuu", 10: "lokakuu", 11: "marraskuu", 12: "joulukuu",
}
EN_MONTH = {
    1: "January", 2: "February", 3: "March", 4: "April",
    5: "May", 6: "June", 7: "July", 8: "August",
    9: "September", 10: "October", 11: "November", 12: "December",
}

# Category names: the nominative must equal coach.spending_baskets.CATEGORY_LABELS_FI
# (what the tools return as category_fi; checked in tests/test_training_data.py).
# (nominative lowercase, illative "mihin", elative "mistä")
CAT_FI: dict[str, tuple[str, str, str]] = {
    "Groceries": ("ruokaostokset", "ruokaostoksiin", "ruokaostoksista"),
    "Restaurants": ("ravintolat", "ravintoloihin", "ravintoloista"),
    "Transportation": ("liikkuminen", "liikkumiseen", "liikkumisesta"),
    "Utilities": ("sähkö, vesi ja tietoliikenne", "sähköön, veteen ja tietoliikenteeseen", "sähkö-, vesi- ja tietoliikennelaskuista"),
    "Entertainment": ("viihde", "viihteeseen", "viihteestä"),
    "Health": ("terveys", "terveyteen", "terveysmenoista"),
    "Home & Tech": ("koti ja elektroniikka", "kotiin ja elektroniikkaan", "kodin ja elektroniikan hankinnoista"),
    "Lifestyle": ("vapaa-aika", "vapaa-aikaan", "vapaa-ajasta"),
    "Travel": ("matkailu", "matkailuun", "matkailusta"),
    "Housing": ("asuminen", "asumiseen", "asumismenoista"),
}

CAT_EN: dict[str, str] = {
    "Groceries": "groceries",
    "Restaurants": "restaurants",
    "Transportation": "transportation",
    "Utilities": "utilities",
    "Entertainment": "entertainment",
    "Health": "health",
    "Home & Tech": "home and electronics",
    "Lifestyle": "leisure",
    "Travel": "travel",
    "Housing": "housing",
}

# Merchant-type labels in clean Finnish (nominative, illative "mihin") and English.
MERCHANT_FI: dict[str, tuple[str, str]] = {
    "supermarket": ("ruokakaupat", "ruokakauppoihin"),
    "butcher": ("lihakaupat", "lihakauppoihin"),
    "dairy shop": ("maito- ja juustokaupat", "maito- ja juustokauppoihin"),
    "convenience / specialty food": ("lähi- ja erikoisruokakaupat", "lähi- ja erikoisruokakauppoihin"),
    "fuel": ("polttoaine", "polttoaineeseen"),
    "service station": ("huoltoasemat", "huoltoasemille"),
    "parking": ("pysäköinti", "pysäköintiin"),
    "public transport": ("julkinen liikenne", "julkiseen liikenteeseen"),
    "taxi": ("taksit", "takseihin"),
    "pharmacy": ("apteekit", "apteekkiin"),
    "doctor": ("lääkärikäynnit", "lääkärikäynteihin"),
    "dentist": ("hammaslääkäri", "hammaslääkäriin"),
    "medical services": ("terveyspalvelut", "terveyspalveluihin"),
    "home supply store": ("kodintarvikekaupat", "kodintarvikekauppoihin"),
    "hardware store": ("rautakaupat", "rautakauppoihin"),
    "electronics": ("elektroniikka", "elektroniikkaan"),
    "furniture": ("huonekalukaupat", "huonekaluihin"),
    "software": ("ohjelmistot ja sovellukset", "ohjelmistoihin ja sovelluksiin"),
    "restaurant": ("ravintolat", "ravintoloihin"),
    "bar": ("baarit", "baareihin"),
    "fast food / café": ("pikaruokapaikat ja kahvilat", "pikaruokapaikkoihin ja kahviloihin"),
    "tickets / events": ("liput ja tapahtumat", "lippuihin ja tapahtumiin"),
    "recreation": ("harrastukset", "harrastuksiin"),
    "cinema": ("elokuvateatterit", "elokuviin"),
    "attractions": ("nähtävyydet", "nähtävyyksiin"),
    "amusement park": ("huvipuistot", "huvipuistoihin"),
    "sporting goods": ("urheiluvälineet", "urheiluvälineisiin"),
    "clothing": ("vaatekaupat", "vaatteisiin"),
    "other retail": ("muut kaupat", "muihin kauppoihin"),
    "bookstore": ("kirjakaupat", "kirjoihin"),
    "hobby / toys": ("harrastus- ja lelukaupat", "harrastuksiin ja leluihin"),
    "travel agency": ("matkatoimistot", "matkatoimistoihin"),
    "airline": ("lentoyhtiöt", "lentoihin"),
    "hotel": ("hotellit", "majoitukseen"),
    "car rental": ("autovuokraamot", "autonvuokraukseen"),
    "other": ("muut ostot", "muihin ostoihin"),
    "bill": ("laskut", "laskuihin"),
}

MERCHANT_EN: dict[str, str] = {
    "supermarket": "supermarkets",
    "butcher": "butchers",
    "dairy shop": "dairy shops",
    "convenience / specialty food": "convenience and specialty food shops",
    "fuel": "fuel",
    "service station": "service stations",
    "parking": "parking",
    "public transport": "public transport",
    "taxi": "taxis",
    "pharmacy": "pharmacies",
    "doctor": "doctors",
    "dentist": "dentists",
    "medical services": "medical services",
    "home supply store": "home supply stores",
    "hardware store": "hardware stores",
    "electronics": "electronics stores",
    "furniture": "furniture stores",
    "software": "software",
    "restaurant": "restaurants",
    "bar": "bars",
    "fast food / café": "cafés and fast food",
    "tickets / events": "event tickets",
    "recreation": "recreation",
    "cinema": "cinemas",
    "attractions": "attractions",
    "amusement park": "amusement parks",
    "sporting goods": "sporting goods",
    "clothing": "clothing stores",
    "other retail": "other retail shops",
    "bookstore": "bookstores",
    "hobby / toys": "hobby and toy shops",
    "travel agency": "travel agencies",
    "airline": "flights",
    "hotel": "hotels",
    "car rental": "car rentals",
    "other": "other card purchases",
    "bill": "bills",
}


def eur_fi(x: float | int) -> str:
    """Format 2541.89 -> '2 541,89 €', -32.5 -> '-32,50 €'."""
    sign = "−" if x < 0 else ""
    whole, dec = f"{abs(float(x)):.2f}".split(".")
    groups: list[str] = []
    while whole:
        groups.insert(0, whole[-3:])
        whole = whole[:-3]
    return f"{sign}{' '.join(groups)},{dec} €"


def eur_en(x: float | int) -> str:
    """Format 2541.89 -> '€2,541.89'."""
    sign = "−" if x < 0 else ""
    return f"{sign}€{abs(float(x)):,.2f}"


def pct_fi(x: float | int, decimals: int = 1) -> str:
    """Format 84.7 -> '84,7 %', 20.0 (decimals=0) -> '20 %'."""
    if decimals == 0 or float(x).is_integer():
        return f"{int(round(float(x)))} %"
    return f"{float(x):.{decimals}f}".replace(".", ",") + " %"


def pct_en(x: float | int, decimals: int = 1) -> str:
    if decimals == 0 or float(x).is_integer():
        return f"{int(round(float(x)))}%"
    return f"{float(x):.{decimals}f}%"


def date_fi(iso_or_date: str | date, with_year: bool = False) -> str:
    """Format '2026-09-15' -> '15.9.' or '15.9.2026' (never leading zeros)."""
    d = date.fromisoformat(iso_or_date) if isinstance(iso_or_date, str) else iso_or_date
    return f"{d.day}.{d.month}.{d.year}" if with_year else f"{d.day}.{d.month}."


def date_en(iso_or_date: str | date, with_year: bool = False) -> str:
    d = date.fromisoformat(iso_or_date) if isinstance(iso_or_date, str) else iso_or_date
    base = f"{d.day} {EN_MONTH[d.month]}"
    return f"{base} {d.year}" if with_year else base


def range_fi(start_iso: str, end_iso: str) -> str:
    """Format '2026-08-01', '2026-08-31' -> '1.8.–31.8.2026' or cross-year '1.9.2025–31.8.2026'."""
    s = date.fromisoformat(start_iso)
    e = date.fromisoformat(end_iso)
    if s.year == e.year:
        return f"{s.day}.{s.month}.–{e.day}.{e.month}.{e.year}"
    return f"{s.day}.{s.month}.{s.year}–{e.day}.{e.month}.{e.year}"


def range_en(start_iso: str, end_iso: str) -> str:
    s = date.fromisoformat(start_iso)
    e = date.fromisoformat(end_iso)
    if s.year == e.year:
        return f"{date_en(s)} to {date_en(e, True)}"
    return f"{date_en(s, True)} to {date_en(e, True)}"


def month_ym_fi(ym: str) -> str:
    """'2026-08' -> 'elokuu 2026'."""
    y, m = ym.split("-")
    return f"{FI_MONTH_NOM[int(m)]} {y}"


def month_ym_en(ym: str) -> str:
    y, m = ym.split("-")
    return f"{EN_MONTH[int(m)]} {y}"


def month_in_fi(m_num: int, y_num: int, today_year: int) -> str:
    """Single-month Finnish time phrase: 'elokuussa' or 'viime vuoden elokuussa'."""
    if y_num == today_year:
        return FI_MONTH_IN[m_num]
    if y_num == today_year - 1:
        return f"viime vuoden {FI_MONTH_IN[m_num]}"
    return f"vuoden {y_num} {FI_MONTH_IN[m_num]}"


def month_in_en(m_num: int, y_num: int, today_year: int) -> str:
    if y_num == today_year:
        return f"in {EN_MONTH[m_num]}"
    if y_num == today_year - 1:
        return f"in {EN_MONTH[m_num]} last year"
    return f"in {EN_MONTH[m_num]} {y_num}"


def cap_first(s: str) -> str:
    return s[0].upper() + s[1:] if s else s
