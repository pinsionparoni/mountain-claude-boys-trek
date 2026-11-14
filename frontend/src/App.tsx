import { useEffect, useState } from "react";
import { uiConfig } from "./config/ui.config";
import { BasketCard } from "./components/BasketCard";
import { BottomNav, type Tab } from "./components/BottomNav";
import { CardCarousel } from "./components/CardCarousel";
import { Chat } from "./components/Chat";
import { EtukorttiPage } from "./components/EtukorttiPage";
import { BackIcon } from "./components/Icons";
import { LoginScreen } from "./components/LoginScreen";
import { MessageCentre } from "./components/MessageCentre";
import { MinaPage } from "./components/MinaPage";
import { PankkiPage } from "./components/PankkiPage";
import { ReceiptsPage } from "./components/ReceiptsPage";
import { SafeToSpendCard } from "./components/SafeToSpendCard";
import { SmobiiliHome } from "./components/SmobiiliHome";
import { demoCustomers } from "./fixtures/demo";
import { PasscodeError, checkPasscode, fetchBudget, fetchHealth, fetchReceipts, fetchSummary, fetchTip, rememberPasscode, withRetry } from "./lib/api";
import { formatDay, text, type Lang } from "./lib/i18n";
import type { BasketKey, BasketSummary, Budget, Receipts, Tip } from "./lib/types";

const BASKETS: BasketKey[] = ["regular_essentials", "unexpected_necessities", "everyday_spending"];

/** What a basket's spending this month is measured against, from the monthly budget. */
const basketReference = (key: BasketKey, budget: Budget) => ({
  regular_essentials: budget.monthly_budget.regular_essentials,
  unexpected_necessities: budget.monthly_budget.unexpected_reserve,
  everyday_spending: budget.this_month.everyday_budget,
})[key];

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
  const [overlay, setOverlay] = useState<null | "messages" | "coach" | "receipts">(null);
  const [summary, setSummary] = useState<BasketSummary | null>(null);
  const [budget, setBudget] = useState<Budget | null>(null);
  const [receipts, setReceipts] = useState<Receipts | null>(null);
  const [tip, setTip] = useState<Tip | null>(null);
  // A question for the coach from the home screen's tip ("Kysy lisää").
  const [pendingQuestion, setPendingQuestion] = useState<string | null>(null);
  // Where the coach's back arrow leads: the message centre, or home when opened from the tip.
  const [coachBack, setCoachBack] = useState<null | "messages">("messages");
  const [error, setError] = useState(false);
  const [reloads, setReloads] = useState(0);   // "Try again" after a failed load
  // The hosted demo needs a passcode before any data loads (null: still asking the backend).
  const [passcodeRequired, setPasscodeRequired] = useState<boolean | null>(null);
  const [passcodeError, setPasscodeError] = useState(false);
  const t = text[lang];

  useEffect(() => {
    fetchHealth()
      .then((h) => setPasscodeRequired(h.passcode_required))
      .catch(() => setPasscodeRequired(false));  // the data calls will show the error
  }, []);

  useEffect(() => {
    document.documentElement.lang = lang;
    try { localStorage.setItem(LANG_KEY, lang); } catch { /* private mode: not remembered */ }
  }, [lang]);

  const pickCustomer = (id: string) => {
    setCustomerId(id);
    setSummary(null);
    setBudget(null);
    setReceipts(null);
    setTip(null);
    setPendingQuestion(null);
    setError(false);
  };

  const login = async (passcode: string) => {
    if (passcodeRequired) {
      const ok = await checkPasscode(passcode).catch(() => false);
      if (!ok) { setPasscodeError(true); return; }
      rememberPasscode(passcode);
    }
    setPasscodeError(false);
    setTab("home"); setOverlay(null); setLoggedIn(true);
  };
  const logout = () => { setOverlay(null); setLoggedIn(false); };
  const openMessages = () => setOverlay("messages");

  // Without a passcode the figures load straight away, as before; with one, after log-in.
  const canLoad = passcodeRequired === false || loggedIn;
  useEffect(() => {
    if (!canLoad) return;
    let current = true;
    // Retried a few times, so a short network drop doesn't leave the cards empty.
    withRetry(() => Promise.all([fetchSummary(customerId), fetchBudget(customerId)]))
      .then(([s, b]) => {
        if (current) { setSummary(s); setBudget(b); setError(false); }
      })
      .catch((e) => {
        if (!current) return;
        if (e instanceof PasscodeError) { setPasscodeError(true); setLoggedIn(false); }
        else setError(true);
      });
    // Receipts and the tip load on their own, so a problem there never hides the cards.
    withRetry(() => fetchReceipts(customerId))
      .then((r) => current && setReceipts(r))
      .catch(() => current && setReceipts({ today: "", receipts: [] }));
    withRetry(() => fetchTip(customerId))
      .then((tp) => current && setTip(tp))
      .catch(() => { /* no tip then: the card keeps its loading text */ });
    return () => { current = false; };
  }, [customerId, canLoad, reloads]);

  return (
    <div className="sp-coach app" data-card-style={uiConfig.cardStyle}>
      <div className="phone">
        <div className="phone-screen">
          {!loggedIn ? (
            <LoginScreen t={t} lang={lang} customerId={customerId}
                         onLang={setLang} onCustomer={pickCustomer}
                         passcodeRequired={passcodeRequired === true} passcodeError={passcodeError}
                         onLogin={login} />
          ) : (
            <>
              {error && (
                <p className="notice notice--error load-error" role="alert">
                  <span>{t.loadError}</span>
                  <button type="button" className="sm-link" onClick={() => { setError(false); setReloads((n) => n + 1); }}>
                    {t.tryAgain}
                  </button>
                </p>
              )}

              <div className="sm-screen" hidden={overlay !== null}>
                <main className="sm-scroll">
                  {tab === "home" && <SmobiiliHome t={t} lang={lang} budget={budget} summary={summary}
                                                   latestReceipt={receipts?.receipts[0] ?? null}
                                                   tip={tip}
                                                   onAsk={(q) => { setPendingQuestion(q); setCoachBack(null); setOverlay("coach"); }}
                                                   onOpenReceipts={() => setOverlay("receipts")}
                                                   onOpenMessages={openMessages} onLogout={logout} />}
                  {tab === "card" && <EtukorttiPage t={t} />}
                  {tab === "bank" && <PankkiPage t={t} lang={lang} budget={budget} summary={summary}
                                                 onOpenMessages={openMessages} />}
                  {tab === "me" && <MinaPage t={t} customerId={customerId} onOpenMessages={openMessages} />}
                </main>
                <BottomNav t={t} active={tab} onSelect={setTab} />
              </div>

              <div className="sm-screen" hidden={overlay !== "receipts"}>
                <ReceiptsPage t={t} lang={lang} receipts={receipts?.receipts ?? null} today={receipts?.today || null}
                              summary={summary} onBack={() => setOverlay(null)} />
              </div>

              <div className="sm-screen" hidden={overlay !== "messages"}>
                <MessageCentre t={t} onBack={() => setOverlay(null)} onOpenCoach={() => { setCoachBack("messages"); setOverlay("coach"); }} />
              </div>

              {/* Kept mounted while hidden so the conversation survives a trip back. */}
              <div className="sm-screen" hidden={overlay !== "coach"}>
                <header className="sm-header">
                  <button type="button" className="sm-icon-button" aria-label={t.home.back}
                          onClick={() => setOverlay(coachBack)}>
                    <BackIcon />
                  </button>
                  <h1 className="sm-header-title">{t.appName}</h1>
                  <span />
                </header>
                <Chat key={customerId} customerId={customerId} t={t} lang={lang}
                      pendingQuestion={pendingQuestion} onPendingSent={() => setPendingQuestion(null)}
                      showSuggestions={uiConfig.showSuggestionChips}>
                  {!error && !budget && <p className="panel muted">{t.loading}</p>}
                  <CardCarousel t={t}>
                    {budget && <SafeToSpendCard budget={budget} t={t} lang={lang} />}
                    {uiConfig.showBasketOverview && summary && budget && BASKETS.map((key) => (
                      <BasketCard key={key} basketKey={key} basket={summary.baskets[key]}
                                  reference={basketReference(key, budget)}
                                  periodLabel={periodLabel(summary.period, lang)}
                                  showBar={uiConfig.showSpendingChart && uiConfig.chartStyle === "bars"}
                                  t={t} lang={lang} />
                    ))}
                  </CardCarousel>
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
