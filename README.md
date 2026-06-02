# Codex-Abaqus MCP Server

MCP Server 连接 Codex AI 与 Abaqus 有限元分析软件。支持作业提交、ODB 结果读取、Python API 建模和任意 Abaqus 脚本执行。

## 功能

Codex-Abaqus 提供 **7 个 MCP 工具**，覆盖完整的 Abaqus 工作流：

| 工具 | 功能 |
|------|------|
| `abaqus_submit_job` | 提交 Abaqus 分析作业（支持多CPU、双精度、用户子程序） |
| `abaqus_job_status` | 查询作业状态（读取 .sta / .log / .msg） |
| `abaqus_read_odb_field` | 读取 ODB 场量输出（应力、位移、应变等） |
| `abaqus_read_odb_history` | 读取 ODB 历史输出（时间序列数据） |
| `abaqus_list_odb_contents` | 列举 ODB 文件结构和可用输出 |
| `abaqus_run_modeling` | 通过 Abaqus CAE API 建模（`abaqus cae noGUI=`） |
| `abaqus_run_python` | 执行任意 Abaqus Python 脚本（`abaqus python`） |

## 安装

### 前置条件

- **Python** >= 3.10
- **Abaqus** >= 2020（带 Python API）
- **mcp** Python 包 >= 1.0.0

### 从源码安装

```bash
git clone <repo-url>
cd codex-abaqus
pip install .
```

### 开发模式安装

```bash
pip install -e .
```

## 配置

通过环境变量配置 Abaqus 路径和行为：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `ABAQUS_COMMAND` | Abaqus 命令路径 | 自动检测 |
| `ABAQUS_WORK_DIR` | 工作目录 | 当前目录 |
| `ABAQUS_SCRATCH` | 临时脚本目录 | `./.abaqus_mcp_scratch` |
| `ABAQUS_CPUS` | 默认 CPU 数 | `4` |
| `ABAQUS_TIMEOUT` | 默认超时（秒） | `3600` |

Windows 上通常自动检测 `D:/SIMULIA/Commands/abaqus.bat`，无需手动设置。

## 使用

### 作为 MCP Server 运行

在 Codex 的 MCP 配置中添加：

```json
{
  "mcpServers": {
    "codex-abaqus": {
      "command": "py",
      "args": ["-m", "codex_abaqus"]
    }
  }
}
```

### 命令行测试

```bash
# 直接启动（通过 stdio 通信）
python -m codex_abaqus
```

## 使用示例

### 1. 提交作业

在 Codex 对话中：

> 帮我用 abaqus_submit_job 跑 `/path/to/analysis.inp`，用 8 核，等它跑完。

Codex 会调用工具提交作业并返回结果。

### 2. 读取结果

> 读取 `/path/to/analysis.odb` 最后一帧的 Mises 应力和位移 U。

Codex 调用 `abaqus_read_odb_field` 返回场量数据。

### 3. 参数化建模

> 用 abaqus_run_modeling 创建一个悬臂梁模型：长 100mm，截面 10x10mm，材料钢，端部 100N 集中力。

Codex 生成完整的 Abaqus Python CAE 脚本并通过 MCP 执行。

### 4. 后处理脚本

> 写一个 Python 脚本遍历 ODB 所有帧，提取最大 Mises 应力，输出 CSV。

Codex 生成脚本，通过 `abaqus_run_python` 执行并返回结果。

## 架构

```
codex-abaqus/
├── pyproject.toml              # 项目配置与依赖
├── README.md                   # 使用文档
├── .codex-plugin/
│   └── plugin.json             # Codex 插件清单
└── src/codex_abaqus/
    ├── __init__.py
    ├── __main__.py             # python -m 入口
    ├── server.py               # MCP Server 主程序
    ├── abaqus_interface/
    │   ├── __init__.py
    │   ├── config.py           # 配置与命令检测
    │   └── runner.py           # Abaqus CLI 封装
    ├── tools/
    │   ├── __init__.py
    │   ├── job.py              # 作业提交/状态工具
    │   ├── odb.py              # ODB 读取工具
    │   ├── modeling.py         # CAE 建模工具
    │   └── scripting.py        # Python 脚本执行工具
    └── templates/
        ├── read_odb_field.py   # 场量读取模板
        └── read_odb_history.py # 历史输出读取模板
```

## 工作原理

1. MCP Server 通过 stdio 与 Codex 通信
2. 收到工具调用后，生成临时 Python 脚本
3. 通过 `abaqus python` 或 `abaqus cae noGUI=` 在 Abaqus 环境中执行
4. 脚本输出 JSON 结果，Server 解析后返回 Codex

ODB 读取模板在 Abaqus Python 环境中运行（使用 `odbAccess`），将结构化的场量/历史数据序列化为 JSON 传回。

## License

MIT
