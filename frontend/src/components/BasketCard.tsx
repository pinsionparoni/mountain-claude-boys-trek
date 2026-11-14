// One spending basket this month so far, measured against what the budget expects
// for it: usual essentials (🏠), the reserve for surprises (🔧) or the everyday
// budget (☕). Figures come from the backend; nothing is calculated here but a share.
import type { Lang, Text } from "../lib/i18n";
import { categoryName } from "../lib/merchants";
import { formatMoney } from "../lib/money";
import type { Basket, BasketKey } from "../lib/types";

interface Props {
  basketKey: BasketKey;
  basket: Basket;
  reference: number | null;   // the monthly amount this basket is measured against
  periodLabel: string;
  showBar: boolean;
  t: Text;
  lang: Lang;
}

const REF_TEXT = { regular_essentials: "refRegular", unexpected_necessities: "refUnexpected", everyday_spending: "refEveryday" } as const;

export function BasketCard({ basketKey, basket, reference, periodLabel, showBar, t, lang }: Props) {
  const label = lang === "fi" ? basket.label_fi : basket.label;
  const [icon, ...name] = label.split(" ");
  const spent = basket.total_eur;
  const share = reference ? Math.min(spent / reference, 1) : 0;
  const over = reference !== null && spent > reference;

  return (
    <section className={`panel basket-card basket-card--${basketKey}`} aria-label={label}>
      <h2 className="panel-title basket-card-title">
        <span className="basket-card-icon" aria-hidden="true">{icon}</span>{name.join(" ")}
      </h2>
      <p className="muted basket-card-period">{t.basketSoFar(periodLabel)}</p>
      <p className="sts-amount money">{formatMoney(spent)}</p>

      {reference !== null && reference > 0 && (
        <>
          {showBar && (
            <div className={`basket-card-bar${over ? " is-over" : ""}`} aria-hidden="true">
              <div className="basket-card-bar-fill" style={{ inlineSize: `${share * 100}%` }} />
            </div>
          )}
          <p className="basket-card-ref">
            <span>{t[REF_TEXT[basketKey]](formatMoney(reference))}</span>
            <span className={over ? "basket-card-over" : "muted"}>
              {over ? t.refOver(formatMoney(spent - reference)) : t.refLeft(formatMoney(reference - spent))}
            </span>
          </p>
        </>
      )}

      {basket.categories.length === 0
        ? <p className="muted">{t.basketEmpty}</p>
        : (
          <ul className="basket-card-cats">
            {basket.categories.slice(0, 3).map((c) => (
              <li key={c.category}>
                <span>{categoryName(c.category, lang)}</span>
                <span className="money">{formatMoney(c.total_eur)}</span>
              </li>
            ))}
          </ul>
        )}
    </section>
  );
}
