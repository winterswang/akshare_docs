import json
import re
from pathlib import Path

# 配置路径
CURRENT_DIR = Path(__file__).parent
APIS_DIR = CURRENT_DIR / 'apis'
MANIFEST_FILE = APIS_DIR / 'manifest.json'
OUTPUT_FILE = CURRENT_DIR / 'docs' / 'skills.json'

def parse_table_row(row_line):
    """解析 Markdown 表格行"""
    parts = [p.strip() for p in row_line.split('|')]
    # Markdown 表格行通常以 | 开头和结尾，所以 split 后首尾是空字符串
    # 例如 "| name | type | desc |" -> ["", "name", "type", "desc", ""]
    if len(parts) >= 5:
        return parts[1], parts[2], parts[3] # name, type, desc
    return None, None, None

def map_type(py_type):
    """将 Python 类型映射到 JSON Schema 类型"""
    py_type = py_type.lower()
    if 'int' in py_type:
        return 'integer'
    elif 'float' in py_type:
        return 'number'
    elif 'bool' in py_type:
        return 'boolean'
    elif 'str' in py_type:
        return 'string'
    else:
        return 'string' # 默认

def extract_enum(description):
    """从描述中提取枚举值"""
    # 匹配 "choice of {'a', 'b'}" 或 "choice of {1, 2}"
    match = re.search(r"choice of \{([^}]+)\}", description)
    if match:
        content = match.group(1)
        # 处理引号
        items = []
        for item in content.split(','):
            item = item.strip()
            # 去除引号
            if (item.startswith("'") and item.endswith("'")) or (item.startswith('"') and item.endswith('"')):
                items.append(item[1:-1])
            else:
                # 尝试转数字
                try:
                    if '.' in item:
                        items.append(float(item))
                    else:
                        items.append(int(item))
                except ValueError:
                    items.append(item)
        return items
    return None

def parse_api_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.split('\n')
    
    description = ""
    parameters = {}
    required_params = []
    
    # 提取描述 (从文件头部)
    for line in lines:
        if line.startswith("描述:"):
            description = line.replace("描述:", "").strip()
            break
            
    # 解析输入参数
    in_input_section = False
    in_table = False
    
    for i, line in enumerate(lines):
        line = line.strip()
        if line == "输入参数":
            in_input_section = True
            continue
        
        if in_input_section:
            if line.startswith("|") and "名称" in line and "类型" in line:
                in_table = True
                continue
            if in_table and line.startswith("|") and "---" in line:
                continue
            
            if in_table and line.startswith("|"):
                name, p_type, desc = parse_table_row(line)
                if name and name != "-" and name != "名称":
                    # 处理参数名
                    param_name = name.strip()
                    param_type = map_type(p_type)
                    param_desc = desc.strip()
                    
                    param_info = {
                        "type": param_type,
                        "description": param_desc
                    }
                    
                    # 尝试提取枚举
                    enums = extract_enum(param_desc)
                    if enums:
                        param_info["enum"] = enums
                        
                    parameters[param_name] = param_info
                    
                    # 简单推断 required: 如果描述中包含 '='，假设有默认值，否则假设必填
                    # 这是一个启发式规则，可能不完全准确
                    if "=" not in param_desc and "默认" not in param_desc:
                         # 很多时候描述里会有 symbol='xxx' 这种示例，也包含 =
                         # 所以这个规则很弱。
                         # 改进：如果描述里有 "default" 或者 "默认"，则可选。
                         # 或者如果描述里是 "symbol='xxx'" 这种格式，通常意味着这是必须传的（作为示例），或者是有默认值？
                         # 在 akshare 文档中， symbol='xxx' 通常是示例值。
                         # 让我们保守一点，默认都是 optional，除非我们非常确定。
                         # 或者反过来，默认都是 required，除非有 "默认" 字样。
                         pass
            
            # 退出表格
            if in_table and not line.startswith("|") and line:
                in_input_section = False
                in_table = False

    # 构建 tool definition
    tool_def = {
        "type": "function",
        "function": {
            "description": description,
            "parameters": {
                "type": "object",
                "properties": parameters,
                "required": [] # 暂时留空，让大模型自己判断或都传
            }
        }
    }
    
    return tool_def

def main():
    if not MANIFEST_FILE.exists():
        print(f"Error: Manifest file not found at {MANIFEST_FILE}")
        return

    with open(MANIFEST_FILE, 'r', encoding='utf-8') as f:
        manifest = json.load(f)

    skills = []
    
    print(f"Found {len(manifest)} APIs in manifest.")
    
    for api in manifest:
        interface_name = api['interface_name']
        file_path = APIS_DIR / api['file']
        
        if not file_path.exists():
            print(f"Warning: File not found for {interface_name}: {file_path}")
            continue
            
        try:
            tool_def = parse_api_file(file_path)
            # 设置函数名
            tool_def['function']['name'] = interface_name
            skills.append(tool_def)
        except Exception as e:
            print(f"Error parsing {interface_name}: {e}")

    # 确保输出目录存在
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(skills, f, ensure_ascii=False, indent=2)
        
    print(f"Successfully generated skills for {len(skills)} APIs at {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
