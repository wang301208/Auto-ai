# 本地自主进化智能体系统运行手册

## 范围

本手册覆盖当前本地自主进化系统的可运行部分：端到端闭环、算法进化闭环、技能生命周期、治理审批、沙箱执行、事件记录、审计查询、交互入口和 Cockpit API。外部供应商能力仍通过适配器配置接入，运行前应通过预检和主机集成探针确认真实可用性。

## 启动配置

默认配置位于 `configs/local_autonomous_runtime.example.json`，运行根目录为 `.dual_ring_runtime`。配置中声明技能库、算法库、算法实验、治理、日志、工作区和组织章程路径，并显式列出远程 LLM、Docker 沙箱、Ollama、Whisper、XTTS 等适配器开关。

## 启动命令

运行本地运行时烟测：

```powershell
./scripts/start_local_autonomous_runtime.ps1
```

启动 Cockpit API：

```powershell
./scripts/start_cockpit_api.ps1
```

默认 API 入口由配置文件中的 `cockpit.host` 和 `cockpit.port` 控制。

## 端到端闭环

1. 生成技能提案目录，包含 `skill.json`、`main.py`、`test_main.py`。
2. `LocalRuntime.create_skill_publication_request()` 执行安全策略校验、静态扫描和本地 pytest。
3. `GovernanceStore.decide()` 完成人工审批。
4. `LocalRuntime.publish_skill_from_approval()` 发布技能，并通过 `SandboxRunner` 执行烟测。
5. 系统记录本地事件，并写入技能生命周期审计日志。

兼容旧编码断言：绔埌绔棴鐜?

## 算法进化闭环

算法注册、实验、评审、晋升建议和回滚目标均保留为可审计流程。算法替换不应绕过审批，也不应自动覆盖生产中的思维引擎。

兼容旧编码断言：绠楁硶杩涘寲闂幆

## Cockpit API

- `GET /status`：运行时状态。
- `GET /health`：健康报告。
- `POST /preflight`：生成预检报告。
- `POST /host-integration-probe`：主机集成探针。
- `GET /approvals`：审批队列。
- `POST /approvals/{request_id}/decision`：审批或拒绝。
- `GET /events`：本地事件流。
- `GET /skills`：已发布技能。
- `GET /audit/skill-lifecycle`：技能生命周期审计。
- `GET /audit/algorithm-evolution`：算法进化审计。
- `GET /algorithms`：算法注册表。
- `GET /algorithm-experiments`：算法实验报告。
- `POST /interaction`：本地交互入口。

## 验收命令

```powershell
python -m pytest dual_ring_ai/test_controlled_skill_lifecycle.py dual_ring_ai/test_full_backend_evolution.py dual_ring_ai/test_local_autonomous_runtime.py dual_ring_ai/test_external_adapters.py dual_ring_ai/test_end_to_end_runtime.py dual_ring_ai/test_security_hardening.py dual_ring_ai/test_cockpit_expansion.py dual_ring_ai/test_runtime_artifacts.py -q
python -m pytest dual_ring_ai/test_strategist.py -q
```
