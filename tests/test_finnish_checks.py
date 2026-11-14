"""
Tests for evals/finnish/checks.py: no model, no database.

Bad examples are real Gemma answers (14 Nov 2026). Good examples are correct
Finnish that must not be flagged: a check that cries wolf gets ignored.
"""

import json

import pytest

from evals.finnish import run
from evals.finnish.checks import ERROR, WARNING, check_answer


def codes(text):
    return [i.code for i in check_answer(text)]


# --------------------------------------------------------------------------
# Correct Finnish passes
# --------------------------------------------------------------------------

@pytest.mark.parametrize("text", [
    "Voit käyttää tällä viikolla turvallisesti **68,23 €**.",
    "Tämä summa perustuu tilanteeseesi ennen seuraavaa palkkapäivääsi 15. syyskuuta.",
    "Yhteensä kulutuksesi oli viime kuussa 1 086,14 €.",
    "Käytät viihteeseen vähemmän rahaa kuin 76,6 % ikäisistäsi.",
    "Vertasin kulutustasi muihin 18–24-vuotiaisiin ajalla 1.9.2025–31.8.2026.",
    "*   **746,21 €** – Asuminen (lasku) 🏠",          # list item opening with a label
    "1. Avaa S-mobiili. 2. Valitse S-Pankin tili.",    # brands, numbered list
    "Voit ohjata Bonuksen Säästäjä-palveluun tai S-Tuottotilille.",
    "Maksutonta apua saa Oikeuspalveluviraston talous- ja velkaneuvonnasta.",
    "Helsingissä ja muualla Suomessa EU:n säännöt pätevät.",
    "Pieni vinkki: kannattaa suosia kotiruokaa. Tsemppiä!",
    "Kokous on klo 14.30.",                            # Finnish time, not a decimal
    "☕ Arjen kulutus\n\nRavintolat kuuluvat arjen kulutukseen.",  # name on its own line
    "Kysymys? Vastaus! Kolmas lause… Neljäs.",
])
def test_correct_finnish_is_not_flagged(text):
    assert check_answer(text) == []


# --------------------------------------------------------------------------
# Capitals
# --------------------------------------------------------------------------

def test_capital_mid_sentence():
    issues = check_answer("Kulutuksesi on Tyypillistä ikäisillesi.")
    assert [(i.code, i.severity) for i in issues] == [("capital_mid_sentence", ERROR)]
    assert "Tyypillistä" in issues[0].excerpt
    assert "'tyypillistä'" in issues[0].hint


def test_basket_name_capital_mid_sentence_is_its_own_warning():
    issues = check_answer("Ravintolakulut kuuluvat ☕ Arjen kulutukseen.")
    assert [(i.code, i.severity) for i in issues] == [("basket_name_capital", WARNING)]
    assert codes("Ne menevät Välttämättömiin menoihin.") == ["basket_name_capital"]


@pytest.mark.parametrize("text", [
    "Kulut jakautuivat kiinteisiin kuluihin (🏠 Välttämättömät menot).",
    "Kolmas kori on **🔧 Yllättävät menot**, jonne menevät yllätykset.",
    "Nämä kulut kuuluvat ☕ Arjen kulutus -koriin.",
])
def test_basket_names_written_as_names_pass(text):
    assert codes(text) == []


def test_capital_after_colon():
    assert codes("Pieni vinkki: Koska varat ovat tiukalla, syö kotona.") == ["capital_after_colon"]


@pytest.mark.parametrize("text", [
    "* **Yleisesti:** Kulutuksesi on tyypillistä.",
    "**Vinkki:** Koska budjettisi on hyvässä tasapainossa, säästä.",
    "- 🏠 **Välttämättömät menot**: Kiinteät ja säännölliset kulut.",
])
def test_bold_labels_work_as_headings(text):
    assert codes(text) == []


def test_month_names_are_lowercase_in_finnish():
    # A period after a number is a date or ordinal, not a sentence end.
    assert codes("Palkkasi tulee 15. Syyskuuta.") == ["capital_mid_sentence"]
    assert codes("Palkkasi tulee ensi Syyskuussa.") == ["capital_mid_sentence"]


# --------------------------------------------------------------------------
# English
# --------------------------------------------------------------------------

@pytest.mark.parametrize("text, word", [
    ("Erityisesti Lifestyle- ja terveysmenot ovat pieniä.", "Lifestyle"),
    ("Kategoria Home & Tech kasvoi.", "Home & Tech"),
    ("Suurin kulu oli restaurants.", "restaurants"),
    ("Tämä on sinun everyday spending -korisi.", "everyday spending"),
])
def test_english_words(text, word):
    issues = check_answer(text)
    assert [i.code for i in issues] == ["english_word"]  # reported once, not also as a capital
    assert word in issues[0].hint


def test_finnish_loanwords_are_not_english():
    assert codes("Menit taksilla supermarkettiin ja ostit budjettiin sopivaa ruokaa.") == []


# --------------------------------------------------------------------------
# Numbers and dates
# --------------------------------------------------------------------------

@pytest.mark.parametrize("text, expected", [
    ("Säästäisit 84.7 % kuluista.", ["decimal_point"]),
    ("Jäljellä on 68.23 €.", ["decimal_point"]),
    ("Jäljellä on €68.23.", ["euro_before_number", "decimal_point"]),
    ("Jäljellä on 1,086.14 €.", ["decimal_point"]),
    ("Säästäisit 20% kuluista.", ["no_space_before_unit"]),
    ("Maksoit 12345 € vuokraa.", ["no_thousands_space"]),
    ("Ajalla 01.09.2025–31.08.2026.", ["date_leading_zero", "date_leading_zero"]),
])
def test_number_formats(text, expected):
    assert sorted(codes(text)) == sorted(expected)


# --------------------------------------------------------------------------
# Known bad phrases, from real answers
# --------------------------------------------------------------------------

@pytest.mark.parametrize("text, code", [
    ("Olet pitänyt taloutesi hyvissä railseissa!", "anglicism"),
    ("Yksikin vähemmän ostettu ulkoilma-ateria auttaa.", "wrong_word"),
    ("Käyttöä rajoittaa tiliasiasi.", "wrong_word"),
    ("Käytät viihkkeeseen vähemmän.", "typo"),
    ("Käytät viihdeen kulutuksiin vähemmän.", "typo"),
    ("Kulutuksesi on tyypillistä ikäisissä.", "grammar"),
    ("Yhteensä kulutuksiasi oli 1 086,14 €.", "grammar"),
    ("Verrattuna muihin (18–24 vuotta).", "age_range"),
    ("Tämä tekee järkeä.", "anglicism"),
])
def test_known_bad_phrases(text, code):
    assert code in codes(text)


def test_issues_are_in_text_order_with_hints():
    issues = check_answer("Pieni vinkki: Koska 84.7% ja hyvissä railseissa.")
    assert [i.code for i in issues] == ["capital_after_colon", "decimal_point", "no_space_before_unit", "anglicism"]
    assert all(i.hint and i.excerpt for i in issues)


# --------------------------------------------------------------------------
# Re-checking saved answers writes the report and review sheet
# --------------------------------------------------------------------------

def test_check_mode_writes_report_and_review_sheet(tmp_path):
    saved = tmp_path / "answers.jsonl"
    rows = [
        {"id": "a", "customer_id": "CUST00001", "question": "Q1", "answer": "Hyvissä railseissa.", "model": "gemma"},
        {"id": "b", "customer_id": "CUST00002", "question": "Q2", "answer": "Kaikki hyvin.", "model": "gemma"},
    ]
    saved.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows), encoding="utf-8")

    run.main(["--check", str(saved), "--out", str(tmp_path / "out")])

    report = (tmp_path / "out" / "report.md").read_text(encoding="utf-8")
    assert "| `anglicism` | error | 1 | 1 |" in report
    assert "- Clean: 1" in report
    sheet = (tmp_path / "out" / "review.csv").read_text(encoding="utf-8-sig")
    assert sheet.splitlines()[0] == "id,customer_id,question,answer,issues,corrected_answer,notes"
    assert "anglicism: Hyvissä railseissa." in sheet


# Added with the coach test set (evals/coach): false alarms seen on real Gemma answers.
@pytest.mark.parametrize("text", [
    "Ota yhteyttä Peluuriin, joka tarjoaa maksutonta apua.",
    "Voit soittaa MIELI ry:n Kriisipuhelimeen.",
    "Kannattaa tutustua Verohallinnon ohjeisiin.",
    "Käytit baareihin yhteensä 72,89 € elokuussa 2026. Nämä menot ovat arjen kulutusta.",
])
def test_names_and_sentences_after_a_year_are_not_flagged(text):
    assert not [i for i in check_answer(text) if i.code == "capital_mid_sentence"]


def test_ordinal_dates_still_continue_the_sentence():
    issues = check_answer("Palkkapäivä on 15. Syyskuuta.")
    assert any(i.code == "capital_mid_sentence" for i in issues)


# Native reviewer's corrections (coach-review-gemma, 14 Nov 2026).
@pytest.mark.parametrize("bad, code", [
    ("Suurimpia eräitä olivat ruokaostokset.", "grammar"),
    ("Yhteensä kulutuksiasi oli elokuussa 2 541,89 €.", "grammar"),
    ("Jos haluat tarkastella, mihin arjen kulutuksen summa muodostuu, kysy.", "wrong_word"),
])
def test_reviewer_corrections_are_caught(bad, code):
    assert any(i.code == code for i in check_answer(bad))


@pytest.mark.parametrize("good", [
    "Suurimpia eriä olivat ruokaostokset.",
    "Elokuussa kulutit yhteensä 2 541,89 €.",
    "Jos haluat tarkastella, mistä arjen kulutus koostuu, kysy.",
])
def test_corrected_wording_passes(good):
    assert not [i for i in check_answer(good) if i.severity == ERROR]
