import type { SafeToSpend } from "../lib/types";
import { formatMoney } from "../lib/money";

export function SafeToSpendCard({ data }: { data: SafeToSpend }) {
  return (
    <section className="panel panel--highlight" aria-labelledby="sts-title">
      <h2 id="sts-title" className="panel-title">Safe to spend</h2>
      <p className="sts-amount money">{formatMoney(data.amount_eur)}</p>
      <p className="muted">
        {data.period_label} · {data.days_until_payday} days
      </p>
      <p>{data.explanation}</p>
      <p className="estimate-note muted">Estimate based on your transactions, not your account balance.</p>
    </section>
  );
}
