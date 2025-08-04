# Git 命令指南

本文介绍常用的 Git 操作以及相关参数，并提供调用示例。

## `git_clone`
克隆远程仓库到本地。

**参数**
- `repo_url`：要克隆的远程仓库地址。
- `destination`（可选）：本地保存目录。
- `branch`（可选）：要检出的分支。

**示例**
```bash
git clone https://github.com/Significant-Gravitas/Auto-GPT.git
```

## `git_commit`
提交当前暂存区的改动。

**参数**
- `message`：提交说明。
- `add_all`（可选）：是否在提交前添加所有变更，相当于 `-a`。

**示例**
```bash
git add docs/commands/git_operations.md
git commit -m "docs: add git command guide"
```

## `git_push`
将本地提交推送到远程仓库。

**参数**
- `remote`（默认 `origin`）：远程仓库名。
- `branch`：要推送的分支名。

**示例**
```bash
git push origin main
```

## `git_create_branch`
创建新的分支。

**参数**
- `branch_name`：新分支名称。
- `start_point`（可选）：起始提交或分支。

**示例**
```bash
git branch feature/new-doc
```

## `git_checkout`
切换分支或恢复工作区文件。

**参数**
- `target`：目标分支或提交。
- `-b`（可选）：创建并切换到新分支。

**示例**
```bash
git checkout feature/new-doc
# 或
git checkout -b feature/new-doc
```

## `git_blame`
显示文件各行最后一次修改的提交信息。

**参数**
- `file`：要查看的文件路径。
- `-L`（可选）：限制行号范围。

**示例**
```bash
git blame README.md
git blame -L 1,20 README.md
```
