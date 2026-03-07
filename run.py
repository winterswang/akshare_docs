#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AkShare API 文档工具

功能:
1. 下载并更新 AkShare API 文档
2. 生成 Agent 能够使用的 Skills 定义 (JSON Schema)

使用方法:
    python run.py
"""

import sys
import importlib.util

def check_dependencies():
    """检查必要的依赖包"""
    required = ['requests', 'packaging', 'akshare']
    missing = []
    
    for package in required:
        if importlib.util.find_spec(package) is None:
            missing.append(package)
    
    if missing:
        print(f"❌ 缺少必要的依赖包: {', '.join(missing)}")
        print("请运行以下命令安装:")
        print(f"pip install -r requirements.txt")
        return False
    return True

def main():
    if not check_dependencies():
        sys.exit(1)

    print("🚀 开始更新 AkShare API 文档...")
    
    # 导入处理模块
    try:
        from scripts import apis_update
        from scripts import generate_skills
    except ImportError as e:
        print(f"❌ 导入模块失败: {e}")
        sys.exit(1)

    # 1. 更新 API 文档
    print("\n[1/2] 更新 API 文档...")
    success = apis_update.main()
    
    if not success:
        print("❌ API 文档更新失败，停止执行。")
        sys.exit(1)

    # 2. 生成 Skills 定义
    print("\n[2/2] 生成 Skills 定义...")
    try:
        generate_skills.main()
        print("✅ Skills 定义生成完成")
    except Exception as e:
        print(f"❌ 生成 Skills 定义失败: {e}")
        sys.exit(1)

    print("\n🎉 所有任务已完成！")
    print("文档位置: apis/")
    print("Skills定义: docs/skills.json")

if __name__ == '__main__':
    main()
