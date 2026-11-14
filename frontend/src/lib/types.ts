// Mirrors the backend's shapes (coach/api.py). Source of truth:
// coach/spending_baskets.py (summarize_baskets) and coach/budget.py (safe_to_spend).

export type BasketKey = "regular_essentials" | "unexpected_necessities" | "everyday_spending";

export interface Basket {
  label: string;
  label_fi: string;
  total_eur: number;
  share_pct: number;
  transaction_count: number;
  categories: { category: string; total_eur: number }[];  // largest first
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

/** One card purchase from GET /customers/{id}/receipts (coach/database/queries.py recent_purchases). */
export interface Receipt {
  timestamp: string;       // ISO, local time of the purchase
  category: string;        // the data's category, e.g. "Groceries"
  merchant_type: string;   // spending_baskets.MERCHANT_TYPES label, or "other"
  basket: BasketKey | "unclassified";
  amount_eur: number;      // money out, positive
  unusual: boolean;        // a large one-off purchase
}

export interface Receipts {
  today: string;
  receipts: Receipt[];
}

/** A chart the coach chose to show (coach/charts.py); every number computed by the backend. */
export type ChartSpec =
  | { type: "categories"; period: { start_date: string; end_date: string };
      items: { category: string; value: number }[]; total: number }
  | { type: "trend"; subject: { category: string | null; basket: BasketKey | null };
      months: { month: string; value: number; partial: boolean }[]; today: string }
  | { type: "balance"; points: { month: string; value: number }[]; today: string }
  | { type: "budget"; today: string; baskets: { basket: BasketKey; spent: number; reference: number }[] }
  | { type: "peers"; age_group: string; period: { start_date: string; end_date: string };
      items: { category: string; me: number; peer_median: number; finland: number | null }[]; left_out: string[];
      finland_source: FinlandSource | null }
  | { type: "peer_range"; category: string; age_group: string; period: { start_date: string; end_date: string };
      me: number; age: PeerGroup; everyone: PeerGroup;
      finland: { age: number; all: number } | null; finland_source: FinlandSource | null };

/** Statistics Finland's open benchmark (coach/statfin.py). */
export interface FinlandSource {
  publisher: string;
  licence: string;
  survey_year: number;
  price_level: string;
}

export interface PeerGroup {
  median: number;
  typical_low: number;    // 25th percentile
  typical_high: number;   // 75th percentile
  spends_more_than_pct: number;
  spends_less_than_pct: number;
}

/** The figures behind a home-screen tip (coach/tips.py); which ones depends on the kind. */
export interface TipFacts {
  safe_this_week: number;
  next_payday: string;
  days_to_payday: number;
  over: number;
  everyday_budget: number;
  category: "Restaurants" | "Entertainment";
  age_group: string;
  my_monthly: number;
  finland_monthly: number;
  difference_pct: number;
  cut_pct: number;
  yearly_saving: number;
  remaining: number;
  per_week: number;
  days_left: number;
  savings_per_month: number;
}

/** GET /customers/{id}/tip: one money-coaching tip for the home screen. */
export interface Tip {
  today: string;
  kind: "cash_tight" | "over_budget" | "above_finland" | "nearly_used" | "on_track";
  facts: TipFacts;
  chart: ChartSpec;
}

export interface ChatMessage {
  id: string;
  author: "user" | "assistant";
  text: string;
  charts?: ChartSpec[];
  /** Where the chart shows: "above" the text when the customer asked for a chart,
   *  "below" once they tap "Show as a chart"; unset = behind the button. */
  chartOpen?: "above" | "below";
  /** True while the answer is still arriving. */
  streaming?: boolean;
}
