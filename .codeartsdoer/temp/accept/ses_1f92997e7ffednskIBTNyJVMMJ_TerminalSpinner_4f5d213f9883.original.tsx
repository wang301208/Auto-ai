import { useState, useEffect } from "react";

const SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"];

interface TerminalSpinnerProps {
  text?: string;
  color?: string;
}

export function TerminalSpinner({ text = "处理中", color = "var(--accent)" }: TerminalSpinnerProps) {
  const [frame, setFrame] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => setFrame((f) => (f + 1) % SPINNER_FRAMES.length), 80);
    return () => clearInterval(interval);
  }, []);

  return (
    <span style={{ color }}>
      {SPINNER_FRAMES[frame]} {text}
    </span>
  );
}
