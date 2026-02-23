import os
import re
import json
import requests
import subprocess
import sys
from pathlib import Path
from packaging import version


# 获取当前脚本所在目录
CURRENT_DIR = Path(__file__).parent
PROJECT_ROOT = CURRENT_DIR.parent

# 目录结构设计
DATA_DIR = CURRENT_DIR / 'data'  # 存放原始数据
APIS_DIR = CURRENT_DIR / 'apis'  # 存放处理后的API文档
CACHE_DIR = CURRENT_DIR / 'cache'  # 存放缓存文件
DOCS_DIR = CURRENT_DIR / 'docs'  # 存放生成的文档

# 文件路径配置
SOURCE_FILE_PATH = DATA_DIR / 'stock.md.txt'
MANIFEST_FILE_PATH = APIS_DIR / 'manifest.json'
API_DOC_URL = 'https://akshare.akfamily.xyz/_sources/data/stock/stock.md.txt'

def extract_info(api_block_content):
    interface_name = None
    description = None

    # Extract interface name (already implicitly handled by splitting, but good for clarity)
    # The block content starts with the interface name after "接口: "
    # We will re-add "接口: " when saving the file
    # For manifest, we need the raw name
    if api_block_content.strip():
        first_line = api_block_content.strip().split('\n')[0]
        interface_name = first_line.strip()

    # Extract description
    description_match = re.search(r"描述:\s*(.*?)(?:\n\n|$)", api_block_content, re.DOTALL)
    if description_match:
        description = description_match.group(1).strip()
    
    return interface_name, description

def download_api_doc(url, destination_path):
    """
    下载API文档文件
    
    Args:
        url (str): 下载链接
        destination_path (Path): 目标文件路径
    
    Returns:
        bool: 下载是否成功
    """
    try:
        print(f"正在从 {url} 下载文件...")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # 确保目标目录存在
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(destination_path, 'w', encoding='utf-8') as f:
            f.write(response.text)
        print(f"文件已成功下载并保存到 {destination_path}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"错误：下载文件失败。URL: {url}, 错误: {e}")
        return False
    except IOError as e:
        print(f"错误：保存文件失败。路径: {destination_path}, 错误: {e}")
        return False

def ensure_directories():
    """
    确保所有必要的目录存在
    """
    directories = [DATA_DIR, APIS_DIR, CACHE_DIR, DOCS_DIR]
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        print(f"确保目录存在: {directory}")


def process_api_docs():
    """
    处理API文档的主函数
    
    1. 确保目录结构存在
    2. 下载API文档文件
    3. 解析并分割API文档
    4. 生成单独的API文件和清单文件
    """
    print("开始处理akshare API文档...")
    
    # 确保目录结构存在
    ensure_directories()
    
    # 下载API文档文件
    if not download_api_doc(API_DOC_URL, SOURCE_FILE_PATH):
        print("由于下载失败，处理中止。")
        return False

    if not SOURCE_FILE_PATH.exists():
        print(f"错误：源文件 {SOURCE_FILE_PATH} 未找到（即使在尝试下载后）。")
        return False

    manifest_data = []

    with open(SOURCE_FILE_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split the content by "接口: " to get individual API blocks.
    # The first element of the split might be empty or content before the first API, so we skip it if it's trivial.
    api_blocks_raw = content.split('\n接口: ')
    
    actual_api_blocks = []
    if api_blocks_raw:
        # Handle the first block if it starts with "接口:" at the very beginning of the file
        if content.startswith('接口:'):
            # Prepend the first part of the split to the second, effectively undoing the split for the first item
            # if api_blocks_raw[0] was just "接口:" and api_blocks_raw[1] was the rest of the first API block.
            # A simpler way is to adjust the split or handle the first block carefully.
            # Let's assume the first block after split (if not empty) is the content *after* the first "接口: "
            if api_blocks_raw[0].strip().startswith('stock_'): # Heuristic: if it looks like an interface name
                 actual_api_blocks.append(api_blocks_raw[0])
            if len(api_blocks_raw) > 1:
                actual_api_blocks.extend(api_blocks_raw[1:])
        elif len(api_blocks_raw) > 1: # If the file doesn't start with "接口:", the first part is preamble
            actual_api_blocks.extend(api_blocks_raw[1:])
        elif api_blocks_raw[0] and not content.startswith('接口:'): # Only one block, and no leading "接口:" in file
            # This case is unlikely given the problem description but good to be aware of.
            # For now, we assume valid blocks are always preceded by "接口: "
            pass # Or handle as an error/special case


    for i, block_content_after_marker in enumerate(actual_api_blocks):
        if not block_content_after_marker.strip():
            continue

        # The block_content_after_marker is the text *after* "接口: "
        # For saving, we prepend "接口: "
        full_api_block_text = "接口: " + block_content_after_marker

        interface_name, description = extract_info(block_content_after_marker)

        if not interface_name:
            print(f"警告：在第 {i+1} 个块中未找到接口名称。块内容：\n{block_content_after_marker[:100]}...")
            continue
        
        if not description:
            print(f"警告：在接口 {interface_name} 中未找到描述。")
            # We might still want to save the file and add to manifest with null/empty description

        # 清理接口名称用作文件名
        filename = f"{interface_name.replace('/', '_').replace(' ', '_')}.txt"
        file_path = APIS_DIR / filename

        try:
            with open(file_path, 'w', encoding='utf-8') as api_file:
                api_file.write(full_api_block_text.strip() + '\n')
            print(f"已保存接口 {interface_name} 到 {file_path}")
        except IOError as e:
            print(f"错误：无法写入文件 {file_path}。错误：{e}")
            continue

        manifest_data.append({
            "file": filename,
            "interface_name": interface_name,
            "description": description if description else "",
            "file_path": str(file_path.relative_to(PROJECT_ROOT))
        })

    # 保存清单文件
    try:
        with open(MANIFEST_FILE_PATH, 'w', encoding='utf-8') as mf:
            json.dump(manifest_data, mf, ensure_ascii=False, indent=4)
        print(f"清单文件已保存到 {MANIFEST_FILE_PATH}")
        print(f"共处理了 {len(manifest_data)} 个API接口")
        return True
    except IOError as e:
        print(f"错误：无法写入清单文件 {MANIFEST_FILE_PATH}。错误：{e}")
        return False

def get_installed_akshare_version():
    """
    获取当前安装的akshare版本
    
    Returns:
        str: 当前安装的版本号，如果未安装则返回None
    """
    try:
        import akshare_docs
        return akshare_docs.__version__
    except ImportError:
        return None
    except AttributeError:
        # 如果没有__version__属性，尝试通过pip show获取
        try:
            result = subprocess.run([sys.executable, '-m', 'pip', 'show', 'akshare'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if line.startswith('Version:'):
                        return line.split(':')[1].strip()
        except Exception:
            pass
        return None

def clean_old_files():
    """
    清理旧的API文件
    """
    if APIS_DIR.exists():
        for file_path in APIS_DIR.glob('*.txt'):
            file_path.unlink()
        print(f"已清理旧的API文件")


def generate_summary():
    """
    生成处理摘要
    """
    if MANIFEST_FILE_PATH.exists():
        with open(MANIFEST_FILE_PATH, 'r', encoding='utf-8') as f:
            manifest_data = json.load(f)
        
        from datetime import datetime
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 获取akshare版本信息
        akshare_version = get_installed_akshare_version()
        akshare_version_info = f"v{akshare_version}" if akshare_version else "未安装"
        
        summary_path = DOCS_DIR / 'summary.md'
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write("# AkShare API 文档摘要\n\n")
            f.write(f"**更新时间**: {current_time}\n\n")
            f.write(f"**总计API数量**: {len(manifest_data)}\n\n")
            f.write(f"**数据源**: {API_DOC_URL}\n\n")
            f.write(f"**AkShare库版本**: {akshare_version_info}\n\n")
            f.write("## 目录结构\n\n")
            f.write("```\n")
            f.write("akshare/\n")
            f.write("├── data/          # 原始数据文件\n")
            f.write("├── apis/          # 处理后的API文档\n")
            f.write("├── cache/         # 缓存文件\n")
            f.write("├── docs/          # 生成的文档\n")
            f.write("└── apis_update.py # 更新脚本\n")
            f.write("```\n\n")
            f.write("## API接口列表\n\n")
            
            for i, api in enumerate(manifest_data, 1):
                f.write(f"{i}. **{api['interface_name']}**\n")
                f.write(f"   - 描述: {api['description'] or '暂无描述'}\n")
                f.write(f"   - 文件: `{api['file']}`\n\n")
        
        print(f"摘要文件已生成: {summary_path}")


def main():
    """
    主函数
    """
    print("=" * 50)
    print("AkShare API 文档更新工具")
    print("=" * 50)
    
    # 清理旧文件
    clean_old_files()
    
    # 处理API文档
    success = process_api_docs()
    
    if success:
        # 生成摘要
        generate_summary()
        print("\n✅ API文档更新完成！")
        return True
    else:
        print("\n❌ API文档更新失败！")
        return False
    
    print("=" * 50)


if __name__ == '__main__':
    main()