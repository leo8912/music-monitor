"""
数据库迁移脚本 - 执行迁移
作者: GOOGLE
"""

import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from sqlalchemy import create_engine
from app.models.metadata import upgrade, downgrade

if __name__ == "__main__":
    engine = create_engine('sqlite:///music_monitor.db')
    
    print("="*80)
    print("🚀 执行数据库迁移")
    print("="*80)
    
    try:
        upgrade(engine)
        print("\n✅ 迁移成功完成!")
    except Exception as e:
        print(f"\n❌ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
