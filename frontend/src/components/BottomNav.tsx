// S-mobiili's tab bar. Switches between the home screen and the mock tab pages.
import type { Text } from "../lib/i18n";
import { HomeIcon, PersonIcon, WalletIcon } from "./Icons";
import { SLogo } from "./SLogo";

export type Tab = "home" | "card" | "bank" | "me";

export function BottomNav({ t, active, onSelect }: { t: Text; active: Tab; onSelect: (tab: Tab) => void }) {
  const nav = t.home.nav;
  const tabs: { id: Tab; label: string; icon: React.ReactNode }[] = [
    { id: "home", label: nav.home, icon: <HomeIcon /> },
    { id: "card", label: nav.card, icon: <SLogo className="sm-tab-logo" /> },
    { id: "bank", label: nav.bank, icon: <WalletIcon /> },
    { id: "me", label: nav.me, icon: <PersonIcon /> },
  ];
  return (
    <nav className="sm-tabbar" aria-label="S-mobiili">
      {tabs.map((tab) => (
        <button key={tab.id} type="button" className={`sm-tab${active === tab.id ? " sm-tab--active" : ""}`}
                aria-current={active === tab.id ? "page" : undefined} onClick={() => onSelect(tab.id)}>
          {tab.icon}
          {tab.label}
        </button>
      ))}
    </nav>
  );
}
