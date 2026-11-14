// "Kuitit": the customer's latest card purchases from their own data, grouped by day,
// each shown in its basket (🏠 🔧 ☕). The data has no shop names, so a receipt is
// named by its merchant type ("Ruokakauppa", "Apteekki").
import { formatDay, locales, type Lang, type Text } from "../lib/i18n";
import { basketLabel, merchantName } from "../lib/merchants";
import { formatMoney } from "../lib/money";
import type { BasketSummary, Receipt } from "../lib/types";
import { BackIcon } from "./Icons";

interface Props {
  t: Text;
  lang: Lang;
  receipts: Receipt[] | null;
  today: string | null;
  summary: BasketSummary | null;   // for the basket names, as the backend writes them
  onBack: () => void;
}

const time = (iso: string, lang: Lang) =>
  new Date(iso).toLocaleTimeString(locales[lang], { hour: "2-digit", minute: "2-digit" });

/** "Tänään", "Eilen" or "7.9.", relative to the coach's "today". */
function dayHeading(day: string, today: string | null, t: Text, lang: Lang) {
  if (today) {
    if (day === today) return t.home.today;
    const yesterday = new Date(`${today}T12:00:00`);
    yesterday.setDate(yesterday.getDate() - 1);
    if (day === yesterday.toISOString().slice(0, 10)) return t.home.yesterday;
  }
  return formatDay(day, lang, { weekday: "short", day: "numeric", month: "numeric" });
}

export function ReceiptRow({ receipt, summary, lang, t }: { receipt: Receipt; summary: BasketSummary | null; lang: Lang; t: Text }) {
  const basket = basketLabel(receipt.basket, summary, lang);
  return (
    <div className="sm-row sm-receipt">
      <span className="sm-receipt-icon" aria-hidden="true">{basket.split(" ")[0] || "🧾"}</span>
      <span className="sm-row-text">
        <span className="sm-row-title">{merchantName(receipt.merchant_type, receipt.category, lang)}</span>
        <span className="sm-row-sub">
          {time(receipt.timestamp, lang)}
          {basket && ` · ${basket.split(" ").slice(1).join(" ")}`}
        </span>
        {receipt.unusual && <span className="sm-receipt-flag">{t.home.unusualPurchase}</span>}
      </span>
      <span className="sm-row-end sm-receipt-amount money">{formatMoney(receipt.amount_eur)}</span>
    </div>
  );
}

export function ReceiptsPage({ t, lang, receipts, today, summary, onBack }: Props) {
  const h = t.home;
  const days = new Map<string, Receipt[]>();
  for (const r of receipts ?? []) {
    const day = r.timestamp.slice(0, 10);
    days.set(day, [...(days.get(day) ?? []), r]);
  }

  return (
    <>
      <header className="sm-header">
        <button type="button" className="sm-icon-button" aria-label={h.back} onClick={onBack}><BackIcon /></button>
        <h1 className="sm-header-title">{h.receipts}</h1>
        <span />
      </header>
      <main className="sm-scroll">
        <div className="sm-section">
          <p className="sm-receipts-lead">{h.receiptsLead}</p>
          {receipts === null && <p className="sm-receipts-lead">{t.loading}</p>}
          {receipts?.length === 0 && <p className="sm-receipts-lead">{h.receiptsEmpty}</p>}
          {[...days].map(([day, list]) => (
            <section key={day} className="sm-receipts-day">
              <h2 className="sm-heading">{dayHeading(day, today, t, lang)}</h2>
              <div className="sm-card sm-list">
                {list.map((r) => <ReceiptRow key={r.timestamp + r.amount_eur} receipt={r} summary={summary} lang={lang} t={t} />)}
              </div>
            </section>
          ))}
        </div>
      </main>
    </>
  );
}
