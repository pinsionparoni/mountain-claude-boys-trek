import { useEffect, useRef, useState, type FormEvent } from "react";
import { streamChat } from "../lib/api";
import { formatAnswer } from "../lib/formatAnswer";
import type { Text } from "../lib/i18n";
import type { ChatMessage } from "../lib/types";

interface Props {
  customerId: string;
  t: Text;
  showSuggestions: boolean;
}

// The composer, history and status live outside ui.config: they are core behaviour.
// Parent renders it with key={customerId}, so a new customer starts a new conversation.
export function Chat({ customerId, t, showSuggestions }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);
  const conversationId = useRef<string | null>(null);
  const logEnd = useRef<HTMLLIElement>(null);

  useEffect(() => {
    logEnd.current?.scrollIntoView({ block: "end" });
  }, [messages, status]);

  const appendToAnswer = (id: string, text: string) =>
    setMessages((all) => all.map((m) => (m.id === id ? { ...m, text: m.text + text } : m)));

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
    <section className="panel chat" aria-labelledby="chat-title">
      <h2 id="chat-title" className="panel-title">{t.chatTitle}</h2>
      <ol className="chat-log" aria-label={t.conversation}>
        {shown
          .filter((m) => m.text)
          .map((m) => (
            <li key={m.id} className={`chat-message chat-message--${m.author}`}>
              <span className="visually-hidden">{m.author === "user" ? t.you : t.coach}</span>
              {m.author === "assistant" ? <div className="answer">{formatAnswer(m.text)}</div> : m.text}
            </li>
          ))}
        {status && <li className="chat-status muted" aria-hidden="true">{status}</li>}
        <li ref={logEnd} aria-hidden="true" />
      </ol>
      <p className="visually-hidden" role="status" aria-live="polite">{busy ? status : ""}</p>

      {showSuggestions && (
        <div className="chips" aria-label={t.suggested}>
          {t.suggestions.map((s) => (
            <button key={s} type="button" className="chip" disabled={busy} onClick={() => void send(s)}>
              {s}
            </button>
          ))}
        </div>
      )}

      <form className="composer" onSubmit={onSubmit}>
        <label htmlFor="composer-input" className="visually-hidden">{t.composerLabel}</label>
        <textarea
          id="composer-input"
          className="composer-input"
          rows={2}
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
        <button type="submit" className="button button--primary" disabled={busy}>{t.send}</button>
      </form>
    </section>
  );
}
