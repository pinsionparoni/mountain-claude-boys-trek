// Names for the data's merchant types and categories, as the customer sees them.
// Keys are the backend's labels (coach/spending_baskets.py MERCHANT_TYPES and the
// dataset's categories); anything unknown falls back to the category, then as is.
import type { Lang } from "./i18n";
import type { BasketKey, BasketSummary, Receipt } from "./types";

const MERCHANT_TYPES: Record<string, { en: string; fi: string }> = {
  "supermarket": { en: "Supermarket", fi: "Ruokakauppa" },
  "butcher": { en: "Butcher", fi: "Lihakauppa" },
  "dairy shop": { en: "Dairy shop", fi: "Maitokauppa" },
  "convenience / specialty food": { en: "Convenience store", fi: "Lähikauppa" },
  "fuel": { en: "Fuel", fi: "Polttoaine" },
  "service station": { en: "Service station", fi: "Huoltoasema" },
  "parking": { en: "Parking", fi: "Pysäköinti" },
  "public transport": { en: "Public transport", fi: "Joukkoliikenne" },
  "taxi": { en: "Taxi", fi: "Taksi" },
  "pharmacy": { en: "Pharmacy", fi: "Apteekki" },
  "doctor": { en: "Doctor", fi: "Lääkäri" },
  "dentist": { en: "Dentist", fi: "Hammaslääkäri" },
  "medical services": { en: "Medical services", fi: "Terveyspalvelut" },
  "home supply store": { en: "Home supplies", fi: "Kodintarvikkeet" },
  "hardware store": { en: "Hardware store", fi: "Rautakauppa" },
  "electronics": { en: "Electronics", fi: "Elektroniikka" },
  "furniture": { en: "Furniture", fi: "Huonekalut" },
  "software": { en: "Software", fi: "Ohjelmistot" },
  "restaurant": { en: "Restaurant", fi: "Ravintola" },
  "bar": { en: "Bar", fi: "Baari" },
  "fast food / café": { en: "Fast food / café", fi: "Pikaruoka / kahvila" },
  "tickets / events": { en: "Tickets / events", fi: "Liput / tapahtumat" },
  "recreation": { en: "Recreation", fi: "Vapaa-aika" },
  "cinema": { en: "Cinema", fi: "Elokuvateatteri" },
  "attractions": { en: "Attractions", fi: "Nähtävyydet" },
  "amusement park": { en: "Amusement park", fi: "Huvipuisto" },
  "sporting goods": { en: "Sporting goods", fi: "Urheiluvälineet" },
  "clothing": { en: "Clothing", fi: "Vaatteet" },
  "other retail": { en: "Other shopping", fi: "Muut ostokset" },
  "bookstore": { en: "Bookstore", fi: "Kirjakauppa" },
  "hobby / toys": { en: "Hobbies / toys", fi: "Harrastukset / lelut" },
  "travel agency": { en: "Travel agency", fi: "Matkatoimisto" },
  "airline": { en: "Airline", fi: "Lentoyhtiö" },
  "hotel": { en: "Hotel", fi: "Hotelli" },
  "car rental": { en: "Car rental", fi: "Autovuokraamo" },
};

const CATEGORIES: Record<string, { en: string; fi: string }> = {
  "Groceries": { en: "Groceries", fi: "Ruoka" },
  "Restaurants": { en: "Restaurants", fi: "Ravintolat" },
  "Transportation": { en: "Transport", fi: "Liikkuminen" },
  "Entertainment": { en: "Entertainment", fi: "Viihde" },
  "Health": { en: "Health", fi: "Terveys" },
  "Home & Tech": { en: "Home & tech", fi: "Koti ja tekniikka" },
  "Lifestyle": { en: "Shopping & hobbies", fi: "Ostokset ja harrastukset" },
  "Travel": { en: "Travel", fi: "Matkailu" },
  "Housing": { en: "Housing", fi: "Asuminen" },
  "Utilities": { en: "Utilities", fi: "Laskut" },
};

export const categoryName = (category: string, lang: Lang) => CATEGORIES[category]?.[lang] ?? category;

/** "Ruokakauppa"; a purchase without a known merchant type is named after its category. */
export const merchantName = (merchantType: string, category: string, lang: Lang) =>
  MERCHANT_TYPES[merchantType]?.[lang] ?? categoryName(category, lang);

/** "🏠 Välttämättömät menot" as the backend names it, or just the icon if the summary isn't loaded. */
export function basketLabel(basket: Receipt["basket"], summary: BasketSummary | null, lang: Lang): string {
  if (basket === "unclassified") return "";
  const b = summary?.baskets[basket as BasketKey];
  if (b) return lang === "fi" ? b.label_fi : b.label;
  return { regular_essentials: "🏠", unexpected_necessities: "🔧", everyday_spending: "☕" }[basket];
}
