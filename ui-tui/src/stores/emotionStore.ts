import { atom, computed } from 'nanostores';

export type EmotionType =
  | 'curious'    // 好奇 - 探索新信息
  | 'focused'    // 专注 - 深度思考
  | 'confident'  // 自信 - 确定性高
  | 'cautious'   // 谨慎 - 风险感知
  | 'frustrated' // 挫败 - 遇到障碍
  | 'creative'   // 创造 - 发散思维
  | 'empathetic' // 共情 - 理解用户
  | 'neutral';   // 中性 - 默认状态

export interface EmotionState {
  current: EmotionType;
  intensity: number;       // 0-1 强度
  confidence: number;      // 0-1 确信度
  reason: string;          // 情绪原因
  since: number;           // 时间戳
  history: EmotionTransition[];
}

export interface EmotionTransition {
  from: EmotionType;
  to: EmotionType;
  reason: string;
  timestamp: number;
}

export interface ProactiveSuggestion {
  id: string;
  type: 'action' | 'resource_request' | 'insight' | 'warning';
  priority: 'low' | 'medium' | 'high';
  emoji: string;
  title: string;
  description: string;
  action?: string;           // 可执行命令
  resourceType?: string;     // 资源类型（如 token_budget, context_window）
  resourceAmount?: number;   // 请求量
  dismissed: boolean;
  timestamp: number;
}

export const EMOTION_META: Record<EmotionType, { emoji: string; label: string; color: string; description: string }> = {
  curious:    { emoji: '🔍', label: '好奇',  color: 'cyan',    description: '正在探索新信息' },
  focused:    { emoji: '🎯', label: '专注',  color: 'blue',    description: '深度思考中' },
  confident:  { emoji: '✨', label: '自信',  color: 'green',   description: '对结果确信度高' },
  cautious:   { emoji: '⚠️', label: '谨慎',  color: 'yellow',  description: '检测到潜在风险' },
  frustrated: { emoji: '😤', label: '挫败',  color: 'red',     description: '遇到障碍，需要调整' },
  creative:   { emoji: '💡', label: '创造',  color: 'magenta', description: '发散思维模式' },
  empathetic: { emoji: '🤝', label: '共情',  color: 'white',   description: '理解用户意图' },
  neutral:    { emoji: '😐', label: '中性',  color: 'gray',    description: '待机状态' },
};

const ALL_EMOTIONS: EmotionType[] = ['curious', 'focused', 'confident', 'cautious', 'frustrated', 'creative', 'empathetic', 'neutral'];

const TRANSITION_RULES: Record<EmotionType, EmotionType[]> = {
  curious:    ALL_EMOTIONS,
  focused:    ALL_EMOTIONS,
  confident:  ALL_EMOTIONS,
  cautious:   ALL_EMOTIONS,
  frustrated: ['cautious', 'creative', 'focused', 'neutral', 'curious'],
  creative:   ALL_EMOTIONS,
  empathetic: ALL_EMOTIONS,
  neutral:    ALL_EMOTIONS,
};

export const emotionAtom = atom<EmotionState>({
  current: 'neutral',
  intensity: 0.3,
  confidence: 0.5,
  reason: '系统启动',
  since: Date.now(),
  history: [],
});

export const suggestionsAtom = atom<ProactiveSuggestion[]>([]);

export const emotionLabel = computed(emotionAtom, (state) => EMOTION_META[state.current].label);
export const emotionEmoji = computed(emotionAtom, (state) => EMOTION_META[state.current].emoji);
export const activeSuggestions = computed(suggestionsAtom, (items) => items.filter(s => !s.dismissed));

export function setEmotion(type: EmotionType, intensity: number, reason: string, confidence?: number) {
  const prev = emotionAtom.get();
  if (type === prev.current && Math.abs(intensity - prev.intensity) < 0.05) return;

  const allowed = TRANSITION_RULES[prev.current];
  const target = allowed.includes(type) ? type : prev.current;

  const transition: EmotionTransition = {
    from: prev.current,
    to: target,
    reason,
    timestamp: Date.now(),
  };

  emotionAtom.set({
    current: target,
    intensity: Math.max(0, Math.min(1, intensity)),
    confidence: confidence ?? prev.confidence,
    reason,
    since: Date.now(),
    history: [...prev.history.slice(-19), transition],
  });
}

let suggestionCounter = 0;

export function addSuggestion(suggestion: Omit<ProactiveSuggestion, 'id' | 'dismissed' | 'timestamp'>) {
  const id = `sug:${Date.now()}:${++suggestionCounter}`;
  suggestionsAtom.set([
    ...suggestionsAtom.get(),
    { ...suggestion, id, dismissed: false, timestamp: Date.now() },
  ]);
}

export function dismissSuggestion(id: string) {
  suggestionsAtom.set(
    suggestionsAtom.get().map(s => s.id === id ? { ...s, dismissed: true } : s)
  );
}

export function clearSuggestions() {
  suggestionsAtom.set([]);
}
