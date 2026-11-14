import { useEffect, useState } from "react";
import { uiConfig } from "./config/ui.config";
import { BasketOverview } from "./components/BasketOverview";
import { SafeToSpendCard } from "./components/SafeToSpendCard";
import { Chat } from "./components/Chat";
import { demoCustomers } from "./fixtures/demo";
import { fetchBudget, fetchSummary } from "./lib/api";
import { formatDay, text, type Lang } from "./lib/i18n";
import type { BasketSummary, Budget } from "./lib/types";

const LANG_KEY = "coach-lang";

function savedLang(): Lang {
  const fromUrl = new URLSearchParams(window.location.search).get("lang");
  if (fromUrl === "fi" || fromUrl === "en") return fromUrl;  // e.g. a shared demo link ?lang=fi
  try {
    return localStorage.getItem(LANG_KEY) === "fi" ? "fi" : "en";
  } catch {
    return "en";
  }
}

const periodLabel = ({ start_date, end_date }: BasketSummary["period"], lang: Lang) =>
  `${formatDay(start_date, lang, { month: "long" })}, ${formatDay(start_date, lang, { day: "numeric" })}–${formatDay(end_date, lang)}`;

export default function App() {
  const [lang, setLang] = useState<Lang>(savedLang);
  const [customerId, setCustomerId] = useState(demoCustomers[0].id);
  const [summary, setSummary] = useState<BasketSummary | null>(null);
  const [budget, setBudget] = useState<Budget | null>(null);
  const [error, setError] = useState(false);
  const t = text[lang];

  useEffect(() => {
    document.documentElement.lang = lang;
    try { localStorage.setItem(LANG_KEY, lang); } catch { /* private mode: not remembered */ }
  }, [lang]);

  const pickCustomer = (id: string) => {
    setCustomerId(id);
    setSummary(null);
    setBudget(null);
    setError(false);
  };

  useEffect(() => {
    let current = true;
    Promise.all([fetchSummary(customerId), fetchBudget(customerId)])
      .then(([s, b]) => {
        if (current) { setSummary(s); setBudget(b); }
      })
      .catch(() => current && setError(true));
    return () => { current = false; };
  }, [customerId]);

  return (
    <div className="sp-coach app" data-card-style={uiConfig.cardStyle}>
      <header className="app-header">
        <span className="app-name">{t.appName}</span>
        <div className="lang-switch" role="group" aria-label={t.language}>
          {(["en", "fi"] as const).map((l) => (
            <button key={l} type="button" aria-pressed={lang === l} onClick={() => setLang(l)}>
              {l.toUpperCase()}
            </button>
          ))}
        </div>
        <label className="customer-picker">
          <span className="visually-hidden">{t.demoCustomer}</span>
          <select value={customerId} onChange={(e) => pickCustomer(e.target.value)}>
            {demoCustomers.map((c) => <option key={c.id} value={c.id}>{c[lang]}</option>)}
          </select>
        </label>
        <span className="demo-badge">{t.demoBadge}</span>
      </header>

      <main className="app-main">
        {uiConfig.showWelcomePanel && (
          <section className="welcome">
            <h1 className="page-title">{t.title}</h1>
            <p className="lead">{t.lead}</p>
          </section>
        )}

        <div className="layout">
          <div className="layout-side">
            {error && <p className="notice notice--error" role="alert">{t.loadError}</p>}
            {!error && !budget && <p className="panel muted">{t.loading}</p>}
            {budget && <SafeToSpendCard budget={budget} t={t} lang={lang} />}
            {uiConfig.showBasketOverview && summary && (
              <BasketOverview
                summary={summary}
                periodLabel={periodLabel(summary.period, lang)}
                showBars={uiConfig.showSpendingChart && uiConfig.chartStyle === "bars"}
                t={t}
                lang={lang}
              />
            )}
          </div>
          <Chat key={customerId} customerId={customerId} t={t} showSuggestions={uiConfig.showSuggestionChips} />
        </div>
      </main>
    </div>
  );
}
