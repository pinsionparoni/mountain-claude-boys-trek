import { useState, type FormEvent } from "react";
import type { ChatMessage } from "../lib/types";

interface Props {
  initial: ChatMessage[];
  suggestions: string[];
  showSuggestions: boolean;
  reply: (question: string) => string;
}

// The composer, history and status live outside ui.config: they are core behaviour.
export function Chat({ initial, suggestions, showSuggestions, reply }: Props) {
  const [messages, setMessages] = useState(initial);
  const [draft, setDraft] = useState("");
  const [status, setStatus] = useState("");

  const send = (text: string) => {
    const question = text.trim();
    if (!question) return;
    const n = messages.length;
    setMessages([
      ...messages,
      { id: `u${n}`, author: "user", text: question },
      { id: `a${n}`, author: "assistant", text: reply(question) },
    ]);
    setDraft("");
    setStatus("The coach replied.");
  };

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    send(draft);
  };

  return (
    <section className="panel chat" aria-labelledby="chat-title">
      <h2 id="chat-title" className="panel-title">Ask your coach</h2>
      <ol className="chat-log" aria-label="Conversation">
        {messages.map((m) => (
          <li key={m.id} className={`chat-message chat-message--${m.author}`}>
            <span className="visually-hidden">{m.author === "user" ? "You:" : "Coach:"}</span>
            {m.text}
          </li>
        ))}
      </ol>
      <p className="visually-hidden" role="status" aria-live="polite">{status}</p>

      {showSuggestions && (
        <div className="chips" aria-label="Suggested questions">
          {suggestions.map((s) => (
            <button key={s} type="button" className="chip" onClick={() => send(s)}>
              {s}
            </button>
          ))}
        </div>
      )}

      <form className="composer" onSubmit={onSubmit}>
        <label htmlFor="composer-input" className="visually-hidden">Message the financial coach</label>
        <textarea
          id="composer-input"
          className="composer-input"
          rows={2}
          value={draft}
          placeholder="Ask about your spending…"
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              send(draft);
            }
          }}
        />
        <button type="submit" className="button button--primary">Send</button>
      </form>
    </section>
  );
}
