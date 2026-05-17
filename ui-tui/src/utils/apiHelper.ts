import type { GatewayClient } from '../gatewayClient.js';

export interface ApiResult<T> {
  ok: boolean;
  data?: T;
  error?: string;
}

export async function safeRequest<T>(
  gateway: GatewayClient,
  method: string,
  params: Record<string, any>
): Promise<ApiResult<T>> {
  try {
    const data = await gateway.request<T>(method, params);
    return { ok: true, data };
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    return { ok: false, error: message };
  }
}

export function formatError(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }
  if (typeof error === 'string') {
    return error;
  }
  return '未知错误';
}

export function logError(context: string, error: unknown): void {
  const message = formatError(error);
  const timestamp = new Date().toISOString();
  
  if (process.env.DEBUG_ERRORS) {
    console.error(`[${timestamp}] [${context}] ${message}`, error);
  }
}
