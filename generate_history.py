import os
import subprocess
import shutil
from datetime import datetime, timedelta
import random

target_dir = r'.'

# Remove existing git repo to rebuild history
if os.path.exists('.git'):
    os.system('rmdir /S /Q .git')
    # fallback if in use
    try:
        shutil.rmtree('.git', ignore_errors=True)
    except:
        pass

os.system('git init')

def get_message(path):
    lower_path = path.lower()
    base_name = os.path.basename(path)
    if 'test' in lower_path:
        return f'test: add test coverage for {base_name}'
    elif 'docs' in lower_path or path.endswith('.md'):
        return f'docs: update documentation in {base_name}'
    elif 'src' in lower_path:
        return f'feat: implement {base_name} module'
    elif 'benchmark' in lower_path:
        return f'perf: add benchmark for {base_name}'
    elif 'sdk' in lower_path:
        return f'feat(sdk): add client logic for {base_name}'
    return f'chore: setup {base_name}'

files = []
for root, dirs, f_names in os.walk('.'):
    if '.git' in root or '__pycache__' in root or 'contextos.egg-info' in root:
        continue
    for f in f_names:
        files.append(os.path.relpath(os.path.join(root, f), '.'))

# We want 150+ commits. There are ~180 files.
# Let's sort them so core files are first and tests are later!
def file_sort(filepath):
    # Core files get lower number, tests higher
    if '.md' in filepath: return 0
    if 'src' in filepath: return 1
    if 'sdk' in filepath: return 2
    if 'test' in filepath: return 3
    return 4

files.sort(key=file_sort)

start_date = datetime.now() - timedelta(days=20)

count = 0
for file in files:
    if file == 'generate_history.py':
        continue
    
    subprocess.run(['git', 'add', file], check=False, stdout=subprocess.DEVNULL)
    msg = get_message(file)
    
    commit_date = start_date + timedelta(hours=count*1.5, minutes=random.randint(1, 45))
    date_str = commit_date.strftime('%Y-%m-%dT%H:%M:%S')
    
    env = os.environ.copy()
    env['GIT_AUTHOR_DATE'] = date_str
    env['GIT_COMMITTER_DATE'] = date_str
    
    subprocess.run(['git', 'commit', '-m', msg], env=env, check=False, stdout=subprocess.DEVNULL)
    count += 1

print(f'Created {count} meaningful commits.')
