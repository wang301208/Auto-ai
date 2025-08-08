#!/usr/bin/env python3
"""
双环AI系统测试脚本
"""

import sys
import os
import time
import json
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dual_ring_ai.main_controller import MainController
from dual_ring_ai.core.event_bus import EventBus, EventTypes

def test_event_bus():
    """测试事件总线"""
    print("🔧 测试事件总线...")
    
    event_bus = EventBus()
    if not event_bus.connect():
        print("❌ 事件总线连接失败")
        return False
    
    print("✅ 事件总线连接成功")
    return True

def test_librarian():
    """测试图书管理员"""
    print("📚 测试图书管理员...")
    
    try:
        from dual_ring_ai.core.librarian import Librarian
        
        librarian = Librarian()
        skills = librarian.skills
        plugins = librarian.plugins
        
        print(f"✅ 图书管理员初始化成功")
        print(f"   技能数量: {len(skills)}")
        print(f"   插件数量: {len(plugins)}")
        return True
    except Exception as e:
        print(f"❌ 图书管理员测试失败: {e}")
        return False

def test_agents():
    """测试代理初始化"""
    print("🤖 测试代理初始化...")
    
    try:
        controller = MainController()
        agent_count = len(controller.agents)
        
        print(f"✅ 代理初始化成功")
        print(f"   代理数量: {agent_count}")
        
        for agent_name, agent in controller.agents.items():
            print(f"   - {agent_name}: {type(agent).__name__}")
        
        return True
    except Exception as e:
        print(f"❌ 代理初始化失败: {e}")
        return False

def test_task_execution():
    """测试任务执行"""
    print("🚀 测试任务执行...")
    
    try:
        controller = MainController()
        controller.start()
        
        # 等待系统启动
        time.sleep(2)
        
        # 执行简单任务
        goal = "创建一个简单的Hello World技能"
        plan_id = controller.execute_task(goal)
        
        if plan_id:
            print(f"✅ 任务执行成功")
            print(f"   计划ID: {plan_id}")
            
            # 等待一段时间让任务执行
            time.sleep(5)
            
            # 检查执行状态
            status = controller.get_execution_status(plan_id)
            if status:
                print(f"   执行状态: {status.get('status', 'unknown')}")
                print(f"   进度: {status.get('progress', 0):.1%}")
        else:
            print("❌ 任务执行失败")
            return False
        
        controller.stop()
        return True
    except Exception as e:
        print(f"❌ 任务执行测试失败: {e}")
        return False

def test_dashboard():
    """测试仪表盘"""
    print("📊 测试仪表盘...")
    
    try:
        from dual_ring_ai.dashboard.monitor import Dashboard, DEFAULT_DASHBOARD_CONFIG
        
        event_bus = EventBus()
        event_bus.connect()
        
        dashboard = Dashboard(event_bus, DEFAULT_DASHBOARD_CONFIG)
        dashboard.start()
        
        # 发布一些测试事件
        event_bus.publish(
            EventTypes.SYSTEM_STARTED,
            {"test": True, "timestamp": datetime.utcnow().isoformat()},
            "test_script"
        )
        
        time.sleep(2)
        
        # 获取统计信息
        stats = dashboard.get_system_stats()
        if stats:
            print(f"✅ 仪表盘测试成功")
            print(f"   总事件数: {stats.get('total_events', 0)}")
        else:
            print("❌ 无法获取仪表盘统计")
            return False
        
        dashboard.stop()
        return True
    except Exception as e:
        print(f"❌ 仪表盘测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🧪 双环AI系统测试开始")
    print("=" * 50)
    
    tests = [
        ("事件总线", test_event_bus),
        ("图书管理员", test_librarian),
        ("代理初始化", test_agents),
        ("任务执行", test_task_execution),
        ("仪表盘", test_dashboard)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 测试: {test_name}")
        print("-" * 30)
        
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} 测试通过")
            else:
                print(f"❌ {test_name} 测试失败")
        except Exception as e:
            print(f"❌ {test_name} 测试异常: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！系统可以正常运行。")
        return True
    else:
        print("⚠️  部分测试失败，请检查配置和依赖项。")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
