import React, { Component, type ErrorInfo, type ReactNode } from 'react';
import { Box, Text } from 'ink';
import { theme } from '../theme.js';

interface Props {
  level: 'root' | 'content' | 'overlay';
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    const timestamp = new Date().toISOString();
    const errorLog = `[${timestamp}] [ErrorBoundary:${this.props.level}] ${error.message}\nStack: ${error.stack || 'N/A'}\nComponent: ${info.componentStack || 'N/A'}`;
    
    if (process.stderr.isTTY) {
      process.stderr.write(errorLog + '\n');
    }
    
    if (process.env.DEBUG_ERRORS) {
      console.error('[ErrorBoundary] Full error details:', { error, info, timestamp });
    }
  }

  render(): ReactNode {
    if (!this.state.hasError) return this.props.children;

    if (this.props.fallback) return this.props.fallback;

    const levelLabels = { root: '系统', content: '内容区', overlay: '浮层' };
    return (
      <Box flexDirection="column" padding={1}>
        <Text bold color={theme.colors.error}>
          {levelLabels[this.props.level]}渲染异常
        </Text>
        <Text color={theme.colors.dim}>
          {this.state.error?.message || '未知错误'}
        </Text>
        {this.props.level === 'root' && (
          <Text color={theme.colors.dim}>
            请按 Ctrl+C 退出后重试
          </Text>
        )}
      </Box>
    );
  }
}
