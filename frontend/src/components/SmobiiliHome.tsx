// S-mobiili's logged-in home screen, laid out like the real app. The only change is
// that the chat bubble (top right) leads to the Message centre, where the financial
// coach lives. Balances come from the demo customer's synthetic data; the Bonus and
// receipt figures are made-up demo values.
import { formatDay, type Lang, type Text } from "../lib/i18n";
import type { Budget } from "../lib/types";
import { formatMoney } from "../lib/money";
import sTiliUrl from "../assets/smobiili/s-tili.png";
import visaUrl from "../assets/smobiili/visa-debit.png";
import { BagIcon, BookmarkIcon, ChatDotIcon, ChevronIcon, InfoIcon, LogoutIcon, MailIcon, PlusIcon, ReceiptIcon } from "./Icons";
import { ListRow } from "./ListRow";
import { SLogo } from "./SLogo";

interface Props {
  t: Text;
  lang: Lang;
  budget: Budget | null;
  onOpenMessages: () => void;
  onLogout: () => void;
}

export function SmobiiliHome({ t, lang, budget, onOpenMessages, onLogout }: Props) {
  const h = t.home;
  return (
    <>
      <div className="sm-topbar">
        <button type="button" className="sm-icon-button" aria-label={h.logout} onClick={onLogout}><LogoutIcon /></button>
        <button type="button" className="sm-icon-button" aria-label={h.messageCentre} onClick={onOpenMessages}>
          <ChatDotIcon />
        </button>
      </div>

      <section className="sm-hero">
        <div className="sm-hero-house">
          <SLogo className="sm-hero-logo" />
          <p className="sm-hero-title">{h.bonusTitle(formatMoney(42.1))}</p>
          <p className="sm-hero-sub">{h.bonusSub} <InfoIcon /></p>
        </div>
        <span className="sm-link sm-hero-link" title={h.notInDemo}>{h.totalBenefits} <ChevronIcon /></span>
        <span className="sm-dots" aria-hidden="true"><i className="on" /><i /></span>
      </section>

      <div className="sm-section">
        <div className="sm-card sm-list">
          <ListRow icon={<MailIcon />} title={h.newMessages} end={<span className="sm-count">3</span>} onClick={onOpenMessages} />
        </div>

        <div className="sm-actions">
          {[
            { icon: <PlusIcon />, label: h.newPayment },
            { icon: <BagIcon />, label: h.latestBenefits },
            { icon: <BookmarkIcon />, label: h.savedBenefits },
          ].map((a) => (
            <span key={a.label} className="sm-action" title={h.notInDemo}>
              <span className="sm-action-circle">{a.icon}</span>
              {a.label}
            </span>
          ))}
        </div>

        <h2 className="sm-heading">{h.accountsTitle}</h2>
        <div className="sm-card sm-list">
          <ListRow icon={<img src={sTiliUrl} alt="" className="sm-product-icon" />} title={h.sTili}
                   end={<span className="sm-amount money">
                     {budget?.cash_check ? formatMoney(budget.cash_check.current_balance) : "–"}
                   </span>}
                   hint={h.notInDemo} />
          <ListRow icon={<img src={visaUrl} alt="" className="sm-product-icon" />} title={h.visaDebit}
                   subtitle={h.cardRowSub} end={<span />} hint={h.notInDemo} />
          <span className="sm-list-footer">{h.hide}</span>
        </div>

        <div className="sm-heading-row">
          <h2 className="sm-heading">{h.receipts}</h2>
          <span className="sm-link">{h.open}</span>
        </div>
        <div className="sm-card sm-list">
          <ListRow icon={<ReceiptIcon />} title="S-market" subtitle={budget ? `08:12 ${formatDay(budget.today, lang)}` : undefined}
                   end={<span className="sm-receipt-amount money">{formatMoney(23.45)}</span>} hint={h.notInDemo} />
        </div>
      </div>
    </>
  );
}
