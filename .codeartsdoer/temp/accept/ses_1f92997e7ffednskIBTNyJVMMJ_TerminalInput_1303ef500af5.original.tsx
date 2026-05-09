import { useRef, useEffect, useCallback, useState } from "react";

interface TerminalInputProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  placeholder?: string;
  disabled?: boolean;
  promptGlyph?: string;
}

export function TerminalInput({
  value,
  onChange,
  onSubmit,
  placeholder = "输入指令或消息...",
  disabled = false,
  promptGlyph = "❯",
}: TerminalInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [cursorVisible, setCursorVisible] = useState(true);

  useEffect(() => {
    const interval = setInterval(() => setCursorVisible((v) => !v), 530);
    return () => clearInterval(interval);
  }, []);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        if (!disabled && value.trim()) {
          onSubmit();
        }
      }
    },
    [onSubmit, disabled, value],
  );

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      onChange(e.target.value);
      const el = e.target;
      el.style.height = "auto";
      el.style.height = Math.min(el.scrollHeight, 200) + "px";
    },
    [onChange],
  );

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height =
        Math.min(textareaRef.current.scrollHeight, 200) + "px";
    }
  }, [value]);

  return (
    <div className="terminal-chat__input-area">
      <span className="terminal-prompt">{promptGlyph}</span>
      <textarea
        ref={textareaRef}
        className="terminal-input"
        value={value}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={disabled}
        rows={1}
        aria-label="终端输入"
        spellCheck={false}
        autoComplete="off"
        autoCorrect="off"
        autoCapitalize="off"
      />
      <button
        className="cmd-button cmd-button--primary terminal-send-btn"
        onClick={onSubmit}
        disabled={disabled || !value.trim()}
        aria-label="发送"
      >
        ↵
      </button>
      {disabled ? (
        <span className="terminal-spinner" style={{ color: "var(--accent)" }}>⠋</span>
      ) : (
        <span style={{ color: cursorVisible ? "var(--accent)" : "transparent", fontSize: "13px", paddingTop: "6px" }}>▍</span>
      )}
    </div>
  );
}
