// Calls to the FastAPI backend. In development Vite forwards /api to it (vite.config.ts).
import type { BasketSummary, Budget, Receipts } from "./types";

const BASE = "/api";

// The hosted demo asks for a passcode (the backend's DEMO_PASSCODE); it is sent
// with every request and remembered on this device. Locally there is none.
const PASSCODE_KEY = "coach-passcode";
let passcode: string | null = (() => {
  try { return localStorage.getItem(PASSCODE_KEY); } catch { return null; }
})();

export const savedPasscode = () => passcode ?? "";

export function rememberPasscode(code: string) {
  passcode = code;
  try { localStorage.setItem(PASSCODE_KEY, code); } catch { /* private mode: asked again next time */ }
}

/** The backend refused the request: the passcode is missing or wrong. */
export class PasscodeError extends Error {}

const withPasscode = (headers: Record<string, string> = {}) =>
  passcode ? { ...headers, "X-Demo-Passcode": passcode } : headers;

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${BASE}${path}`, { headers: withPasscode() });
  if (response.status === 401) throw new PasscodeError("Wrong or missing demo passcode");
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
  return response.json() as Promise<T>;
}

export const fetchHealth = () =>
  getJson<{ ok: boolean; model: string; passcode_required: boolean }>("/health");

/** True if the backend accepts this passcode. */
export async function checkPasscode(code: string): Promise<boolean> {
  const response = await fetch(`${BASE}/passcode`, { headers: { "X-Demo-Passcode": code } });
  if (response.status === 401) return false;
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
  return true;
}

export const fetchSummary = (customerId: string) =>
  getJson<BasketSummary>(`/customers/${encodeURIComponent(customerId)}/summary`);

export const fetchBudget = (customerId: string) =>
  getJson<Budget>(`/customers/${encodeURIComponent(customerId)}/budget`);

export const fetchReceipts = (customerId: string) =>
  getJson<Receipts>(`/customers/${encodeURIComponent(customerId)}/receipts?limit=40`);

export interface ChatHandlers {
  onConversation: (conversationId: string) => void;
  onTool: (name: string) => void;
  onText: (text: string) => void;
  onError: (message: string) => void;
}

/**
 * Send a message and read the streamed answer (server-sent events over a POST,
 * which EventSource can't do). Resolves when the backend sends "done".
 */
export async function streamChat(
  customerId: string,
  message: string,
  conversationId: string | null,
  handlers: ChatHandlers,
): Promise<void> {
  const response = await fetch(`${BASE}/chat`, {
    method: "POST",
    headers: withPasscode({ "Content-Type": "application/json", Accept: "text/event-stream" }),
    body: JSON.stringify({ customer_id: customerId, message, conversation_id: conversationId }),
  });
  if (response.status === 401) throw new PasscodeError("Wrong or missing demo passcode");
  if (!response.ok || !response.body) throw new Error(`The coach is unavailable (${response.status})`);

  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) return;
    buffer += value;
    // Events are separated by a blank line: "event: <name>\ndata: <json>\n\n".
    let end: number;
    while ((end = buffer.indexOf("\n\n")) !== -1) {
      const block = buffer.slice(0, end);
      buffer = buffer.slice(end + 2);
      const event = /^event: (.*)$/m.exec(block)?.[1];
      const data = JSON.parse(/^data: (.*)$/m.exec(block)?.[1] ?? "{}");
      if (event === "conversation") handlers.onConversation(data.conversation_id);
      else if (event === "tool") handlers.onTool(data.name);
      else if (event === "text") handlers.onText(data.text);
      else if (event === "error") handlers.onError(data.message);
      else if (event === "done") return;
    }
  }
}
