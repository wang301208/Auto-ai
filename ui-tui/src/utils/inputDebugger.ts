/**
 * 输入序列调试工具（仅在开发模式启用）
 * 用于诊断未知的按键序列和鼠标事件
 */
export function debugInputSequence(chunk: Buffer, enabled: boolean = false): void {
  if (!enabled || !process.env.DEBUG_INPUT) return;
  
  const hex = chunk.toString('hex');
  const ascii = chunk.toString('ascii').replace(/[\x00-\x1F\x7F]/g, '.');
  const utf8 = chunk.toString('utf8');
  
  console.error(`[INPUT DEBUG] Hex: ${hex} | ASCII: ${ascii} | UTF8: ${utf8} | Length: ${chunk.length}`);
}
