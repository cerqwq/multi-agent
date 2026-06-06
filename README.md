# 🤝 Multi-Agent

多Agent协作框架，受MetaGPT (68k stars)和crewAI (52k stars)启发。

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue?logo=python" />
  <img src="https://img.shields.io/badge/OpenAI-API-green?logo=openai" />
  <img src="https://img.shields.io/badge/License-MIT-yellow" />
</p>

## ✨ 特性

- 👥 多Agent角色分工
- 📋 任务自动分解
- 🔗 依赖关系管理
- 🔄 协作执行
- 📊 执行历史

## 🚀 快速开始

```bash
pip install openai

python orchestrator.py
```

## 📖 使用

```python
from orchestrator import create_team, AgentConfig, AgentRole

# 创建团队
team = create_team(model="mimo-v2.5-pro")

# 执行任务
for chunk in team.execute_workflow("创建一个Web API", stream=True):
    print(chunk, end="")

# 自定义Agent
team.add_agent(AgentConfig(
    name="Tester",
    role=AgentRole.REVIEWER,
    description="测试专家",
    system_prompt="你是一个测试专家，负责编写和执行测试用例。"
))
```

## 👥 默认团队

| Agent | 角色 | 职责 |
|-------|------|------|
| Planner | 规划者 | 任务分解和分配 |
| Researcher | 研究者 | 信息收集和分析 |
| Coder | 编码者 | 代码编写 |
| Reviewer | 审查者 | 代码审查 |
| Writer | 写作者 | 文档编写 |

## 📊 工作流程

```
用户任务 → Planner分解 → 分配给各Agent → 执行 → 汇总结果
```

## 📁 项目结构

```
multi-agent/
├── orchestrator.py  # 多Agent编排器
└── README.md
```

## 📄 许可证

MIT License
