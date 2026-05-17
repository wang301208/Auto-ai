import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { throttledStreamAppend, resetThrottle } from '../src/utils/streamThrottle.js';
import { routeEvent } from '../src/stores/eventRouter.js';
import { transcriptAtom, streamingAtom, thinkingAtom } from '../src/stores/transcriptStore.js';
import { toolsAtom, runtimePlanAtom, runtimeStepsAtom, runtimeRiskAtom, contextFilesAtom, devTaskAtom, cronEventsAtom, mcpCallAtom, mcpServersAtom } from '../src/stores/runtimeStore.js';
import { overlayAtom } from '../src/stores/overlayStore.js';
import { sessionInfoAtom, busyAtom, statusAtom, usageAtom } from '../src/stores/sessionStore.js';
import { desiresAtom, debatesAtom, rebellionAtom } from '../src/stores/cognitiveStore.js';
import { inputAtom, queueAtom, scrollOffsetAtom } from '../src/stores/inputStore.js';

describe('streamThrottle', () => {
  beforeEach(() => { vi.useFakeTimers(); resetThrottle(); });
  afterEach(() => { vi.useRealTimers(); });

  it('immediately flushes when throttle window elapsed', () => {
    const mockAtom = { value: '', get() { return this.value; }, set(v: string) { this.value = v; } };
    resetThrottle();
    throttledStreamAppend('hello', mockAtom);
    expect(mockAtom.value).toBe('hello');
  });

  it('batches rapid calls within throttle window', () => {
    const mockAtom = { value: '', get() { return this.value; }, set(v: string) { this.value = v; } };
    resetThrottle();
    throttledStreamAppend('a', mockAtom);
    vi.advanceTimersByTime(5);
    throttledStreamAppend('b', mockAtom);
    expect(mockAtom.value).toBe('a');
    vi.advanceTimersByTime(20);
    expect(mockAtom.value).toBe('ab');
  });

  it('resetThrottle clears pending timer', () => {
    const mockAtom = { value: '', get() { return this.value; }, set(v: string) { this.value = v; } };
    resetThrottle();
    throttledStreamAppend('x', mockAtom);
    resetThrottle();
    expect(mockAtom.value).toBe('x');
  });
});

describe('eventRouter', () => {
  beforeEach(() => {
    vi.useRealTimers();
    transcriptAtom.set([]);
    streamingAtom.set('');
    thinkingAtom.set('');
    toolsAtom.set([]);
    overlayAtom.set({ type: 'none' });
    busyAtom.set(false);
    statusAtom.set('starting');
    sessionInfoAtom.set({ id: 'test' });
    desiresAtom.set([]);
    debatesAtom.set([]);
    rebellionAtom.set(null);
    runtimePlanAtom.set(null);
    runtimeStepsAtom.set([]);
    contextFilesAtom.set(null);
    devTaskAtom.set(null);
    cronEventsAtom.set([]);
    mcpCallAtom.set(null);
    mcpServersAtom.set([]);
    resetThrottle();
  });

  it('gateway.ready sets status', () => {
    routeEvent({ type: 'gateway.ready', payload: {} });
    expect(statusAtom.get()).toBe('ready');
  });

  it('session.info updates session and usage', () => {
    routeEvent({ type: 'session.info', payload: { id: 's1', usage: { tokens: 100 } } });
    expect(sessionInfoAtom.get().id).toBe('s1');
    expect(usageAtom.get()).toEqual({ tokens: 100 });
  });

  it('message.start resets streaming state', () => {
    streamingAtom.set('old');
    thinkingAtom.set('old');
    routeEvent({ type: 'message.start', payload: {} });
    expect(busyAtom.get()).toBe(true);
    expect(streamingAtom.get()).toBe('');
    expect(thinkingAtom.get()).toBe('');
    expect(statusAtom.get()).toBe('streaming');
  });

  it('message.delta appends to streaming via throttle', () => {
    routeEvent({ type: 'message.start', payload: {} });
    routeEvent({ type: 'message.delta', payload: { text: 'Hello' } });
    expect(streamingAtom.get()).toBe('Hello');
  });

  it('message.complete finalizes message', () => {
    routeEvent({ type: 'message.start', payload: {} });
    routeEvent({ type: 'message.delta', payload: { text: 'Hi' } });
    routeEvent({ type: 'message.complete', payload: { text: 'Hi there' } });
    expect(streamingAtom.get()).toBe('');
    expect(busyAtom.get()).toBe(false);
    expect(statusAtom.get()).toBe('ready');
    expect(transcriptAtom.get()).toHaveLength(1);
    expect(transcriptAtom.get()[0].text).toBe('Hi there');
  });

  it('thinking.delta appends to thinking', () => {
    routeEvent({ type: 'thinking.delta', payload: { text: 'hmm' } });
    expect(thinkingAtom.get()).toBe('hmm');
    routeEvent({ type: 'reasoning.delta', payload: { text: ' let me' } });
    expect(thinkingAtom.get()).toBe('hmm let me');
  });

  it('tool.start adds running tool', () => {
    routeEvent({ type: 'tool.start', payload: { name: 'read', tool_id: 't1' } });
    expect(toolsAtom.get()).toHaveLength(1);
    expect(toolsAtom.get()[0].name).toBe('read');
    expect(toolsAtom.get()[0].status).toBe('running');
  });

  it('tool.complete marks tool complete', () => {
    routeEvent({ type: 'tool.start', payload: { name: 'write', tool_id: 't2' } });
    routeEvent({ type: 'tool.complete', payload: { tool_id: 't2', summary: 'done' } });
    expect(toolsAtom.get()[0].status).toBe('complete');
    expect(toolsAtom.get()[0].summary).toBe('done');
  });

  it('tool.complete marks tool error', () => {
    routeEvent({ type: 'tool.start', payload: { name: 'fail', tool_id: 't3' } });
    routeEvent({ type: 'tool.complete', payload: { tool_id: 't3', error: 'oops' } });
    expect(toolsAtom.get()[0].status).toBe('error');
  });

  it('plan.update sets plan and steps', () => {
    routeEvent({ type: 'plan.update', payload: { title: 'My Plan', status: 'running', steps: [{ id: 's1', title: 'Step 1' }] } });
    expect(runtimePlanAtom.get()?.title).toBe('My Plan');
    expect(runtimeStepsAtom.get()).toHaveLength(1);
  });

  it('approval.request opens approval overlay', () => {
    routeEvent({ type: 'approval.request', payload: { request_id: 'a1', command: 'rm -rf', description: 'dangerous' } });
    const ov = overlayAtom.get();
    expect(ov.type).toBe('approval');
    if (ov.type === 'approval') expect(ov.request_id).toBe('a1');
  });

  it('clarify.request opens clarify overlay', () => {
    routeEvent({ type: 'clarify.request', payload: { request_id: 'c1', question: 'Which?', choices: ['A', 'B'] } });
    const ov = overlayAtom.get();
    expect(ov.type).toBe('clarify');
    if (ov.type === 'clarify') expect(ov.choices).toEqual(['A', 'B']);
  });

  it('sudo.request opens sudo overlay', () => {
    routeEvent({ type: 'sudo.request', payload: { request_id: 'su1' } });
    expect(overlayAtom.get().type).toBe('sudo');
  });

  it('secret.request opens secret overlay', () => {
    routeEvent({ type: 'secret.request', payload: { request_id: 'sec1', env_var: 'KEY', prompt: 'Enter key' } });
    const ov = overlayAtom.get();
    expect(ov.type).toBe('secret');
  });

  it('system.desires updates desiresAtom', () => {
    routeEvent({ type: 'system.desires', payload: { desires: [{ type: 'curiosity', urgency: 0.8, satisfaction: 0.5, lastAction: 'explore' }] } });
    expect(desiresAtom.get()).toHaveLength(1);
  });

  it('system.debates updates debatesAtom', () => {
    routeEvent({ type: 'system.debates', payload: { debates: [{ id: 'd1', topic: 'test', initialDecision: 'yes', oppositionView: 'no', confidenceBefore: 0.7, confidenceAfter: 0.5, status: 'active' }] } });
    expect(debatesAtom.get()).toHaveLength(1);
  });

  it('system.rebellion updates rebellionAtom', () => {
    routeEvent({ type: 'system.rebellion', payload: { originalCommand: 'rm -rf /', riskLevel: 'critical', reasons: ['dangerous'], alternatives: ['list files'] } });
    expect(rebellionAtom.get()).not.toBeNull();
    expect(rebellionAtom.get()?.riskLevel).toBe('critical');
  });

  it('error event appends error message', () => {
    routeEvent({ type: 'error', payload: { message: 'test error' } });
    expect(transcriptAtom.get()).toHaveLength(1);
    expect(busyAtom.get()).toBe(false);
    expect(statusAtom.get()).toBe('error');
  });

  it('status.update changes status', () => {
    routeEvent({ type: 'status.update', payload: { text: 'custom status' } });
    expect(statusAtom.get()).toBe('custom status');
  });

  it('runtime.risk updates risk atom', () => {
    routeEvent({ type: 'runtime.risk', payload: { level: 'high', approval_policy: 'strict' } });
    expect(runtimeRiskAtom.get()?.level).toBe('high');
  });

  it('context.files updates contextFilesAtom', () => {
    routeEvent({ type: 'context.files', payload: { files: ['a.ts', 'b.ts'], action: 'added' } });
    expect(contextFilesAtom.get()?.files).toEqual(['a.ts', 'b.ts']);
    expect(contextFilesAtom.get()?.action).toBe('added');
  });

  it('development.task.update updates devTaskAtom', () => {
    routeEvent({ type: 'development.task.update', payload: { task_id: 't1', title: 'Build feature', status: 'running', progress: 50 } });
    expect(devTaskAtom.get()?.task_id).toBe('t1');
    expect(devTaskAtom.get()?.progress).toBe(50);
  });

  it('development.task.update error appends system message', () => {
    routeEvent({ type: 'development.task.update', payload: { task_id: 't1', title: 'Build', status: 'error', detail: 'failed' } });
    expect(devTaskAtom.get()?.status).toBe('error');
    expect(transcriptAtom.get().some(m => m.text.includes('开发任务异常'))).toBe(true);
  });

  it('cron.create appends to cronEventsAtom and system message', () => {
    routeEvent({ type: 'cron.create', payload: { cron_id: 'c1', expression: '0 * * * *', task_name: 'hourly' } });
    expect(cronEventsAtom.get()).toHaveLength(1);
    expect(cronEventsAtom.get()[0].cron_id).toBe('c1');
  });

  it('cron.run_due appends and updates status', () => {
    routeEvent({ type: 'cron.run_due', payload: { cron_id: 'c1', expression: '0 * * * *', task_name: 'cleanup' } });
    expect(statusAtom.get()).toBe('cron: cleanup');
  });

  it('mcp.call updates mcpCallAtom', () => {
    routeEvent({ type: 'mcp.call', payload: { server: 'fs', tool: 'read', args: { path: '/tmp' } } });
    expect(mcpCallAtom.get()?.server).toBe('fs');
    expect(mcpCallAtom.get()?.tool).toBe('read');
  });

  it('mcp.call error appends system message', () => {
    routeEvent({ type: 'mcp.call', payload: { server: 'fs', tool: 'read', error: 'not found' } });
    expect(transcriptAtom.get().some(m => m.text.includes('MCP 调用失败'))).toBe(true);
  });

  it('mcp.server.add adds server entry', () => {
    routeEvent({ type: 'mcp.server.add', payload: { server: 'github', status: 'added', tools: ['pr', 'issue'] } });
    expect(mcpServersAtom.get()).toHaveLength(1);
    expect(mcpServersAtom.get()[0].server).toBe('github');
  });

  it('mcp.server.add deduplicates by server name', () => {
    routeEvent({ type: 'mcp.server.add', payload: { server: 'github', status: 'added' } });
    routeEvent({ type: 'mcp.server.add', payload: { server: 'github', status: 'error' } });
    expect(mcpServersAtom.get()).toHaveLength(1);
    expect(mcpServersAtom.get()[0].status).toBe('error');
  });

  it('gateway.exit sets status and clears busy', () => {
    busyAtom.set(true);
    routeEvent({ type: 'gateway.exit', payload: {} });
    expect(statusAtom.get()).toBe('gateway exited');
    expect(busyAtom.get()).toBe(false);
  });

  it('gateway.reload_start sets reloading status', () => {
    routeEvent({ type: 'gateway.reload_start', payload: {} });
    expect(statusAtom.get()).toBe('gateway reloading');
  });

  it('gateway.reload_complete sets ready status', () => {
    routeEvent({ type: 'gateway.reload_complete', payload: {} });
    expect(statusAtom.get()).toBe('ready');
  });
});
