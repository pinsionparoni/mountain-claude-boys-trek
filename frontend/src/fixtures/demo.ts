// Demo setup: which synthetic customers the team can switch between.
// All numbers come from the backend; UI text is in src/lib/i18n.ts.

// Picked with COACH_TODAY=2026-09-10 (see SETUP.md); their situation changes with the date.
export const demoCustomers = [
  { id: "CUST00226", en: "CUST00226 · 21 y · cash tight before payday", fi: "CUST00226 · 21 v · rahat tiukalla ennen palkkaa" },
  { id: "CUST00050", en: "CUST00050 · 23 y · on track", fi: "CUST00050 · 23 v · budjetissa" },
  { id: "CUST00127", en: "CUST00127 · 24 y · budget nearly used", fi: "CUST00127 · 24 v · budjetti lähes käytetty" },
  { id: "CUST00001", en: "CUST00001 · 63 y", fi: "CUST00001 · 63 v" },
];
