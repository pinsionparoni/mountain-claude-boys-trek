// Cards side by side that you swipe between, with S-mobiili's grey dots underneath.
// Swiping is the browser's own scroll snapping (native feel on phones, works with a
// trackpad or mouse); the dots follow the card in view and jump to a card when tapped.
import { Children, useEffect, useRef, useState, type ReactNode } from "react";
import type { Text } from "../lib/i18n";

interface Props {
  t: Text;
  children: ReactNode;
}

export function CardCarousel({ t, children }: Props) {
  const cards = Children.toArray(children).filter(Boolean);
  const track = useRef<HTMLDivElement>(null);
  const [active, setActive] = useState(0);

  // The card at least 60 % in view is the active one.
  useEffect(() => {
    const el = track.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) setActive(Number((entry.target as HTMLElement).dataset.index));
        }
      },
      { root: el, threshold: 0.6 },
    );
    el.querySelectorAll<HTMLElement>(".carousel-slide").forEach((slide) => observer.observe(slide));
    return () => observer.disconnect();
  }, [cards.length]);

  // Scroll only the track sideways (scrollIntoView would also move the chat up or down).
  const show = (i: number) => {
    const el = track.current;
    const slide = el?.querySelectorAll<HTMLElement>(".carousel-slide")[i];
    if (el && slide) el.scrollTo({ left: slide.offsetLeft - el.offsetLeft, behavior: "smooth" });
  };

  if (cards.length === 0) return null;
  return (
    <section className="carousel" aria-roledescription="carousel" aria-label={t.cardsLabel}>
      <div className="carousel-track" ref={track} tabIndex={0}
           onKeyDown={(e) => {
             if (e.key === "ArrowRight") { e.preventDefault(); show(Math.min(active + 1, cards.length - 1)); }
             if (e.key === "ArrowLeft") { e.preventDefault(); show(Math.max(active - 1, 0)); }
           }}>
        {cards.map((card, i) => (
          <div key={i} className="carousel-slide" data-index={i}
               role="group" aria-roledescription="slide" aria-label={t.cardOf(i + 1, cards.length)}>
            {card}
          </div>
        ))}
      </div>
      {cards.length > 1 && (
        <div className="sm-dots carousel-dots">
          {cards.map((_, i) => (
            <button key={i} type="button" className={i === active ? "on" : undefined}
                    aria-label={t.showCard(i + 1)} aria-current={i === active ? "true" : undefined}
                    onClick={() => show(i)} />
          ))}
        </div>
      )}
    </section>
  );
}
