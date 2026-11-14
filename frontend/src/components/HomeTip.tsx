// "Talousneuvoja" on the home screen: one tip picked by rules from the customer's own
// data (coach/tips.py), the same kind of chart the coach draws in the chat, and a
// button that opens the coach and asks the tip's follow-up question.
import type { Lang, Text } from "../lib/i18n";
import type { Tip } from "../lib/types";
import { ChatChart } from "./ChatChart";

interface Props {
  t: Text;
  lang: Lang;
  tip: Tip | null;
  onAsk: (question: string) => void;
}

function words(tip: Tip, t: Text) {
  const texts = t.home.tip;
  if (tip.kind === "above_finland") return texts.above_finland[tip.facts.category];
  return texts[tip.kind];
}

export function HomeTip({ t, lang, tip, onAsk }: Props) {
  const h = t.home;
  if (!tip) {
    return <div className="sm-card sm-tip"><p className="sm-tip-body muted">{t.loading}</p></div>;
  }
  const w = words(tip, t);
  return (
    <section className="sm-card sm-tip" aria-labelledby="tip-title">
      <h3 id="tip-title" className="sm-tip-title"><span aria-hidden="true">💡</span> {w.title}</h3>
      <p className="sm-tip-body">{w.body(tip.facts)}</p>
      <ChatChart chart={tip.chart} t={t} lang={lang} />
      <button type="button" className="sm-tip-button" onClick={() => onAsk(w.question)}>
        {h.askMore}
      </button>
    </section>
  );
}
