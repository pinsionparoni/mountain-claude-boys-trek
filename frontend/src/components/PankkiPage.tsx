// Pankki tab: the account, this month's spending in S-Bank's three baskets (real
// figures from the backend), and the usual banking shortcuts (not part of the demo).
import type { Lang, Text } from "../lib/i18n";
import type { BasketSummary, Budget } from "../lib/types";
import { formatMoney } from "../lib/money";
import sTiliUrl from "../assets/smobiili/s-tili.png";
import { ChatDotIcon, DocIcon, LoanIcon, PayIcon, SavingsIcon } from "./Icons";
import { ListRow } from "./ListRow";

interface Props {
  t: Text;
  lang: Lang;
  budget: Budget | null;
  summary: BasketSummary | null;
  onOpenMessages: () => void;
}

const ORDER = ["regular_essentials", "unexpected_necessities", "everyday_spending"] as const;

export function PankkiPage({ t, lang, budget, summary, onOpenMessages }: Props) {
  const h = t.home;
  return (
    <>
      <div className="sm-topbar sm-topbar--titled">
        <h1 className="sm-page-title">{h.bank}</h1>
        <button type="button" className="sm-icon-button" aria-label={h.messageCentre} onClick={onOpenMessages}>
          <ChatDotIcon />
        </button>
      </div>

      <div className="sm-section">
        <div className="sm-card sm-list">
          <ListRow icon={<img src={sTiliUrl} alt="" className="sm-product-icon" />} title={h.sTili} subtitle={h.balance}
                   end={<span className="sm-amount money">
                     {budget?.cash_check ? formatMoney(budget.cash_check.current_balance) : "–"}
                   </span>}
                   hint={h.notInDemo} />
        </div>

        {summary && (
          <>
            <h2 className="sm-heading">{h.thisMonth}</h2>
            <div className="sm-card sm-list">
              {ORDER.map((key) => {
                const b = summary.baskets[key];
                // Labels look like "🏠 Regular essentials": icon, space, name.
                const [icon, ...name] = (lang === "fi" ? b.label_fi : b.label).split(" ");
                return (
                  <ListRow key={key} icon={<span className="sm-basket-emoji">{icon}</span>}
                           title={name.join(" ")}
                           subtitle={`${b.share_pct.toLocaleString("fi-FI")} %`}
                           end={<span className="sm-receipt-amount money">{formatMoney(b.total_eur)}</span>}
                           hint={h.notInDemo} />
                );
              })}
            </div>
          </>
        )}

        <div className="sm-card sm-list">
          <ListRow icon={<PayIcon />} title={h.payments} hint={h.notInDemo} />
          <ListRow icon={<DocIcon />} title={h.eInvoices} hint={h.notInDemo} />
          <ListRow icon={<SavingsIcon />} title={h.savings} hint={h.notInDemo} />
          <ListRow icon={<LoanIcon />} title={h.loans} hint={h.notInDemo} />
        </div>
      </div>
    </>
  );
}
