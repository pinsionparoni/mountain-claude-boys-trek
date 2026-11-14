// Start screen: S-mobiili's logo animation (cut from a screen recording, used with the
// team's permission), then the demo log-in where you pick the language and customer.
import { useState } from "react";
import { demoCustomers } from "../fixtures/demo";
import type { Lang, Text } from "../lib/i18n";
import animationUrl from "../assets/smobiili/s-logo-animation.mp4";
import { SLogo } from "./SLogo";

interface Props {
  t: Text;
  lang: Lang;
  customerId: string;
  onLang: (lang: Lang) => void;
  onCustomer: (id: string) => void;
  onLogin: () => void;
}

const reducedMotion = () => window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;

export function LoginScreen({ t, lang, customerId, onLang, onCustomer, onLogin }: Props) {
  const [ready, setReady] = useState(reducedMotion);

  return (
    <div className="sm-login">
      <div className="sm-login-logo">
        {ready
          ? <SLogo className="sm-login-static" label="S-mobiili" />
          : <video src={animationUrl} autoPlay muted playsInline onEnded={() => setReady(true)}
                   onError={() => setReady(true)} aria-label="S-mobiili" />}
      </div>

      <form className={`sm-login-form${ready ? " is-visible" : ""}`} aria-hidden={!ready}
            onSubmit={(e) => { e.preventDefault(); onLogin(); }}>
        <h1 className="sm-login-title">{t.home.loginTitle}</h1>
        <p className="sm-login-lead">{t.home.loginLead}</p>

        <div className="lang-switch sm-login-lang" role="group" aria-label={t.language}>
          {(["fi", "en"] as const).map((l) => (
            <button key={l} type="button" aria-pressed={lang === l} onClick={() => onLang(l)} tabIndex={ready ? 0 : -1}>
              {l === "fi" ? "Suomi" : "English"}
            </button>
          ))}
        </div>

        <label className="sm-login-field">
          <span>{t.demoCustomer}</span>
          <select value={customerId} onChange={(e) => onCustomer(e.target.value)} tabIndex={ready ? 0 : -1}>
            {demoCustomers.map((c) => <option key={c.id} value={c.id}>{c[lang]}</option>)}
          </select>
        </label>

        <button type="submit" className="sm-login-button" tabIndex={ready ? 0 : -1}>{t.home.loginButton}</button>
        <p className="sm-login-badge">{t.demoBadge}</p>
      </form>
    </div>
  );
}
