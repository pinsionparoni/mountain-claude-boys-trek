// Format only at presentation time; the backend does the arithmetic.
// Finnish money format under an English UI is a deliberate choice.
const eur = new Intl.NumberFormat("fi-FI", {
  style: "currency",
  currency: "EUR",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

export const formatMoney = (amountEur: number): string => eur.format(amountEur);
