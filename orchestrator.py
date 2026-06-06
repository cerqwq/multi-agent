"""
Multi-Agent - 多Agent协作框架
受 MetaGPT (68k stars) 和 crewAI (52k stars) 启发
支持角色分工、任务协作、结果汇总
"""

import json
import os
from typing import Dict, List, Any, Generator, Callable
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class AgentRole(Enum):
    """Agent角色"""
    PLANNER = "planner"      # 规划者
    RESEARCHER = "researcher" # 研究者
    CODER = "coder"          # 编码者
    REVIEWER = "reviewer"    # 审查者
    WRITER = "writer"        # 写作者
    ANALYST = "analyst"      # 分析者


@dataclass
class AgentConfig:
    """Agent配置"""
    name: str
    role: AgentRole
    description: str
    system_prompt: str
    tools: List[str] = field(default_factory=list)
    model: str = "mimo-v2.5-pro"


@dataclass
class Task:
    """任务"""
    id: str
    description: str
    assigned_to: str = ""
    status: str = "pending"  # pending, in_progress, completed, failed
    result: str = ""
    dependencies: List[str] = field(default_factory=list)


class Agent:
    """单个Agent"""

    def __init__(self, config: AgentConfig, client: 'OpenAI' = None):
        self.config = config
        self.client = client
        self.memory: List[Dict] = []
        self.task_history: List[Dict] = []

    def execute(self, task: str, context: str = "") -> str:
        """执行任务"""
        if not self.client:
            return f"[{self.config.name}] LLM客户端未配置"

        messages = [
            {"role": "system", "content": self.config.system_prompt}
        ]

        if context:
            messages.append({"role": "user", "content": f"上下文信息：\n{context}"})

        messages.append({"role": "user", "content": task})

        try:
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                max_tokens=2000
            )
            result = response.choices[0].message.content

            # 记录历史
            self.task_history.append({
                "task": task,
                "result": result,
                "timestamp": datetime.now().isoformat()
            })

            return result
        except Exception as e:
            return f"[{self.config.name}] 执行失败: {e}"

    def stream_execute(self, task: str, context: str = "") -> Generator[str, None, None]:
        """流式执行"""
        if not self.client:
            yield f"[{self.config.name}] LLM客户端未配置"
            return

        messages = [
            {"role": "system", "content": self.config.system_prompt}
        ]

        if context:
            messages.append({"role": "user", "content": f"上下文信息：\n{context}"})

        messages.append({"role": "user", "content": task})

        try:
            stream = self.client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                stream=True,
                max_tokens=2000
            )

            full_response = ""
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    text = chunk.choices[0].delta.content
                    full_response += text
                    yield text

            self.task_history.append({
                "task": task,
                "result": full_response,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            yield f"[{self.config.name}] 执行失败: {e}"


class MultiAgentOrchestrator:
    """
    多Agent编排器
    支持：任务分解、Agent协作、结果汇总
    """

    def __init__(self, model: str = "mimo-v2.5-pro", api_key: str = None, base_url: str = None):
        self.model = model
        self.agents: Dict[str, Agent] = {}
        self.tasks: Dict[str, Task] = {}
        self.execution_history: List[Dict] = []

        # 创建LLM客户端
        if OPENAI_AVAILABLE:
            self.client = OpenAI(
                api_key=api_key or os.environ.get('OPENAI_API_KEY', ''),
                base_url=base_url or os.environ.get('OPENAI_BASE_URL', 'https://api.xiaomimimo.com/v1')
            )
        else:
            self.client = None

    def add_agent(self, config: AgentConfig) -> Agent:
        """添加Agent"""
        agent = Agent(config, self.client)
        self.agents[config.name] = agent
        return agent

    def create_default_team(self):
        """创建默认团队"""
        agents_config = [
            AgentConfig(
                name="Planner",
                role=AgentRole.PLANNER,
                description="任务规划和分解",
                system_prompt="你是一个任务规划专家。你的职责是分析任务，将其分解为子任务，并分配给合适的团队成员。输出JSON格式的子任务列表。"
            ),
            AgentConfig(
                name="Researcher",
                role=AgentRole.RESEARCHER,
                description="信息收集和研究",
                system_prompt="你是一个研究员。你的职责是收集信息、分析数据、提供研究结果。回答要详细、准确、有依据。"
            ),
            AgentConfig(
                name="Coder",
                role=AgentRole.CODER,
                description="代码编写和调试",
                system_prompt="你是一个高级程序员。你的职责是编写高质量的代码、解决技术问题、提供技术方案。代码要简洁、高效、有注释。"
            ),
            AgentConfig(
                name="Reviewer",
                role=AgentRole.REVIEWER,
                description="代码审查和质量控制",
                system_prompt="你是一个代码审查专家。你的职责是审查代码质量、发现潜在问题、提供改进建议。关注：正确性、性能、安全性、可读性。"
            ),
            AgentConfig(
                name="Writer",
                role=AgentRole.WRITER,
                description="文档编写和内容创作",
                system_prompt="你是一个技术写作者。你的职责是编写清晰的文档、教程、报告。内容要结构清晰、易于理解、有实用价值。"
            ),
        ]

        for config in agents_config:
            self.add_agent(config)

    def decompose_task(self, task: str) -> List[Task]:
        """分解任务"""
        planner = self.agents.get("Planner")
        if not planner:
            return [Task(id="task_0", description=task)]

        prompt = f"""请将以下任务分解为2-5个子任务，每个子任务分配给合适的团队成员。

团队成员：{', '.join(f'{name}({agent.config.description})' for name, agent in self.agents.items())}

任务：{task}

请返回JSON格式：
[
    {{"id": "task_1", "description": "子任务描述", "assigned_to": "Agent名称", "dependencies": []}},
    ...
]"""

        result = planner.execute(prompt)

        try:
            import re
            json_match = re.search(r'\[.*\]', result, re.DOTALL)
            if json_match:
                tasks_data = json.loads(json_match.group())
                tasks = []
                for td in tasks_data:
                    task_obj = Task(
                        id=td.get("id", f"task_{len(tasks)}"),
                        description=td.get("description", ""),
                        assigned_to=td.get("assigned_to", ""),
                        dependencies=td.get("dependencies", [])
                    )
                    tasks.append(task_obj)
                    self.tasks[task_obj.id] = task_obj
                return tasks
        except Exception as e:
            print(f"任务分解失败: {e}")

        # 备用方案
        default_task = Task(id="task_0", description=task, assigned_to="Researcher")
        self.tasks[default_task.id] = default_task
        return [default_task]

    def execute_task(self, task: Task, context: str = "") -> str:
        """执行单个任务"""
        task.status = "in_progress"

        agent = self.agents.get(task.assigned_to)
        if not agent:
            # 默认使用Researcher
            agent = self.agents.get("Researcher")
            if not agent:
                task.status = "failed"
                task.result = "没有可用的Agent"
                return task.result

        result = agent.execute(task.description, context)
        task.status = "completed"
        task.result = result

        return result

    def execute_workflow(self, task: str, stream: bool = False) -> Generator[str, None, None]:
        """执行完整工作流"""
        yield f"[Orchestrator] 分析任务: {task}\n\n"

        # 1. 分解任务
        yield "[Orchestrator] 分解任务中...\n"
        tasks = self.decompose_task(task)

        for t in tasks:
            yield f"  - [{t.assigned_to}] {t.description}\n"
        yield "\n"

        # 2. 按依赖顺序执行
        completed = set()
        context_parts = []

        for t in tasks:
            # 检查依赖
            if not all(dep in completed for dep in t.dependencies):
                yield f"[Orchestrator] 跳过 {t.id}（依赖未满足）\n"
                continue

            yield f"[{t.assigned_to}] 执行: {t.description}\n"

            # 构建上下文
            context = "\n\n".join(context_parts) if context_parts else ""

            if stream:
                result = ""
                for chunk in self.agents[t.assigned_to].stream_execute(t.description, context):
                    result += chunk
                    yield chunk
            else:
                result = self.execute_task(t, context)
                yield result

            yield "\n\n"
            completed.add(t.id)
            context_parts.append(f"[{t.assigned_to}的输出]: {result[:500]}")

        # 3. 汇总
        yield "[Orchestrator] 任务完成！\n"

        self.execution_history.append({
            "task": task,
            "tasks_count": len(tasks),
            "timestamp": datetime.now().isoformat()
        })

    def get_status(self) -> Dict:
        """获取状态"""
        return {
            "agents_count": len(self.agents),
            "agents": {name: agent.config.description for name, agent in self.agents.items()},
            "tasks_count": len(self.tasks),
            "executions_count": len(self.execution_history)
        }


def create_team(model: str = "mimo-v2.5-pro", **kwargs) -> MultiAgentOrchestrator:
    """创建默认团队"""
    orchestrator = MultiAgentOrchestrator(model=model, **kwargs)
    orchestrator.create_default_team()
    return orchestrator


if __name__ == "__main__":
    team = create_team()

    print("Multi-Agent Team")
    print(f"Status: {json.dumps(team.get_status(), ensure_ascii=False, indent=2)}")
    print()

    # 测试
    task = "创建一个简单的Python Web API，包含用户注册和登录功能"

    print(f"Task: {task}")
    print("=" * 50)

    for chunk in team.execute_workflow(task, stream=True):
        print(chunk, end="", flush=True)
