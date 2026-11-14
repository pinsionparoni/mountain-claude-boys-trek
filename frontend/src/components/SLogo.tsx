// The S logo (used with the team's permission), drawn from a transparent PNG used as a
// CSS mask so the same file can be white on green or green on white.
import logoUrl from "../assets/smobiili/s-logo.png";

export function SLogo({ className = "", label }: { className?: string; label?: string }) {
  return (
    <span
      className={`s-logo ${className}`}
      style={{ maskImage: `url(${logoUrl})`, WebkitMaskImage: `url(${logoUrl})` }}
      role={label ? "img" : undefined}
      aria-label={label}
      aria-hidden={label ? undefined : true}
    />
  );
}
