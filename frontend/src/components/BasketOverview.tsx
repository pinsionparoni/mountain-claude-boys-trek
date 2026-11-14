import type { BasketKey, BasketSummary } from "../lib/types";
import { formatMoney } from "../lib/money";

const ORDER: BasketKey[] = ["regular_essentials", "unexpected_necessities", "everyday_spending"];
const CSS_NAME: Record<BasketKey, string> = {
  regular_essentials: "regular",
  unexpected_necessities: "unexpected",
  everyday_spending: "everyday",
};

interface Props {
  summary: BasketSummary;
  periodLabel: string;
  showBars: boolean;
}

export function BasketOverview({ summary, periodLabel, showBars }: Props) {
  return (
    <section className="panel" aria-labelledby="baskets-title">
      <h2 id="baskets-title" className="panel-title">Your spending baskets</h2>
      <p className="muted">{periodLabel} · {formatMoney(summary.total_spending_eur)} in total</p>
      <ul className="basket-list">
        {ORDER.map((key) => {
          const b = summary.baskets[key];
          return (
            <li key={key} className={`basket basket--${CSS_NAME[key]}`}>
              <div className="basket-row">
                <span className="basket-label">{b.label}</span>
                <span className="money basket-amount">{formatMoney(b.total_eur)}</span>
              </div>
              {showBars && (
                <div className="basket-bar" aria-hidden="true">
                  <div className="basket-bar-fill" style={{ inlineSize: `${b.share_pct}%` }} />
                </div>
              )}
              <p className="basket-meta muted">
                {b.share_pct.toLocaleString("fi-FI")} % · {b.transaction_count} purchases
              </p>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
