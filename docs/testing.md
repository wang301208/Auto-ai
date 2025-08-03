# 运行测试

首先安装测试和类型检查依赖：

```shell
pip install .[test,dev]  # includes test tools and type stubs
```

要运行所有测试，使用以下命令：

```shell
pytest
```

如果找不到 `pytest`：

```shell
python -m pytest
```

### 运行特定测试套件

- 不运行集成测试：

```shell
pytest --without-integration
```

- 不运行 *慢速* 集成测试：

```shell
pytest --without-slow-integration
```

- 运行测试并查看覆盖率：

```shell
pytest --cov=autogpt --without-integration --without-slow-integration
```

## 运行代码检查器

本项目使用 [flake8](https://flake8.pycqa.org/en/latest/) 进行代码检查。
我们目前使用以下规则：`E303,W293,W291,W292,E305,E231,E302`。
更多信息参见 [flake8 规则](https://www.flake8rules.com/)。

运行代码检查器：

```shell
flake8 .
```

或者：

```shell
python -m flake8 .
```
