export interface ApiResponse<T = unknown> {
  code: number;
  message: string;
  data: T;
}

export interface PaginationParams {
  limit?: number;
  offset?: number;
}

export interface TimeRangeParams {
  startTime?: string;
  endTime?: string;
}

export interface ErrorResponse {
  code: number;
  message: string;
  details?: Record<string, unknown>;
}

export interface SessionInfo {
  id: string;
  userId?: string;
  createdAt: string;
  lastActiveAt: string;
}
