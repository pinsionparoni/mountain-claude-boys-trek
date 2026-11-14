import { uiConfig } from "./config/ui.config";
import { BasketOverview } from "./components/BasketOverview";
import { SafeToSpendCard } from "./components/SafeToSpendCard";
import { Chat } from "./components/Chat";
import {
  demoBaskets,
  demoConversation,
  demoReply,
  demoSafeToSpend,
  demoSuggestions,
} from "./fixtures/demo";

export default function App() {
  return (
    <div className="sp-coach app" data-card-style={uiConfig.cardStyle}>
      <header className="app-header">
        <span className="app-name">Financial Coach</span>
        <span className="demo-badge">Junction prototype · synthetic data</span>
      </header>

      <main className="app-main">
        {uiConfig.showWelcomePanel && (
          <section className="welcome">
            <h1 className="page-title">Talk with your money</h1>
            <p className="lead">Plain answers about your spending, computed from your own transactions.</p>
          </section>
        )}

        <div className="layout">
          <div className="layout-side">
            <SafeToSpendCard data={demoSafeToSpend} />
            {uiConfig.showBasketOverview && (
              <BasketOverview
                summary={demoBaskets}
                periodLabel="November, 1–14 Nov"
                showBars={uiConfig.showSpendingChart && uiConfig.chartStyle === "bars"}
              />
            )}
          </div>
          <Chat
            initial={demoConversation}
            suggestions={demoSuggestions}
            showSuggestions={uiConfig.showSuggestionChips}
            reply={() => demoReply}
          />
        </div>
      </main>
    </div>
  );
}
