// Mirrors the backend's shapes (coach/api.py). Source of truth:
// coach/spending_baskets.py (summarize_baskets) and coach/budget.py (safe_to_spend).

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
  period: { start_date: string; end_date: string };
  today: string;
}

export interface Budget {
  today: string;
  monthly_budget: {
    monthly_income: number;
    regular_essentials: number;
    unexpected_reserve: number;
    savings: number;
    everyday_budget: number;
    shortfall: number;
  };
  this_month: {
    everyday_budget: number;
    everyday_spent: number;
    remaining: number;
    over_budget: number;
    days_left_in_month: number;
    per_week: number;
  };
  cash_check: {
    current_balance: number;
    next_payday: string;
    days_to_payday: number;
    rent_due_before_payday: number;
    per_week: number;
    enough_cash: boolean;
  } | null;
  safe_to_spend_this_week: number;
  limited_by: "budget" | "cash";
}

export interface ChatMessage {
  id: string;
  author: "user" | "assistant";
  text: string;
}
