import { useEffect, useState } from "react";
import { uiConfig } from "./config/ui.config";
import { BasketOverview } from "./components/BasketOverview";
import { BottomNav, type Tab } from "./components/BottomNav";
import { Chat } from "./components/Chat";
import { EtukorttiPage } from "./components/EtukorttiPage";
import { BackIcon } from "./components/Icons";
import { LoginScreen } from "./components/LoginScreen";
import { MessageCentre } from "./components/MessageCentre";
import { MinaPage } from "./components/MinaPage";
import { PankkiPage } from "./components/PankkiPage";
import { SafeToSpendCard } from "./components/SafeToSpendCard";
import { SmobiiliHome } from "./components/SmobiiliHome";
import { demoCustomers } from "./fixtures/demo";
import { fetchBudget, fetchSummary } from "./lib/api";
import { formatDay, text, type Lang } from "./lib/i18n";
import type { BasketSummary, Budget } from "./lib/types";

const LANG_KEY = "coach-lang";

function savedLang(): Lang {
  const fromUrl = new URLSearchParams(window.location.search).get("lang");
  if (fromUrl === "fi" || fromUrl === "en") return fromUrl;  // e.g. a shared demo link ?lang=fi
  try {
    return localStorage.getItem(LANG_KEY) === "en" ? "en" : "fi";
  } catch {
    return "fi";
  }
}

const periodLabel = ({ start_date, end_date }: BasketSummary["period"], lang: Lang) =>
  `${formatDay(start_date, lang, { month: "long" })}, ${formatDay(start_date, lang, { day: "numeric" })}–${formatDay(end_date, lang)}`;

export default function App() {
  const [lang, setLang] = useState<Lang>(savedLang);
  const [customerId, setCustomerId] = useState(demoCustomers[0].id);
  const [loggedIn, setLoggedIn] = useState(false);
  const [tab, setTab] = useState<Tab>("home");
  // Message centre and coach open over the tabs, like full screens in S-mobiili.
  const [overlay, setOverlay] = useState<null | "messages" | "coach">(null);
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

  const login = () => { setTab("home"); setOverlay(null); setLoggedIn(true); };
  const logout = () => { setOverlay(null); setLoggedIn(false); };
  const openMessages = () => setOverlay("messages");

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
      <div className="phone">
        <div className="phone-screen">
          {!loggedIn ? (
            <LoginScreen t={t} lang={lang} customerId={customerId}
                         onLang={setLang} onCustomer={pickCustomer} onLogin={login} />
          ) : (
            <>
              {error && <p className="notice notice--error" role="alert">{t.loadError}</p>}

              <div className="sm-screen" hidden={overlay !== null}>
                <main className="sm-scroll">
                  {tab === "home" && <SmobiiliHome t={t} lang={lang} budget={budget}
                                                   onOpenMessages={openMessages} onLogout={logout} />}
                  {tab === "card" && <EtukorttiPage t={t} />}
                  {tab === "bank" && <PankkiPage t={t} lang={lang} budget={budget} summary={summary}
                                                 onOpenMessages={openMessages} />}
                  {tab === "me" && <MinaPage t={t} customerId={customerId} onOpenMessages={openMessages} />}
                </main>
                <BottomNav t={t} active={tab} onSelect={setTab} />
              </div>

              <div className="sm-screen" hidden={overlay !== "messages"}>
                <MessageCentre t={t} onBack={() => setOverlay(null)} onOpenCoach={() => setOverlay("coach")} />
              </div>

              {/* Kept mounted while hidden so the conversation survives a trip back. */}
              <div className="sm-screen" hidden={overlay !== "coach"}>
                <header className="sm-header">
                  <button type="button" className="sm-icon-button" aria-label={t.home.back}
                          onClick={() => setOverlay("messages")}>
                    <BackIcon />
                  </button>
                  <h1 className="sm-header-title">{t.appName}</h1>
                  <span />
                </header>
                <Chat key={customerId} customerId={customerId} t={t} showSuggestions={uiConfig.showSuggestionChips}>
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
                </Chat>
              </div>
            </>
          )}
        </div>
      </div>
      <p className="phone-caption">{t.demoBadge}</p>
    </div>
  );
}
