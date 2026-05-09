import { useState, type ReactNode } from "react";

interface TerminalSectionProps {
  title: string;
  glyph?: string;
  action?: ReactNode;
  children: ReactNode;
  defaultOpen?: boolean;
  id?: string;
}

export function TerminalSection({
  title,
  glyph = "▸",
  action,
  children,
  defaultOpen = true,
  id,
}: TerminalSectionProps) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className={`terminal-section ${open ? "terminal-section--open" : "terminal-section--closed"}`} id={id}>
      <div
        className="terminal-section__header"
        onClick={() => setOpen(!open)}
        role="button"
        tabIndex={0}
        aria-expanded={open}
      >
        <div className="terminal-section__title">
          <span className="terminal-section__chevron">{open ? "▾" : "▸"}</span>
          <span>{glyph}</span>
          <span>{title}</span>
        </div>
        {action ? <div className="terminal-section__actions">{action}</div> : null}
      </div>
      <div className="terminal-section__body">{children}</div>
    </div>
  );
}
