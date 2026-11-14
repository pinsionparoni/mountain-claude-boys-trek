// Minä tab, laid out like S-mobiili. Shows the synthetic demo customer, never a real person.
import type { Text } from "../lib/i18n";
import { ChatDotIcon, DocIcon, IdCardIcon, KeyIcon, PersonIcon, QrIcon, ShieldIcon } from "./Icons";
import { ListRow } from "./ListRow";

export function MinaPage({ t, customerId, onOpenMessages }: { t: Text; customerId: string; onOpenMessages: () => void }) {
  const h = t.home;
  return (
    <>
      <div className="sm-topbar sm-topbar--end">
        <button type="button" className="sm-icon-button" aria-label={h.messageCentre} onClick={onOpenMessages}>
          <ChatDotIcon />
        </button>
      </div>
      <section className="sm-profile">
        <span className="sm-avatar" aria-hidden="true">D</span>
        <p className="sm-profile-name">{h.demoName}</p>
        <p className="muted">{customerId}</p>
      </section>

      <div className="sm-section">
        <div className="sm-card sm-list">
          <ListRow icon={<PersonIcon />} title={h.myInfo} subtitle={h.myInfoSub} hint={h.notInDemo} />
        </div>

        <h2 className="sm-heading">{h.authentication}</h2>
        <div className="sm-tiles">
          <span className="sm-tile" title={h.notInDemo}><span className="sm-row-icon"><QrIcon /></span>{h.scanQr}</span>
          <span className="sm-tile" title={h.notInDemo}><span className="sm-row-icon"><ShieldIcon /></span>{h.confirmTx}</span>
        </div>

        <h2 className="sm-heading">{h.bankServices}</h2>
        <div className="sm-card sm-list">
          <ListRow icon={<KeyIcon />} title={h.identification} hint={h.notInDemo} />
          <ListRow icon={<IdCardIcon />} title={h.userId} hint={h.notInDemo} />
          <ListRow icon={<DocIcon />} title={h.customerInfo} hint={h.notInDemo} />
        </div>
      </div>
    </>
  );
}
