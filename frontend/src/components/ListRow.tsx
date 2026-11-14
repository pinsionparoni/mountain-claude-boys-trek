// One row of an S-mobiili list card: green line icon, title, grey subtitle, and a
// chevron, amount or badge on the right. Rows without onClick are only for the look.
import type { ReactNode } from "react";
import { ChevronIcon } from "./Icons";

interface Props {
  icon: ReactNode;
  title: string;
  subtitle?: string;
  end?: ReactNode;       // defaults to a chevron
  onClick?: () => void;
  highlight?: boolean;   // the coach's own rows
  hint?: string;         // tooltip for rows that do nothing in the demo
}

export function ListRow({ icon, title, subtitle, end, onClick, highlight, hint }: Props) {
  const content = (
    <>
      <span className="sm-row-icon">{icon}</span>
      <span className="sm-row-text">
        <span className="sm-row-title">{title}</span>
        {subtitle && <span className="sm-row-sub">{subtitle}</span>}
      </span>
      <span className="sm-row-end">{end ?? <ChevronIcon />}</span>
    </>
  );
  const className = `sm-row${highlight ? " sm-row--highlight" : ""}`;
  return onClick
    ? <button type="button" className={className} onClick={onClick}>{content}</button>
    : <div className={className} title={hint}>{content}</div>;
}
