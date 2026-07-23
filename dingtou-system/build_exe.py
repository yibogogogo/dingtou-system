"""
量化定投择时系统 - PyInstaller打包
运行: python build_exe.py
"""
import PyInstaller.__main__
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.dirname(BASE_DIR)

# 分离符 (Windows: ;)
SEP = ';'

args = [
    '--name=量化定投择时系统',
    '--onedir',
    '--console',
    '--clean',
    '--noconfirm',
    '--log-level=WARN',

    # 入口
    os.path.join(BASE_DIR, 'run_app.py'),

    # 源代码和数据
    f'--add-data={BASE_DIR}/app.py{SEP}.',
    f'--add-data={BASE_DIR}/config.py{SEP}.',
    f'--add-data={BASE_DIR}/engine{SEP}engine',
    f'--add-data={BASE_DIR}/data{SEP}data',
    f'--add-data={BASE_DIR}/ui{SEP}ui',

    # Excel数据文件
    f'--add-data={PARENT}/000688perf科创50.xlsx{SEP}.',
    f'--add-data={PARENT}/000922perf中证红利.xlsx{SEP}.',
    f'--add-data={PARENT}/H30269perf红利低波.xlsx{SEP}.',

    # 打包关键模块
    '--collect-all=streamlit',
    '--collect-submodules=streamlit',
    '--collect-all=plotly',
    '--collect-all=pandas',
    '--collect-all=numpy',
    '--collect-all=openpyxl',
    '--collect-all=altair',

    # 隐藏导入
    '--hidden-import=akshare',
    '--hidden-import=requests',
    '--hidden-import=json',
    '--hidden-import=pickle',
    '--hidden-import=hashlib',
    '--hidden-import=re',
    '--hidden-import=pyarrow',
    '--hidden-import=tzdata',
    '--hidden-import=scipy',
    '--hidden-import=sklearn',
    '--hidden-import=PIL',
    '--hidden-import=watchdog',
    '--hidden-import=tornado',
    '--hidden-import=blinker',
    '--hidden-import=packaging',
    '--hidden-import=yaml',
    '--hidden-import=toml',
    '--hidden-import=rich',
    '--hidden-import=gitpython',
    '--hidden-import=pydeck',
    '--hidden-import=tenacity',
    '--hidden-import=cachetools',
    '--hidden-import=click',
    '--hidden-import=jinja2',
    '--hidden-import=attrs',
    '--hidden-import=referencing',
    '--hidden-import=jsonschema',
    '--hidden-import=jsonschema_specifications',

    # 排除不需要的模块（减小体积）
    '--exclude-module=tkinter',
    '--exclude-module=matplotlib',
    '--exclude-module=IPython',
    '--exclude-module=jupyter',
    '--exclude-module=notebook',
    '--exclude-module=sqlalchemy',
    '--exclude-module=pytest',
    '--exclude-module=setuptools',
    '--exclude-module=pip',
]

print("=" * 60)
print("  开始打包...")
print(f"  源目录: {BASE_DIR}")
print(f"  输出: {os.path.join(BASE_DIR, 'dist')}")
print("=" * 60)
print()

PyInstaller.__main__.run(args)

print()
print("=" * 60)
print("  打包完成!")
print(f"  输出: {os.path.join(BASE_DIR, 'dist', '量化定投择时系统')}")
print("=" * 60)
