// Format only at presentation time; the backend does the arithmetic.
// Finnish money format under an English UI is a deliberate choice.
const eur = new Intl.NumberFormat("fi-FI", {
  style: "currency",
  currency: "EUR",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

export const formatMoney = (amountEur: number): string => eur.format(amountEur);

const wholeEur = new Intl.NumberFormat("fi-FI", { style: "currency", currency: "EUR", maximumFractionDigits: 0 });

/** Whole euros ("115 €") for chart labels, where cents only add clutter. */
export const formatWholeMoney = (amountEur: number): string => wholeEur.format(amountEur);
