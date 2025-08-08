# 双环AI系统 - 快速启动指南

## 🚀 5分钟快速启动

### 1. 安装依赖

```bash
# 安装Python依赖
pip install -r dual_ring_ai/requirements.txt

# 或者手动安装核心依赖
pip install redis chromadb sentence-transformers streamlit watchdog requests
```

### 2. 启动Redis

```bash
# Ubuntu/Debian
sudo systemctl start redis-server

# macOS
brew services start redis

# Windows
# 启动Redis服务
```

### 3. 运行系统测试

```bash
# 测试系统组件
python dual_ring_ai/test_system.py
```

### 4. 启动系统

```bash
# 交互模式（推荐）
python dual_ring_ai/run.py --interactive

# 或者直接运行
python -m dual_ring_ai.main_controller --interactive
```

### 5. 使用系统

启动后，在交互界面中输入：

```
# 查看帮助
help

# 查看系统状态
status

# 执行任务
execute 创建一个数据分析和可视化工具

# 查看执行状态
status plan_20231201_143022

# 查看系统统计
stats

# 查看最近事件
events

# 退出系统
quit
```

## 📋 系统组件

### 创世纪工厂 (Genesis Factory)
- **哨兵代理**: 监控系统状态，检测问题
- **考古学家代理**: 诊断问题，分析根本原因  
- **TDD开发者代理**: 开发代码修复
- **QA代理**: 质量保证和审批

### 执行者系统 (Executor System)
- **任务规划器**: 分解用户目标
- **技能组合器**: 找到合适技能
- **执行引擎**: 执行技能组合

### 监控系统
- **仪表盘**: 实时可视化界面

## 🔧 配置选项

### 基本配置

创建 `config.json`:

```json
{
  "redis_host": "localhost",
  "redis_port": 6379,
  "redis_db": 0,
  "skill_library_path": "skill_library",
  "plugin_library_path": "plugins",
  "vector_db_path": "vector_db",
  "workspace_path": "workspace",
  "enable_genesis": true,
  "enable_executor": true,
  "enable_dashboard": true
}
```

### 启动选项

```bash
# 使用配置文件
python dual_ring_ai/run.py --config config.json --interactive

# 执行特定目标
python dual_ring_ai/run.py --goal "创建一个Web API"

# 守护进程模式
python dual_ring_ai/run.py --daemon
```

## 📊 监控界面

### Streamlit仪表盘
启动系统后，自动打开Web界面：
- 系统状态监控
- 事件统计图表
- 代理状态显示
- 实时事件流

### 控制台界面
在终端显示：
- 系统运行状态
- 代理状态
- 最近事件
- 错误信息

## 🛠️ 故障排除

### 常见问题

1. **Redis连接失败**
   ```bash
   # 检查Redis状态
   redis-cli ping
   
   # 启动Redis
   sudo systemctl start redis-server
   ```

2. **依赖项缺失**
   ```bash
   # 重新安装依赖
   pip install -r dual_ring_ai/requirements.txt
   ```

3. **权限问题**
   ```bash
   # 确保有写入权限
   chmod +x dual_ring_ai/run.py
   ```

### 调试模式

```bash
# 启用详细日志
export LOG_LEVEL=DEBUG
python dual_ring_ai/run.py --interactive
```

## 📚 下一步

1. **阅读完整文档**: 查看 `README.md`
2. **开发自定义技能**: 参考技能开发指南
3. **配置监控**: 设置日志和告警
4. **扩展系统**: 添加新的代理和功能

## 🆘 获取帮助

- 查看 `README.md` 获取详细文档
- 运行 `help` 命令查看交互式帮助
- 检查日志文件获取错误信息
- 提交Issue报告问题

---

**双环AI系统** - 让AI代理协同工作，实现智能自动化 🤖
