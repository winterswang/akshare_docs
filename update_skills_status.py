import json
import os

RESULTS_FILE = '/Users/wangguangchao/code/langchain_financial/akshare_docs/api_test_results.json'
SKILLS_FILE = '/Users/wangguangchao/code/langchain_financial/akshare_docs/docs/skills.json'

def update_skills():
    if not os.path.exists(RESULTS_FILE) or not os.path.exists(SKILLS_FILE):
        print("Files not found.")
        return

    with open(RESULTS_FILE, 'r', encoding='utf-8') as f:
        results = json.load(f)

    with open(SKILLS_FILE, 'r', encoding='utf-8') as f:
        skills = json.load(f)

    failed_interfaces = {name for name, res in results.items() if res['status'] == 'failed_max_retries'}
    print(f"Found {len(failed_interfaces)} failed interfaces.")

    updated_count = 0
    for skill in skills:
        func_name = skill.get('function', {}).get('name')
        if func_name in failed_interfaces:
            description = skill['function'].get('description', '')
            if "[UNAVAILABLE]" not in description:
                skill['function']['description'] = f"[UNAVAILABLE] {description}"
                updated_count += 1
    
    with open(SKILLS_FILE, 'w', encoding='utf-8') as f:
        json.dump(skills, f, ensure_ascii=False, indent=2)
    
    print(f"Updated {updated_count} skills in {SKILLS_FILE}.")

if __name__ == "__main__":
    update_skills()
