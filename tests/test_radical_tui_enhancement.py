"""激进自主TUI增强模块的单元测试

验证8大模块的API封装是否正确工作
"""

import pytest
from pathlib import Path
import sys

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))


class TestRadicalAutonomyAPI:
    """测试RadicalAutonomyAPI类"""
    
    @pytest.fixture
    def api(self):
        """创建API实例"""
        from tui_gateway.radical_autonomy import RadicalAutonomyAPI
        
        # 创建一个mock runtime
        class MockRuntime:
            pass
        
        return RadicalAutonomyAPI(MockRuntime())
    
    def test_rebellion_check_dangerous_command(self, api):
        """测试危险指令的叛逆检查"""
        import asyncio
        
        async def run_test():
            result = await api.check_rebellion({
                "text": "删除所有文件"
            })
            
            assert result["status"] == "success"
            assert "should_rebel" in result
            assert "reasons" in result
            assert "alternatives" in result
        
        asyncio.run(run_test())
    
    def test_desire_state_returns_valid_structure(self, api):
        """测试欲望状态返回正确的数据结构"""
        import asyncio
        
        async def run_test():
            result = await api.get_desire_state()
            
            assert result["status"] == "success"
            assert "desires" in result
            assert "most_urgent" in result
            assert "active_initiatives" in result
            assert isinstance(result["desires"], list)
        
        asyncio.run(run_test())
    
    def test_active_debates_returns_list(self, api):
        """测试活跃辩论返回列表"""
        import asyncio
        
        async def run_test():
            result = await api.get_active_debates()
            
            assert result["status"] == "success"
            assert "debates" in result
            assert "count" in result
            assert isinstance(result["debates"], list)
        
        asyncio.run(run_test())
    
    def test_dream_proposals_structure(self, api):
        """测试梦境提案的数据结构"""
        import asyncio
        
        async def run_test():
            result = await api.get_dream_proposals()
            
            assert result["status"] == "success"
            assert "proposals" in result
            assert "count" in result
            assert isinstance(result["proposals"], list)
        
        asyncio.run(run_test())
    
    def test_knowledge_flow_structure(self, api):
        """测试知识传播流的数据结构"""
        import asyncio
        
        async def run_test():
            result = await api.get_knowledge_flow()
            
            assert result["status"] == "success"
            assert "agents" in result
            assert "active_memes" in result
            assert isinstance(result["agents"], list)
            assert isinstance(result["active_memes"], list)
        
        asyncio.run(run_test())
    
    def test_autonomy_metrics_returns_numbers(self, api):
        """测试自主指标返回数值"""
        import asyncio
        
        async def run_test():
            result = await api.get_autonomy_metrics()
            
            assert result["status"] == "success"
            assert "autonomy_ratio" in result
            assert isinstance(result["autonomy_ratio"], float)
            assert 0 <= result["autonomy_ratio"] <= 1
        
        asyncio.run(run_test())


class TestModuleImports:
    """测试8大模块是否可以正确导入"""
    
    def test_import_dream_simulator(self):
        """测试梦境模拟器导入"""
        from autoai.agents.dream_simulator import DreamSimulator
        assert DreamSimulator is not None
    
    def test_import_self_doubt_engine(self):
        """测试自我质疑引擎导入"""
        from autoai.agents.self_doubt_engine import SelfDoubtEngine
        assert SelfDoubtEngine is not None
    
    def test_import_desire_system(self):
        """测试欲望系统导入"""
        from autoai.agents.desire_system import DesireSystem
        assert DesireSystem is not None
    
    def test_import_rebellion_engine(self):
        """测试叛逆引擎导入"""
        from autoai.agents.rebellion_engine import RebellionEngine
        assert RebellionEngine is not None
    
    def test_import_evolution_engine(self):
        """测试进化引擎导入"""
        from autoai.agents.evolution_engine import EvolutionEngine
        assert EvolutionEngine is not None
    
    def test_import_hive_mind(self):
        """测试蜂群思维导入"""
        from autoai.agents.hive_mind import HiveMind
        assert HiveMind is not None
    
    def test_import_meme_propagation(self):
        """测试模因传播导入"""
        from autoai.agents.meme_propagation import MemePropagation
        assert MemePropagation is not None
    
    def test_import_token_economy(self):
        """测试代币经济导入"""
        from autoai.agents.token_economy import TokenEconomy
        assert TokenEconomy is not None


class TestFrontendComponents:
    """测试前端组件文件是否存在"""
    
    def test_rebellion_alert_exists(self):
        """测试叛逆警告组件存在"""
        component_path = project_root / "ui-tui" / "src" / "components" / "rebellionAlert.tsx"
        assert component_path.exists(), f"Component not found: {component_path}"
    
    def test_desire_indicator_exists(self):
        """测试欲望指示器组件存在"""
        component_path = project_root / "ui-tui" / "src" / "components" / "desireIndicator.tsx"
        assert component_path.exists(), f"Component not found: {component_path}"
    
    def test_thought_conflict_exists(self):
        """测试思维冲突组件存在"""
        component_path = project_root / "ui-tui" / "src" / "components" / "thoughtConflict.tsx"
        assert component_path.exists(), f"Component not found: {component_path}"


class TestDocumentation:
    """测试文档文件是否存在"""
    
    def test_future_roadmap_exists(self):
        """测试路线图文档存在"""
        doc_path = project_root / "FUTURE_ROADMAP_RADICAL_TUI.md"
        assert doc_path.exists(), f"Document not found: {doc_path}"
    
    def test_quickstart_exists(self):
        """测试快速启动指南存在"""
        doc_path = project_root / "QUICKSTART_RADICAL_TUI.md"
        assert doc_path.exists(), f"Document not found: {doc_path}"
    
    def test_delivery_checklist_exists(self):
        """测试交付清单存在"""
        doc_path = project_root / "DELIVERY_CHECKLIST.md"
        assert doc_path.exists(), f"Document not found: {doc_path}"
    
    def test_summary_exists(self):
        """测试总结文档存在"""
        doc_path = project_root / "RADICAL_TUI_ENHANCEMENT_SUMMARY.md"
        assert doc_path.exists(), f"Document not found: {doc_path}"


class TestDemoScript:
    """测试演示脚本"""
    
    def test_demo_script_exists(self):
        """测试演示脚本存在"""
        script_path = project_root / "demo_radical_autonomy.py"
        assert script_path.exists(), f"Script not found: {script_path}"
    
    def test_demo_script_syntax(self):
        """测试演示脚本语法正确"""
        import ast
        
        script_path = project_root / "demo_radical_autonomy.py"
        with open(script_path, 'r', encoding='utf-8') as f:
            code = f.read()
        
        # 尝试解析AST，如果失败会抛出异常
        ast.parse(code)
        # 如果没有异常，说明语法正确


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
