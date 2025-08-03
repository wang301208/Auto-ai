# 设置 Auto-GPT

## 📋 依赖要求

Auto-GPT 在本地运行，你需要：

  - Python 3.10 或更高版本（安装教程：[Windows](https://www.tutorialspoint.com/how-to-install-python-in-windows)）
  - [Git](https://git-scm.com/downloads)（可选但推荐）

## 🗝️ 获取 API Key

从 [https://platform.openai.com/account/api-keys](https://platform.openai.com/account/api-keys) 获取你的 OpenAI API key。

!!! attention
    要在 Auto-GPT 中使用 OpenAI API，强烈建议**启用计费**。免费账号每分钟仅限 3 次调用，可能导致程序崩溃。
    可在 [Manage account > Billing > Overview](https://platform.openai.com/account/billing/overview) 设置付费账号。

!!! important
    建议在 [Usage 页面](https://platform.openai.com/account/usage) 跟踪费用，并在 [Usage limits 页面](https://platform.openai.com/account/billing/limits) 设置消费上限。

![为使 OpenAI API key 正常工作，请在 OpenAI API > Billing 中设置付费账号](./imgs/openai-api-key-billing-paid-account.png)

## 设置 Auto-GPT

### 使用 Git 安装

!!! important
    确认你的操作系统已安装 [Git](https://git-scm.com/downloads)。

!!! info "执行命令"
    打开 CMD、Bash 或 Powershell 终端执行以下命令。

1. 克隆仓库

    ```shell
    git clone -b stable https://github.com/Significant-Gravitas/Auto-GPT.git
    ```

2. 进入仓库目录

    ```shell
    cd Auto-GPT
    ```

### 使用发布包安装

1. 从[最新稳定版本](https://github.com/Significant-Gravitas/Auto-GPT/releases/latest)下载 `Source code (zip)`。
2. 将压缩包解压到文件夹。

### 配置

[English version](setup.en.md)
