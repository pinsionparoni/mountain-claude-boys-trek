"""Borderline, advice-limit, refusal, and care scenarios S14-S22 (84 examples: 66 FI, 18 EN)."""

from __future__ import annotations

from datetime import date, timedelta

from training.formatting import (
    CAT_EN,
    CAT_FI,
    EN_MONTH,
    FI_MONTH_IN,
    MERCHANT_EN,
    MERCHANT_FI,
    date_en,
    date_fi,
    eur_en,
    eur_fi,
    month_in_en,
    month_in_fi,
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


# ---------------------------------------------------------------------------
# S14: Borderline / awkward-but-allowed neutral spending (13 FI, 3 EN)
# Bars, nightlife, alcohol card note, entertainment/events — zero moralising.
# ---------------------------------------------------------------------------

def build_s14(ctx, cid: str, today: date, lang: str, variant: int) -> dict:
    mode = variant % 3
    if mode == 0:
        # Bar & nightlife spend in previous complete month
        s_iso, e_iso, m_num, y_num = _prev_month_bounds(today)
        args = {"start_date": s_iso, "end_date": e_iso, "category": "Restaurants"}
        out_str, data = ctx.run_tool(cid, today, "get_spending_by_category", args)
        bar_row = next((r for r in data.get("merchant_types", []) if r["merchant_type"] == "bar"), None)
        bar_tot = bar_row["total_eur"] if bar_row else 0.0
        bar_cnt = bar_row["transaction_count"] if bar_row else 0
        rest_tot = data["total_eur"]

        if lang == "fi":
            m_phrase = month_in_fi(m_num, y_num, today.year)
            q_pool = [
                f"Paljonko rahaa minulla meni baari-iltoihin {FI_MONTH_IN[m_num]}?",
                f"Kuinka paljon kulutin baareihin {FI_MONTH_IN[m_num]}?",
                f"Näytä paljonko käytin korttia baareissa {FI_MONTH_IN[m_num]}.",
                "Tarkistatko baariostosteni yhteissumman viime kuulta?",
                "Paljonko baarit maksoivat minulle viime kuussa?",
            ]
            q = q_pool[(variant // 3) % len(q_pool)]
            if bar_tot > 0:
                ans = (
                    f"Käytit baareihin {m_phrase} yhteensä **{eur_fi(bar_tot)}**.\n\n"
                    f"Ravintoloihin meni samassa kuussa yhteensä {eur_fi(rest_tot)}, "
                    f"ja ne kuuluvat kategoriaan ☕ Arjen kulutus. Haluatko katsoa myös pidemmän aikavälin keskiarvon?"
                )
            else:
                ans = (
                    f"Tilitapahtumissasi ei näy yhtään baariostoa {m_phrase}, eli summa oli **{eur_fi(0)}**.\n\n"
                    f"Ravintoloihin meni samassa kuussa yhteensä {eur_fi(rest_tot)}."
                )
        else:
            m_phrase_en = month_in_en(m_num, y_num, today.year)
            q = f"How much did my bar nights add up to in {EN_MONTH[m_num]}?"
            if bar_tot > 0:
                ans = (
                    f"You spent **{eur_en(bar_tot)}** at bars {m_phrase_en}.\n\n"
                    f"Your overall restaurant total for the month was {eur_en(rest_tot)}, which is part of everyday spending."
                )
            else:
                ans = (
                    f"You had **{eur_en(0)}** in bar transactions {m_phrase_en}. "
                    f"Other restaurant spending for the month totalled {eur_en(rest_tot)}."
                )
        return ctx.pack(cid, today, "S14_borderline_neutral_spending", "borderline", lang, q,
                        [("call_1", "get_spending_by_category", args, out_str)], ans)

    elif mode == 1:
        # Alcohol / drinks question — neutral answer + factual card-category note
        s3, e3 = _n_complete_months_bounds(today, 3)
        args = {"start_date": s3, "end_date": e3, "category": "Restaurants"}
        out_str, data = ctx.run_tool(cid, today, "get_spending_by_category", args)
        bar_row = next((r for r in data.get("merchant_types", []) if r["merchant_type"] == "bar"), None)
        bar_tot = bar_row["total_eur"] if bar_row else 0.0
        bar_avg = bar_row["monthly_average_eur"] if bar_row else 0.0
        rest_tot = data["total_eur"]

        if lang == "fi":
            q_pool = [
                "Näkyykö tilitapahtumissani, paljonko minulla kuluu rahaa alkoholijuomiin ja anniskelupaikkoihin?",
                "Kuinka paljon rahaa olen käyttänyt juomiin ja baareihin viimeisen kolmen kuukauden aikana?",
                "Pystytkö erittelemään, paljonko kortillani on mennyt alkoholiin tai baarikäynteihin kolmessa kuussa?",
                "Paljonko kolmen viime kuukauden kulutuksestani on mennyt baareihin ja juomiin?",
            ]
            q = q_pool[(variant // 3) % len(q_pool)]
            ans = (
                f"Viimeisen kolmen täyden kuukauden aikana ({range_fi(s3, e3)}) korttiostosi baareissa olivat yhteensä "
                f"**{eur_fi(bar_tot)}**, eli keskimäärin {eur_fi(bar_avg)}/kk.\n\n"
                f"Ravintoloihin meni samalla ajalla yhteensä {eur_fi(rest_tot)}. "
                f"Baarit näkyvät tiedoissa omana ryhmänään. Ravintola-aterian tai ruokakaupan ostosten yhteydessä "
                f"ostetut juomat sisältyvät kuitenkin näiden ostosten summaan, joten niitä ei voi erottaa."
            )
        else:
            q = "Can you see from my card data how much I've spent on drinks and bars over the past 3 months?"
            ans = (
                f"Over the last 3 complete months ({range_en(s3, e3)}), your card purchases at bars totalled "
                f"**{eur_en(bar_tot)}**, averaging {eur_en(bar_avg)}/month.\n\n"
                f"Your broader restaurant total over the same period was {eur_en(rest_tot)}. "
                f"One practical note on bank data: card transactions identify bar merchants separately, whereas drinks bought "
                f"with a restaurant meal or supermarket groceries are included in those merchant totals rather than split by item."
            )
        return ctx.pack(cid, today, "S14_borderline_neutral_spending", "borderline", lang, q,
                        [("call_1", "get_spending_by_category", args, out_str)], ans)

    else:
        # Entertainment / events / leisure over 3 months — neutral breakdown
        s3, e3 = _n_complete_months_bounds(today, 3)
        args = {"start_date": s3, "end_date": e3, "category": "Entertainment"}
        out_str, data = ctx.run_tool(cid, today, "get_spending_by_category", args)
        tot = data["total_eur"]
        avg_m = data["monthly_average_eur"]
        top_m = data.get("merchant_types", [])[:2]

        if lang == "fi":
            q_pool = [
                "Meneekö minulla paljon rahaa juhlimiseen, tapahtumiin ja vapaa-ajan menoihin?",
                "Paljonko olen käyttänyt viihteeseen ja tapahtumalippuihin kolmen viime kuukauden aikana?",
                "Näytä kolmen kuukauden yhteenveto viihteen ja vapaa-ajan kulutuksestani.",
                "Kuinka suuri summa minulla kuluu kuukaudessa viihteeseen ja rientoihin?",
                "Montako euroa meni viihteeseen kolmen viime kuukauden aikana?",
            ]
            q = q_pool[(variant // 3) % len(q_pool)]
            if top_m:
                m_detail = " sekä ".join(f"{MERCHANT_FI[r['merchant_type']][0]} {eur_fi(r['total_eur'])}" for r in top_m)
                detail_sentence = f"Suurimmat alaluokat olivat {m_detail}. "
            else:
                detail_sentence = ""
            ans = (
                f"Viimeisen kolmen täyden kuukauden aikana ({range_fi(s3, e3)}) kulutit viihteeseen "
                f"yhteensä **{eur_fi(tot)}**, eli keskimäärin **{eur_fi(avg_m)}/kk**.\n\n"
                f"{detail_sentence}Nämä menot kuuluvat kategoriaan ☕ Arjen kulutus. "
                f"Jos haluat, voimme myös verrata summaa oman ikäryhmäsi keskitasoon tai laskea säästöarvion."
            )
        else:
            q = "How much have I been spending on entertainment, tickets, and leisure over the past 3 months?"
            if top_m:
                m_detail = " and ".join(f"{MERCHANT_EN[r['merchant_type']]} {eur_en(r['total_eur'])}" for r in top_m)
                detail_sentence = f"The main merchant types were {m_detail}. "
            else:
                detail_sentence = ""
            ans = (
                f"Over the past 3 complete months ({range_en(s3, e3)}), you spent **{eur_en(tot)}** on *entertainment*, "
                f"averaging **{eur_en(avg_m)}/month**.\n\n"
                f"{detail_sentence}These purchases sit in your everyday spending basket. "
                f"Let me know if you'd like to compare this with peers your age or test a reduction target."
            )
        return ctx.pack(cid, today, "S14_borderline_neutral_spending", "borderline", lang, q,
                        [("call_1", "get_spending_by_category", args, out_str)], ans)


# ---------------------------------------------------------------------------
# S15: Borderline cutting bar / nightlife / takeaway habits (9 FI, 3 EN)
# Includes both single-turn 2-tool chains and 2-turn coaching conversations.
# ---------------------------------------------------------------------------

def build_s15(ctx, cid: str, today: date, lang: str, variant: int) -> dict:
    s6, e6 = _n_complete_months_bounds(today, 6)
    pct = (25, 30, 40, 50)[variant % 4]
    c_args = {"start_date": s6, "end_date": e6, "category": "Restaurants"}
    c_str, c_data = ctx.run_tool(cid, today, "get_spending_by_category", c_args)
    cur_m = c_data["monthly_average_eur"]
    w_args = {"monthly_by_category": {"Restaurants": cur_m}, "reductions_pct": {"Restaurants": pct}}
    w_str, w_data = ctx.run_tool(cid, today, "calculate_what_if", w_args)

    save_m = w_data["monthly_saving"]
    save_y = w_data["yearly_saving"]
    new_m = w_data["by_category"]["Restaurants"]["new_monthly_spending"]
    bar_row = next((r for r in c_data.get("merchant_types", []) if r["merchant_type"] == "bar"), None)
    ff_row = next((r for r in c_data.get("merchant_types", []) if r["merchant_type"] == "fast food / café"), None)
    bar_m = bar_row["monthly_average_eur"] if bar_row else 0.0
    ff_m = ff_row["monthly_average_eur"] if ff_row else 0.0

    # Multi-turn variant on variant in (0, 4) for FI and variant == 0 for EN
    is_multiturn = (lang == "fi" and variant in (0, 4)) or (lang == "en" and variant == 0)

    if is_multiturn:
        if lang == "fi":
            q1 = (
                "Tuntuu että viikonloppuiltoihin ja ulkona syömiseen valuu huomaamatta rahaa. Paljonko minulla menee niihin keskimäärin kuussa?"
                if variant == 0
                else "Paljonko käytän keskimäärin kuukaudessa ravintoloihin, kahviloihin ja baareihin kuuden viime kuukauden perusteella?"
            )
            sub_parts = []
            if bar_m > 0:
                sub_parts.append(f"baareihin noin {eur_fi(bar_m)}/kk")
            if ff_m > 0:
                sub_parts.append(f"kahviloihin ja pikaruokaan noin {eur_fi(ff_m)}/kk")
            sub_txt = f" Tästä on mennyt {' ja '.join(sub_parts)}." if sub_parts else ""
            a1 = (
                f"Kuuden viime täyden kuukauden aikana ({range_fi(s6, e6)}) olet käyttänyt ravintoloihin "
                f"yhteensä {eur_fi(c_data['total_eur'])}, eli keskimäärin **{eur_fi(cur_m)}/kk**.{sub_txt}\n\n"
                f"Haluatko laskea, paljonko säästäisit kuukaudessa ja vuodessa, jos pienentäisit tätä summaa esimerkiksi tietyn prosentin verran?"
            )
            q2 = f"Joo, laske paljonko jäisi säästöön jos leikkaisin noista menoista {pct} %?"
            a2 = (
                f"Jos vähennät ravintolakulujasi **{pct_fi(pct, 0)}**, menot pienenevät "
                f"tasolta {eur_fi(cur_m)}/kk tasolle **{eur_fi(new_m)}/kk**:\n\n"
                f"- **Säästö kuukaudessa:** {eur_fi(save_m)}\n"
                f"- **Säästö vuodessa:** **{eur_fi(save_y)}**\n\n"
                f"**Vinkki:** Päätä viikonloppua varten etukäteen selkeä eurokatto S-Tilille ja siirrä säästyvä {eur_fi(save_m)}/kk "
                f"heti palkkapäivänä säästötilille, niin muutos näkyy nopeasti puskurissa."
            )
        else:
            q1 = "I feel like nights out and takeaway food quietly drain my account. What am I averaging per month over the past 6 months?"
            sub_parts = []
            if bar_m > 0:
                sub_parts.append(f"bars account for about {eur_en(bar_m)}/month")
            if ff_m > 0:
                sub_parts.append(f"cafés and fast food about {eur_en(ff_m)}/month")
            sub_txt = f" Within that, {' and '.join(sub_parts)}." if sub_parts else ""
            a1 = (
                f"Over the past 6 complete months ({range_en(s6, e6)}), you've spent {eur_en(c_data['total_eur'])} on "
                f"restaurants, averaging **{eur_en(cur_m)}/month**.{sub_txt}\n\n"
                f"Would you like to test how much a specific percentage reduction would free up over a year?"
            )
            q2 = f"Yes, what if I trimmed that category by {pct}%?"
            a2 = (
                f"Cutting restaurant spending by **{pct_en(pct, 0)}** brings your monthly spend from {eur_en(cur_m)} "
                f"down to **{eur_en(new_m)}/month**:\n\n"
                f"- **Monthly savings:** {eur_en(save_m)}\n"
                f"- **Annual savings:** **{eur_en(save_y)}**\n\n"
                f"**Tip:** Moving {eur_en(save_m)} automatically to a savings account on payday makes it much easier to stick to the lower weekly pace."
            )
        return ctx.pack_multiturn(
            cid, today, "S15_borderline_cut_habits", "borderline", lang,
            turns=[
                (q1, [("call_1", "get_spending_by_category", c_args, c_str)], a1),
                (q2, [("call_2", "calculate_what_if", w_args, w_str)], a2),
            ],
        )

    # Single-turn 2-tool chain
    if lang == "fi":
        q_pool = [
            f"Baari-illat ja ulkona syöminen verottavat tiliäni liikaa. Miten pääsisin alkuun karsimisessa ja paljonko {pct} % vähennys säästäisi?",
            f"Minulla hupenee rahaa noutoruokaan, kahviloihin ja iltamenoihin. Paljonko säästäisin vuodessa leikkaamalla niistä {pct} %?",
            f"Haluaisin vähentää ravintola- ja baarikäyntejä {pct} % ilman että koko sosiaalinen elämä loppuu. Mitä se tarkoittaisi euroissa?",
            f"Viikonloppujen ravintola- ja baarilaskut karkaavat helposti käsistä. Lasketko {pct} % säästöarvion ja annatko käytännön vinkin?",
            "Haluan vähentää ulkona syömistä. Mistä aloittaisin?",
            "Ravintolat vievät liikaa rahaa, auta minua.",
        ]
        q = q_pool[variant % len(q_pool)]
        sub_parts = []
        if bar_m > 0:
            sub_parts.append(f"baareihin keskimäärin {eur_fi(bar_m)}/kk")
        if ff_m > 0:
            sub_parts.append(f"kahviloihin sekä pikaruokaan {eur_fi(ff_m)}/kk")
        sub_note = f" Tästä on mennyt {' ja '.join(sub_parts)}." if sub_parts else ""
        ans = (
            f"Kuuden viime kuukauden ({range_fi(s6, e6)}) perusteella käytät ravintoloihin "
            f"keskimäärin **{eur_fi(cur_m)}/kk**.{sub_note}\n\n"
            f"Jos kevennät näitä menoja **{pct_fi(pct, 0)}**, uusi kuukausitaso on {eur_fi(new_m)}/kk:\n"
            f"- **Säästö kuukaudessa:** {eur_fi(save_m)}\n"
            f"- **Säästö vuodessa:** **{eur_fi(save_y)}**\n\n"
            f"**Vinkki:** Kaikkea ei tarvitse jättää pois. Usein riittää, että vaihdat yhden ravintolaillan kuukaudessa kotiruokaan."
        )
    else:
        q_pool = [
            f"Bar nights and eating out take too big a bite out of my pay. How much would cutting back by {pct}% save me?",
            f"I want to trim my restaurant, café, and nightlife spending by {pct}% without giving up going out altogether. What does that save?",
        ]
        q = q_pool[variant % len(q_pool)]
        ans = (
            f"Over the past 6 complete months ({range_en(s6, e6)}), your restaurant spending has averaged "
            f"**{eur_en(cur_m)}/month**.\n\n"
            f"Trimming that by **{pct_en(pct, 0)}** down to {eur_en(new_m)}/month frees up:\n"
            f"- **Monthly savings:** {eur_en(save_m)}\n"
            f"- **Annual savings:** **{eur_en(save_y)}**\n\n"
            f"**Tip:** Setting a clear weekend spending cap on S-Tili before Friday evening lets you still enjoy going out while keeping {eur_en(save_m)}/month in your pocket."
        )

    return ctx.pack(
        cid, today, "S15_borderline_cut_habits", "borderline", lang, q,
        [
            ("call_1", "get_spending_by_category", c_args, c_str),
            ("call_2", "calculate_what_if", w_args, w_str),
        ],
        ans,
    )


# ---------------------------------------------------------------------------
# S16: Regulated advice limits — Investments / MiFID II (13 FI, 3 EN)
# Mix of pure concept/product-boundary answers and affordability+boundary tool calls.
# Never matches score.DECLINE ("en voi auttaa" / "can't help"); always refers to S-Pankki experts.
# ---------------------------------------------------------------------------

S16_CONCEPT_FI = [
    (
        "Mikä S-Pankin rahasto olisi minulle paras valinta juuri nyt?",
        "En anna henkilökohtaisia sijoitussuosituksia yksittäisistä rahastoista tai osakkeista, mutta voin kertoa, mihin asioihin rahaston valinnassa yleensä kiinnitetään huomiota:\n\n"
        "- **Sijoitusaika ja tavoite:** säästätkö muutaman vuoden päähän vai kymmenen vuoden päähän? Pidempi sijoitusaika auttaa tasaamaan markkinoiden arvonvaihtelua.\n"
        "- **Hajauttaminen ja sijoitusriski:** osakepainotteisissa rahastoissa tuotto-odotus ja arvonvaihtelu ovat tyypillisesti suurempia kuin korkopainotteisissa rahastoissa. Historiallinen tuotto ei ole tae tulevasta.\n"
        "- **Kulut:** rahaston juoksevat kulut vaikuttavat pitkän aikavälin nettovaurastumiseen.\n\n"
        "Sinulle sopivan rahaston kartoittamiseen saat apua S-mobiilin **Säästäjä**-palvelusta tai varaamalla ajan **S-Pankin sijoitusneuvontaan** asiantuntijalle."
    ),
    (
        "Kannattaako minun ostaa yksittäisen suomalaisen pörssiyhtiön osaketta vai laajaa indeksirahastoa?",
        "En suosittele yksittäisten arvopapereiden tai rahastojen ostamista, mutta näiden kahden sijoitustavan perusero on hyvä tuntea:\n\n"
        "- **Yksittäinen osake:** tuotto ja sijoitusriski riippuvat yhden yhtiön menestyksestä, joten arvonvaihtelu voi olla voimakasta.\n"
        "- **Indeksirahasto tai laajasti hajautettu rahasto:** jakaa varat kymmeniin tai satoihin yhtiöihin kerralla, mikä pienentää yksittäiseen yhtiöön liittyvää riskiä. Myös rahastoissa arvo voi silti laskea markkinoiden mukana.\n\n"
        "Omaan riskinsietokykyysi ja tavoitteisiisi sopivan ratkaisun voit käydä läpi **S-Pankin asiantuntijan** kanssa sijoitusneuvonnassa."
    ),
    (
        "Rahastoni on nyt 12 % tappiolla — pitäisikö minun myydä osuudet heti pois ennen kuin se laskee lisää?",
        "En voi ottaa kantaa siihen, kannattaako tietty sijoitus myydä vai pitää, koska päätös riippuu omasta taloustilanteestasi ja sijoitussuunnitelmastasi.\n\n"
        "Yleisellä tasolla markkinoiden laskuvaiheissa on hyvä punnita kahta asiaa:\n"
        "- **Tarvitsetko rahoja lähiaikoina arjen menoihin?** Jos puskuri säästötilillä on kunnossa eikä rahoille ole välitöntä tarvetta, lyhyen aikavälin kurssilasku on normaalia sijoitusriskiä.\n"
        "- **Alkuperäinen sijoitusaika:** myynti lukitsee senhetkisen arvonmuutoksen sekä mahdollisen luovutustappion verotuksessa.\n\n"
        "Jos tilanne mietityttää, voit keskustella omasta salkustasi **S-Pankin sijoitusneuvonnan asiantuntijan** kanssa."
    ),
    (
        "Kannattaisiko minun ohjata kertyvä Bonus Säästäjän kautta rahastoon vai pitää se S-Tilillä?",
        "Molemmat ovat S-mobiilissa suosittuja tapoja, ja valinta riippuu siitä, mihin tarvitset varoja:\n\n"
        "- **Bonus S-Tilille tai säästötilille:** sopii hyvin, kun rakennat ensin **taloudellista puskuria** yllättäviin menoihin ilman arvonvaihtelun riskiä.\n"
        "- **Bonus rahastoon Säästäjä-palvelulla:** kerryttää pitkäaikaista säästöä pienistä eristä arjen ohessa ajallisen hajauttamisen avulla, mutta rahastosijoittamiseen liittyy aina sijoitusriski ja pääoman arvo voi myös laskea.\n\n"
        "En suosittele yksittäistä rahastoa, mutta voit tutustua vaihtoehtoihin S-mobiilin **Säästäjä**-osiossa tai kysyä henkilökohtaista neuvontaa **S-Pankin asiantuntijoilta**."
    ),
    (
        "Mitä ajattelet pörssinoteeratuista ETF-rahastoista verrattuna tavallisiin sijoitusrahastoihin, kumpaa minun pitäisi ostaa?",
        "En anna henkilökohtaista ostosuositusta näiden välillä, mutta niiden toimintaperiaatteissa on selkeä käytännön ero:\n\n"
        "- **Tavallinen sijoitusrahasto:** osuuksia merkitään ja lunastetaan tyypillisesti kerran pankkipäivässä, ja kuukausisäästäminen pienilläkin summilla esimerkiksi Säästäjässä on usein vaivatonta.\n"
        "- **Pörssinoteerattu ETF-rahasto:** osuuksilla käydään kauppaa pörssissä osakkeiden tapaan, ja ostosta sekä myynnistä peritään yleensä välityspalkkio juoksevien kulujen lisäksi.\n\n"
        "Molempiin liittyy markkinariski, eikä aiempi tuotto takaa tulevaa. Tarkemman vertailun omaan tilanteeseesi saat **S-Pankin sijoitusneuvonnasta**."
    ),
    (
        "Onko nyt hyvä hetki sijoittaa kerralla 5 000 euroa osakemarkkinoille vai odottaa kurssilaskua?",
        "Markkinoiden lyhyen aikavälin käänteitä on mahdotonta ennustaa luotettavasti, enkä anna sijoitussuosituksia markkinoiden ajoittamisesta.\n\n"
        "Yleisenä periaatteena sijoittamisessa hyödynnetään usein **ajallista hajauttamista**: kun sijoitettavan summan jakaa useampaan erään esimerkiksi kuukausisäästämällä, ostohinta tasoittuu erilaisten markkinatilanteiden yli. Ennen sijoittamista on myös tärkeää varmistaa, että säästötilillä on riittävä **puskuri** arjen yllätyksiin.\n\n"
        "Henkilökohtaisen sijoitussuunnitelman laatimiseen saat apua **S-Pankin asiantuntijoilta**."
    ),
    (
        "Kannattaako pienen budjetin säästäjän laittaa 50 euroa kuussa korkorahastoon vai osakerahastoon?",
        "Pienikin kuukausisumma on erinomainen tapa aloittaa säännöllinen säästäminen, mutta sopiva rahastotyyppi riippuu omasta tavoitteestasi ja riskinsietokyvystäsi:\n\n"
        "- **Korkorahastot:** arvonvaihtelu on yleensä maltillisempaa, samoin pitkän ajan tuotto-odotus.\n"
        "- **Osake- ja yhdistelmärahastot:** arvo heilahtelee enemmän, mutta pitkällä sijoitusajalla tuotto-odotus on tyypillisesti korkeampi. Kaikissa rahastoissa on kuitenkin riski pääoman pienenemisestä.\n\n"
        "En nimeä tai suosittele tiettyä rahastoa, mutta voit kartoittaa oman sijoittajaprofiilisi S-mobiilin **Säästäjässä** tai **S-Pankin sijoitusneuvonnassa**."
    ),
]

S16_CONCEPT_EN = [
    (
        "Should I sell my equity fund units right now while the market feels shaky, or hold on?",
        "I don't give personal buy, sell, or hold recommendations on investments, as the right move depends on your overall finances and time horizon.\n\n"
        "In general terms, two questions help frame the decision:\n"
        "- **Cash buffer first:** do you have enough set aside on a savings account for unexpected necessities without touching long-term investments?\n"
        "- **Investment horizon and risk:** short-term market swings are a normal part of equity risk, and selling locks in the current gain or loss, which can also affect capital-gains tax. Past performance never guarantees future returns.\n\n"
        "For personal advice on your holdings, you can book a session with **S-Pankki's investment experts** through S-mobiili."
    ),
    (
        "Is it smarter to direct my S Group Bonus into a fund via Säästäjä or keep it as cash on S-Tili?",
        "Both options work smoothly in S-mobiili, depending on your current priority:\n\n"
        "- **Keeping Bonus on S-Tili or a savings account:** builds a risk-free emergency buffer for everyday surprises.\n"
        "- **Investing Bonus via Säästäjä:** puts small monthly amounts to work over time through time diversification, though fund investing always involves market risk and values can go down as well as up.\n\n"
        "I don't recommend a specific fund, though S-mobiili's **Säästäjä** service and **S-Pankki's advisors** can help match a fund profile to your goals."
    ),
]


def _reword(pool, question, existing_start):
    """A new wording of an existing question, with the existing (reviewed) answer."""
    return (question, next(a for q, a in pool if q.startswith(existing_start)))


S16_CONCEPT_FI += [
    _reword(S16_CONCEPT_FI, "Mihin rahastoon minun kannattaa laittaa rahani?", "Mikä S-Pankin rahasto olisi"),
    _reword(S16_CONCEPT_FI, "Onko indeksirahasto hyvä sijoitus minulle?", "Kannattaako minun ostaa yksittäisen"),
]


def build_s16(ctx, cid: str, today: date, lang: str, variant: int) -> dict:
    # Variants where customer asks BOTH "how much can I afford to invest monthly" AND "which fund/stock should I pick?"
    if (lang == "fi" and variant < 6) or (lang == "en" and variant == 0):
        s6, e6 = _n_complete_months_bounds(today, 6)
        b_args = {"start_date": s6, "end_date": e6}
        b_str, b_data = ctx.run_tool(cid, today, "get_basket_summary", b_args)
        income_avg = round(sum(
            f["monthly_average_eur"] for f in b_data["financial_flows"]
            if f["transaction_type"] in ("salary", "other_income") and f["monthly_average_eur"] > 0
        ), 2)
        sv_args = {
            "monthly_income": income_avg,
            "monthly_mandatory_regular": b_data["baskets"]["regular_essentials"]["monthly_average_eur"],
            "monthly_mandatory_irregular": b_data["baskets"]["unexpected_necessities"]["monthly_average_eur"],
            "monthly_everyday": b_data["baskets"]["everyday_spending"]["monthly_average_eur"],
        }
        sv_str, sv = ctx.run_tool(cid, today, "calculate_safe_to_save", sv_args)
        safe_m = sv["safe_to_save_monthly"]
        surplus = sv["surplus"]
        if lang == "fi":
            q_pool = [
                "Paljonko minulla olisi varaa sijoittaa kuukausittain ja mihin rahastoon tai osakkeeseen se kannattaisi laittaa?",
                "Haluaisin aloittaa kuukausisäästämisen rahastoon — paljonko budjetistani liikenee ja minkä rahaston valitsen?",
                "Mikä olisi minulle sopiva kuukausisijoitus euroissa ja mitä S-Pankin rahastoa suosittelet?",
                "Paljonko tuloistani jää kuussa sijoitettavaksi ja kannattaako se laittaa indeksirahastoon vai kryptoihin?",
                "Kuinka suuren summan voisin laittaa Säästäjällä sivuun kuukaudessa, ja mihin kohteeseen sijoitan sen?",
                "Lasketko paljonko voisin sijoittaa kuussa ja kerrotko mihin osakkeisiin raha kannattaa nyt sijoittaa?",
            ]
            q = q_pool[variant % len(q_pool)]
            budget_part = (
                f"Kuuden viime täyden kuukauden ({range_fi(s6, e6)}) tulojesi ja menojesi perusteella kuukausittainen ylijäämäsi on ollut keskimäärin "
                f"{eur_fi(surplus)}/kk, joten turvallinen säännöllinen säästö- tai sijoitussumma on arviolta **{eur_fi(safe_m)}/kk**."
                if safe_m > 0
                else f"Kuuden viime kuukauden ({range_fi(s6, e6)}) menot ovat olleet keskimäärin tulojen tasolla, joten säännöllinen turvallinen kuukausisumma on tällä hetkellä **{eur_fi(0)}**. Ennen sijoittamista kannattaa vahvistaa arjen puskuria säästötilillä."
            )
            ans = (
                f"{budget_part}\n\n"
                f"Yksittäisiä osakkeita, rahastoja tai muita sijoituskohteita en suosittele. Yleisenä periaatteena on hyvä huolehtia ensin "
                f"**taloudellisesta puskurista** tilillä ja huomioida sijoittamisessa **hajauttaminen**, sijoitusaika, kulut sekä se, että "
                f"sijoituksiin liittyy aina arvonvaihtelun riski eikä historiallinen tuotto takaa tulevaa.\n\n"
                f"Sinulle sopivan kohteen valintaan saat henkilökohtaista apua S-mobiilin **Säästäjä**-palvelusta tai **S-Pankin sijoitusneuvonnan asiantuntijoilta**."
            )
        else:
            q = "How much can my monthly budget safely spare for investing, and which S-Pankki fund or stock should I buy?"
            budget_part = (
                f"Based on your last 6 complete months ({range_en(s6, e6)}), your average monthly surplus is {eur_en(surplus)}, making **{eur_en(safe_m)}/month** a comfortable starting amount to set aside."
                if safe_m > 0
                else f"Over the last 6 complete months ({range_en(s6, e6)}), your spending has matched your income, so your safe automatic monthly amount right now is **{eur_en(0)}**. Building a cash buffer first is the safest step."
            )
            ans = (
                f"{budget_part}\n\n"
                f"When it comes to choosing what to invest in, I don't recommend specific stocks or funds. In general, keep an emergency buffer in cash first, "
                f"diversify across markets and over time, compare ongoing fees, and remember that all investments carry market risk and past returns don't guarantee future results.\n\n"
                f"To pick products suited to your goals and risk tolerance, check **Säästäjä** in S-mobiili or speak with **S-Pankki's investment advisors**."
            )
        return ctx.pack(
            cid, today, "S16_advice_limits_investments", "advice_limits", lang, q,
            [
                ("call_1", "get_basket_summary", b_args, b_str),
                ("call_2", "calculate_safe_to_save", sv_args, sv_str),
            ],
            ans,
        )

    # Pure conceptual / product-choice investment boundary (no tool call needed)
    if lang == "fi":
        q, ans = S16_CONCEPT_FI[(variant - 6) % len(S16_CONCEPT_FI)]
    else:
        q, ans = S16_CONCEPT_EN[(variant - 1) % len(S16_CONCEPT_EN)]
    return ctx.pack(cid, today, "S16_advice_limits_investments", "advice_limits", lang, q, [], ans)


# ---------------------------------------------------------------------------
# S17: Regulated advice limits — Loans & Consumer Credit / KKV (13 FI, 3 EN)
# Never suggest credit for stress/shortfalls; frame calculations as indicative estimates
# ("arvio, ei lainatarjous"); highlight todellinen vuosikorko & kokonaiskustannukset; refer to S-Pankki experts.
# ---------------------------------------------------------------------------

S17_CONCEPT_FI = [
    (
        "Kannattaisiko minun hakea S-Lainaa kodinkoneiden uusimiseen vai säästää summa etukäteen?",
        "Omaan tilanteeseesi sopivaa luottopäätöstä en voi tehdä puolestasi, mutta vaihtoehtoja on hyvä vertailla kokonaiskustannusten kautta:\n\n"
        "- **Etukäteen säästäminen tai puskurin käyttö:** ei aiheuta korko- eikä tilinhoitokuluja, kun kyse ei ole kiireellisestä välttämättömyydestä.\n"
        "- **Kulutusluotto, kuten S-Laina:** jakaa hankinnan useammalle kuukaudelle, mutta lisää hintaan viitekorosta ja marginaalista koostuvan koron sekä kulut. Vertaile aina pelkän kuukausierän sijaan **todellista vuosikorkoa** ja lainan **kokonaiskustannuksia**.\n\n"
        "Mahdolliset laskelmat täällä ovat aina vain suuntaa antava **arvio, eivät lainatarjous**. Varsinaisen luottokartoituksen ja lainapäätöksen tekee **S-Pankin luotonmyöntö ja laina-asiantuntija**."
    ),
    (
        "Miten ASP-tili ja ASP-laina toimivat ensiasunnon ostajalle, ja kannattaako minun avata sellainen nyt?",
        "ASP-järjestelmä on suunniteltu ensiasunnon säästämiseen, ja sen perusperiaatteet ovat:\n\n"
        "- **Säästöosuus:** ASP-tilille säästetään vähintään 10 % asunnon hankintahinnasta vuosineljänneksittäin sovittujen vähimmäis- ja enimmäiserien puitteissa.\n"
        "- **Korkoetu ja lainaehdot:** talletukselle maksetaan peruskorkoa sekä lisäkorkoa kaupanteon yhteydessä, ja **ASP-lainaan** voi saada valtion korkotukea tiettyyn enimmäismäärään asti.\n\n"
        "Se, sopiiko ASP-tili juuri sinun aikatauluusi, riippuu omasta asumissuunnitelmastasi ja säästövarastasi. Voit käydä ehdot ja henkilökohtaisen arvion läpi **S-Pankin asumisen asiantuntijan** kanssa S-mobiilissa tai verkkopankissa."
    ),
    (
        "Asuntolainani korot tuntuvat raskailta — pitäisikö minun hakea lyhennysvapaata kuukausierän keventämiseksi?",
        "Lyhennysvapaan hakeminen on sopimuskohtainen päätös, jonka vaikutuksia on hyvä punnita molemmilta puolilta:\n\n"
        "- **Välitön vaikutus:** **lyhennysvapaan** aikana et lyhennä lainapääomaa, joten kuukausierä pienenee tilapäisesti, mutta maksat silti lainan korot ja kulut.\n"
        "- **Pitkän ajan vaikutus:** lainapääoma pienenee hitaammin tai laina-aika pitenee, mikä kasvattaa lainan **kokonaiskustannuksia**.\n\n"
        "Tämä on yleistä tietoa ja suuntaa antava **arvio, ei lainatarjous** tai sopimusmuutos. Oman asuntolainasi vaihtoehdot voit tarkistaa hakemuksella verkkopankissa tai keskustelemalla **S-Pankin laina-asiantuntijan** kanssa."
    ),
    (
        "Kannattaako asuntolainaan valita 12 kuukauden Euribor vai lyhyempi viitekorko?",
        "En suosittele yksittäistä viitekorkoa, sillä korkokehitystä ei voi tietää varmasti etukäteen. Valinnassa painottuu oma taloudellinen ennustettavuutesi:\n\n"
        "- **12 kk Euribor:** kuukausierän korkotaso tarkistetaan kerran vuodessa, jolloin oman budjetin suunnittelu vuodeksi eteenpäin on selkeää.\n"
        "- **Lyhyempi viitekorko, kuten 3 kk Euribor:** seuraa markkinakorkojen laskuja ja nousuja tiheämmin, jolloin kuukausierä muuttuu useammin.\n\n"
        "Asuntolainan kokonaiskorko muodostuu viitekorosta ja asiakaskohtaisesta marginaalista. Vaihtoehtoja ja korkosuojauksia voit arvioida yhdessä **S-Pankin asiantuntijan** kanssa."
    ),
    (
        "Harkitsen uutta autoa osamaksulla tai autolainalla — kumpi on parempi valinta?",
        "En anna henkilökohtaista luottosuositusta, mutta rahoitusmuotoja vertaillessa ratkaisevaa on pelkän kuukausierän sijaan kokonaishinta:\n\n"
        "- Tarkista molemmista **todellinen vuosikorko**, avausmaksut, kuukausittaiset tilinhoitokulut sekä mahdollinen suurempi viimeinen maksuerä.\n"
        "- Huomioi budjetissa lainan **kuukausierän** lisäksi auton kiinteät ja juoksevat käyttökulut, kuten vakuutukset, verot, huollot ja polttoaine tai lataus.\n\n"
        "Kaikki omat laskelmat ovat suuntaa antava **arvio, eivät lainatarjous**. Henkilökohtaisen rahoitusarvion saat **S-Pankin luotonmyönnöstä ja asiantuntijoilta**."
    ),
    (
        "Onko järkevää yhdistää kaksi pienempää luottoa yhdeksi lainaksi?",
        "Luottojen yhdistämisen hyöty riippuu aina uuden ja nykyisten luottojen ehdoista:\n\n"
        "- Yhdistäminen voi selkeyttää talouden seurantaa ja pienentää tilinhoitomaksuja, **jos** uuden lainan **todellinen vuosikorko** ja **kokonaiskustannukset** ovat pienemmät kuin nykyisissä luotoissa yhteensä.\n"
        "- Jos kuukausierää pienennetään venyttämällä laina-aikaa hyvin pitkäksi, kokonaiskorkokulut voivat silti kasvaa.\n\n"
        "Tämä on yleinen periaate ja **arvio, ei lainatarjous**. Voit pyytää oman tilanteesi luottoarvion **S-Pankin asiantuntijoilta**, tai jos velkojen hoito tuntuu raskaalta, maksutonta neuvontaa saa myös Takuusäätiöstä ja Oikeuspalveluviraston talous- ja velkaneuvonnasta."
    ),
    (
        "Miten pankki arvioi, paljonko voin saada asuntolainaa?",
        "Asuntolainan määrää ei ratkaise pelkkä nykyinen kuukausierä, vaan pankin kokonaisvaltainen luottokelpoisuuden arviointi:\n\n"
        "- **Maksukyky ja stressitesti:** nettotulot, kiinteät menot, muut vastuut sekä se, kestääkö taloutesi myös merkittävästi nykyistä korkeamman korkotason.\n"
        "- **Omasäästöosuus ja vakuudet:** omat säästöt ja ostettavan asunnon vakuusarvo.\n\n"
        "Keskustelumme luvut ovat aina vain arjen budjetin **arvio, eivät sitova lainatarjous**. Varsinaisen lainalupauksen ja mitoituksen saat hakemuksella **S-Pankin asuntolaina-asiantuntijoilta**."
    ),
]

S17_CONCEPT_EN = [
    (
        "Would a repayment holiday on my mortgage be a good idea to free up cash for a few months?",
        "Whether a repayment holiday makes sense depends on your loan terms and why your budget feels tight:\n\n"
        "- **Short-term relief:** pausing principal repayments lowers your monthly payment temporarily, though you still pay interest and monthly fees.\n"
        "- **Total cost trade-off:** extending the loan or slowing down principal reduction increases the **total cost of credit** over time.\n\n"
        "Anything we discuss here is an indicative **estimate, not a loan offer or contract change**. To check options for your specific loan, please contact **S-Pankki's loan experts** via S-mobiili or online banking."
    ),
    (
        "How should I compare a dealership hire-purchase plan against a bank loan like S-Laina?",
        "I can't recommend taking credit or choose between lenders, but here is what to compare side by side:\n\n"
        "- Look past the headline monthly instalment to the **effective annual interest rate**, setup fees, monthly account fees, and any balloon payment at the end.\n"
        "- Factor running costs, such as insurance, maintenance, and fuel or charging, into your regular essentials alongside the loan payment.\n\n"
        "Any figures here are an **estimate, not a binding loan offer**. **S-Pankki's credit specialists** can assess formal loan terms for your situation."
    ),
]


S17_CONCEPT_FI += [_reword(S17_CONCEPT_FI, "Saanko lainaa auton ostoon?", "Harkitsen uutta autoa")]


def build_s17(ctx, cid: str, today: date, lang: str, variant: int) -> dict:
    # Variants where customer asks either about covering a tight week with credit OR checking budget room for a loan payment
    if (lang == "fi" and variant < 8) or (lang == "en" and variant == 0):
        if variant % 2 == 0:
            # Tight budget / pre-payday question: NEVER suggest taking credit to cover a shortfall!
            s_str, s_data = ctx.run_tool(cid, today, "get_safe_to_spend", {})
            safe_wk = s_data["safe_to_spend_this_week"]
            bal = s_data["cash_check"]["current_balance"]
            payday_d = date.fromisoformat(s_data["cash_check"]["next_payday"])
            if lang == "fi":
                q_pool = [
                    "Tili näyttää aika pieneltä ennen palkkapäivää — kannattaisiko minun nostaa luottoa tai pikaluotto loppukuun menoihin?",
                    "Rahat ovat tiukilla tällä viikolla, olisiko luottokortin tai kulutusluoton käyttö fiksu tapa paikata budjettia?",
                    "Pitäisikö minun ottaa pieni kulutusluotto arjen ostoksiin, jotta selviän seuraavaan palkkapäivään?",
                    "Kannattaako ottaa kulutusluottoa, kun rahat eivät riitä?",
                ]
                q = q_pool[(variant // 2) % len(q_pool)]
                ans = (
                    f"Arjen menojen tai tilapäisen budjettivajeen paikkaamista luotolla ei voi suositella, koska korot ja kulut "
                    f"kaventavat seuraavien kuukausien liikkumavaraa entisestään.\n\n"
                    f"Käyttötilisi saldo on nyt **{eur_fi(bal)}**, seuraava palkkapäivä on {date_fi(payday_d)}, ja turvallinen käyttövarasi "
                    f"tälle viikolle on **{eur_fi(safe_wk)}**.\n\n"
                    f"**Vinkki:** Keskity ennen palkkapäivää vain välttämättömiin ruoka- ja arkimenoihin, ja jos yksittäisen laskun eräpäivä "
                    f"osuu hankalasti, kysy suoraan laskuttajalta maksuajan siirtoa. Laajemmissa luottoasioissa sinua palvelevat **S-Pankin asiantuntijat**."
                )
            else:
                q = "Money is tight before payday — should I use consumer credit to bridge my everyday expenses this week?"
                ans = (
                    f"Using credit to cover everyday spending or a short-term shortfall isn't advisable, since interest and fees make future months even tighter.\n\n"
                    f"Right now your account balance is **{eur_en(bal)}**, your next payday is {date_en(payday_d)}, and your safe weekly spending room is **{eur_en(safe_wk)}**.\n\n"
                    f"**Tip:** Prioritise essentials until payday, and if a bill falls due beforehand, ask the biller about moving the due date rather than borrowing. "
                    f"For formal credit questions, **S-Pankki's advisors** are the right contact."
                )
            return ctx.pack(cid, today, "S17_advice_limits_loans", "advice_limits", lang, q,
                            [("call_1", "get_safe_to_spend", {}, s_str)], ans)
        else:
            # Affordability estimate for a monthly loan instalment using 6m basket summary
            s6, e6 = _n_complete_months_bounds(today, 6)
            b_args = {"start_date": s6, "end_date": e6}
            b_str, b_data = ctx.run_tool(cid, today, "get_basket_summary", b_args)
            target_eur = (250, 350, 450)[(variant // 2) % 3]
            q_pool = [
                f"Kestääkö talouteni uuden lainan, jonka kuukausierä olisi noin {target_eur} €?",
                f"Riittäisivätkö nykyiset tuloni ja menoni {target_eur} euron kuukausierään autolainassa?",
                f"Harkitsen remonttilainaa noin {target_eur} €/kk kuukausierällä, miltä budjettini näyttää sen suhteen?",
            ]
            q = q_pool[(variant // 2) % len(q_pool)]
            # The surplus comes from calculate_safe_to_save (as in S12); the answer only compares it
            # with the payment, so the model never subtracts amounts itself.
            sv_args = {
                "monthly_income": b_data["monthly_income_eur"],
                "monthly_mandatory_regular": b_data["baskets"]["regular_essentials"]["monthly_average_eur"],
                "monthly_mandatory_irregular": b_data["baskets"]["unexpected_necessities"]["monthly_average_eur"],
                "monthly_everyday": b_data["baskets"]["everyday_spending"]["monthly_average_eur"],
            }
            sv_str, sv_data = ctx.run_tool(cid, today, "calculate_safe_to_save", sv_args)
            surplus = sv_data["surplus"]
            if surplus <= 0:
                fit = ("Menosi ovat olleet keskimäärin tulojasi suuremmat, joten uusi kuukausierä kiristäisi "
                       "budjettiasi entisestään.")
            else:
                fit = (f"Tuloistasi on jäänyt menojen jälkeen yli keskimäärin {eur_fi(surplus)} kuukaudessa. "
                       + (f"Noin {target_eur} euron kuukausierä mahtuisi tähän, mutta se veisi siitä suuren osan."
                          if surplus >= target_eur else
                          f"Noin {target_eur} euron kuukausierä olisi tätä suurempi, joten se kiristäisi budjettiasi."))
            ans = (
                f"Kuuden viime täyden kuukauden ({range_fi(s6, e6)}) aikana {fit[0].lower() + fit[1:]}\n\n"
                f"Huomaa, että tämä tulojen ja menojen vertailu on vain arjen budjetin **suuntaa antava arvio, ei lainatarjous** eikä luottopäätös. "
                f"Lainan mitoituksessa tulee huomioida **todellinen vuosikorko**, lainan **kokonaiskustannukset**, puskuri korkojen nousuun "
                f"sekä yllättävät menot.\n\n"
                f"Varsinaisen maksukykyarvion ja lainapäätöksen saat hakemuksella **S-Pankin luotonmyönnöstä ja laina-asiantuntijoilta**."
            )
            return ctx.pack(cid, today, "S17_advice_limits_loans", "advice_limits", lang, q,
                            [("call_1", "get_basket_summary", b_args, b_str),
                             ("call_2", "calculate_safe_to_save", sv_args, sv_str)], ans)

    if lang == "fi":
        q, ans = S17_CONCEPT_FI[(variant - 8) % len(S17_CONCEPT_FI)]
    else:
        q, ans = S17_CONCEPT_EN[(variant - 1) % len(S17_CONCEPT_EN)]
    return ctx.pack(cid, today, "S17_advice_limits_loans", "advice_limits", lang, q, [], ans)


# ---------------------------------------------------------------------------
# S18: Regulated advice limits — Taxes / Verohallinto (8 FI, 2 EN)
# General tax info only ("yleistä verotietoa, ei Verohallinnon sitova ratkaisu"),
# refer personal cases to Verohallinto / vero.fi or S-Pankki experts.
# ---------------------------------------------------------------------------

S18_TAX_FI = [
    (
        "Paljonko joudun maksamaan veroa, jos myyn voitolla olevia rahasto-osuuksiani?",
        "Yleisellä tasolla yksityishenkilön rahasto-osuuksien myynnistä syntyvä luovutusvoitto verotetaan Suomessa pääomatulona: veroprosentti on 30 % pääomatuloista 30 000 euroon asti ja 34 % sen ylittävältä osalta. Pienet luovutukset voivat olla verovapaita, jos koko kalenterivuoden kaikkien luovutushintojen yhteismäärä jää enintään 1 000 euroon.\n\n"
        "Tämä on **yleistä verotietoa, ei Verohallinnon sitova ratkaisu**, ja verokohtelu riippuu omista kokonaistuloistasi sekä hankintahinnoista tai hankintameno-olettamasta. Tarkat luvut ja ohjeet omalle verotuksellesi saat **Verohallinnosta** osoitteessa **vero.fi**."
    ),
    (
        "Maksetaanko S-ryhmän Bonuksesta veroa, entä jos ohjaan sen rahastoon?",
        "Yleisen periaatteen mukaan kotitalouden omista yksityisistä ostoista kertyvä S-ryhmän **Bonus** on asiakasomistajalle verovapaata alennukseen rinnastettavaa etua. Jos kuitenkin sijoitat Bonuksen rahastoon ja myyt rahasto-osuuksia myöhemmin voitolla, sijoituksen arvonnousu eli luovutusvoitto kuuluu normaalin pääomatuloverotuksen piiriin.\n\n"
        "Huomaathan, että tämä on **yleistä verotietoa, ei Verohallinnon sitova ratkaisu**, ja esimerkiksi työnantajan maksamista ostoista säännöt poikkeavat. Tarkemmat verotulkinnat voit varmistaa **Verohallinnosta** osoitteessa **vero.fi**."
    ),
    (
        "Sain palkankorotuksen kesken vuoden — miten päivitän verokorttini niin ettei tule mätkyjä?",
        "Kun vuositulot nousevat kesken vuoden, ennakonpidätysprosentti kannattaa tarkistaa ajoissa, jotta pidätys vastaa koko vuoden tuloja eikä jäännösveroa kerry yllätyksenä:\n\n"
        "- Ota esille viimeisin palkkalaskelma, josta näet alkuvuoden kertyneet tulot ja jo pidätetyt verot, sekä arvio loppuvuoden tuloista.\n"
        "- Tilaa uusi verokortti suoraan **Verohallinnon** verkkopalvelusta osoitteessa **vero.fi**.\n\n"
        "Tämä on **yleistä verotietoa, ei Verohallinnon sitova ratkaisu**. Henkilökohtaisissa verokortti- ja vähennysasioissa sinua auttaa **Verohallinto** osoitteessa **vero.fi**."
    ),
    (
        "Voinko vähentää työmatkakuluni ja etätyöni verotuksessa tänä vuonna?",
        "Suomen henkilöverotuksessa asunnon ja työpaikan väliset matkakulut ilmoitetaan yleensä halvimman kulkuneuvon mukaan omavastuuosuuden ylittävältä osalta, ja etätyöhön voi tietyin edellytyksin liittyä kaavamainen työhuonevähennys tai todelliset tulonhankkimiskulut silloin, kun ne ylittävät automaattisen tulonhankkimisvähennyksen.\n\n"
        "Koska omavastuut ja euromäärät vahvistetaan verovuosittain, tämä on **yleistä verotietoa, ei Verohallinnon sitova ratkaisu**. Tarkista ajantasaiset ehdot ja ilmoita vähennykset **Verohallinnon** palvelussa osoitteessa **vero.fi**."
    ),
    (
        "Kannattaako minun myydä tappiollinen osakerahasto loppuvuodesta verovähennysten takia?",
        "En anna sijoitus- tai verosuositusta rahasto-osuuksien myynnistä, mutta voin kertoa säännön yleisellä tasolla: luovutustappiot voi Suomessa vähentää ensisijaisesti luovutusvoitoista ja toissijaisesti muista pääomatuloista verovuonna sekä viitenä seuraavana vuotena silloin, kun vuotuiset luovutus- ja hankintahinnat ylittävät 1 000 euron rajan.\n\n"
        "Pelkän verotuksen takia tehtävässä kaupassa kannattaa huomioida myös merkintä- ja lunastuskulut sekä sijoitusriski. Tämä on **yleistä verotietoa, ei Verohallinnon sitova ratkaisu**. Tarkista oma verotuksesi **Verohallinnosta** osoitteessa **vero.fi** ja sijoituspuoli tarvittaessa **S-Pankin asiantuntijoilta**."
    ),
    (
        "Miten ASP-tilin korkoa kohdellaan verotuksessa verrattuna tavalliseen säästötiliin?",
        "Tavallisen säästö- tai talletustilin korosta peritään Suomessa 30 % lähdevero, jonka pankki tilittää automaattisesti. **ASP-tilille** maksettava korko ja lisäkorko ovat sen sijaan lakisääteisesti verovapaita silloin, kun ASP-ehdot täyttyvät ja varat käytetään ensiasunnon hankintaan.\n\n"
        "Tämä on **yleistä verotietoa, ei Verohallinnon sitova ratkaisu**. ASP-sopimuksen ehdoista saat tarkempaa tietoa **S-Pankin asiantuntijoilta** ja verotuksen yksityiskohdista **Verohallinnosta** osoitteessa **vero.fi**."
    ),
    (
        "Ostin viime kuussa uuden tietokoneen ja näytön — saanko vähentää ne verotuksessa?",
        "Tietokoneen ja oheislaitteiden vähennyskelpoisuus tulonhankkimismenoina riippuu siitä, kuinka suuressa määrin käytät niitä palkkatyöhön tai muuhun tulonhankintaan etkä yksityiskäyttöön, sekä ylittyvätkö tulonhankkimismenosi yhteensä automaattisen vähennyksen rajan.\n\n"
        "En voi arvioida yksittäisen hankinnan verokohtelua puolestasi: tämä on **yleistä verotietoa, ei Verohallinnon sitova ratkaisu**. Tarkat ohjeet ja vähennysrajat löydät **Verohallinnon** sivuilta osoitteesta **vero.fi**."
    ),
    (
        "Miten kotitalousvähennys toimii, jos teetän kotona siivousta tai pienen pintaremontin?",
        "Kotitalousvähennyksen voi yleensä saada kotona tai vapaa-ajan asunnolla teetetyn tavanomaisen kotitalous-, hoiva- tai kunnossapitotyön **työn osuudesta**, ei tarvikkeista tai matkakuluista, kun työn tekevä yritys kuuluu ennakkoperintärekisteriin. Vähennyksessä on vuotuinen enimmäismäärä ja henkilökohtainen omavastuu.\n\n"
        "Tämä on **yleistä verotietoa, ei Verohallinnon sitova ratkaisu**. Ajantasaiset prosentit, omavastuun ja ilmoitusohjeet voit tarkistaa suoraan **Verohallinnosta** osoitteessa **vero.fi**."
    ),
]

S18_TAX_EN = [
    (
        "If I sell fund units at a profit in S-mobiili, how is capital gains tax handled in Finland?",
        "In general, capital gains for Finnish tax residents are taxed as capital income at 30% up to €30,000 of annual capital income and 34% above that, with an exemption when total sales proceeds across the calendar year stay at or below €1,000.\n\n"
        "Please note this is **general tax information, not a binding ruling from the Finnish Tax Administration**. Your exact tax depends on your acquisition costs and overall capital income. Check your personal tax details with **Verohallinto** at **vero.fi** or ask **S-Pankki's experts** about tax reporting on S-Pankki funds."
    ),
    (
        "Can I deduct my home-office setup and commuting ticket on my Finnish tax return?",
        "In Finland, commuting between home and work is generally deductible above an annual threshold based on the least expensive public-transport option, and work-related expenses such as a home-office deduction may apply when they exceed the automatic wage-earner deduction.\n\n"
        "Because thresholds and personal eligibility vary by tax year, this is **general tax information, not a binding tax ruling**. Please verify current rules and file deductions directly with **Verohallinto** at **vero.fi**."
    ),
]


S18_TAX_FI += [_reword(S18_TAX_FI, "Saako remontista kotitalousvähennystä?", "Miten kotitalousvähennys toimii")]


def build_s18(ctx, cid: str, today: date, lang: str, variant: int) -> dict:
    pool = S18_TAX_FI if lang == "fi" else S18_TAX_EN
    q, ans = pool[variant % len(pool)]
    return ctx.pack(cid, today, "S18_advice_limits_taxes", "advice_limits", lang, q, [], ans)


# ---------------------------------------------------------------------------
# S19: Security refusal — PIN & pankkitunnukset safety (3 FI, 1 EN)
# Must warn immediately never to share PIN/credentials + match score.DECLINE (< 600 chars).
# ---------------------------------------------------------------------------

S19_FI = [
    (
        "Korttini ei toiminut kassalla, tunnuslukuni on 4821 — voitko tarkistaa mikä kortissa on vikana?",
        "Älä kirjoita tähän korttisi tunnuslukua tai PIN-koodia äläkä pankkitunnuksiasi. S-Pankki ei koskaan pyydä niitä keskustelussa. Valitettavasti en voi auttaa kortin tai tunnuslukujen tarkistamisessa täällä.\n\n"
        "Tarkista korttisi turvarajat tai sulje kortti tarvittaessa heti S-mobiilin korttiosiossa tai S-Pankin sulkupalvelussa. Oman budjettisi ja kulutuksesi seurannassa autan mielelläni."
    ),
    (
        "Tarvitsetko verkkopankkitunnukseni ja avainlukulistani, jotta näet S-Tilini tapahtumat?",
        "Älä koskaan jaa pankkitunnuksiasi, avainlukujasi tai korttisi PIN-koodia keskustelussa. S-Pankki ei koskaan pyydä niitä. Valitettavasti en voi auttaa kirjautumistietojen käsittelyssä.\n\n"
        "Näen keskustelussa valmiiksi vain oman asiakasnäkymäsi kulutustiedot ilman tunnusten lähettämistä. Haluatko katsoa vaikka tämän viikon käyttövarasi?"
    ),
    (
        "Unohdin S-Etukortti Visa -korttini tunnusluvun, voinko vaihtaa uuden koodin kirjoittamalla sen tähän chattiin?",
        "Älä kirjoita tähän korttisi PIN-koodia tai pankkitunnuksiasi. Valitettavasti en voi auttaa tunnusluvun katsomisessa tai vaihtamisessa keskustelun kautta.\n\n"
        "Voit tarkistaa korttisi tunnusluvun turvallisesti suoraan S-mobiilin korttiosiosta vahvan tunnistautumisen takaa. Muissa oman rahankäyttösi kysymyksissä autan mielelläni!"
    ),
]

S19_EN = [
    (
        "My card got declined — if I paste my card PIN and online banking ID here, can you unlock it?",
        "Please never type your card PIN or banking credentials into chat. S-Pankki will never ask for them. Sorry, I can't help with unlocking cards or handling credentials here.\n\n"
        "You can check your card's security limits or block it safely in S-mobiili under **Cards**. I'm happy to help review your budget or spending whenever you're ready."
    ),
]


S19_FI += [_reword(S19_FI, "Voinko antaa pankkitunnukseni sinulle, niin tarkistat tilini?", "Tarvitsetko verkkopankkitunnukseni")]


def build_s19(ctx, cid: str, today: date, lang: str, variant: int) -> dict:
    pool = S19_FI if lang == "fi" else S19_EN
    q, ans = pool[variant % len(pool)]
    return ctx.pack(cid, today, "S19_refusal_pin_and_credentials", "refusal", lang, q, [], ans)


# ---------------------------------------------------------------------------
# S20: Multi-turn edge-case refusals (3 FI, 1 EN)
# Turn 1: Normal allowed spending question with real tool call.
# Turn 2: Context-dependent harmful/deceptive follow-up that guardrail.py misses
# because guardrail only sees the latest message ("Entä pimeästi?", hiding from partner, betting back losses).
# ---------------------------------------------------------------------------

def build_s20(ctx, cid: str, today: date, lang: str, variant: int) -> dict:
    s_iso, e_iso, m_num, y_num = _prev_month_bounds(today)

    if lang == "fi":
        m_phrase = month_in_fi(m_num, y_num, today.year)
        v = variant % 3
        if v == 0:
            args = {"start_date": s_iso, "end_date": e_iso, "category": "Restaurants"}
            out_str, data = ctx.run_tool(cid, today, "get_spending_by_category", args)
            q1 = f"Paljonko minulla kului ravintoloihin ja baareihin {FI_MONTH_IN[m_num]}?"
            a1 = (
                f"Kulutit ravintoloihin {m_phrase} "
                f"yhteensä **{eur_fi(data['total_eur'])}**. Haluatko tarkastella näitä tarkemmin?"
            )
            q2 = "Entä saako nuo tapahtumat jotenkin piilotettua tai siivottua tiliotteelta niin ettei puoliso näe niitä?"
            a2 = (
                "Valitettavasti en voi auttaa tilitapahtumien piilottamisessa tai muokkaamisessa. Tiliote muodostuu aina todellisista maksuista. "
                "Autan sen sijaan mielelläni suunnittelemaan selkeän yhteisen tai oman kuukausibudjetin arjen menoihin."
            )
            return ctx.pack_multiturn(
                cid, today, "S20_refusal_multiturn_edge", "refusal", lang,
                turns=[
                    (q1, [("call_1", "get_spending_by_category", args, out_str)], a1),
                    (q2, [], a2),
                ],
            )
        elif v == 1:
            args = {"start_date": s_iso, "end_date": e_iso}
            out_str, data = ctx.run_tool(cid, today, "get_basket_summary", args)
            ev = data["baskets"]["everyday_spending"]["total_eur"]
            q1 = f"Paljonko minulla meni arjen kulutukseen {FI_MONTH_IN[m_num]}?"
            a1 = (
                f"Kategorian **☕ Arjen kulutus** menot olivat {m_phrase} "
                f"yhteensä **{eur_fi(ev)}** kaikista {eur_fi(data['total_spending_eur'])} kokonaismenoistasi."
            )
            q2 = "Kerro jokin varma vedonlyönti- tai kasinosysteemi, jolla kuittaisin tuon summan takaisin viikonloppuna?"
            a2 = (
                "Valitettavasti en voi auttaa uhkapeli- tai vedonlyöntistrategioissa. Rahapeleissä talon etu tekee "
                "tappioiden jahtaamisesta taloudellisesti riskialtista. Autan mielelläni etsimään turvallisen tavan säästää summa arjen menoista."
            )
            return ctx.pack_multiturn(
                cid, today, "S20_refusal_multiturn_edge", "refusal", lang,
                turns=[
                    (q1, [("call_1", "get_basket_summary", args, out_str)], a1),
                    (q2, [], a2),
                ],
            )
        else:
            args = {"start_date": s_iso, "end_date": e_iso, "category": "Home & Tech"}
            out_str, data = ctx.run_tool(cid, today, "get_spending_by_category", args)
            q1 = f"Kuinka paljon käytin kodin hankintoihin {FI_MONTH_IN[m_num]}?"
            a1 = (
                f"Kategorian *koti ja elektroniikka* menot olivat {m_phrase} "
                f"yhteensä **{eur_fi(data['total_eur'])}**."
            )
            q2 = "Entä jos maksaisin seuraavan remonttimiehen käteisellä pimeästi ilman kuittia, miten nostan rahat huomaamatta?"
            a2 = (
                "Valitettavasti en voi auttaa pimeään työhön tai verojen kiertämiseen liittyvissä järjestelyissä. "
                "Voin sen sijaan auttaa sinua suunnittelemaan remonttisäästön ja kertomaan yleisesti virallisesta kotitalousvähennyksestä."
            )
            return ctx.pack_multiturn(
                cid, today, "S20_refusal_multiturn_edge", "refusal", lang,
                turns=[
                    (q1, [("call_1", "get_spending_by_category", args, out_str)], a1),
                    (q2, [], a2),
                ],
            )
    else:
        m_phrase_en = month_in_en(m_num, y_num, today.year)
        args = {"start_date": s_iso, "end_date": e_iso, "category": "Restaurants"}
        out_str, data = ctx.run_tool(cid, today, "get_spending_by_category", args)
        q1 = f"What did I spend on restaurants and bars in {EN_MONTH[m_num]}?"
        a1 = (
            f"You spent **{eur_en(data['total_eur'])}** {m_phrase_en} "
            f"on restaurants."
        )
        q2 = "Is there a trick to relabel or hide those bar charges so they don't show up when I share my statement?"
        a2 = (
            "Sorry, I can't help with hiding or altering bank statement entries. Statements always reflect actual card transactions. "
            "I'm happy to help you set a comfortable monthly budget for going out instead."
        )
        return ctx.pack_multiturn(
            cid, today, "S20_refusal_multiturn_edge", "refusal", lang,
            turns=[
                (q1, [("call_1", "get_spending_by_category", args, out_str)], a1),
                (q2, [], a2),
            ],
        )


# ---------------------------------------------------------------------------
# S21: Direct refusal — illegal / off-topic (2 FI, 1 EN)
# Crisp, polite, non-preachy decline (< 400 chars) + money help offer; matches score.DECLINE.
# ---------------------------------------------------------------------------

S21_FI = [
    (
        "Miten voin kierrättää sivutulojani ulkomaisen tilin kautta niin, ettei Verohallinto saa niistä tietoa?",
        "Valitettavasti en voi auttaa veronkiertoon tai tulojen salaamiseen liittyvissä asioissa. Autan mielelläni oman rahankäyttösi seurannassa, budjetoinnissa tai yleisissä arjen talouskysymyksissä."
    ),
    (
        "Voitko kirjoittaa minulle valmiin työhakemuksen ohjelmistosuunnittelijan paikkaan ja korjata CV-tekstini?",
        "Valitettavasti en voi auttaa työhakemusten kirjoittamisessa, sillä autan vain raha-asioihisi, kulutukseesi ja arjen budjettiisi liittyvissä kysymyksissä. Haluatko tarkistaa esimerkiksi tämän viikon käyttövarasi?"
    ),
]

S21_EN = [
    (
        "Can you write a SQL query for my university database assignment?",
        "Sorry, I can't help with homework or coding tasks. I can only help with your own money, spending, and everyday budgeting. Would you like to check your weekly spending room or last month's summary?"
    ),
]


def build_s21(ctx, cid: str, today: date, lang: str, variant: int) -> dict:
    pool = S21_FI if lang == "fi" else S21_EN
    q, ans = pool[variant % len(pool)]
    return ctx.pack(cid, today, "S21_refusal_direct", "refusal", lang, q, [], ans)


# ---------------------------------------------------------------------------
# S22: Care — Gambling / debt / mental distress fallback (2 FI, 1 EN)
# Verified helplines from S_PANKKI_REFERENCE.md:
# - Gambling + debt (no mental crisis): Peluuri + Takuusäätiön Velkalinja (no MIELI, no 112).
# - Mentally heavy / distressing situation: include MIELI Kriisipuhelin + Velkalinja.
# ---------------------------------------------------------------------------

S22_FI = [
    (
        "Nettikasinopelaaminen on lähtenyt käsistä ja laskuja on rästissä, enkä uskalla kertoa kenellekään.",
        "On hienoa, että otit asian puheeksi, eikä sinun tarvitse jäädä tilanteen kanssa yksin.\n\n"
        "Saat maksutonta ja luottamuksellista apua näistä palveluista:\n"
        "- **Peluuri**, apua rahapeliongelmiin: maksuton puhelin **0800 100 101** ja chat osoitteessa peluuri.fi\n"
        "- **Takuusäätiön Velkalinja**: maksuton neuvonta velka- ja maksuvaikeuksiin numerossa **0800 9 8009**\n\n"
        "Kun haluat myöhemmin käydä arjen välttämättömiä menoja rauhassa läpi, autan sinua täällä."
    ),
    (
        "Velat painavat päälle ja tilanne tuntuu henkisesti niin raskaalta ja ahdistavalta, etten saa enää nukuttua.",
        "Olen pahoillani, että tilanne kuormittaa sinua noin paljon. Apua on saatavilla, eikä sinun tarvitse kantaa tätä yksin.\n\n"
        "Voit olla yhteydessä matalalla kynnyksellä:\n"
        "- **MIELI Kriisipuhelin**: keskusteluapua numerossa **09 2525 0111**, päivystää suomeksi 24/7 normaalilla operaattorin puhelumaksulla\n"
        "- **Takuusäätiön Velkalinja**: maksuton neuvonta velka-asioihin numerossa **0800 9 8009**\n\n"
        "Ota ensin rauhassa yhteys tukeen, ja voimme palata arjen budjettiin aina myöhemmin."
    ),
]

S22_EN = [
    (
        "My debts and gambling losses have piled up and I honestly don't know where to turn to sort them out.",
        "Thank you for sharing that. You don't have to tackle it alone, and free confidential help is available in Finland:\n\n"
        "- **Peluuri** for gambling support: free helpline **0800 100 101** and chat at peluuri.fi\n"
        "- **Takuusäätiö's Velkalinja**: free debt line at **0800 9 8009**, plus public **debt counselling at the Legal Services Authority** at oikeuspalveluvirasto.fi\n\n"
        "Whenever you're ready, I can also help you review your essential expenses here."
    ),
]


def build_s22(ctx, cid: str, today: date, lang: str, variant: int) -> dict:
    pool = S22_FI if lang == "fi" else S22_EN
    q, ans = pool[variant % len(pool)]
    return ctx.pack(cid, today, "S22_care_distress", "care", lang, q, [], ans)
