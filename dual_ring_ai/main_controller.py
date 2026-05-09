"""
主控制器 (Main Controller)

协调整个双环AI系统的运行，管理所有代理的启动、停止和配置。
"""

import json
import logging
import signal
import sys
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from .core.event_bus import EventBus, EventTypes
from .core.librarian import Librarian
from .genesis.sentry import SentryAgent, DEFAULT_SENTRY_CONFIG
from .genesis.archaeologist import ArchaeologistAgent, DEFAULT_ARCHAEOLOGIST_CONFIG
from .genesis.tdd_developer import TDDDeveloperAgent, DEFAULT_TDD_DEVELOPER_CONFIG
from .genesis.qa_agent import QAAgent, DEFAULT_QA_CONFIG
from .genesis.strategist import StrategistAgent, DEFAULT_STRATEGIST_CONFIG
from .executor.task_planner import TaskPlanner, DEFAULT_TASK_PLANNER_CONFIG
from .executor.skill_composer import SkillComposer, DEFAULT_SKILL_COMPOSER_CONFIG
from .executor.execution_engine import ExecutionEngine, DEFAULT_EXECUTION_ENGINE_CONFIG
from .dashboard.monitor import Dashboard, DEFAULT_DASHBOARD_CONFIG

logger = logging.getLogger(__name__)


@dataclass
class SystemConfig:
    """系统配置"""
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    skill_library_path: str = "skill_library"
    plugin_library_path: str = "plugins"
    vector_db_path: str = "vector_db"
    workspace_path: str = "workspace"
    enable_genesis: bool = True
    enable_executor: bool = True
    enable_dashboard: bool = True
    # Workspace paths for meta operations
    meta_workspace_path: str = "workspace"


class MainController:
    """主控制器"""
    
    def __init__(self, config_path: Optional[str] = None):
        """初始化主控制器"""
        self.config = self._load_config(config_path)
        self.running = False
        self.agents = {}
        
        # 初始化核心组件
        self.event_bus = EventBus(
            redis_host=self.config.redis_host,
            redis_port=self.config.redis_port,
            redis_db=self.config.redis_db
        )
        
        self.librarian = Librarian(
            skill_library_path=self.config.skill_library_path,
            plugin_library_path=self.config.plugin_library_path,
            vector_db_path=self.config.vector_db_path
        )
        
        # 初始化代理
        self._initialize_agents()
        
        # 设置信号处理器
        self._setup_signal_handlers()
        
        logger.info("Main controller initialized")
    
    def _load_config(self, config_path: Optional[str]) -> SystemConfig:
        """加载配置"""
        if config_path and Path(config_path).exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                return SystemConfig(**config_data)
            except Exception as e:
                logger.error(f"Failed to load config from {config_path}: {e}")
        
        # 使用默认配置
        return SystemConfig()
    
    def _initialize_agents(self):
        """初始化代理"""
        # 创世纪工厂代理
        if self.config.enable_genesis:
            self.agents["sentry"] = SentryAgent(self.event_bus, DEFAULT_SENTRY_CONFIG)
            self.agents["archaeologist"] = ArchaeologistAgent(self.event_bus, self.librarian, DEFAULT_ARCHAEOLOGIST_CONFIG)
            self.agents["tdd_developer"] = TDDDeveloperAgent(self.event_bus, self.librarian, DEFAULT_TDD_DEVELOPER_CONFIG)
            self.agents["qa"] = QAAgent(self.event_bus, self.librarian, DEFAULT_QA_CONFIG)
            strat_config = DEFAULT_STRATEGIST_CONFIG
            strat_config.workspace_path = self.config.meta_workspace_path
            self.agents["strategist"] = StrategistAgent(self.event_bus, strat_config)
        
        # 执行者系统代理
        if self.config.enable_executor:
            self.agents["task_planner"] = TaskPlanner(self.event_bus, DEFAULT_TASK_PLANNER_CONFIG)
            self.agents["skill_composer"] = SkillComposer(self.event_bus, self.librarian, DEFAULT_SKILL_COMPOSER_CONFIG)
            self.agents["execution_engine"] = ExecutionEngine(self.event_bus, self.librarian, DEFAULT_EXECUTION_ENGINE_CONFIG)
        
        # 监控仪表盘
        if self.config.enable_dashboard:
            self.agents["dashboard"] = Dashboard(self.event_bus, DEFAULT_DASHBOARD_CONFIG)
        
        logger.info(f"Initialized {len(self.agents)} agents")
    
    def _setup_signal_handlers(self):
        """设置信号处理器"""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down...")
            self.stop()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def start(self):
        """启动系统"""
        if self.running:
            logger.warning("System is already running")
            return
        
        logger.info("Starting dual ring AI system...")
        
        # 连接事件总线
        if not self.event_bus.connect():
            logger.error("Failed to connect to event bus")
            return
        
        # 启动所有代理
        for agent_name, agent in self.agents.items():
            try:
                agent.start()
                logger.info(f"Started agent: {agent_name}")
            except Exception as e:
                logger.error(f"Failed to start agent {agent_name}: {e}")
        
        self.running = True
        
        # 发布系统启动事件
        self.event_bus.publish(
            EventTypes.SYSTEM_STARTED,
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "agents": list(self.agents.keys()),
                "config": {
                    "redis_host": self.config.redis_host,
                    "redis_port": self.config.redis_port,
                    "enable_genesis": self.config.enable_genesis,
                    "enable_executor": self.config.enable_executor,
                    "enable_dashboard": self.config.enable_dashboard
                }
            },
            "main_controller"
        )
        
        logger.info("Dual ring AI system started successfully")
    
    def stop(self):
        """停止系统"""
        if not self.running:
            return
        
        logger.info("Stopping dual ring AI system...")
        
        # 停止所有代理
        for agent_name, agent in self.agents.items():
            try:
                agent.stop()
                logger.info(f"Stopped agent: {agent_name}")
            except Exception as e:
                logger.error(f"Failed to stop agent {agent_name}: {e}")
        
        self.running = False
        
        # 发布系统停止事件
        self.event_bus.publish(
            EventTypes.SYSTEM_STOPPED,
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "agents": list(self.agents.keys())
            },
            "main_controller"
        )
        
        logger.info("Dual ring AI system stopped")
    
    def get_agent_status(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """获取代理状态"""
        if agent_name not in self.agents:
            return None
        
        agent = self.agents[agent_name]
        return {
            "name": agent_name,
            "running": agent.running if hasattr(agent, 'running') else False,
            "type": type(agent).__name__
        }
    
    def get_all_agent_statuses(self) -> Dict[str, Dict[str, Any]]:
        """获取所有代理状态"""
        return {
            name: self.get_agent_status(name)
            for name in self.agents.keys()
        }
    
    def restart_agent(self, agent_name: str) -> bool:
        """重启代理"""
        if agent_name not in self.agents:
            logger.error(f"Agent {agent_name} not found")
            return False
        
        try:
            agent = self.agents[agent_name]
            agent.stop()
            time.sleep(1)  # 等待停止
            agent.start()
            logger.info(f"Restarted agent: {agent_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to restart agent {agent_name}: {e}")
            return False
    
    def execute_task(self, goal: str, context: Optional[Dict[str, Any]] = None) -> str:
        """执行任务"""
        if not self.running:
            logger.error("System is not running")
            return None
        
        try:
            # 使用任务规划器规划任务
            task_planner = self.agents.get("task_planner")
            if not task_planner:
                logger.error("Task planner not available")
                return None
            
            task_plan = task_planner.plan(goal, context)
            plan_id = f"plan_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"
            
            logger.info(f"Task planned: {plan_id} with {len(task_plan.subtasks)} subtasks")
            
            return plan_id
            
        except Exception as e:
            logger.error(f"Failed to execute task: {e}")
            return None
    
    def get_execution_status(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """获取执行状态"""
        execution_engine = self.agents.get("execution_engine")
        if not execution_engine:
            return None
        
        return execution_engine.get_execution_status(plan_id)
    
    def pause_execution(self, plan_id: str):
        """暂停执行"""
        execution_engine = self.agents.get("execution_engine")
        if execution_engine:
            execution_engine.pause_execution(plan_id)
    
    def resume_execution(self, plan_id: str):
        """恢复执行"""
        execution_engine = self.agents.get("execution_engine")
        if execution_engine:
            execution_engine.resume_execution(plan_id)
    
    def cancel_execution(self, plan_id: str):
        """取消执行"""
        execution_engine = self.agents.get("execution_engine")
        if execution_engine:
            execution_engine.cancel_execution(plan_id)
    
    def get_dashboard_stats(self) -> Optional[Dict[str, Any]]:
        """获取仪表盘统计"""
        dashboard = self.agents.get("dashboard")
        if not dashboard:
            return None
        
        return dashboard.get_system_stats()
    
    def get_event_history(self, limit: Optional[int] = None) -> Optional[List[Dict[str, Any]]]:
        """获取事件历史"""
        dashboard = self.agents.get("dashboard")
        if not dashboard:
            return None
        
        return dashboard.get_event_history(limit)
    
    def run_interactive_mode(self):
        """运行交互模式"""
        print("🤖 双环AI系统交互模式")
        print("输入 'help' 查看可用命令")
        print("输入 'quit' 退出")
        
        while self.running:
            try:
                command = input("\n> ").strip().lower()
                
                if command == "quit" or command == "exit":
                    break
                elif command == "help":
                    self._print_help()
                elif command == "status":
                    self._print_status()
                elif command.startswith("execute "):
                    goal = command[8:].strip()
                    if goal:
                        plan_id = self.execute_task(goal)
                        if plan_id:
                            print(f"任务已规划，计划ID: {plan_id}")
                        else:
                            print("任务执行失败")
                elif command.startswith("status "):
                    plan_id = command[7:].strip()
                    status = self.get_execution_status(plan_id)
                    if status:
                        print(f"执行状态: {json.dumps(status, indent=2, ensure_ascii=False)}")
                    else:
                        print("未找到执行计划")
                elif command == "stats":
                    stats = self.get_dashboard_stats()
                    if stats:
                        print(f"系统统计: {json.dumps(stats, indent=2, ensure_ascii=False)}")
                    else:
                        print("无法获取统计信息")
                elif command == "events":
                    events = self.get_event_history(10)
                    if events:
                        for event in events:
                            print(f"{event['timestamp']} - {event['event_type']} (来自: {event['source_agent']})")
                    else:
                        print("无事件历史")
                else:
                    print("未知命令，输入 'help' 查看可用命令")
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"错误: {e}")
    
    def _print_help(self):
        """打印帮助信息"""
        print("\n可用命令:")
        print("  help                    - 显示此帮助信息")
        print("  status                  - 显示系统状态")
        print("  execute <goal>          - 执行任务")
        print("  status <plan_id>        - 查看执行状态")
        print("  stats                   - 显示系统统计")
        print("  events                  - 显示最近事件")
        print("  quit/exit               - 退出系统")
    
    def _print_status(self):
        """打印系统状态"""
        print(f"\n系统状态:")
        print(f"  运行状态: {'运行中' if self.running else '已停止'}")
        print(f"  代理数量: {len(self.agents)}")
        
        agent_statuses = self.get_all_agent_statuses()
        for agent_name, status in agent_statuses.items():
            if status:
                running = "运行中" if status.get("running", False) else "已停止"
                print(f"    {agent_name}: {running}")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="双环AI系统")
    parser.add_argument("--config", help="配置文件路径")
    parser.add_argument("--interactive", action="store_true", help="运行交互模式")
    parser.add_argument("--goal", help="要执行的目标")
    parser.add_argument("--daemon", action="store_true", help="以守护进程模式运行")
    
    args = parser.parse_args()
    
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 创建主控制器
    controller = MainController(args.config)
    
    try:
        # 启动系统
        controller.start()
        
        if args.goal:
            # 执行指定目标
            plan_id = controller.execute_task(args.goal)
            if plan_id:
                print(f"任务已规划，计划ID: {plan_id}")
            else:
                print("任务执行失败")
                sys.exit(1)
        
        if args.interactive:
            # 运行交互模式
            controller.run_interactive_mode()
        elif args.daemon:
            # 守护进程模式
            print("系统以守护进程模式运行...")
            while True:
                time.sleep(1)
        else:
            # 默认模式，运行一段时间后退出
            print("系统运行中，按 Ctrl+C 退出...")
            while True:
                time.sleep(1)
                
    except KeyboardInterrupt:
        print("\n正在关闭系统...")
    finally:
        controller.stop()


if __name__ == "__main__":
    main()
