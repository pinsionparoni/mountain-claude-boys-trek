// All UI text in English and Finnish. Numbers and basket names come from the backend;
// the coach itself answers in the language the question is written in.

export type Lang = "en" | "fi";

export const locales: Record<Lang, string> = { en: "en-GB", fi: "fi-FI" };

export const text = {
  en: {
    appName: "Financial Coach",
    demoBadge: "Junction prototype · synthetic data",
    demoCustomer: "Demo customer",
    language: "Language",
    title: "Talk with your money",
    lead: "Plain answers about your spending, computed from your own transactions.",
    loading: "Loading your figures…",
    loadError: "Couldn't load your figures. Is the backend running?",
    stsTitle: "Safe to spend this week",
    overBudget: (over: string) => `You're ${over} over this month's everyday budget.`,
    left: (left: string, budget: string) => `${left} left of your ${budget} everyday budget this month.`,
    cashLimited: (perWeek: string, payday: string) =>
      `Your budget would allow ${perWeek} this week, but your account also needs to cover rent and essentials until payday on ${payday}.`,
    enoughCash: (payday: string) => `Next payday ${payday} · enough in your account until then.`,
    estimate: (today: string) => `Estimate from your own transactions and balance · today is ${today}.`,
    basketsTitle: "Your spending baskets",
    inTotal: (total: string) => `${total} in total`,
    purchases: (n: number) => `${n} purchases`,
    chatTitle: "Ask your coach",
    conversation: "Conversation",
    you: "You:",
    coach: "Coach:",
    suggested: "Suggested questions",
    composerLabel: "Message the financial coach",
    placeholder: "Ask about your spending…",
    send: "Send",
    thinking: "Thinking…",
    checking: "Checking…",
    unreachable: "Sorry, I couldn't reach the coach. Is the backend running?",
    unavailable: (status: number) => `The coach is unavailable (${status}).`,
    greeting: "Hi! I can answer questions about your own spending. Ask me anything, or pick a suggestion below.",
    suggestions: [
      "What can I safely spend this week?",
      "Where did my money go last month?",
      "What kind of spender am I?",
      "How much did I spend on taxis last month?",
    ],
    tools: {
      get_safe_to_spend: "Working out your budget…",
      get_basket_summary: "Sorting your spending into baskets…",
      get_spending_by_category: "Checking your spending…",
      get_monthly_balance_trend: "Looking at your balance…",
      get_transactions: "Finding your transactions…",
      calculate_safe_to_save: "Calculating what you could save…",
      calculate_what_if: "Calculating the what-if…",
    } as Record<string, string>,
  },
  fi: {
    appName: "Talousvalmentaja",
    demoBadge: "Junction-prototyyppi · synteettinen data",
    demoCustomer: "Demoasiakas",
    language: "Kieli",
    title: "Juttele rahojesi kanssa",
    lead: "Selkeät vastaukset kulutuksestasi, laskettuna omista tilitapahtumistasi.",
    loading: "Haetaan lukujasi…",
    loadError: "Lukujen haku epäonnistui. Onko taustapalvelu käynnissä?",
    stsTitle: "Turvallisesti käytettävissä tällä viikolla",
    overBudget: (over: string) => `Olet ${over} yli tämän kuun arjen kulutuksen budjetin.`,
    left: (left: string, budget: string) => `${left} jäljellä tämän kuun ${budget} arjen kulutuksen budjetista.`,
    cashLimited: (perWeek: string, payday: string) =>
      `Budjettisi sallisi ${perWeek} tällä viikolla, mutta tililläsi on katettava myös vuokra ja välttämättömät menot palkkapäivään ${payday} asti.`,
    enoughCash: (payday: string) => `Seuraava palkkapäivä ${payday} · tililläsi on siihen asti riittävästi rahaa.`,
    // Finnish dates already end with a dot ("10.9."), so no full stop after it.
    estimate: (today: string) => `Arvio omista tilitapahtumistasi ja saldostasi · tänään on ${today}`,
    basketsTitle: "Kulutuskorisi",
    inTotal: (total: string) => `yhteensä ${total}`,
    purchases: (n: number) => `${n} ostoa`,
    chatTitle: "Kysy valmentajalta",
    conversation: "Keskustelu",
    you: "Sinä:",
    coach: "Valmentaja:",
    suggested: "Ehdotettuja kysymyksiä",
    composerLabel: "Viesti talousvalmentajalle",
    placeholder: "Kysy kulutuksestasi…",
    send: "Lähetä",
    thinking: "Mietitään…",
    checking: "Tarkistetaan…",
    unreachable: "Valmentajaan ei saatu yhteyttä. Onko taustapalvelu käynnissä?",
    unavailable: (status: number) => `Valmentaja ei ole käytettävissä (${status}).`,
    greeting: "Hei! Vastaan kysymyksiin omasta kulutuksestasi. Kysy mitä vain tai valitse ehdotus alta.",
    suggestions: [
      "Paljonko voin käyttää rahaa tällä viikolla?",
      "Mihin rahani menivät viime kuussa?",
      "Millainen kuluttaja olen?",
      "Paljonko käytin takseihin viime kuussa?",
    ],
    tools: {
      get_safe_to_spend: "Lasketaan budjettiasi…",
      get_basket_summary: "Lajitellaan kulutustasi koreihin…",
      get_spending_by_category: "Tarkistetaan kulutustasi…",
      get_monthly_balance_trend: "Katsotaan saldoasi…",
      get_transactions: "Haetaan tilitapahtumiasi…",
      calculate_safe_to_save: "Lasketaan säästömahdollisuutta…",
      calculate_what_if: "Lasketaan entä jos -laskelmaa…",
    } as Record<string, string>,
  },
};

export type Text = (typeof text)["en"];

export const formatDay = (iso: string, lang: Lang, opts: Intl.DateTimeFormatOptions = { day: "numeric", month: "short" }) =>
  new Date(`${iso}T00:00:00`).toLocaleDateString(locales[lang], opts);
