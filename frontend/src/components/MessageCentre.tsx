// S-mobiili's Message centre with the coach added as its first row: where the
// coach would plug into the existing app, next to the virtual assistant.
import type { Text } from "../lib/i18n";
import { BackIcon, ChatsIcon, CoachIcon, ExternalIcon, FeedbackIcon, InfoIcon, MailIcon } from "./Icons";
import { ListRow } from "./ListRow";

interface Props {
  t: Text;
  onBack: () => void;
  onOpenCoach: () => void;
}

export function MessageCentre({ t, onBack, onOpenCoach }: Props) {
  const h = t.home;
  return (
    <>
      <header className="sm-header">
        <button type="button" className="sm-icon-button" aria-label={h.back} onClick={onBack}><BackIcon /></button>
        <h1 className="sm-header-title">{h.messageCentre}</h1>
        <span />
      </header>
      <main className="sm-scroll">
        <div className="sm-section">
          <div className="sm-card sm-list">
            <ListRow icon={<CoachIcon />} title={h.mcCoach} subtitle={h.mcCoachSub}
                     end={<span className="sm-pill">{h.coachNew}</span>} onClick={onOpenCoach} highlight />
            <ListRow icon={<ChatsIcon />} title={h.mcAssistant} subtitle={h.mcAssistantSub} hint={h.notInDemo} />
            <ListRow icon={<InfoIcon />} title={h.mcFaq} end={<ExternalIcon />} hint={h.notInDemo} />
            <ListRow icon={<FeedbackIcon />} title={h.mcFeedback} hint={h.notInDemo} />
          </div>
          <h2 className="sm-heading">{h.mcServiceTitle}</h2>
          <div className="sm-card sm-list">
            <ListRow icon={<MailIcon />} title={h.mcMessages} subtitle={h.mcMessagesSub} hint={h.notInDemo} />
          </div>
        </div>
      </main>
    </>
  );
}
