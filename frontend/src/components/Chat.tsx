import { useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { streamChat } from "../lib/api";
import { formatAnswer } from "../lib/formatAnswer";
import type { Lang, Text } from "../lib/i18n";
import type { ChartSpec, ChatMessage } from "../lib/types";
import { ChatChart } from "./ChatChart";
import { SendIcon } from "./Icons";

interface Props {
  customerId: string;
  t: Text;
  lang: Lang;
  showSuggestions: boolean;
  children?: ReactNode;  // cards shown above the conversation
}

// The coach screen's body: a scrolling area (cards, conversation, suggestions) and an
// input bar pinned to the bottom, like S-mobiili's tab bar. The composer, history and
// status live outside ui.config: they are core behaviour.
// Parent renders it with key={customerId}, so a new customer starts a new conversation.
export function Chat({ customerId, t, lang, showSuggestions, children }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);
  const conversationId = useRef<string | null>(null);
  const scroller = useRef<HTMLElement>(null);

  // Scroll only the conversation area to the newest text. (scrollIntoView would also
  // scroll the page around the phone.)
  useEffect(() => {
    const el = scroller.current;
    if (el && messages.length) el.scrollTop = el.scrollHeight;
  }, [messages, status]);

  const appendToAnswer = (id: string, text: string) =>
    setMessages((all) => all.map((m) => (m.id === id ? { ...m, text: m.text + text } : m)));
  const addChart = (id: string, chart: ChartSpec) =>
    setMessages((all) => all.map((m) => (m.id === id ? { ...m, charts: [...(m.charts ?? []), chart] } : m)));

  const send = async (text: string) => {
    const question = text.trim();
    if (!question || busy) return;
    const n = Date.now();
    const answerId = `a${n}`;
    setMessages((all) => [
      ...all,
      { id: `u${n}`, author: "user", text: question },
      { id: answerId, author: "assistant", text: "" },
    ]);
    setDraft("");
    setBusy(true);
    setStatus(t.thinking);

    try {
      await streamChat(customerId, question, conversationId.current, {
        onConversation: (id) => { conversationId.current = id; },
        onTool: (name) => setStatus(t.tools[name] ?? t.checking),
        onText: (chunk) => { setStatus(""); appendToAnswer(answerId, chunk); },
        onChart: (chart) => addChart(answerId, chart),
        onError: (message) => appendToAnswer(answerId, `\n\n${message}`),
      });
    } catch {
      appendToAnswer(answerId, t.unreachable);
    } finally {
      setBusy(false);
      setStatus("");
    }
  };

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    void send(draft);
  };

  // The greeting follows the current language; it is not part of the conversation.
  const shown: ChatMessage[] = [{ id: "greeting", author: "assistant", text: t.greeting }, ...messages];

  return (
    <>
      <main className="sm-scroll sm-coach" ref={scroller}>
        {children}
        <section className="chat" aria-label={t.chatTitle}>
          <ol className="chat-log" aria-label={t.conversation}>
            {shown
              .filter((m) => m.text || m.charts?.length)
              .map((m) => (
                <li key={m.id} className={`chat-message chat-message--${m.author}`}>
                  <span className="visually-hidden">{m.author === "user" ? t.you : t.coach}</span>
                  {m.author === "assistant"
                    ? <>
                        {/* The chart first: it gives the picture before the words explain it. */}
                        {m.charts?.map((chart, i) => <ChatChart key={i} chart={chart} t={t} lang={lang} />)}
                        {m.text && <div className="answer">{formatAnswer(m.text)}</div>}
                      </>
                    : m.text}
                </li>
              ))}
            {status && (
              <li className="chat-status" aria-hidden="true">
                <span className="chat-status-dots"><i /><i /><i /></span>{status}
              </li>
            )}
          </ol>
          <p className="visually-hidden" role="status" aria-live="polite">{busy ? status : ""}</p>

          {showSuggestions && !messages.length && (
            <div className="chips" aria-label={t.suggested}>
              {t.suggestions.map((s) => (
                <button key={s} type="button" className="chip" disabled={busy} onClick={() => void send(s)}>
                  {s}
                </button>
              ))}
            </div>
          )}
        </section>
      </main>

      <form className="sm-composer" onSubmit={onSubmit}>
        <label htmlFor="composer-input" className="visually-hidden">{t.composerLabel}</label>
        <textarea
          id="composer-input"
          className="sm-composer-input"
          rows={1}
          value={draft}
          placeholder={t.placeholder}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              void send(draft);
            }
          }}
        />
        <button type="submit" className="sm-send" disabled={busy || !draft.trim()} aria-label={t.send}>
          <SendIcon />
        </button>
      </form>
    </>
  );
}
