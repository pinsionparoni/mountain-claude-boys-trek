// A small chart inside the coach's answer. The coach chose what to show; every number
// comes from the backend (coach/charts.py). Bars are HTML so their text stays crisp and
// wraps on narrow phones; only the balance line is SVG. Values are labelled sparingly,
// hover shows a mark's value, and a hidden table gives screen readers every figure.
import type { ReactNode } from "react";
import { formatDay, locales, type Lang, type Text } from "../lib/i18n";
import { basketName, categoryName } from "../lib/merchants";
import { formatMoney } from "../lib/money";
import type { ChartSpec } from "../lib/types";

interface Props {
  chart: ChartSpec;
  t: Text;
  lang: Lang;
}

type Row = { label: string; value: string };

const monthName = (month: string, lang: Lang) =>
  new Date(`${month}-01T12:00:00`).toLocaleDateString(locales[lang], { month: "short" });

const period = (start: string, end: string, lang: Lang) =>
  `${formatDay(start, lang)}–${formatDay(end, lang)}`;

const pct = (value: number, max: number) => `${max > 0 ? Math.max((value / max) * 100, value > 0 ? 1 : 0) : 0}%`;

function Frame({ title, note, source, legend, rows, t, children }:
  { title: string; note?: string; source?: string; legend?: ReactNode; rows: Row[]; t: Text; children: ReactNode }) {
  return (
    <figure className="chat-chart">
      <figcaption className="chat-chart-title">{title}</figcaption>
      {legend}
      <div aria-hidden="true">{children}</div>
      {note && <p className="chat-chart-note">{note}</p>}
      {source && <p className="chat-chart-note chat-chart-source">{source}</p>}
      <table className="visually-hidden">
        <caption>{t.chart.tableCaption}</caption>
        <tbody>{rows.map((r) => <tr key={r.label}><th scope="row">{r.label}</th><td>{r.value}</td></tr>)}</tbody>
      </table>
    </figure>
  );
}

export function ChatChart({ chart, t, lang }: Props) {
  const c = t.chart;

  if (chart.type === "categories") {
    const max = Math.max(...chart.items.map((i) => i.value), 0);
    const name = (cat: string) => (cat === "Other" ? c.other : categoryName(cat, lang));
    return (
      <Frame t={t} title={c.categories(period(chart.period.start_date, chart.period.end_date, lang))}
             note={c.total(formatMoney(chart.total))}
             rows={chart.items.map((i) => ({ label: name(i.category), value: formatMoney(i.value) }))}>
        <div className="hbars">
          {chart.items.map((i) => (
            <div key={i.category} className="hbar" title={`${name(i.category)}: ${formatMoney(i.value)}`}>
              <span className="hbar-label">{name(i.category)}</span>
              <span className="hbar-track"><span className="hbar-fill" style={{ inlineSize: pct(i.value, max) }} /></span>
              <span className="hbar-value money">{formatMoney(i.value)}</span>
            </div>
          ))}
        </div>
      </Frame>
    );
  }

  if (chart.type === "trend") {
    const { category, basket } = chart.subject;
    const what = category ? categoryName(category, lang) : basket ? basketName(basket, lang) : null;
    const max = Math.max(...chart.months.map((m) => m.value), 0);
    const peak = chart.months.reduce((a, m, i) => (m.value > chart.months[a].value ? i : a), 0);
    return (
      <Frame t={t} title={what ? c.trendOf(what) : c.trendAll}
             rows={chart.months.map((m) => ({
               label: `${monthName(m.month, lang)}${m.partial ? ` (${c.soFar})` : ""}`, value: formatMoney(m.value) }))}>
        <div className="columns" style={{ gridTemplateColumns: `repeat(${chart.months.length}, minmax(0, 1fr))` }}>
          {chart.months.map((m, i) => {
            const label = i === peak || i === chart.months.length - 1;  // the peak and the latest month
            return (
              <div key={m.month} className={`column${m.partial ? " is-partial" : ""}`}
                   title={`${monthName(m.month, lang)}: ${formatMoney(m.value)}${m.partial ? ` (${c.soFar})` : ""}`}>
                <span className="column-value money">{label ? formatMoney(Math.round(m.value)) : ""}</span>
                <span className="column-track"><span className="column-fill" style={{ blockSize: pct(m.value, max) }} /></span>
                <span className="column-month">{monthName(m.month, lang)}</span>
              </div>
            );
          })}
        </div>
        {chart.months.at(-1)?.partial && <p className="chat-chart-note">{monthName(chart.months.at(-1)!.month, lang)}: {c.soFar}</p>}
      </Frame>
    );
  }

  if (chart.type === "balance") {
    const values = chart.points.map((p) => p.value);
    const lo = Math.min(...values, 0), hi = Math.max(...values, 0);
    const span = hi - lo || 1;
    const W = 300, H = 110, PAD = 8;
    const x = (i: number) => PAD + (i * (W - 2 * PAD)) / Math.max(chart.points.length - 1, 1);
    const y = (v: number) => PAD + ((hi - v) / span) * (H - 2 * PAD);
    const line = chart.points.map((p, i) => `${x(i)},${y(p.value)}`).join(" ");
    const last = chart.points.at(-1);
    return (
      <Frame t={t} title={c.balance}
             rows={chart.points.map((p) => ({ label: monthName(p.month, lang), value: formatMoney(p.value) }))}>
        <div className="line-chart">
          <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" className="line-svg">
            <line x1={0} x2={W} y1={y(0)} y2={y(0)} className="line-zero" />
            <polygon points={`${x(0)},${y(0)} ${line} ${x(chart.points.length - 1)},${y(0)}`} className="line-area" />
            <polyline points={line} className="line-path" vectorEffect="non-scaling-stroke" />
          </svg>
          {last && <span className="line-end money" style={{ insetBlockStart: `${(y(last.value) / H) * 100}%` }}>{formatMoney(last.value)}</span>}
          {last && <span className="line-dot" style={{ insetBlockStart: `${(y(last.value) / H) * 100}%` }} />}
        </div>
        <div className="line-months"><span>{monthName(chart.points[0].month, lang)}</span><span>{last && monthName(last.month, lang)}</span></div>
      </Frame>
    );
  }

  if (chart.type === "budget") {
    return (
      <Frame t={t} title={c.budget}
             rows={chart.baskets.map((b) => ({ label: basketName(b.basket, lang), value: `${formatMoney(b.spent)} / ${formatMoney(b.reference)}` }))}>
        <div className="meters">
          {chart.baskets.map((b) => {
            const over = b.spent > b.reference;
            return (
              <div key={b.basket} className={`meter${over ? " is-over" : ""}`} title={`${formatMoney(b.spent)} / ${formatMoney(b.reference)}`}>
                <span className="meter-label">{basketName(b.basket, lang)}</span>
                <span className="meter-value money">{formatMoney(b.spent)} / {formatMoney(b.reference)}</span>
                <span className="meter-track"><span className="meter-fill" style={{ inlineSize: pct(Math.min(b.spent, b.reference), b.reference) }} /></span>
              </div>
            );
          })}
        </div>
      </Frame>
    );
  }

  if (chart.type === "peer_range") {
    // One category: a strip per group with the typical range (middle half) as a band,
    // the median as a tick and the customer as a green dot. One shared scale.
    const groups = [
      { key: "age", label: c.ageRow(chart.age_group), g: chart.age },
      { key: "everyone", label: c.everyoneRow, g: chart.everyone },
    ];
    const finland = { age: chart.finland?.age ?? null, everyone: chart.finland?.all ?? null } as Record<string, number | null>;
    const max = Math.max(chart.me, ...groups.flatMap(({ g }) => [g.typical_high, g.median]),
                         ...Object.values(finland).map((v) => v ?? 0)) * 1.08 || 1;
    const at = (v: number) => `${Math.min(v / max, 1) * 100}%`;
    const what = categoryName(chart.category, lang);
    return (
      <Frame t={t} title={c.peerRange(what)}
             note={c.rangeNote(period(chart.period.start_date, chart.period.end_date, lang))}
             source={chart.finland_source ? c.finlandSource(chart.finland_source.survey_year) : undefined}
             legend={
               <p className="chart-legend">
                 <span><i className="swatch swatch--dot" />{c.you}</span>
                 <span><i className="swatch swatch--tick" />{c.medianMark}</span>
                 <span><i className="swatch swatch--band" />{c.typicalRange}</span>
                 {chart.finland && <span><i className="swatch swatch--finland" />{c.finlandMark}</span>}
               </p>
             }
             rows={[
               { label: c.you, value: formatMoney(chart.me) },
               ...groups.flatMap(({ key, label, g }) => [
                 { label: `${label}: ${c.medianMark}`, value: formatMoney(g.median) },
                 { label: `${label}: ${c.typicalRange}`, value: `${formatMoney(g.typical_low)}–${formatMoney(g.typical_high)}` },
                 ...(finland[key] !== null ? [{ label: `${label}: ${c.finlandMark}`, value: formatMoney(finland[key]!) }] : []),
               ]),
             ]}>
        <div className="ranges">
          {groups.map(({ key, label, g }) => (
            <div key={key} className="range">
              <span className="range-label">{label}</span>
              <span className="range-track"
                    title={`${c.typicalRange}: ${formatMoney(g.typical_low)}–${formatMoney(g.typical_high)} · ${c.medianMark}: ${formatMoney(g.median)}`}>
                <span className="range-band" style={{ insetInlineStart: at(g.typical_low), inlineSize: `calc(${at(g.typical_high)} - ${at(g.typical_low)})` }} />
                <span className="range-median" style={{ insetInlineStart: at(g.median) }} />
                {finland[key] !== null && (
                  <span className="mark-finland" style={{ insetInlineStart: at(finland[key]!) }}
                        title={`${c.finlandMark}: ${formatMoney(finland[key]!)}`} />
                )}
                <span className="range-me" style={{ insetInlineStart: at(chart.me) }} title={`${c.you}: ${formatMoney(chart.me)}`} />
              </span>
              <span className="range-figures">
                <span className="money">{c.you} {formatMoney(Math.round(chart.me))}</span>
                <span className="money">{c.medianMark} {formatMoney(Math.round(g.median))}</span>
              </span>
            </div>
          ))}
        </div>
      </Frame>
    );
  }

  // peers: you (green) against the age group's median (grey); two series, so a legend.
  const max = Math.max(...chart.items.flatMap((i) => [i.me, i.peer_median, i.finland ?? 0]), 0);
  return (
    <Frame t={t} title={c.peers(chart.age_group)} note={c.billsLeftOut}
           source={chart.finland_source ? c.finlandSource(chart.finland_source.survey_year) : undefined}
           legend={
             <p className="chart-legend">
               <span><i className="swatch swatch--you" />{c.you}</span>
               <span><i className="swatch swatch--peer" />{c.median(chart.age_group)}</span>
               {chart.finland_source && <span><i className="swatch swatch--finland" />{c.finlandMark}</span>}
             </p>
           }
           rows={chart.items.map((i) => ({ label: categoryName(i.category, lang),
                                          value: `${c.you} ${formatMoney(i.me)} · ${c.median(chart.age_group)} ${formatMoney(i.peer_median)}`
                                            + (i.finland !== null ? ` · ${c.finlandMark} ${formatMoney(i.finland)}` : "") }))}>
      <div className="pairs">
        {chart.items.map((i) => (
          <div key={i.category} className="pair">
            <span className="pair-label">{categoryName(i.category, lang)}</span>
            <span className="hbar-track" title={`${c.you}: ${formatMoney(i.me)}`}>
              <span className="hbar-fill" style={{ inlineSize: pct(i.me, max) }} />
            </span>
            <span className="hbar-value money">{formatMoney(Math.round(i.me))}</span>
            <span className="hbar-track" title={`${c.median(chart.age_group)}: ${formatMoney(i.peer_median)}`}>
              <span className="hbar-fill hbar-fill--peer" style={{ inlineSize: pct(i.peer_median, max) }} />
              {i.finland !== null && (
                <span className="mark-finland" style={{ insetInlineStart: pct(i.finland, max) }}
                      title={`${c.finlandMark}: ${formatMoney(i.finland)}`} />
              )}
            </span>
            <span className="hbar-value hbar-value--peer money">{formatMoney(Math.round(i.peer_median))}</span>
          </div>
        ))}
      </div>
    </Frame>
  );
}
