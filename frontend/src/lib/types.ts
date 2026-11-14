// Mirrors the backend's shapes so fixtures can be swapped for API calls later.
// Source of truth: coach/spending_baskets.py (summarize_baskets) and coach/budget.py.

export type BasketKey = "regular_essentials" | "unexpected_necessities" | "everyday_spending";

export interface Basket {
  label: string;
  label_fi: string;
  total_eur: number;
  share_pct: number;
  transaction_count: number;
}

export interface BasketSummary {
  baskets: Record<BasketKey, Basket>;
  total_spending_eur: number;
}

export interface SafeToSpend {
  amount_eur: number;
  days_until_payday: number;
  period_label: string;
  explanation: string;
}

export interface ChatMessage {
  id: string;
  author: "user" | "assistant";
  text: string;
}
