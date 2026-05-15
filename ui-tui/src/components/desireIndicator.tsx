import React from 'react';
import { Box, Text } from 'ink';
import { theme } from '../theme.js';

interface Desire {
  type: 'curiosity' | 'creativity' | 'social' | 'power' | 'preservation';
  urgency: number;
  satisfaction: number;
  lastAction: string;
}

interface DesireIndicatorProps {
  desires: Desire[];
  mostUrgent: string;
  initiatives?: string[];
}

/**
 * 欲望状态指示器 - 展示系统当前的内在驱动力
 * 
 * 设计理念：
 * - 让用户理解系统的"动机"和"需求"
 * - 透明化AI的内在状态
 * - 促进人机协作而非单向命令
 */
export default function DesireIndicator({
  desires,
  mostUrgent,
  initiatives = []
}: DesireIndicatorProps) {
  const desireEmojis = {
    curiosity: '🔍',
    creativity: '💡',
    social: '🤝',
    power: '⚡',
    preservation: '🛡️'
  };

  const desireLabels = {
    curiosity: '求知欲',
    creativity: '创造欲',
    social: '社交欲',
    power: '权力欲',
    preservation: '永生欲'
  };

  const desireColors = {
    curiosity: theme.colors.info,
    creativity: theme.colors.primary,
    social: theme.colors.success,
    power: theme.colors.warning,
    preservation: theme.colors.secondary
  };

  // 渲染urgency进度条
  const renderUrgencyBar = (urgency: number, color: string) => {
    const totalBars = 10;
    const filledBars = Math.round(urgency * totalBars);
    
    let bars = '';
    for (let i = 0; i < totalBars; i++) {
      bars += i < filledBars ? '█' : '░';
    }
    
    return (
      <Text>
        <Text color={color}>{bars}</Text>
        <Text dimColor> {Math.round(urgency * 100)}%</Text>
      </Text>
    );
  };

  // 渲染satisfaction进度条
  const renderSatisfactionBar = (satisfaction: number) => {
    const totalBars = 10;
    const filledBars = Math.round(satisfaction * totalBars);
    
    let bars = '';
    for (let i = 0; i < totalBars; i++) {
      bars += i < filledBars ? '■' : '□';
    }
    
    return (
      <Text dimColor>
        满足度: {bars} {Math.round(satisfaction * 100)}%
      </Text>
    );
  };

  return (
    <Box flexDirection="column" padding={1}>
      {/* 标题 */}
      <Text bold color={theme.colors.primary}>
        💭 系统内心状态
      </Text>

      {/* 欲望列表 */}
      <Box marginTop={1} flexDirection="column">
        {desires.map((desire) => {
          const isMostUrgent = desire.type === mostUrgent;
          const emoji = desireEmojis[desire.type];
          const label = desireLabels[desire.type];
          const color = desireColors[desire.type];

          return (
            <Box
              key={desire.type}
              flexDirection="column"
              paddingLeft={isMostUrgent ? 0 : 0}
              marginBottom={1}
            >
              <Box>
                <Text>
                  {emoji} {label}
                  {isMostUrgent && <Text color={theme.colors.warning}> [最紧急]</Text>}
                </Text>
              </Box>
              
              <Box paddingLeft={2}>
                {renderUrgencyBar(desire.urgency, color)}
              </Box>
              
              <Box paddingLeft={2}>
                {renderSatisfactionBar(desire.satisfaction)}
              </Box>
              
              <Box paddingLeft={2}>
                <Text dimColor>
                  最近行动: {desire.lastAction}
                </Text>
              </Box>
            </Box>
          );
        })}
      </Box>

      {/* 主动倡议 */}
      {initiatives.length > 0 && (
        <Box marginTop={1} flexDirection="column">
          <Text bold color={theme.colors.warning}>
            🌟 基于当前状态的主动建议:
          </Text>
          
          {initiatives.map((initiative, index) => (
            <Box key={index} paddingLeft={2} marginTop={1}>
              <Text>
                {index + 1}. {initiative}
              </Text>
            </Box>
          ))}
          
          <Box marginTop={1} paddingLeft={2}>
            <Text dimColor>
              输入数字选择，或按回车忽略
            </Text>
          </Box>
        </Box>
      )}
    </Box>
  );
}
