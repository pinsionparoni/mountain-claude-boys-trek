import { formatDay, type Lang, type Text } from "../lib/i18n";
import type { Budget } from "../lib/types";
import { formatMoney } from "../lib/money";

export function SafeToSpendCard({ budget, t, lang }: { budget: Budget; t: Text; lang: Lang }) {
  const month = budget.this_month;
  const cash = budget.cash_check;
  return (
    <section className="panel panel--highlight" aria-labelledby="sts-title">
      <h2 id="sts-title" className="panel-title">{t.stsTitle}</h2>
      <p className="sts-amount money">{formatMoney(budget.safe_to_spend_this_week)}</p>
      <p>
        {month.over_budget > 0
          ? t.overBudget(formatMoney(month.over_budget))
          : t.left(formatMoney(month.remaining), formatMoney(month.everyday_budget))}
      </p>
      {budget.limited_by === "cash" && cash && (
        <p className="notice notice--warning">
          {t.cashLimited(formatMoney(month.per_week), formatDay(cash.next_payday, lang))}
        </p>
      )}
      {budget.limited_by === "budget" && cash && (
        <p className="muted">{t.enoughCash(formatDay(cash.next_payday, lang))}</p>
      )}
      <p className="estimate-note muted">{t.estimate(formatDay(budget.today, lang))}</p>
    </section>
  );
}
