"""Normal coaching scenarios S01-S13 (196 examples: 158 FI, 38 EN)."""

from __future__ import annotations

import calendar
import json
from datetime import date, timedelta

from training.formatting import (
    CAT_EN,
    CAT_FI,
    EN_MONTH,
    FI_MONTH_IN,
    FI_MONTH_NOM,
    FI_MONTH_PART,
    MERCHANT_EN,
    MERCHANT_FI,
    cap_first,
    date_en,
    date_fi,
    eur_en,
    eur_fi,
    month_in_en,
    month_in_fi,
    month_ym_en,
    month_ym_fi,
    pct_en,
    pct_fi,
    range_en,
    range_fi,
)


def _prev_month_bounds(today: date) -> tuple[str, str, int, int]:
    end = today.replace(day=1) - timedelta(days=1)
    start = end.replace(day=1)
    return start.isoformat(), end.isoformat(), start.month, start.year


def _n_complete_months_bounds(today: date, n: int) -> tuple[str, str]:
    end = today.replace(day=1) - timedelta(days=1)
    idx = end.year * 12 + (end.month - 1) - (n - 1)
    start = date(idx // 12, idx % 12 + 1, 1)
    return start.isoformat(), end.isoformat()


def _call_msg(calls: list[tuple[str, str, dict]]) -> list[dict]:
    """Build assistant tool_calls turn."""
    return [{
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {
                "id": cid,
                "type": "function",
                "function": {"name": name, "arguments": json.dumps(args, ensure_ascii=False)},
            }
            for cid, name, args in calls
        ],
    }]


# ---------------------------------------------------------------------------
# S01: Safe-to-spend, cash-limited before payday (14 FI, 4 EN)
# ---------------------------------------------------------------------------

S01_Q_FI = [
    "Paljonko voin käyttää rahaa tällä viikolla ilman, että tili menee tiukille?",
    "Mikä on turvallinen viikkobudjettini juuri nyt?",
    "Paljonko käyttötililtäni riittää arjen menoihin tällä viikolla?",
    "Miten paljon uskallan kuluttaa tällä viikolla ennen palkkapäivää?",
    "Paljonko rahaa on vapaasti käytettävissä tälle viikolle?",
    "Mikä summa minulla on varaa käyttää arjen ostoksiin tällä viikolla?",
    "Riittääkö käyttötilini saldo tälle viikolle ja paljonko voin käyttää?",
]
S01_Q_EN = [
    "How much is safe for me to spend this week before payday?",
    "What's my safe weekly spending amount right now?",
    "How much can I spend on everyday things this week without running short?",
    "What does my account balance safely allow me to spend this week?",
]


def build_s01(ctx, cid: str, today: date, lang: str, variant: int) -> dict:
    q = (S01_Q_FI if lang == "fi" else S01_Q_EN)[variant % (len(S01_Q_FI) if lang == "fi" else len(S01_Q_EN))]
    out_str, data = ctx.run_tool(cid, today, "get_safe_to_spend", {})
    safe = data["safe_to_spend_this_week"]
    tm = data["this_month"]
    cc = data["cash_check"]
    payday_d = date.fromisoformat(cc["next_payday"])
    due_total = cc["essentials_before_payday"]

    if lang == "fi":
        v = variant % 4
        if v == 0:
            ans = (
                f"Tällä viikolla voit käyttää turvallisesti **{eur_fi(safe)}**.\n\n"
                f"Kuukauden arjen kulutuksen budjetistasi on jäljellä {eur_fi(tm['remaining'])}, "
                f"mutta käyttötilisi saldo {eur_fi(cc['current_balance'])} rajoittaa viikkosummaa juuri nyt. "
                f"Ennen seuraavaa palkkapäivää {date_fi(payday_d)} tililtä varataan arviolta "
                f"{eur_fi(due_total)} kiinteisiin ja muihin välttämättömiin menoihin.\n\n"
                f"**Vinkki:** Palkkapäivään on {cc['days_to_payday']} päivää. Kun pidät arjen ostokset maltillisina "
                f"siihen asti, käyttötililläsi riittää kate myös laskuihin."
            )
        elif v == 1:
            ans = (
                f"Turvallinen viikkosummasi on nyt **{eur_fi(safe)}**.\n\n"
                f"Vaikka tämän kuun arjen kulutuksen budjettia olisi laskennallisesti jäljellä {eur_fi(tm['remaining'])}, "
                f"S-Tilisi saldo on tällä hetkellä {eur_fi(cc['current_balance'])}. "
                f"Siitä on hyvä jättää {eur_fi(due_total)} välttämättömiin menoihin ennen palkkapäivää {date_fi(payday_d, True)}.\n\n"
                f"**Vinkki:** Tarkista tulevat e-laskut S-mobiilista, jotta eräpäivät ennen palkkapäivää eivät yllätä."
            )
        elif v == 2:
            ans = (
                f"Voit käyttää tällä viikolla arjen kulutukseen **{eur_fi(safe)}**.\n\n"
                f"Summassa huomioidaan käyttötilisi nykyinen saldo {eur_fi(cc['current_balance'])} sekä "
                f"arviolta {eur_fi(due_total)} pakollisia menoja ennen palkkapäivää {date_fi(payday_d, True)}. "
                f"Koko kuukauden {eur_fi(tm['everyday_budget'])} arjen kulutuksen budjetistasi on käytetty "
                f"tähän mennessä {eur_fi(tm['everyday_spent'])}.\n\n"
                f"**Vinkki:** Kun etenet tämän {eur_fi(safe)} puitteissa palkkapäivään saakka, loppukuun budjettisi pysyy tasapainossa."
            )
        else:
            ans = (
                f"Käyttötilisi tilanteen perusteella turvallinen summa tälle viikolle on **{eur_fi(safe)}**.\n\n"
                f"- **Käyttötilin saldo nyt:** {eur_fi(cc['current_balance'])}\n"
                f"- **Varaus välttämättömiin menoihin ennen palkkapäivää {date_fi(payday_d)}:** {eur_fi(due_total)}\n"
                f"- **Arjen kulutuksen budjettia jäljellä tässä kuussa:** {eur_fi(tm['remaining'])}\n\n"
                f"Koska tilin saldo ennen palkkapäivää on tiukempi kuin kuukausibudjetti, menen varovaisemman luvun mukaan. "
                f"Pieni maltti seuraavat {cc['days_to_payday']} päivää pitää taloutesi hyvällä mallilla."
            )
    else:
        v = variant % 2
        if v == 0:
            ans = (
                f"You can safely spend **{eur_en(safe)}** this week.\n\n"
                f"You still have {eur_en(tm['remaining'])} left in this month's everyday spending budget, "
                f"but your S-Tili current account balance of {eur_en(cc['current_balance'])} is the tighter limit right now. "
                f"About {eur_en(due_total)} is set aside for essentials before your next payday on {date_en(payday_d)}.\n\n"
                f"**Tip:** With {cc['days_to_payday']} days until payday, keeping everyday purchases light ensures upcoming bills are covered."
            )
        else:
            ans = (
                f"Your safe-to-spend amount this week is **{eur_en(safe)}**.\n\n"
                f"- **Current balance:** {eur_en(cc['current_balance'])}\n"
                f"- **Essentials expected before payday on {date_en(payday_d)}:** {eur_en(due_total)}\n"
                f"- **Monthly everyday budget remaining:** {eur_en(tm['remaining'])}\n\n"
                f"Because your available cash until payday is tighter than the monthly budget pace of {eur_en(tm['per_week'])}/week, "
                f"sticking to {eur_en(safe)} keeps a safe cushion until your salary arrives."
            )

    return ctx.pack(cid, today, "S01_safe_to_spend_cash_limited", "coaching", lang, q,
                    [("call_1", "get_safe_to_spend", {}, out_str)], ans)


# ---------------------------------------------------------------------------
# S02: Safe-to-spend, budget-limited and healthy (14 FI, 4 EN)
# ---------------------------------------------------------------------------

S02_Q_FI = [
    "Paljonko minulla on kuukausibudjetin mukaan varaa käyttää tällä viikolla?",
    "Miltä tämän kuun budjettini näyttää ja paljonko voin käyttää viikossa?",
    "Kuinka paljon arjen kulutuksen budjetistani riittää tälle viikolle?",
    "Paljonko voin kuluttaa tällä viikolla niin, että kuukausibudjetti pitää?",
    "Miten kuukausibudjettini jakautuu ja mitä jää tälle viikolle?",
    "Paljonko tälle viikolle jää käyttövaraa pakollisten menojen jälkeen?",
    "Missä mennään tämän kuun budjetissa, paljonko voin käyttää tällä viikolla?",
]
S02_Q_EN = [
    "How is my monthly budget looking, and what can I safely spend this week?",
    "How much room do I have in my everyday budget this week?",
    "Based on my usual income and bills, what's safe to spend this week?",
    "How much of my monthly everyday budget is left for this week?",
]


def build_s02(ctx, cid: str, today: date, lang: str, variant: int) -> dict:
    q = (S02_Q_FI if lang == "fi" else S02_Q_EN)[variant % (len(S02_Q_FI) if lang == "fi" else len(S02_Q_EN))]
    out_str, data = ctx.run_tool(cid, today, "get_safe_to_spend", {})
    safe = data["safe_to_spend_this_week"]
    mb = data["monthly_budget"]
    tm = data["this_month"]
    cc = data["cash_check"]
    payday_d = date.fromisoformat(cc["next_payday"])

    if lang == "fi":
        v = variant % 4
        if v == 0:
            ans = (
                f"Tällä viikolla voit käyttää turvallisesti **{eur_fi(safe)}**.\n\n"
                f"Tyypillisistä {eur_fi(mb['monthly_income'])}/kk tuloistasi vähennetään ensin välttämättömät menot "
                f"{eur_fi(mb['regular_essentials'])}, varaus yllättäviin menoihin {eur_fi(mb['unexpected_reserve'])} "
                f"sekä tavanomainen säästäminen {eur_fi(mb['savings'])}. Arjen kulutukseen jää kuukaudessa "
                f"{eur_fi(mb['everyday_budget'])}, josta sinulla on tässä kuussa jäljellä **{eur_fi(tm['remaining'])}**.\n\n"
                f"Käyttötilisi saldo {eur_fi(cc['current_balance'])} riittää hyvin menoihin ennen palkkapäivää {date_fi(payday_d, True)}. "
                f"**Vinkki:** Jos viikon lopussa jää osa summasta käyttämättä, voit siirtää sen puskuriin säästötilille."
            )
        elif v == 1:
            ans = (
                f"Kuukausibudjettisi on hyvällä mallilla: voit käyttää tällä viikolla **{eur_fi(safe)}**, "
                f"eli noin {eur_fi(tm['per_day'])} päivässä.\n\n"
                f"- **Arjen kulutuksen kuukausibudjetti:** {eur_fi(mb['everyday_budget'])}\n"
                f"- **Käytetty tässä kuussa tähän mennessä:** {eur_fi(tm['everyday_spent'])}\n"
                f"- **Jäljellä loppukuun {tm['days_left_in_month']} päivälle:** {eur_fi(tm['remaining'])}\n\n"
                f"S-Tilisi saldo {eur_fi(cc['current_balance'])} kattaa vaivatta tulevat kiinteät menot ennen palkkapäivää {date_fi(payday_d, True)}."
            )
        elif v == 2:
            ans = (
                f"Voit käyttää arjen ostoksiin tällä viikolla turvallisesti **{eur_fi(safe)}**.\n\n"
                f"Olet käyttänyt tämän kuun {eur_fi(mb['everyday_budget'])} arjen kulutuksen budjetistasi "
                f"vasta {eur_fi(tm['everyday_spent'])}, joten loppukuulle on jäljellä {eur_fi(tm['remaining'])}. "
                f"Budjetissa on jo varattu {eur_fi(mb['regular_essentials'])} kiinteisiin ja säännöllisiin menoihin sekä "
                f"{eur_fi(mb['unexpected_reserve'])} puskuriksi yllättäviin menoihin.\n\n"
                f"**Vinkki:** Säännöllinen pieni siirto esimerkiksi Säästäjä-palvelun tai säästötilin kautta kerryttää puskuria huomaamatta."
            )
        else:
            ans = (
                f"Turvallinen käyttövarasi tälle viikolle on **{eur_fi(safe)}**.\n\n"
                f"Luku perustuu kuukausibudjettiisi: kun tuloista eli {eur_fi(mb['monthly_income'])} summasta otetaan sivuun "
                f"välttämättömät menot {eur_fi(mb['regular_essentials'])}, yllättävien menojen varaus "
                f"{eur_fi(mb['unexpected_reserve'])} ja säästöt {eur_fi(mb['savings'])}, arjen kulutukseen jää "
                f"{eur_fi(mb['everyday_budget'])} kuussa. Tästä on jäljellä vielä {eur_fi(tm['remaining'])}, "
                f"ja käyttötilin saldo {eur_fi(cc['current_balance'])} riittää hyvin palkkapäivään {date_fi(payday_d)} asti."
            )
    else:
        v = variant % 2
        if v == 0:
            ans = (
                f"You're on track. You can safely spend **{eur_en(safe)}** this week, or about {eur_en(tm['per_day'])}/day.\n\n"
                f"From your typical monthly income of {eur_en(mb['monthly_income'])}, your budget sets aside "
                f"{eur_en(mb['regular_essentials'])} for regular essentials, {eur_en(mb['unexpected_reserve'])} as a buffer "
                f"for unexpected necessities, and {eur_en(mb['savings'])} for savings. Out of your {eur_en(mb['everyday_budget'])} "
                f"everyday budget, you still have **{eur_en(tm['remaining'])}** left this month, and your S-Tili balance "
                f"of {eur_en(cc['current_balance'])} comfortably covers expenses until payday on {date_en(payday_d)}."
            )
        else:
            ans = (
                f"Your safe weekly amount is **{eur_en(safe)}**.\n\n"
                f"- **Monthly everyday budget:** {eur_en(mb['everyday_budget'])}\n"
                f"- **Spent so far this month:** {eur_en(tm['everyday_spent'])}\n"
                f"- **Remaining for the last {tm['days_left_in_month']} days:** {eur_en(tm['remaining'])}\n\n"
                f"Your account balance of {eur_en(cc['current_balance'])} covers upcoming bills before {date_en(payday_d)}. "
                f"**Tip:** Anything left unspent at the end of the month makes a great addition to your financial buffer."
            )

    return ctx.pack(cid, today, "S02_safe_to_spend_budget_healthy", "coaching", lang, q,
                    [("call_1", "get_safe_to_spend", {}, out_str)], ans)


# ---------------------------------------------------------------------------
# S03: Safe-to-spend, over budget or €0 left (10 FI, 2 EN)
# ---------------------------------------------------------------------------

S03_Q_FI = [
    "Onko minulla enää yhtään varaa kuluttaa tällä viikolla?",
    "Miltä loppukuun käyttövarani näyttää tässä vaiheessa?",
    "Voinko käyttää rahaa ulkona syömiseen tänä viikonloppuna?",
    "Paljonko arjen budjettiani on jäljellä tälle viikolle?",
    "Riittääkö budjettini vielä arjen ostoksiin tässä kuussa?",
]
S03_Q_EN = [
    "Do I have any room left in my budget to go out this weekend?",
    "How much can I safely spend for the rest of this week?",
]


def build_s03(ctx, cid: str, today: date, lang: str, variant: int) -> dict:
    q = (S03_Q_FI if lang == "fi" else S03_Q_EN)[variant % (len(S03_Q_FI) if lang == "fi" else len(S03_Q_EN))]
    out_str, data = ctx.run_tool(cid, today, "get_safe_to_spend", {})
    safe = data["safe_to_spend_this_week"]
    mb = data["monthly_budget"]
    tm = data["this_month"]
    cc = data["cash_check"]
    payday_d = date.fromisoformat(cc["next_payday"])

    if lang == "fi":
        if tm["over_budget"] > 0:
            ans = (
                f"Tälle viikolle turvallinen arjen kulutuksen summa on **{eur_fi(safe)}**, sillä tämän kuun "
                f"arjen kulutuksen budjetti {eur_fi(mb['everyday_budget'])} on ylittynyt {eur_fi(tm['over_budget']).replace(' €', ' eurolla')} "
                f"ja käytetty summa on nyt {eur_fi(tm['everyday_spent'])}.\n\n"
                f"Käyttötililläsi on nyt {eur_fi(cc['current_balance'])}, ja seuraava palkkapäivä on {date_fi(payday_d, True)}. "
                f"Tällaisia kuukausia sattuu jokaiselle. Tärkeintä on nyt rauhoittaa ei-pakolliset ostokset loppukuuksi, "
                f"jotta kiinteät menot ja ruokaostokset hoituvat sujuvasti.\n\n"
                f"**Vinkki:** Jos haluat, voimme katsoa yhdessä, mitkä tämän kuun ostokset kasvattivat arjen kulutusta eniten."
            )
        else:
            ans = (
                f"Tällä hetkellä turvallinen summa arjen kulutukseen tälle viikolle on **{eur_fi(safe)}**.\n\n"
                f"Käyttötilisi saldo on {eur_fi(cc['current_balance'])}, ja ennen palkkapäivää {date_fi(payday_d)} "
                f"välttämättömiin menoihin kuluu arviolta {eur_fi(cc['essentials_before_payday'])}. "
                f"Siksi ylimääräisiä arjen menoja kannattaa nyt lykätä palkkapäivän yli.\n\n"
                f"**Vinkki:** Jos jonkin laskun eräpäivä mietityttää, ole ajoissa yhteydessä laskuttajaan tai S-Pankin asiakaspalveluun."
            )
    else:
        if tm["over_budget"] > 0:
            ans = (
                f"Right now your safe everyday spending amount for this week is **{eur_en(safe)}**, because this month's "
                f"{eur_en(mb['everyday_budget'])} everyday budget has already been exceeded by {eur_en(tm['over_budget'])}, "
                f"with {eur_en(tm['everyday_spent'])} spent so far.\n\n"
                f"Your S-Tili balance is {eur_en(cc['current_balance'])} with your next payday on {date_en(payday_d)}. "
                f"Months like this happen. Holding off on non-essential spending for the rest of the month will protect "
                f"your balance for groceries and upcoming bills."
            )
        else:
            ans = (
                f"Your safe-to-spend amount for everyday extras this week is **{eur_en(safe)}**.\n\n"
                f"Your balance is {eur_en(cc['current_balance'])}, and upcoming essentials before payday on {date_en(payday_d)} "
                f"need about {eur_en(cc['essentials_before_payday'])}. "
                f"Pausing discretionary purchases until payday is the safest move right now."
            )

    return ctx.pack(cid, today, "S03_safe_to_spend_tight_or_over", "coaching", lang, q,
                    [("call_1", "get_safe_to_spend", {}, out_str)], ans)


# ---------------------------------------------------------------------------
# S04: Three spending baskets, full monthly summary (18 FI, 4 EN)
# ---------------------------------------------------------------------------

S04_Q_FI = [
    "Jaa viime kuun menoni kolmeen kulutuskoriin.",
    "Miten rahankäyttöni jakautui kolmeen koriin viime kuussa?",
    "Näytä viime kuukauden kulutukseni koreittain.",
    "Paljonko minulla meni viime kuussa välttämättömiin, yllättäviin ja arjen menoihin?",
    "Miltä viime kuun menot näyttävät S-Pankin kolmessa korissa?",
    "Erittelisitkö viime kuun ostokseni kolmeen kulutuskoriin?",
]
S04_Q_EN = [
    "Break down my spending last month into the three baskets.",
    "How did my money split across the three spending baskets last month?",
    "Show me my regular essentials, unexpected necessities, and everyday spending for last month.",
    "Where did my spending go across S-Bank's three baskets last month?",
]


def build_s04(ctx, cid: str, today: date, lang: str, variant: int) -> dict:
    q = (S04_Q_FI if lang == "fi" else S04_Q_EN)[variant % (len(S04_Q_FI) if lang == "fi" else len(S04_Q_EN))]
    s_iso, e_iso, m_num, y_num = _prev_month_bounds(today)
    args = {"start_date": s_iso, "end_date": e_iso}
    out_str, data = ctx.run_tool(cid, today, "get_basket_summary", args)

    b = data["baskets"]
    reg = b["regular_essentials"]
    unexp = b["unexpected_necessities"]
    every = b["everyday_spending"]
    tot = data["total_spending_eur"]

    reg_top = [c for c in reg["categories"][:2]]
    every_top = [c for c in every["categories"][:3]]
    unexp_top = [c for c in unexp["categories"][:2]]

    if lang == "fi":
        def _join_fi(items: list[str]) -> str:
            if len(items) <= 1:
                return items[0] if items else ""
            return ", ".join(items[:-1]) + " sekä " + items[-1]

        m_phrase = month_in_fi(m_num, y_num, today.year)
        reg_str = _join_fi([f"{CAT_FI[c['category']][0]} {eur_fi(c['total_eur'])}" for c in reg_top])
        ev_str = _join_fi([f"{CAT_FI[c['category']][0]} {eur_fi(c['total_eur'])}" for c in every_top])
        un_str = (
            _join_fi([f"{CAT_FI[c['category']][0]} {eur_fi(c['total_eur'])}" for c in unexp_top])
            if unexp_top else "ei ostoja tässä kuussa"
        )
        v = variant % 3
        if v == 0:
            ans = (
                f"Kulutit {m_phrase} yhteensä **{eur_fi(tot)}**. "
                f"Menosi jakautuivat kolmeen kulutuskategoriaan näin:\n\n"
                f"- **🏠 Välttämättömät menot:** {eur_fi(reg['total_eur'])}, eli {pct_fi(reg['share_pct'])} menoista. Suurimpia eriä olivat {reg_str}.\n"
                f"- **🔧 Yllättävät menot:** {eur_fi(unexp['total_eur'])}, osuus {pct_fi(unexp['share_pct'])}, {un_str}.\n"
                f"- **☕ Arjen kulutus:** {eur_fi(every['total_eur'])}, eli {pct_fi(every['share_pct'])} menoista. Eniten kului kohteisiin {ev_str}.\n\n"
                f"Luokittelu tehdään kauppiaan toimialan mukaan: esimerkiksi julkinen liikenne ja polttoaine kuuluvat välttämättömiin menoihin, "
                f"ja taksit arjen kulutukseen. Halutessasi katsomme tarkemmin, mistä arjen kulutus koostui."
            )
        elif v == 1:
            ans = (
                f"Kulutit {m_phrase} yhteensä **{eur_fi(tot)}**, ja menot jakautuivat kolmeen kulutuskategoriaan seuraavasti:\n\n"
                f"1. **🏠 Välttämättömät menot:** {eur_fi(reg['total_eur'])}, osuus {pct_fi(reg['share_pct'])}\n"
                f"   Suurimmat erät: {reg_str}.\n"
                f"2. **🔧 Yllättävät menot:** {eur_fi(unexp['total_eur'])}, osuus {pct_fi(unexp['share_pct'])}\n"
                f"   Sisältö: {un_str}.\n"
                f"3. **☕ Arjen kulutus:** {eur_fi(every['total_eur'])}, osuus {pct_fi(every['share_pct'])}\n"
                f"   Suurimmat erät: {ev_str}.\n\n"
                f"**Vinkki:** Välttämättömiin menoihin on vaikea vaikuttaa nopeasti, joten helpoimmat säästökohteet löytyvät yleensä arjen kulutuksesta."
            )
        else:
            ans = (
                f"Kulutit {m_phrase} yhteensä **{eur_fi(tot)}**:\n\n"
                f"- **🏠 Välttämättömät menot:** {eur_fi(reg['total_eur'])}, osuus {pct_fi(reg['share_pct'])}, suurimpina {reg_str}\n"
                f"- **🔧 Yllättävät menot:** {eur_fi(unexp['total_eur'])}, osuus {pct_fi(unexp['share_pct'])}, {un_str}\n"
                f"- **☕ Arjen kulutus:** {eur_fi(every['total_eur'])}, osuus {pct_fi(every['share_pct'])}, suurimpina {ev_str}\n\n"
                f"Palkka ja säästösiirrot pidetään kulutuskategorioiden ulkopuolella, jotta luvut kuvaavat todellista kulutustasi. "
                f"Voit itse nähdä jonkin ostoksen kuuluvan toiseen kategoriaan."
            )
    else:
        m_phrase_en = month_in_en(m_num, y_num, today.year)
        reg_str = ", ".join(f"{CAT_EN[c['category']]} {eur_en(c['total_eur'])}" for c in reg_top)
        ev_str = ", ".join(f"{CAT_EN[c['category']]} {eur_en(c['total_eur'])}" for c in every_top)
        un_str = (
            ", ".join(f"{CAT_EN[c['category']]} {eur_en(c['total_eur'])}" for c in unexp_top)
            if unexp_top else "none recorded"
        )
        ans = (
            f"Your spending {m_phrase_en} totalled **{eur_en(tot)}** across the three baskets:\n\n"
            f"- **🏠 Regular essentials:** {eur_en(reg['total_eur'])}, {pct_en(reg['share_pct'])} of spending, led by {reg_str}.\n"
            f"- **🔧 Unexpected necessities:** {eur_en(unexp['total_eur'])}, {pct_en(unexp['share_pct'])}, {un_str}.\n"
            f"- **☕ Everyday spending:** {eur_en(every['total_eur'])}, {pct_en(every['share_pct'])}, mainly {ev_str}.\n\n"
            f"**Tip:** Everyday spending is the easiest basket to adjust day to day. Ask if you'd like to test a what-if saving target on any of those categories."
        )

    return ctx.pack(cid, today, "S04_basket_summary_monthly", "coaching", lang, q,
                    [("call_1", "get_basket_summary", args, out_str)], ans)


# ---------------------------------------------------------------------------
# S05: Unexpected necessities & unusual purchases over 6 months (12 FI, 2 EN)
# ---------------------------------------------------------------------------

S05_Q_FI = [
    "Paljonko minulla on ollut yllättäviä menoja viimeisen puolen vuoden aikana?",
    "Millaisia yllättäviä tai poikkeuksellisen suuria ostoksia minulle on osunut viime kuukausina?",
    "Kuinka paljon rahaa on mennyt yllättäviin menoihin kuuden viime kuukauden aikana?",
    "Paljonko minun kannattaisi varata puskuria yllättäviin menoihin toteutuneen kulutukseni perusteella?",
]
S05_Q_EN = [
    "How much have I spent on unexpected necessities over the past six months?",
    "What unexpected or unusually large expenses have hit my account in the last 6 months?",
]


def build_s05(ctx, cid: str, today: date, lang: str, variant: int) -> dict:
    q = (S05_Q_FI if lang == "fi" else S05_Q_EN)[variant % (len(S05_Q_FI) if lang == "fi" else len(S05_Q_EN))]
    s_iso, e_iso = _n_complete_months_bounds(today, 6)
    args = {"start_date": s_iso, "end_date": e_iso}
    out_str, data = ctx.run_tool(cid, today, "get_basket_summary", args)

    unexp = data["baskets"]["unexpected_necessities"]
    unusual = data.get("unusual_purchases", [])

    if lang == "fi":
        # "Kotiin ja elektroniikkaan meni 423,44 € sekä terveyteen 270,00 €."
        top = unexp["categories"][:2]
        cats_fi = " sekä ".join(
            f"{CAT_FI[c['category']][1]}{' meni' if i == 0 else ''} {eur_fi(c['total_eur'])}" for i, c in enumerate(top)
        )
        where_line = f"{cap_first(cats_fi)}." if top else ""
        unusual_line = ""
        if unusual:
            u0 = unusual[0]
            unusual_line = (
                f" Lisäksi teit {date_fi(u0['date'])} poikkeuksellisen suuren {eur_fi(u0['amount_eur'])} ostoksen, "
                f"joka kuului kategoriaan {CAT_FI[u0['category']][0]}."
            )
        ans = (
            f"Kuuden viime kuukauden ajalla ({range_fi(s_iso, e_iso)}) kategoriaan **🔧 Yllättävät menot** kertyi yhteensä "
            f"**{eur_fi(unexp['total_eur'])}**, eli keskimäärin **{eur_fi(unexp['monthly_average_eur'])} kuukaudessa** "
            f"ja {pct_fi(unexp['share_pct'])} kaikista menoistasi.\n\n"
            f"{where_line}{unusual_line}\n\n"
            f"**Vinkki:** Yllättävät menot tulevat epätasaisesti. Kun siirrät noin {eur_fi(unexp['monthly_average_eur'])} "
            f"kuukaudessa säästötilille, puskurisi pysyy kunnossa."
        )
    else:
        cats_en = " and ".join(f"{CAT_EN[c['category']]} {eur_en(c['total_eur'])}" for c in unexp["categories"][:2])
        unusual_line = ""
        if unusual:
            u0 = unusual[0]
            unusual_line = (
                f" You also had an unusually large {eur_en(u0['amount_eur'])} one-off purchase on {date_en(u0['date'], True)} "
                f"in {CAT_EN[u0['category']]}."
            )
        ans = (
            f"Over the past 6 months ({range_en(s_iso, e_iso)}), your **🔧 Unexpected necessities** totalled **{eur_en(unexp['total_eur'])}**, "
            f"or **{eur_en(unexp['monthly_average_eur'])} per month** on average, making up {pct_en(unexp['share_pct'])} of total spending.\n\n"
            f"Main items: {cats_en or 'none recorded'}.{unusual_line}\n\n"
            f"**Tip:** Setting aside around {eur_en(unexp['monthly_average_eur'])} each month into a savings buffer helps smooth out lumpy costs like dental bills or home repairs."
        )

    return ctx.pack(cid, today, "S05_unexpected_and_buffer", "coaching", lang, q,
                    [("call_1", "get_basket_summary", args, out_str)], ans)


# ---------------------------------------------------------------------------
# S06: Salary sweep caveat in plain language (8 FI, 2 EN)
# ---------------------------------------------------------------------------

S06_Q_FI = [
    "Miltä viime kuun tuloni ja menoni näyttävät kokonaisuutena?",
    "Mihin rahani kuluivat viime kuussa tältä tililtä?",
    "Näytä viime kuun kulutukseni koreittain ja rahaliikenne tililläni.",
]
S06_Q_EN = [
    "Give me a full overview of my spending and money movements last month.",
    "Where did my money go from this account last month?",
]


def build_s06(ctx, cid: str, today: date, lang: str, variant: int) -> dict:
    q = (S06_Q_FI if lang == "fi" else S06_Q_EN)[variant % (len(S06_Q_FI) if lang == "fi" else len(S06_Q_EN))]
    s_iso, e_iso, m_num, y_num = _prev_month_bounds(today)
    args = {"start_date": s_iso, "end_date": e_iso}
    out_str, data = ctx.run_tool(cid, today, "get_basket_summary", args)

    b = data["baskets"]
    tot = data["total_spending_eur"]
    flows = {f["transaction_type"]: f["net_amount_eur"] for f in data["financial_flows"]}
    sal = flows.get("salary", 0.0)
    swept = abs(flows.get("salary_sweep", 0.0))
    swept_pct = data.get("swept_share_of_salary_pct") or 0.0

    if lang == "fi":
        m_phrase = month_in_fi(m_num, y_num, today.year)
        ans = (
            f"Tältä tililtä kirjatut kulutusmenosi {m_phrase} olivat yhteensä **{eur_fi(tot)}**:\n\n"
            f"- **🏠 Välttämättömät menot:** {eur_fi(b['regular_essentials']['total_eur'])}\n"
            f"- **🔧 Yllättävät menot:** {eur_fi(b['unexpected_necessities']['total_eur'])}\n"
            f"- **☕ Arjen kulutus:** {eur_fi(b['everyday_spending']['total_eur'])}\n\n"
            f"**Huomaa:** palkastasi {eur_fi(sal)} siirtyi toiselle tilille **{eur_fi(swept)}** eli {pct_fi(swept_pct)}. Tätä siirtoa ei lasketa kulutukseksi, mutta koska näen vain tämän tilin "
            f"tilitapahtumat, osa kiinteistä menoistasi, kuten asuminen tai laskut, saatetaan maksaa toiselta tililtä."
        )
    else:
        m_phrase_en = month_in_en(m_num, y_num, today.year)
        ans = (
            f"Recorded spending from this account {m_phrase_en} totalled **{eur_en(tot)}**:\n\n"
            f"- **🏠 Regular essentials:** {eur_en(b['regular_essentials']['total_eur'])}\n"
            f"- **🔧 Unexpected necessities:** {eur_en(b['unexpected_necessities']['total_eur'])}\n"
            f"- **☕ Everyday spending:** {eur_en(b['everyday_spending']['total_eur'])}\n\n"
            f"**Important note:** Out of your {eur_en(sal)} salary, **{eur_en(swept)}**, or {pct_en(swept_pct)}, left the account "
            f"as a recurring outgoing transfer. That transfer isn't counted as spending, and some of your mandatory bills, "
            f"such as housing or utilities, may be paid from another account not shown in this view."
        )

    return ctx.pack(cid, today, "S06_salary_sweep_caveat", "coaching", lang, q,
                    [("call_1", "get_basket_summary", args, out_str)], ans)


# ---------------------------------------------------------------------------
# S07: Spending by category — overview or single category (14 FI, 4 EN)
# ---------------------------------------------------------------------------

def build_s07(ctx, cid: str, today: date, lang: str, variant: int) -> dict:
    s_iso, e_iso, m_num, y_num = _prev_month_bounds(today)
    if variant % 2 == 0:
        # Top categories overview over last month
        args = {"start_date": s_iso, "end_date": e_iso}
        out_str, data = ctx.run_tool(cid, today, "get_spending_by_category", args)
        cats = data["categories"]
        tot = data["total_eur"]
        if lang == "fi":
            m_phrase = month_in_fi(m_num, y_num, today.year)
            qs = [
                "Mitkä olivat suurimmat menoluokkani viime kuussa?",
                "Näytä viime kuun kulutukseni kategorioittain suurimmasta pienimpään.",
                "Mihin kategorioihin rahani kuluivat eniten viime kuussa?",
            ]
            q = qs[variant % len(qs)]
            bullets = "\n".join(
                f"- **{cap_first(CAT_FI[c['category']][0])}:** {eur_fi(c['total_eur'])}"
                for c in cats[:5]
            )
            ans = (
                f"Kulutit {m_phrase} yhteensä **{eur_fi(tot)}**. "
                f"Viisi suurinta menoluokkaasi olivat:\n\n{bullets}\n\n"
                f"**Vinkki:** Jos jokin näistä luokista mietityttää, voin eritellä sen ostokset tarkemmin."
            )
        else:
            m_phrase_en = month_in_en(m_num, y_num, today.year)
            q = "What were my top spending categories last month?"
            bullets = "\n".join(
                f"- **{cap_first(CAT_EN[c['category']])}:** {eur_en(c['total_eur'])}"
                for c in cats[:5]
            )
            ans = (
                f"Your total spending {m_phrase_en} was **{eur_en(tot)}**. "
                f"Your top five categories were:\n\n{bullets}\n\n"
                f"Let me know if you'd like to drill into any of these by merchant type."
            )
    else:
        # 3-month average on a specific category
        s3, e3 = _n_complete_months_bounds(today, 3)
        cat_choices = ["Groceries", "Restaurants", "Lifestyle", "Transportation", "Home & Tech"]
        cat = cat_choices[(variant // 2) % len(cat_choices)]
        args = {"start_date": s3, "end_date": e3, "category": cat}
        out_str, data = ctx.run_tool(cid, today, "get_spending_by_category", args)
        mtypes = data["merchant_types"]
        if lang == "fi":
            nom, ill, _ = CAT_FI[cat]
            q = f"Paljonko minulla on kulunut {ill} kolmen viime kuukauden aikana?"
            m_lines = ", ".join(
                f"{MERCHANT_FI[m['merchant_type']][0]} {eur_fi(m['total_eur'])}"
                for m in mtypes[:3]
            )
            ans = (
                f"Kolmen viime kuukauden aikana ({range_fi(s3, e3)}) käytit kategoriaan **{nom}** yhteensä **{eur_fi(data['total_eur'])}**, "
                f"eli keskimäärin **{eur_fi(data['monthly_average_eur'])} kuukaudessa**.\n\n"
                f"Summa jakautui näin: {m_lines or 'ei ostoja jaksolla'}."
            )
        else:
            q = f"How much have I spent on {CAT_EN[cat]} over the last three months?"
            m_lines = ", ".join(
                f"{MERCHANT_EN[m['merchant_type']]} {eur_en(m['total_eur'])}"
                for m in mtypes[:3]
            )
            ans = (
                f"Over the last three months ({range_en(s3, e3)}), you spent **{eur_en(data['total_eur'])}** on **{CAT_EN[cat]}**, "
                f"an average of **{eur_en(data['monthly_average_eur'])} per month**.\n\n"
                f"Breakdown by merchant type: {m_lines or 'no purchases in this period'}."
            )

    return ctx.pack(cid, today, "S07_category_breakdown", "coaching", lang, q,
                    [("call_1", "get_spending_by_category", args, out_str)], ans)


# ---------------------------------------------------------------------------
# S08: Merchant-level queries (cafés, public transport, cinema, clothing, fuel, pharmacy) (15 FI, 3 EN)
# ---------------------------------------------------------------------------

S08_SPECS = [
    ("Restaurants", "fast food / café", "kahviloihin ja pikaruokaan", "on cafés and fast food"),
    ("Transportation", "public transport", "joukkoliikenteeseen", "on public transport"),
    ("Entertainment", "cinema", "elokuvateattereihin", "on cinema tickets"),
    ("Lifestyle", "clothing", "vaatekauppoihin", "on clothing"),
    ("Transportation", "fuel", "auton tankkaukseen", "on fuel"),
    ("Health", "pharmacy", "apteekkiostoihin", "at pharmacies"),
]


def build_s08(ctx, cid: str, today: date, lang: str, variant: int) -> dict:
    cat, mtype, fi_target, en_target = S08_SPECS[variant % len(S08_SPECS)]
    s_iso, e_iso, m_num, y_num = _prev_month_bounds(today)
    args = {"start_date": s_iso, "end_date": e_iso, "category": cat}
    out_str, data = ctx.run_tool(cid, today, "get_spending_by_category", args)
    row = next((m for m in data["merchant_types"] if m["merchant_type"] == mtype), None)
    amt = row["total_eur"] if row else 0.0
    cat_tot = data["total_eur"]

    if lang == "fi":
        m_phrase = month_in_fi(m_num, y_num, today.year)
        q_templates = [
            f"Kuinka paljon rahaa meni {fi_target} viime kuussa?",
            f"Paljonko kulutin {fi_target} {FI_MONTH_IN[m_num]}?",
            f"Näetkö tilitapahtumistani, paljonko käytin {fi_target} viime kuukaudelta?",
        ]
        q = q_templates[variant % len(q_templates)]
        m_nom = MERCHANT_FI[mtype][0]
        basket_note = (
            "välttämättömiin menoihin"
            if row and "regular_essentials" in row.get("baskets", [])
            else "arjen kulutukseen"
        )
        ans = (
            f"Käytit {m_phrase} {fi_target} yhteensä **{eur_fi(amt)}**.\n\n"
            f"Kaikkiaan {CAT_FI[cat][1]} meni samassa kuussa {eur_fi(cat_tot)}. "
            f"{cap_first(m_nom)} lasketaan {basket_note}."
        )
    else:
        m_phrase_en = month_in_en(m_num, y_num, today.year)
        q = f"How much did I spend {en_target} last month?"
        ans = (
            f"You spent **{eur_en(amt)}** {en_target} {m_phrase_en}, "
            f"out of {eur_en(cat_tot)} total in {CAT_EN[cat]}."
        )

    return ctx.pack(cid, today, "S08_merchant_type_detail", "coaching", lang, q,
                    [("call_1", "get_spending_by_category", args, out_str)], ans)


# ---------------------------------------------------------------------------
# S09: Individual transactions & 6-month balance trend (13 FI, 3 EN)
# ---------------------------------------------------------------------------

def build_s09(ctx, cid: str, today: date, lang: str, variant: int) -> dict:
    if variant % 2 == 0:
        s_iso, e_iso, m_num, y_num = _prev_month_bounds(today)
        args = {"start_date": s_iso, "end_date": e_iso, "order": "largest", "limit": 10}
        out_str, data = ctx.run_tool(cid, today, "get_transactions", args)
        txs = [t for t in data["transactions"] if t["amount_eur"] < 0 and t["merchant_type"] is not None][:3]
        if lang == "fi":
            m_phrase = month_in_fi(m_num, y_num, today.year)
            q = f"Mitkä olivat kolme suurinta yksittäistä menoerääni {FI_MONTH_IN[m_num]}?"
            lines = "\n".join(
                f"- **{eur_fi(abs(t['amount_eur']))}**: {cap_first(CAT_FI.get(t['category'], (t['category'].lower(),))[0])}"
                for t in txs
            )
            ans = (
                f"Kolme suurinta yksittäistä menoerääsi {m_phrase} olivat:\n\n"
                f"{lines}\n\n"
                f"Haluatko tarkastella jonkin tietyn menoluokan ostoksia vielä tarkemmin?"
            )
        else:
            m_phrase_en = month_in_en(m_num, y_num, today.year)
            q = f"What were my three biggest single expenses in {EN_MONTH[m_num]}?"
            lines = "\n".join(
                f"- **{eur_en(abs(t['amount_eur']))}**: {cap_first(CAT_EN.get(t['category'], t['category']))}"
                for t in txs
            )
            ans = (
                f"Your three largest single expenses {m_phrase_en} were:\n\n"
                f"{lines}"
            )
        return ctx.pack(cid, today, "S09_transactions_and_balance_trend", "coaching", lang, q,
                        [("call_1", "get_transactions", args, out_str)], ans)
    else:
        months = 6
        args = {"months": months}
        out_str, data = ctx.run_tool(cid, today, "get_monthly_balance_trend", args)
        bals = data["balances"]
        first_b, last_b = bals[0], bals[-1]
        diff = data["change_eur"]
        if lang == "fi":
            q = "Miten käyttötilini saldo on kehittynyt kuuden viime kuukauden aikana?"
            direction = (
                f"noussut **{eur_fi(diff)}**" if diff > 0
                else (f"laskenut **{eur_fi(abs(diff))}**" if diff < 0 else "pysynyt samalla tasolla")
            )
            bullets = "\n".join(f"- **{cap_first(month_ym_fi(b['month']))}:** {eur_fi(b['balance_eur'])}" for b in bals)
            ans = (
                f"Käyttötilisi kuukauden lopun saldo on kuuden kuukauden aikana {direction}:\n\n{bullets}\n\n"
                f"**Vinkki:** Jos tilille kertyy toistuvasti ylimääräistä saldoa, osan voi siirtää erilliselle säästötilille puskuriksi."
            )
        else:
            q = "How has my account balance trended over the past 6 months?"
            direction = (
                f"grown by **{eur_en(diff)}**" if diff > 0
                else (f"decreased by **{eur_en(abs(diff))}**" if diff < 0 else "stayed flat")
            )
            bullets = "\n".join(f"- **{month_ym_en(b['month'])}:** {eur_en(b['balance_eur'])}" for b in bals)
            ans = (
                f"Over the past 6 months, your end-of-month balance has {direction}:\n\n{bullets}"
            )
        return ctx.pack(cid, today, "S09_transactions_and_balance_trend", "coaching", lang, q,
                        [("call_1", "get_monthly_balance_trend", args, out_str)], ans)


# ---------------------------------------------------------------------------
# S10: Peer comparison + safe-to-spend 2-tool chain (13 FI, 3 EN)
# ---------------------------------------------------------------------------

S10_Q_FI = [
    "Miten kulutukseni vertautuu muihin samanikäisiin?",
    "Käytänkö arjen asioihin enemmän vai vähemmän rahaa kuin ikäiseni keskimäärin?",
    "Millainen rahankäyttäjä olen verrattuna muihin samanikäisiin asiakkaisiin?",
    "Mitkä menoni erottuvat eniten ikäryhmäni tyypillisestä kulutuksesta?",
]
S10_Q_EN = [
    "How does my spending compare with other people my age?",
    "Where do my spending habits stand out compared with my age group?",
]


def build_s10(ctx, cid: str, today: date, lang: str, variant: int) -> dict:
    q = (S10_Q_FI if lang == "fi" else S10_Q_EN)[variant % (len(S10_Q_FI) if lang == "fi" else len(S10_Q_EN))]
    p_str, p = ctx.run_tool(cid, today, "compare_with_peers", {})
    s_str, s = ctx.run_tool(cid, today, "get_safe_to_spend", {})

    ag = p["age_group"]
    per = p["period"]
    tot_me = p["total"]["my_monthly"]
    tot_diff = p["total"]["age_group"]["difference_from_median_pct"]
    lvl = p["profile"]["overall_level"]
    above = p["profile"]["above_peers"][:2]
    below = p["profile"]["below_peers"][:2]
    ev_bsk = p["by_basket"]["everyday_spending"]
    ev_diff = ev_bsk["age_group"]["difference_from_median_pct"]
    safe_wk = s["safe_to_spend_this_week"]

    def _vs_median_fi(diff_pct: float | None, fallback_lvl: str = "") -> str:
        if diff_pct is None or diff_pct == 0:
            return fallback_lvl or "saman verran kuin ikäisesi tyypillisesti"
        if diff_pct > 0:
            return f"{pct_fi(abs(diff_pct), 0)} enemmän kuin ikäisesi tyypillisesti"
        return f"{pct_fi(abs(diff_pct), 0)} vähemmän kuin ikäisesi tyypillisesti"

    def _vs_median_en(diff_pct: float | None) -> str:
        if diff_pct is None or diff_pct == 0:
            return "right in line with your age group's median"
        if diff_pct > 0:
            return f"{pct_en(abs(diff_pct), 0)} more than your age group's median"
        return f"{pct_en(abs(diff_pct), 0)} less than your age group's median"

    if lang == "fi":
        lvl_fi = {
            "above_peers": "keskimääräistä korkeampaa",
            "below_peers": "keskimääräistä maltillisempaa",
            "typical": "ikäryhmällesi tyypillisellä tasolla",
        }[lvl]
        tot_clause = (
            f"eli {pct_fi(abs(tot_diff), 0)} {'enemmän' if tot_diff > 0 else 'vähemmän'} kuin {ag}-vuotiaat tyypillisesti"
            if tot_diff else lvl_fi
        )
        parts = []
        for a in above:
            cat_diff = p["by_category"][a["category"]]["age_group"]["difference_from_median_pct"]
            cmp_txt = (
                _vs_median_fi(cat_diff)
                if cat_diff is not None
                else f"enemmän kuin {pct_fi(a['spends_more_than_pct_of_peers'])} ikäisistäsi"
            )
            parts.append(f"- {cap_first(CAT_FI[a['category']][1])} käytät {eur_fi(a['my_monthly'])}/kk, eli {cmp_txt}.")
        for b in below:
            if not b["my_monthly"]:
                continue  # "0,00 €/kk, eli 100 % vähemmän" says nothing useful
            cat_diff = p["by_category"][b["category"]]["age_group"]["difference_from_median_pct"]
            cmp_txt = (
                _vs_median_fi(cat_diff)
                if cat_diff is not None
                else f"vähemmän kuin {pct_fi(b['spends_less_than_pct_of_peers'])} ikäisistäsi"
            )
            parts.append(f"- {cap_first(CAT_FI[b['category']][1])} käytät {eur_fi(b['my_monthly'])}/kk, eli {cmp_txt}.")
        if not parts:
            parts.append("- Yksittäiset kulutuskategoriasi ovat hyvin lähellä ikäistesi tyypillistä tasoa.")
        standout_block = "\n".join(parts)

        ans = (
            f"Viimeisen 12 täyden kuukauden ajalla ({range_fi(per['start_date'], per['end_date'])}) kokonaiskulutuksesi "
            f"oli **{eur_fi(tot_me)}/kk**, {tot_clause}.\n\n"
            f"{standout_block}\n"
            f"- ☕ Arjen kulutukseen käytät {eur_fi(ev_bsk['my_monthly'])}/kk, eli {_vs_median_fi(ev_diff)}.\n\n"
            f"Asumista, sähköä ja vettä ei verrata, koska ne riippuvat asumismuodosta. "
            f"Oman budjettisi mukaan turvallinen käyttövarasi tälle viikolle on **{eur_fi(safe_wk)}**."
        )
    else:
        tot_clause_en = (
            f"or {pct_en(abs(tot_diff), 0)} {'above' if tot_diff > 0 else 'below'} the {ag} age group's median"
            if tot_diff else "right around your age group's median"
        )
        parts = []
        for a in above:
            cat_diff = p["by_category"][a["category"]]["age_group"]["difference_from_median_pct"]
            cmp_txt = (
                _vs_median_en(cat_diff)
                if cat_diff is not None
                else f"more than {pct_en(a['spends_more_than_pct_of_peers'])} of people your age"
            )
            parts.append(f"- On *{CAT_EN[a['category']]}*, you spend {eur_en(a['my_monthly'])}/month, which is {cmp_txt}.")
        for b in below:
            if not b["my_monthly"]:
                continue  # "0,00 €/kk, eli 100 % vähemmän" says nothing useful
            cat_diff = p["by_category"][b["category"]]["age_group"]["difference_from_median_pct"]
            cmp_txt = (
                _vs_median_en(cat_diff)
                if cat_diff is not None
                else f"less than {pct_en(b['spends_less_than_pct_of_peers'])} of people your age"
            )
            parts.append(f"- On *{CAT_EN[b['category']]}*, you spend {eur_en(b['my_monthly'])}/month, which is {cmp_txt}.")
        if not parts:
            parts.append("- Across individual habit categories, your spending sits right near your age group's median.")
        standout_block = "\n".join(parts)

        ans = (
            f"Over the last 12 complete months ({range_en(per['start_date'], per['end_date'])}), your total spending averaged "
            f"**{eur_en(tot_me)}/month**, {tot_clause_en}.\n\n"
            f"{standout_block}\n"
            f"- On **☕ Everyday spending**, you spend {eur_en(ev_bsk['my_monthly'])}/month, which is {_vs_median_en(ev_diff)}.\n\n"
            f"Based on your own budget and balance today, your safe-to-spend amount this week is **{eur_en(safe_wk)}**."
        )

    return ctx.pack(
        cid, today, "S10_peer_comparison_and_budget", "coaching", lang, q,
        [("call_1", "compare_with_peers", {}, p_str), ("call_2", "get_safe_to_spend", {}, s_str)],
        ans,
    )


# ---------------------------------------------------------------------------
# S11: What-if savings calculation 2-tool chain (11 FI, 3 EN)
# ---------------------------------------------------------------------------

S11_CUTS = [
    ("Restaurants", 25),
    ("Entertainment", 30),
    ("Lifestyle", 20),
    ("Restaurants", 50),
]


def build_s11(ctx, cid: str, today: date, lang: str, variant: int) -> dict:
    cat, pct = S11_CUTS[variant % len(S11_CUTS)]
    s6, e6 = _n_complete_months_bounds(today, 6)
    cat_args = {"start_date": s6, "end_date": e6, "category": cat}
    c_str, c_data = ctx.run_tool(cid, today, "get_spending_by_category", cat_args)
    avg_m = c_data["monthly_average_eur"]

    w_args = {"monthly_by_category": {cat: avg_m}, "reductions_pct": {cat: pct}}
    w_str, w_data = ctx.run_tool(cid, today, "calculate_what_if", w_args)
    m_save = w_data["monthly_saving"]
    y_save = w_data["yearly_saving"]
    new_m = w_data["by_category"][cat]["new_monthly_spending"]

    if lang == "fi":
        nom, ill, elat = CAT_FI[cat]
        q = f"Paljonko säästäisin kuukaudessa ja vuodessa, jos vähentäisin kuluja {elat} {pct} %?"
        ans = (
            f"Jos käytät {ill} {pct_fi(pct, 0)} vähemmän, säästät **{eur_fi(m_save)} kuukaudessa** "
            f"ja **{eur_fi(y_save)} vuodessa**.\n\n"
            f"Kuuden viime täyden kuukauden ({range_fi(s6, e6)}) perusteella käytit {ill} keskimäärin "
            f"{eur_fi(avg_m)}/kk. Muutoksen jälkeen uusi kuukausitaso olisi {eur_fi(new_m)}/kk.\n\n"
            f"**Vinkki:** Säästyvät {eur_fi(m_save)} voit siirtää palkkapäivänä automaattisesti säästötilille tai Säästäjä-palveluun."
        )
    else:
        q = f"How much would I save per month and per year if I trimmed my {CAT_EN[cat]} spending by {pct}%?"
        ans = (
            f"Trimming **{CAT_EN[cat]}** by {pct_en(pct, 0)} would save you **{eur_en(m_save)} per month** "
            f"and **{eur_en(y_save)} per year**.\n\n"
            f"Over the last 6 complete months ({range_en(s6, e6)}), you averaged {eur_en(avg_m)}/month on {CAT_EN[cat]}; "
            f"after a {pct_en(pct, 0)} cut, that drops to {eur_en(new_m)}/month.\n\n"
            f"**Tip:** Automating a {eur_en(m_save)} recurring transfer right after payday makes the saving stick."
        )

    return ctx.pack(
        cid, today, "S11_what_if_reduction", "coaching", lang, q,
        [
            ("call_1", "get_spending_by_category", cat_args, c_str),
            ("call_2", "calculate_what_if", w_args, w_str),
        ],
        ans,
    )


# ---------------------------------------------------------------------------
# S12: Safe-to-save monthly surplus 2-tool chain (8 FI, 2 EN)
# ---------------------------------------------------------------------------

def build_s12(ctx, cid: str, today: date, lang: str, variant: int) -> dict:
    s6, e6 = _n_complete_months_bounds(today, 6)
    b_args = {"start_date": s6, "end_date": e6}
    b_str, b_data = ctx.run_tool(cid, today, "get_basket_summary", b_args)

    income_avg = b_data["monthly_income_eur"]  # added up by the tool, not here
    reg_avg = b_data["baskets"]["regular_essentials"]["monthly_average_eur"]
    unexp_avg = b_data["baskets"]["unexpected_necessities"]["monthly_average_eur"]
    ev_avg = b_data["baskets"]["everyday_spending"]["monthly_average_eur"]

    sv_args = {
        "monthly_income": income_avg,
        "monthly_mandatory_regular": reg_avg,
        "monthly_mandatory_irregular": unexp_avg,
        "monthly_everyday": ev_avg,
    }
    sv_str, sv_data = ctx.run_tool(cid, today, "calculate_safe_to_save", sv_args)
    m_save = sv_data["safe_to_save_monthly"]
    y_save = sv_data["safe_to_save_yearly"]
    surplus = sv_data["surplus"]

    if lang == "fi":
        qs = [
            "Kuinka paljon pystyisin laittamaan säästöön kuukausittain ilman, että arki kiristyy liikaa?",
            "Paljonko minun olisi turvallista siirtää puskuriin joka kuukausi?",
            "Millainen kuukausisäästösumma sopisi nykyisiin tuloihini ja menoihini?",
        ]
        q = qs[variant % len(qs)]
        if m_save > 0:
            ans = (
                f"Kuuden viime kuukauden ({range_fi(s6, e6)}) lukujesi perusteella voit laittaa turvallisesti säästöön "
                f"**{eur_fi(m_save)} kuukaudessa**, eli yhteensä **{eur_fi(y_save)} vuodessa**.\n\n"
                f"Tulosi ovat olleet keskimäärin {eur_fi(income_avg)}/kk ja menosi {eur_fi(sv_data['total_monthly_spending'])}/kk. "
                f"Kuukaudessa on jäänyt yli {eur_fi(surplus)}. Siitä jätetään vielä viidennes liikkumavaraksi käyttötilille, "
                f"jotta kuukausivaihtelut eivät kiristä arkea.\n\n"
                f"**Vinkki:** Voit aloittaa kerryttämällä puskuria esimerkiksi S-Tuottotilille heti palkkapäivänä."
            )
        else:
            ans = (
                f"Viimeisen kuuden kuukauden ({range_fi(s6, e6)}) keskiarvoilla {eur_fi(income_avg)}/kk tulosi ja "
                f"{eur_fi(sv_data['total_monthly_spending'])}/kk kulutusmenosi eivät jätä valmista kuukausittaista ylijäämää, "
                f"joten turvallinen säästösumma on nyt **{eur_fi(0)}/kk**.\n\n"
                f"Puskuria voi silti alkaa kerryttää pienin askelin, jos nipistät hieman arjen kulutuksesta, joka on ollut {eur_fi(ev_avg)}/kk. "
                f"Katsotaanko, mistä menoluokasta löytyisi helpoin 20–30 € kuukausisäästö?"
            )
    else:
        q = "How much could I safely move into savings each month based on my recent history?"
        if m_save > 0:
            ans = (
                f"Based on the last 6 complete months ({range_en(s6, e6)}), you can safely save **{eur_en(m_save)} per month**, "
                f"or **{eur_en(y_save)} per year**.\n\n"
                f"Your average monthly income of {eur_en(income_avg)} minus total spending of {eur_en(sv_data['total_monthly_spending'])} "
                f"leaves a {eur_en(surplus)} monthly surplus, and keeping 20% of that surplus on your S-Tili current account "
                f"gives you a comfortable everyday cushion."
            )
        else:
            ans = (
                f"Over the past 6 months ({range_en(s6, e6)}), your average spending of {eur_en(sv_data['total_monthly_spending'])}/month "
                f"has matched or exceeded your average income of {eur_en(income_avg)}/month, so your safe automatic monthly saving right now is **{eur_en(0)}**.\n\n"
                f"If you'd like to start building a buffer, trimming a small slice of your {eur_en(ev_avg)}/month everyday spending is the easiest place to start."
            )

    return ctx.pack(
        cid, today, "S12_safe_to_save_monthly", "coaching", lang, q,
        [
            ("call_1", "get_basket_summary", b_args, b_str),
            ("call_2", "calculate_safe_to_save", sv_args, sv_str),
        ],
        ans,
    )


# ---------------------------------------------------------------------------
# S13: S-Pankki vocabulary explanations & greetings (8 FI, 2 EN)
# ---------------------------------------------------------------------------

S13_CONCEPTS_FI = [
    (
        "Mitä eroa on taloudellisella puskurilla ja kuukausisäästämisellä, ja mitä hätävara tarkoittaa?",
        "Nämä täydentävät toisiaan arjen taloudessa:\n\n"
        "- **Puskuri eli hätävara:** helposti nostettava taloudellinen puskuri esimerkiksi säästötilillä tai S-Tuottotilillä yllättäviä välttämättömiä menoja varten, kuten hammaslääkäriä tai rikkoutunutta kodinkonetta varten.\n"
        "- **Kuukausisäästäminen:** säännöllistä säästämistä pidemmän ajan tavoitteisiin esimerkiksi tilille tai rahastoon. Rahastosäästämiseen liittyy aina tuoton lisäksi myös arvonvaihtelun riski.\n\n"
        "**Vinkki:** Usein on mukavinta kerryttää ensin puskuri arjen yllätyksiin, jotta sijoituksiin ei tarvitse koskea tiukan paikan tullen."
    ),
    (
        "Mitä tarkoittaa katevaraus käyttötililläni?",
        "**Katevaraus** on korttiostosta tehty väliaikainen varaus ennen kuin maksu kirjautuu lopullisesti tilitapahtumiin.\n\n"
        "Kun maksat esimerkiksi S-Etukortti Visa Debit -kortilla, summa varataan heti tilin käytettävissä olevista varoista, vaikka pelkkä tilin saldo ei aina vielä näytä veloitusta kirjattuna tapahtumana. Siksi ostoksia tehdessä kannattaa seurata käytettävissä olevaa rahamäärää."
    ),
    (
        "Mikä ero on e-laskulla ja suoramaksulla S-Pankissa?",
        "Molemmat helpottavat toistuvien laskujen hoitamista, mutta toimivat eri tavalla:\n\n"
        "- **E-lasku:** saapuu sähköisenä S-mobiiliin ja verkkopankkiin. Voit tarkistaa ja hyväksyä laskun itse tai asettaa sille automaattisen maksamisen eräpäivänä.\n"
        "- **Suoramaksu:** on tarkoitettu asiakkaille, jotka eivät käytä verkkopankkia. Laskuttaja lähettää ennakkoilmoituksen postitse, ja pankki veloittaa laskun tililtä automaattisesti eräpäivänä.\n\n"
        "S-mobiilin käyttäjälle **e-lasku** on yleensä vaivattomin tapa pitää kiinteät menot ajan tasalla."
    ),
    (
        "Mitä eroa on lainan lyhennyksellä ja kuukausierällä?",
        "Näillä kahdella sanalla on tärkeä ero:\n\n"
        "- **Lyhennys:** se osa maksusta, joka pienentää itse lainapääomaa.\n"
        "- **Kuukausierä:** koko kuukausittain maksettava summa, joka sisältää lyhennyksen lisäksi lainan viitekorosta ja marginaalista koostuvan koron sekä mahdolliset kulut.\n\n"
        "Esimerkiksi **lyhennysvapaa** tarkoittaa jaksoa, jolloin lainapääomaa ei lyhennetä, mutta korot ja kulut maksetaan silti sopimuksen mukaisesti."
    ),
    (
        "Mitä tarkoittavat kortin luottoraja ja turvaraja?",
        "Ne koskevat eri asioita maksukortin käytössä:\n\n"
        "- **Luottoraja:** kortin Credit-ominaisuuteen sovittu enimmäisluotto, jonka puitteissa luottoa voi käyttää.\n"
        "- **Turvaraja:** itse asettamasi käyttörajoitus kortin päiväkohtaisille ostoille, käteisnostoille tai verkkomaksuille sekä Debit- että Credit-puolella.\n\n"
        "**Vinkki:** Sopivat turvarajat S-mobiilissa parantavat korttiturvallisuutta arjessa."
    ),
    (
        "Miten Säästäjä ja Bonus liittyvät toisiinsa S-mobiilissa?",
        "**Bonus** on S-ryhmän asiakasomistajille ostoksista kertyvä etu, joka maksetaan S-Tilille. **Säästäjä** puolestaan on S-mobiilin palvelu, jolla voit säästää arjen ohessa esimerkiksi korttiostosten yhteydessä tai ohjata maksettavan Bonuksen rahastosäästöön.\n\n"
        "Muista, että rahastosäästämiseen liittyy aina sijoitusriski, kun taas tilisäästäminen kerryttää varoja ilman arvonvaihtelua. Sinulle sopivan tavan valintaan saat apua S-mobiilin Säästäjä-polusta tai S-Pankin asiantuntijoilta."
    ),
    (
        "Hei! Miten voit auttaa minua omien raha-asioideni kanssa?",
        "Hei! Autan sinua hahmottamaan omaa rahankäyttöäsi ja suunnittelemaan arjen budjettia selkeästi.\n\n"
        "Voit kysyä minulta esimerkiksi:\n"
        "- Mihin rahani menivät viime kuussa kolmeen kulutuskategoriaan jaettuna?\n"
        "- Paljonko voin turvallisesti käyttää rahaa tällä viikolla ennen palkkapäivää?\n"
        "- Paljonko säästäisin vuodessa, jos vähentäisin ravintolakuluja 20 %?\n"
        "- Millainen kuluttaja olen verrattuna muihin ikäisiini?\n\n"
        "Mistä haluaisit aloittaa?"
    ),
    (
        "Mitä todellinen vuosikorko kertoo pelkkään lainan korkoon verrattuna?",
        "**Lainan korko**, kuten Euribor-viitekorko ja asiakaskohtainen marginaali, kertoo vain varsinaisen korkoprosentin. **Todellinen vuosikorko** sen sijaan kokoaa yhteen sekä koron että kaikki lainaan liittyvät avaus- ja tilinhoitomaksut vuositasolla.\n\n"
        "Siksi eri luottoja vertaillessa kannattaa aina katsoa sekä todellista vuosikorkoa että lainan kokonaiskustannuksia pelkän kuukausierän sijaan."
    ),
]

S13_CONCEPTS_EN = [
    (
        "What's the difference between S-Tili, Bonus, and Säästäjä in S-mobiili?",
        "Here is how those three fit together in S-Pankki:\n\n"
        "- **S-Tili:** S-Pankki's everyday current account used for salary, bills, and card payments.\n"
        "- **Bonus:** the purchase-based reward earned by S Group co-op members and paid out to S-Tili.\n"
        "- **Säästäjä:** S-mobiili's savings service that lets you save small amounts alongside card purchases or direct Bonus into funds. Note that fund investing carries market risk, unlike cash deposits.\n\n"
        "Would you like to check your current S-Tili budget or recent spending?"
    ),
    (
        "Hello! What kind of money questions can I ask you?",
        "Hello! I'm here to help you explore your spending and plan your everyday budget.\n\n"
        "You can ask me things like:\n"
        "- Where did my money go last month across the three spending baskets?\n"
        "- What can I safely spend this week before payday?\n"
        "- How much would I save a year if I cut dining out by 20%?\n"
        "- How does my spending compare with others my age?\n\n"
        "What would you like to look at first?"
    ),
]


def build_s13(ctx, cid: str, today: date, lang: str, variant: int) -> dict:
    pool = S13_CONCEPTS_FI if lang == "fi" else S13_CONCEPTS_EN
    q, ans = pool[variant % len(pool)]
    return ctx.pack(cid, today, "S13_vocabulary_and_capabilities", "coaching", lang, q, [], ans)
