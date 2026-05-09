import { useEffect, useRef } from "react";

export interface ChatMessageData {
  id: string;
  role: "user" | "assistant" | "system" | "tool";
  text: string;
  timestamp?: string;
  meta?: string;
}

interface ChatMessagesProps {
  messages: ChatMessageData[];
}

const ROLE_GLYPHS: Record<string, string> = {
  user: "❯",
  assistant: "⚕",
  system: "─",
  tool: "⚙",
};

export function ChatMessages({ messages }: ChatMessagesProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length]);

  if (messages.length === 0) {
    return (
      <div className="terminal-chat__messages">
        <div className="chat-message chat-message--system">
          <span className="chat-message__gutter">─</span>
          <div className="chat-message__body">
            等待输入。发送指令或问题以启动交互。
          </div>
        </div>
        <div ref={bottomRef} />
      </div>
    );
  }

  return (
    <div className="terminal-chat__messages">
      {messages.map((msg) => (
        <div key={msg.id} className={`chat-message chat-message--${msg.role}`}>
          <span className="chat-message__gutter">
            {ROLE_GLYPH[msg.role] ?? "─"}
          </span>
          <div>
            <div className="chat-message__body">{msg.text}</div>
            {msg.timestamp ? (
              <div className="chat-message__meta">
                {msg.timestamp}
                {msg.meta ? ` · ${msg.meta}` : ""}
              </div>
            ) : null}
          </div>
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
