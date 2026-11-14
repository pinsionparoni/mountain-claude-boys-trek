/**
 * Editable presentation switches for OPTIONAL content.
 * Copy to frontend/src/config/ui.config.ts.
 * A developer must wire these flags to the corresponding React sections.
 * No effect on chat/API/data logic; no critical controls may depend on them.
 */
export const uiConfig = {
  showWelcomePanel: true,
  showBasketOverview: true,
  showSpendingChart: true,
  showSuggestionChips: true,
  cardStyle: "outlined",
  chartStyle: "bars",
} as const satisfies {
  showWelcomePanel: boolean;
  showBasketOverview: boolean;
  showSpendingChart: boolean;
  showSuggestionChips: boolean;
  cardStyle: "outlined" | "flat";
  chartStyle: "bars" | "none";
};
