#!/usr/bin/env python3
"""
双环AI系统启动脚本
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dual_ring_ai.main_controller import main

if __name__ == "__main__":
    main()
