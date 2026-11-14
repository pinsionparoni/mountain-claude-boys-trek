// Illustrative demo numbers, not results from the dataset.
import type { BasketSummary, ChatMessage, SafeToSpend } from "../lib/types";

export const demoBaskets: BasketSummary = {
  total_spending_eur: 1842.6,
  baskets: {
    regular_essentials: {
      label: "🏠 Regular essentials",
      label_fi: "🏠 Välttämättömät menot",
      total_eur: 1124.3,
      share_pct: 61.0,
      transaction_count: 23,
    },
    unexpected_necessities: {
      label: "🔧 Unexpected necessities",
      label_fi: "🔧 Yllättävät menot",
      total_eur: 289.0,
      share_pct: 15.7,
      transaction_count: 2,
    },
    everyday_spending: {
      label: "☕ Everyday spending",
      label_fi: "☕ Arjen kulutus",
      total_eur: 429.3,
      share_pct: 23.3,
      transaction_count: 31,
    },
  },
};

export const demoSafeToSpend: SafeToSpend = {
  amount_eur: 312.4,
  days_until_payday: 9,
  period_label: "Until payday, 23 Nov",
  explanation: "After your rent and usual bills, with a small buffer kept aside.",
};

export const demoSuggestions = [
  "What is safe for me to spend this week?",
  "How much did I spend on taxis last month?",
  "What if I cut dining out by 20%?",
];

export const demoConversation: ChatMessage[] = [
  {
    id: "m1",
    author: "assistant",
    text: "Hi! I can answer questions about your own spending. Ask me anything, or pick a suggestion below.",
  },
];

export const demoReply =
  "This is a mockup reply. Once the backend is connected, the coach answers from your transactions.";
