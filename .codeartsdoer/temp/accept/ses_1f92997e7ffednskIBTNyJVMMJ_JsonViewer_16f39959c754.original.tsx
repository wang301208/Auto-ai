import { useState, useEffect, useRef } from "react";

interface JsonViewerProps {
  value: unknown;
  maxHeight?: number;
}

export function JsonViewer({ value, maxHeight = 360 }: JsonViewerProps) {
  const [collapsed, setCollapsed] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const json = JSON.stringify(value, null, 2);

  const highlighted = json
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"([^"]+)"(?=\s*:)/g, '<span class="json-key">"$1"</span>')
    .replace(/:\s*"([^"]*?)"/g, ': <span class="json-string">"$1"</span>')
    .replace(/:\s*(-?\d+\.?\d*)/g, ': <span class="json-number">$1</span>')
    .replace(/:\s*(true|false)/g, ': <span class="json-bool">$1</span>')
    .replace(/:\s*(null)/g, ': <span class="json-null">$1</span>');

  return (
    <div
      ref={containerRef}
      className="json-viewer"
      style={{ maxHeight: collapsed ? 80 : maxHeight }}
      onClick={() => setCollapsed(!collapsed)}
      role="button"
      tabIndex={0}
      title={collapsed ? "点击展开" : "点击折叠"}
    >
      <pre dangerouslySetInnerHTML={{ __html: highlighted }} />
    </div>
  );
}
