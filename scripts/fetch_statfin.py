"""
Download Statistics Finland's household spending by age and write coach/statfin_data.py.

The open benchmark for "how does my spending compare?": what Finnish households spend
per month, per consumption unit (adjusted for household size with the OECD-modified
scale, so comparable to one person), by age of the household's reference person.

Sources (Statistics Finland, StatFin, licence CC BY 4.0, "Source: Statistics Finland"):
- ktutk/14q4: Household consumption expenditure by age of reference person, 2022
  (the latest Household Budget Survey), at 2022 prices
- ktutk/14q9: Background information by age (households and consumption units),
  to combine 75-84 and 85+ into our 75+
- khi/11xs: Consumer Price Index (2015=100), monthly, to move 2022 prices to the
  price level of the months we compare against

Only categories that map cleanly onto ours are kept (see CATEGORY_MAP). Run it again
to refresh; the app never calls Statistics Finland itself.

    .venv/bin/python scripts/fetch_statfin.py                 # price level Sep 2025 - Aug 2026
    .venv/bin/python scripts/fetch_statfin.py --price-months 2026M01 2026M06
"""

import argparse
import itertools
import json
import urllib.request
from datetime import date
from pathlib import Path

API = "https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin"
OUT = Path(__file__).resolve().parent.parent / "coach" / "statfin_data.py"
SURVEY_YEAR = "2022"
PER_CU_PER_MONTH = "kulukk_kt_hk_2_2"  # per consumption unit, 2022 prices, per month, EUR

# Our category -> COICOP 2018 codes in table 14q4. Housing, utilities, travel,
# Home & Tech and Lifestyle are left out: they are counted too differently to compare.
CATEGORY_MAP = {
    "Groceries": ["01"],            # Food and non-alcoholic beverages
    "Restaurants": ["111"],         # Food and beverage serving services
    "Transportation": ["072", "073"],  # Running a vehicle; passenger transport (no car purchases)
    "Health": ["06"],               # Health
    "Entertainment": ["094", "096"],   # Recreational services; cultural services
}

# Statistics Finland's age bands -> ours (coach/calculations.py AGE_GROUPS).
AGE_MAP = {"17-24": "18–24", "25-34": "25–34", "35-44": "35–44", "45-54": "45–54",
           "55-64": "55–64", "65-74": "65–74", "SSS": "all"}
COMBINED_75 = ["75-84", "85-"]


def query(table: str, selections: dict) -> dict:
    """POST a PxWeb query; returns {(value per dimension, ...): number}."""
    body = {"query": [{"code": k, "selection": {"filter": "item", "values": v}} for k, v in selections.items()],
            "response": {"format": "json-stat2"}}
    req = urllib.request.Request(f"{API}/{table}", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.load(r)
    dims = d["id"]
    keys = [list(d["dimension"][k]["category"]["index"]) for k in dims]
    return {"dims": dims, "updated": d.get("updated"),
            "values": {combo: v for combo, v in zip(itertools.product(*keys), d["value"])}}


def months_between(first: str, last: str) -> list[str]:
    y, m = int(first[:4]), int(first[5:])
    out = []
    while f"{y}M{m:02d}" <= last:
        out.append(f"{y}M{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--price-months", nargs=2, default=["2025M09", "2026M08"], metavar=("FIRST", "LAST"),
                        help="months whose average price level the figures are moved to (default: the peer period)")
    args = parser.parse_args(argv)

    codes = sorted({c for cs in CATEGORY_MAP.values() for c in cs})
    ages = list(AGE_MAP) + COMBINED_75
    spend = query("ktutk/14q4.px", {"timeperiod_y": [SURVEY_YEAR], "coicop_46_20231201": codes,
                                    "ikaryhma_10_20180101": ages, "contentscode": [PER_CU_PER_MONTH]})
    background = query("ktutk/14q9.px", {"timeperiod_y": [SURVEY_YEAR], "ikaryhma_10_20180101": COMBINED_75,
                                         "contentscode": ["pklkm_sum", "oecdmod_mean"]})
    price_months = months_between(*args.price_months)
    cpi = query("khi/11xs.px", {"timeperiod_m": months_between(f"{SURVEY_YEAR}M01", f"{SURVEY_YEAR}M12") + price_months,
                                "contentscode": ["ip_0_2015"]})

    def spend_of(code, age):
        return next(v for k, v in spend["values"].items() if code in k and age in k)

    cpi_by_month = {k[0]: v for k, v in cpi["values"].items()}
    base = sum(cpi_by_month[m] for m in months_between(f"{SURVEY_YEAR}M01", f"{SURVEY_YEAR}M12")) / 12
    target = sum(cpi_by_month[m] for m in price_months) / len(price_months)
    factor = target / base

    # Consumption units in the population per old-age band, to weight per-unit spending.
    bg = {k: v for k, v in background["values"].items()}
    units = {a: next(v for k, v in bg.items() if a in k and "pklkm_sum" in k)
                * next(v for k, v in bg.items() if a in k and "oecdmod_mean" in k) for a in COMBINED_75}

    table = {}
    for ours_cat, cat_codes in CATEGORY_MAP.items():
        for sf_age, our_age in AGE_MAP.items():
            raw = sum(spend_of(c, sf_age) for c in cat_codes)
            table.setdefault(our_age, {})[ours_cat] = round(raw * factor, 2)
        raw75 = sum(sum(spend_of(c, a) for c in cat_codes) * units[a] for a in COMBINED_75) / sum(units.values())
        table.setdefault("75+", {})[ours_cat] = round(raw75 * factor, 2)

    source = {
        "publisher": "Statistics Finland",
        "attribution": "Source: Statistics Finland",
        "licence": "CC BY 4.0",
        "tables": ["StatFin ktutk/14q4", "StatFin ktutk/14q9", "StatFin khi/11xs"],
        "survey_year": int(SURVEY_YEAR),
        "measure": "consumption expenditure per consumption unit (OECD-modified scale) per month, EUR",
        "price_level": f"{args.price_months[0]}–{args.price_months[1]} average (CPI 2015=100: "
                       f"{target:.2f} vs {SURVEY_YEAR} average {base:.2f}, factor {factor:.4f})",
        "retrieved": date.today().isoformat(),
        "coicop": CATEGORY_MAP,
        "note": "75+ combines 75-84 and 85+, weighted by consumption units in the population.",
    }
    OUT.write_text(
        '"""\nGenerated by scripts/fetch_statfin.py: do not edit by hand, run the script again.\n\n'
        "What Finnish households spend per month per consumption unit, by age of the\n"
        "household's reference person (Statistics Finland, CC BY 4.0). See SOURCE.\n"
        '"""\n\n'
        f"SOURCE = {json.dumps(source, ensure_ascii=False, indent=4)}\n\n"
        f"SPENDING_PER_MONTH = {json.dumps(table, ensure_ascii=False, indent=4)}\n",
        encoding="utf-8",
    )
    print(f"Wrote {OUT} (price factor {factor:.4f}, {len(table)} age groups x {len(CATEGORY_MAP)} categories)")


if __name__ == "__main__":
    main()
