// Renders the coach's light Markdown (paragraphs, "*"/"-" bullet lists, **bold**)
// as React elements. No HTML is ever injected, so model output can't run scripts.
import type { ReactNode } from "react";

function inline(text: string, key: string): ReactNode[] {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
    part.startsWith("**") && part.endsWith("**") && part.length > 4
      ? <strong key={`${key}-${i}`}>{part.slice(2, -2)}</strong>
      : part,
  );
}

export function formatAnswer(text: string): ReactNode[] {
  const blocks: ReactNode[] = [];
  let bullets: string[] = [];
  let paragraph: string[] = [];

  const flush = () => {
    if (paragraph.length) {
      const k = `p${blocks.length}`;
      blocks.push(<p key={k}>{inline(paragraph.join(" "), k)}</p>);
      paragraph = [];
    }
    if (bullets.length) {
      const k = `ul${blocks.length}`;
      blocks.push(<ul key={k}>{bullets.map((b, i) => <li key={i}>{inline(b, `${k}-${i}`)}</li>)}</ul>);
      bullets = [];
    }
  };

  for (const raw of text.split("\n")) {
    const line = raw.trim();
    const bullet = /^[*-]\s+(.*)$/.exec(line);
    if (!line) flush();
    else if (bullet) {
      if (paragraph.length) flush();
      bullets.push(bullet[1]);
    } else {
      if (bullets.length) flush();
      paragraph.push(line);
    }
  }
  flush();
  return blocks;
}
