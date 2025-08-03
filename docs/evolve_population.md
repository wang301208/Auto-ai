# 策略演化

`evolve_strategies/population` 文件夹包含描述不同代理策略的 YAML 文件。每个文件定义了提示模板、允许使用的工具以及代理使用这些工具的顺序等选项。这些 YAML 文件可以通过 `build_agent_from_strategy` 自动构建代理。

## 策略种子

使用 `seed_population.py` 生成初始的一组随机策略。脚本会将文件写入 `evolve_strategies/population/generation_0`。

```bash
python seed_population.py -n 20
```

## 策略评估

`evaluate_population.py` 会从 `bench_tasks` 加载任务，并评估人口目录中的每个策略文件。

```bash
python evaluate_population.py
```

每个策略的适应度分数都会打印出来，方便你挑选最优配置。

## 根据自定义策略构建代理

在拥有 YAML 策略后，你可以直接在 Python 中创建代理：

```python
from autogpt import build_agent_from_strategy

agent = build_agent_from_strategy("path/to/strategy.yaml")
result = agent.run("Write a short poem about the sea")
print(result)
```

该方法会将 YAML 设置应用于标准配置，并返回一个初始化完成、可以立即使用的代理。

## 完整演化循环

`auto_evolve.py` 脚本会运行多代策略演化。运行结束后，表现最好的 YAML 配置会被写入 `evolve_strategies/best/best_strategy.yaml` 以便重复使用。为保持向后兼容，该文件也会复制到 `configs/default_strategy.yaml`：

```bash
python auto_evolve.py -g 10 -p 20 -r 5
```
