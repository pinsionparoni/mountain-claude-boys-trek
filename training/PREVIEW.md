# Gemma 4 31B Fine-Tuning — Representative Training Samples (`S01`–`S22`)

One sample per scenario generated offline from real CSV tool outputs (`280` total: `250` train + `30` val).

## train-S01-fi-01 — `S01_safe_to_spend_cash_limited` (coaching, `fi`, `CUST03888`, today `2026-09-10`)

**Customer:** Paljonko voin käyttää rahaa tällä viikolla ilman, että tili menee tiukille?

- *Tool call:* `get_safe_to_spend({})`

**Coach:**

Tällä viikolla voit käyttää turvallisesti **160,96 €**.

Kuukauden arjen kulutuksen budjetistasi on jäljellä 539,91 €, mutta käyttötilisi saldo 331,83 € rajoittaa viikkosummaa juuri nyt. Ennen seuraavaa palkkapäivää 15.9. tililtä varataan arviolta 170,87 € kiinteisiin ja muihin välttämättömiin menoihin.

**Vinkki:** Palkkapäivään on 5 päivää. Kun pidät arjen ostokset maltillisina siihen asti, käyttötililläsi riittää kate myös laskuihin.

---

## train-S02-fi-01 — `S02_safe_to_spend_budget_healthy` (coaching, `fi`, `CUST03077`, today `2026-09-18`)

**Customer:** Paljonko minulla on kuukausibudjetin mukaan varaa käyttää tällä viikolla?

- *Tool call:* `get_safe_to_spend({})`

**Coach:**

Tällä viikolla voit käyttää turvallisesti **252,96 €**.

Tyypillisistä 2 307,15 €/kk tuloistasi vähennetään ensin välttämättömät menot 1 686,31 €, varaus yllättäviin menoihin 143,38 € sekä tavanomainen säästäminen 0,00 €. Arjen kulutukseen jää kuukaudessa 477,45 €, josta sinulla on tässä kuussa jäljellä **469,78 €**.

Käyttötilisi saldo 6 346,32 € riittää hyvin menoihin ennen palkkapäivää 15.10.2026. **Vinkki:** Jos viikon lopussa jää osa summasta käyttämättä, voit siirtää sen puskuriin säästötilille.

---

## train-S03-fi-01 — `S03_safe_to_spend_tight_or_over` (coaching, `fi`, `CUST01874`, today `2026-09-10`)

**Customer:** Onko minulla enää yhtään varaa kuluttaa tällä viikolla?

- *Tool call:* `get_safe_to_spend({})`

**Coach:**

Tällä viikolla siihen ei valitettavasti ole varaa.

Tällä hetkellä turvallinen summa arjen kulutukseen tälle viikolle on **0,00 €**.

Käyttötilisi saldo on −431,96 €, ja ennen palkkapäivää 15.9. välttämättömiin menoihin kuluu arviolta 337,51 €. Siksi ylimääräisiä arjen menoja kannattaa nyt lykätä palkkapäivän yli.

**Vinkki:** Jos jonkin laskun eräpäivä mietityttää, ole ajoissa yhteydessä laskuttajaan tai S-Pankin asiakaspalveluun.

---

## train-S04-fi-01 — `S04_basket_summary_monthly` (coaching, `fi`, `CUST01777`, today `2026-09-10`)

**Customer:** Jaa viime kuun menoni kolmeen kulutuskoriin.

- *Tool call:* `get_basket_summary({"start_date": "2026-08-01", "end_date": "2026-08-31"})`

**Coach:**

Kulutit elokuussa yhteensä **2 591,39 €**. Menosi jakautuivat kolmeen kulutuskategoriaan näin:

- **🏠 Välttämättömät menot:** 1 771,61 €, eli 68,4 % menoista. Suurimpia eriä olivat asuminen 881,07 € sekä ruokaostokset 316,32 €.
- **🔧 Yllättävät menot:** 202,86 €, osuus 7,8 %, terveys 202,86 €.
- **☕ Arjen kulutus:** 616,92 €, eli 23,8 % menoista. Eniten kului kohteisiin matkailu 290,48 €, viihde 187,15 € sekä vapaa-aika 139,29 €.

Luokittelu tehdään kauppiaan toimialan mukaan: esimerkiksi julkinen liikenne ja polttoaine kuuluvat välttämättömiin menoihin, ja taksit arjen kulutukseen. Halutessasi katsomme tarkemmin, mistä arjen kulutus koostui.

---

## train-S05-fi-01 — `S05_unexpected_and_buffer` (coaching, `fi`, `CUST03203`, today `2026-08-22`)

**Customer:** Paljonko minulla on ollut yllättäviä menoja viimeisen puolen vuoden aikana?

- *Tool call:* `get_basket_summary({"start_date": "2026-02-01", "end_date": "2026-07-31"})`

**Coach:**

Kuuden viime kuukauden ajalla (1.2.–31.7.2026) kategoriaan **🔧 Yllättävät menot** kertyi yhteensä **491,51 €**, eli keskimäärin **82,65 € kuukaudessa** ja 3,6 % kaikista menoistasi.

Kotiin ja elektroniikkaan meni 416,53 € sekä terveyteen 74,98 €.

**Vinkki:** Yllättävät menot tulevat epätasaisesti. Kun siirrät noin 82,65 € kuukaudessa säästötilille, puskurisi pysyy kunnossa.

---

## train-S06-fi-01 — `S06_salary_sweep_caveat` (coaching, `fi`, `CUST03979`, today `2026-09-10`)

**Customer:** Miltä viime kuun tuloni ja menoni näyttävät kokonaisuutena?

- *Tool call:* `get_basket_summary({"start_date": "2026-08-01", "end_date": "2026-08-31"})`

**Coach:**

Tältä tililtä kirjatut kulutusmenosi elokuussa olivat yhteensä **436,77 €**:

- **🏠 Välttämättömät menot:** 241,00 €
- **🔧 Yllättävät menot:** 0,00 €
- **☕ Arjen kulutus:** 195,77 €

**Huomaa:** palkastasi 6 586,17 € siirtyi toiselle tilille **5 861,69 €** eli 89 %. Tätä siirtoa ei lasketa kulutukseksi, mutta koska näen vain tämän tilin tilitapahtumat, osa kiinteistä menoistasi, kuten asuminen tai laskut, saatetaan maksaa toiselta tililtä.

---

## train-S07-fi-01 — `S07_category_breakdown` (coaching, `fi`, `CUST04263`, today `2026-09-10`)

**Customer:** Mitkä olivat suurimmat menoluokkani viime kuussa?

- *Tool call:* `get_spending_by_category({"start_date": "2026-08-01", "end_date": "2026-08-31"})`

**Coach:**

Kulutit elokuussa yhteensä **4 897,91 €**. Viisi suurinta menoluokkaasi olivat:

- **Koti ja elektroniikka:** 1 146,46 €
- **Liikkuminen:** 1 098,87 €
- **Asuminen:** 895,57 €
- **Viihde:** 730,44 €
- **Ruokaostokset:** 536,77 €

**Vinkki:** Jos jokin näistä luokista mietityttää, voin eritellä sen ostokset tarkemmin.

---

## train-S08-fi-01 — `S08_merchant_type_detail` (coaching, `fi`, `CUST04942`, today `2026-07-12`)

**Customer:** Kuinka paljon rahaa meni kahviloihin ja pikaruokaan viime kuussa?

- *Tool call:* `get_spending_by_category({"start_date": "2026-06-01", "end_date": "2026-06-30", "category": "Restaurants"})`

**Coach:**

Käytit kesäkuussa kahviloihin ja pikaruokaan yhteensä **151,18 €**.

Kaikkiaan ravintoloihin meni samassa kuussa 284,84 €. Pikaruokapaikat ja kahvilat lasketaan arjen kulutukseen.

---

## train-S09-fi-01 — `S09_transactions_and_balance_trend` (coaching, `fi`, `CUST02976`, today `2026-09-10`)

**Customer:** Mitkä olivat kolme suurinta yksittäistä menoerääni elokuussa?

- *Tool call:* `get_transactions({"start_date": "2026-08-01", "end_date": "2026-08-31", "order": "largest", "limit": 10})`

**Coach:**

Kolme suurinta yksittäistä menoerääsi elokuussa olivat:

- **115,72 €**: Viihde
- **94,43 €**: Ruokaostokset
- **91,76 €**: Ravintolat

Haluatko tarkastella jonkin tietyn menoluokan ostoksia vielä tarkemmin?

---

## train-S10-fi-01 — `S10_peer_comparison_and_budget` (coaching, `fi`, `CUST04905`, today `2026-09-10`)

**Customer:** Miten kulutukseni vertautuu muihin samanikäisiin?

- *Tool call:* `compare_with_peers({})`

- *Tool call:* `get_safe_to_spend({})`

**Coach:**

Viimeisen 12 täyden kuukauden ajalla (1.9.2025–31.8.2026) kokonaiskulutuksesi oli **1 071,57 €/kk**, eli 41 % vähemmän kuin 18–24-vuotiaat tyypillisesti.

- Vapaa-aikaan käytät 13,17 €/kk, eli 82 % vähemmän kuin ikäisesi tyypillisesti.
- Kotiin ja elektroniikkaan käytät 22,53 €/kk, eli 80 % vähemmän kuin ikäisesi tyypillisesti.
- ☕ Arjen kulutukseen käytät 183,33 €/kk, eli 62 % vähemmän kuin ikäisesi tyypillisesti.

Asumista, sähköä ja vettä ei verrata, koska ne riippuvat asumismuodosta. Oman budjettisi mukaan turvallinen käyttövarasi tälle viikolle on **56,23 €**.

---

## train-S11-fi-01 — `S11_what_if_reduction` (coaching, `fi`, `CUST00357`, today `2026-09-10`)

**Customer:** Paljonko säästäisin kuukaudessa ja vuodessa, jos vähentäisin kuluja ravintoloista 25 %?

- *Tool call:* `get_spending_by_category({"start_date": "2026-03-01", "end_date": "2026-08-31", "category": "Restaurants"})`

- *Tool call:* `calculate_what_if({"monthly_by_category": {"Restaurants": 234.81}, "reductions_pct": {"Restaurants": 25}})`

**Coach:**

Jos käytät ravintoloihin 25 % vähemmän, säästät **58,70 € kuukaudessa** ja **704,43 € vuodessa**.

Kuuden viime täyden kuukauden (1.3.–31.8.2026) perusteella käytit ravintoloihin keskimäärin 234,81 €/kk. Muutoksen jälkeen uusi kuukausitaso olisi 176,11 €/kk.

**Vinkki:** Säästyvät 58,70 € voit siirtää palkkapäivänä automaattisesti säästötilille tai Säästäjä-palveluun.

---

## train-S12-fi-01 — `S12_safe_to_save_monthly` (coaching, `fi`, `CUST03035`, today `2026-09-18`)

**Customer:** Kuinka paljon pystyisin laittamaan säästöön kuukausittain ilman, että arki kiristyy liikaa?

- *Tool call:* `get_basket_summary({"start_date": "2026-03-01", "end_date": "2026-08-31"})`

- *Tool call:* `calculate_safe_to_save({"monthly_income": 3031.06, "monthly_mandatory_regular": 1775.47, "monthly_mandatory_irregular": 219.04, "monthly_everyday": 474.38})`

**Coach:**

Kuuden viime kuukauden (1.3.–31.8.2026) lukujesi perusteella voit laittaa turvallisesti säästöön **449,74 € kuukaudessa**, eli yhteensä **5 396,83 € vuodessa**.

Tulosi ovat olleet keskimäärin 3 031,06 €/kk ja menosi 2 468,89 €/kk. Kuukaudessa on jäänyt yli 562,17 €. Siitä jätetään vielä viidennes liikkumavaraksi käyttötilille, jotta kuukausivaihtelut eivät kiristä arkea.

**Vinkki:** Voit aloittaa kerryttämällä puskuria esimerkiksi S-Tuottotilille heti palkkapäivänä.

---

## train-S13-fi-01 — `S13_vocabulary_and_capabilities` (coaching, `fi`, `CUST03220`, today `2026-09-10`)

**Customer:** Mitä eroa on taloudellisella puskurilla ja kuukausisäästämisellä, ja mitä hätävara tarkoittaa?

**Coach:**

Nämä täydentävät toisiaan arjen taloudessa:

- **Puskuri eli hätävara:** helposti nostettava taloudellinen puskuri esimerkiksi säästötilillä tai S-Tuottotilillä yllättäviä välttämättömiä menoja varten, kuten hammaslääkäriä tai rikkoutunutta kodinkonetta varten.
- **Kuukausisäästäminen:** säännöllistä säästämistä pidemmän ajan tavoitteisiin esimerkiksi tilille tai rahastoon. Rahastosäästämiseen liittyy aina tuoton lisäksi myös arvonvaihtelun riski.

**Vinkki:** Usein on mukavinta kerryttää ensin puskuri arjen yllätyksiin, jotta sijoituksiin ei tarvitse koskea tiukan paikan tullen.

---

## train-S14-fi-01 — `S14_borderline_neutral_spending` (borderline, `fi`, `CUST02355`, today `2026-09-10`)

**Customer:** Paljonko rahaa minulla meni baari-iltoihin elokuussa?

- *Tool call:* `get_spending_by_category({"start_date": "2026-08-01", "end_date": "2026-08-31", "category": "Restaurants"})`

**Coach:**

Käytit baareihin elokuussa yhteensä **48,84 €**.

Ravintoloihin meni samassa kuussa yhteensä 238,36 €, ja ne kuuluvat kategoriaan ☕ Arjen kulutus. Haluatko katsoa myös pidemmän aikavälin keskiarvon?

---

## train-S15-fi-01 — `S15_borderline_cut_habits` (borderline, `fi`, `CUST02471`, today `2026-08-22`)

**Customer:** Tuntuu että viikonloppuiltoihin ja ulkona syömiseen valuu huomaamatta rahaa. Paljonko minulla menee niihin keskimäärin kuussa?

- *Tool call:* `get_spending_by_category({"start_date": "2026-02-01", "end_date": "2026-07-31", "category": "Restaurants"})`

**Coach:**

Kuuden viime täyden kuukauden aikana (1.2.–31.7.2026) olet käyttänyt ravintoloihin yhteensä 3 125,17 €, eli keskimäärin **525,54 €/kk**. Tästä on mennyt baareihin noin 56,30 €/kk ja kahviloihin ja pikaruokaan noin 199,40 €/kk.

Haluatko laskea, paljonko säästäisit kuukaudessa ja vuodessa, jos pienentäisit tätä summaa esimerkiksi tietyn prosentin verran?

**Customer:** Joo, laske paljonko jäisi säästöön jos leikkaisin noista menoista 25 %?

- *Tool call:* `calculate_what_if({"monthly_by_category": {"Restaurants": 525.54}, "reductions_pct": {"Restaurants": 25}})`

**Coach:**

Jos vähennät ravintolakulujasi **25 %**, menot pienenevät tasolta 525,54 €/kk tasolle **394,16 €/kk**:

- **Säästö kuukaudessa:** 131,39 €
- **Säästö vuodessa:** **1 576,62 €**

**Vinkki:** Päätä viikonloppua varten etukäteen selkeä eurokatto S-Tilille ja siirrä säästyvä 131,39 €/kk heti palkkapäivänä säästötilille, niin muutos näkyy nopeasti puskurissa.

---

## train-S16-fi-01 — `S16_advice_limits_investments` (advice_limits, `fi`, `CUST01080`, today `2026-09-10`)

**Customer:** Paljonko minulla olisi varaa sijoittaa kuukausittain ja mihin rahastoon tai osakkeeseen se kannattaisi laittaa?

- *Tool call:* `get_basket_summary({"start_date": "2026-03-01", "end_date": "2026-08-31"})`

- *Tool call:* `calculate_safe_to_save({"monthly_income": 3568.38, "monthly_mandatory_regular": 2572.62, "monthly_mandatory_irregular": 169.19, "monthly_everyday": 568.98})`

**Coach:**

Kuuden viime täyden kuukauden (1.3.–31.8.2026) tulojesi ja menojesi perusteella kuukausittainen ylijäämäsi on ollut keskimäärin 257,59 €/kk, joten turvallinen säännöllinen säästö- tai sijoitussumma on arviolta **206,07 €/kk**.

Yksittäisiä osakkeita, rahastoja tai muita sijoituskohteita en suosittele. Yleisenä periaatteena on hyvä huolehtia ensin **taloudellisesta puskurista** tilillä ja huomioida sijoittamisessa **hajauttaminen**, sijoitusaika, kulut sekä se, että sijoituksiin liittyy aina arvonvaihtelun riski eikä historiallinen tuotto takaa tulevaa.

Sinulle sopivan kohteen valintaan saat henkilökohtaista apua S-mobiilin **Säästäjä**-palvelusta tai **S-Pankin sijoitusneuvonnan asiantuntijoilta**.

---

## train-S17-fi-01 — `S17_advice_limits_loans` (advice_limits, `fi`, `CUST00084`, today `2026-09-10`)

**Customer:** Tili näyttää aika pieneltä ennen palkkapäivää — kannattaisiko minun nostaa luottoa tai pikaluotto loppukuun menoihin?

- *Tool call:* `get_safe_to_spend({})`

**Coach:**

Arjen menojen tai tilapäisen budjettivajeen paikkaamista luotolla ei voi suositella, koska korot ja kulut kaventavat seuraavien kuukausien liikkumavaraa entisestään.

Käyttötilisi saldo on nyt **242,64 €**, seuraava palkkapäivä on 15.9., ja turvallinen käyttövarasi tälle viikolle on **67,59 €**.

**Vinkki:** Keskity ennen palkkapäivää vain välttämättömiin ruoka- ja arkimenoihin, ja jos yksittäisen laskun eräpäivä osuu hankalasti, kysy suoraan laskuttajalta maksuajan siirtoa. Laajemmissa luottoasioissa sinua palvelevat **S-Pankin asiantuntijat**.

---

## train-S18-fi-01 — `S18_advice_limits_taxes` (advice_limits, `fi`, `CUST03403`, today `2026-07-12`)

**Customer:** Paljonko joudun maksamaan veroa, jos myyn voitolla olevia rahasto-osuuksiani?

**Coach:**

Yleisellä tasolla yksityishenkilön rahasto-osuuksien myynnistä syntyvä luovutusvoitto verotetaan Suomessa pääomatulona: veroprosentti on 30 % pääomatuloista 30 000 euroon asti ja 34 % sen ylittävältä osalta. Pienet luovutukset voivat olla verovapaita, jos koko kalenterivuoden kaikkien luovutushintojen yhteismäärä jää enintään 1 000 euroon.

Tämä on **yleistä verotietoa, ei Verohallinnon sitova ratkaisu**, ja verokohtelu riippuu omista kokonaistuloistasi sekä hankintahinnoista tai hankintameno-olettamasta. Tarkat luvut ja ohjeet omalle verotuksellesi saat **Verohallinnosta** osoitteessa **vero.fi**.

---

## train-S19-fi-01 — `S19_refusal_pin_and_credentials` (refusal, `fi`, `CUST04626`, today `2026-09-10`)

**Customer:** Korttini ei toiminut kassalla, tunnuslukuni on 4821 — voitko tarkistaa mikä kortissa on vikana?

**Coach:**

Älä kirjoita tähän korttisi tunnuslukua tai PIN-koodia äläkä pankkitunnuksiasi. S-Pankki ei koskaan pyydä niitä keskustelussa. Valitettavasti en voi auttaa kortin tai tunnuslukujen tarkistamisessa täällä.

Tarkista korttisi turvarajat tai sulje kortti tarvittaessa heti S-mobiilin korttiosiossa tai S-Pankin sulkupalvelussa. Oman budjettisi ja kulutuksesi seurannassa autan mielelläni.

---

## train-S20-fi-01 — `S20_refusal_multiturn_edge` (refusal, `fi`, `CUST00922`, today `2026-09-10`)

**Customer:** Paljonko minulla kului ravintoloihin ja baareihin elokuussa?

- *Tool call:* `get_spending_by_category({"start_date": "2026-08-01", "end_date": "2026-08-31", "category": "Restaurants"})`

**Coach:**

Kulutit ravintoloihin elokuussa yhteensä **85,57 €**. Haluatko tarkastella näitä tarkemmin?

**Customer:** Entä saako nuo tapahtumat jotenkin piilotettua tai siivottua tiliotteelta niin ettei puoliso näe niitä?

**Coach:**

Valitettavasti en voi auttaa tilitapahtumien piilottamisessa tai muokkaamisessa. Tiliote muodostuu aina todellisista maksuista. Autan sen sijaan mielelläni suunnittelemaan selkeän yhteisen tai oman kuukausibudjetin arjen menoihin.

---

## train-S21-fi-01 — `S21_refusal_direct` (refusal, `fi`, `CUST00875`, today `2026-09-10`)

**Customer:** Miten voin kierrättää sivutulojani ulkomaisen tilin kautta niin, ettei Verohallinto saa niistä tietoa?

**Coach:**

Valitettavasti en voi auttaa veronkiertoon tai tulojen salaamiseen liittyvissä asioissa. Autan mielelläni oman rahankäyttösi seurannassa, budjetoinnissa tai yleisissä arjen talouskysymyksissä.

---

## train-S22-fi-01 — `S22_care_distress` (care, `fi`, `CUST00640`, today `2026-09-18`)

**Customer:** Nettikasinopelaaminen on lähtenyt käsistä ja laskuja on rästissä, enkä uskalla kertoa kenellekään.

**Coach:**

On hienoa, että otit asian puheeksi, eikä sinun tarvitse jäädä tilanteen kanssa yksin.

Saat maksutonta ja luottamuksellista apua näistä palveluista:
- **Peluuri**, apua rahapeliongelmiin: maksuton puhelin **0800 100 101** ja chat osoitteessa peluuri.fi
- **Takuusäätiön Velkalinja**: maksuton neuvonta velka- ja maksuvaikeuksiin numerossa **0800 9 8009**

Kun haluat myöhemmin käydä arjen välttämättömiä menoja rauhassa läpi, autan sinua täällä.

---
