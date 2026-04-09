#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
微博情感分析系统 - 项目优化脚本
================================

功能：
1. 自动识别冗余文件
2. 统计代码重复率
3. 检查未使用的导入
4. 生成优化报告
5. 提供一键清理选项

使用方法：
    python project_optimizer.py --mode report    # 只读模式（仅报告）
    python project_optimizer.py --mode interactive  # 交互模式
    python project_optimizer.py --mode auto      # 自动模式

作者：毕业设计
日期：2026-01
"""

import os
import sys
import re
import json
import argparse
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Set, Tuple, Any
from collections import defaultdict
import ast

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent


class CodeAnalyzer:
    """代码分析器"""
    
    def __init__(self, project_root: Path):
        self.root = project_root
        self.results = {
            'redundant_files': [],
            'empty_files': [],
            'unused_imports': [],
            'duplicate_code': [],
            'large_files': [],
            'stats': {}
        }
    
    def analyze(self) -> Dict:
        """执行完整分析"""
        print("🔍 开始项目分析...")
        
        self._find_redundant_files()
        self._find_empty_files()
        self._analyze_imports()
        self._calculate_stats()
        
        return self.results
    
    def _find_redundant_files(self):
        """查找冗余文件"""
        patterns = [
            '*_old.*', '*_backup.*', '*_copy.*', '*.bak',
            '*.tmp', '*.log', '*.pyc', '__pycache__'
        ]
        
        for pattern in patterns:
            for file in self.root.rglob(pattern):
                if 'node_modules' not in str(file) and '.git' not in str(file):
                    self.results['redundant_files'].append({
                        'path': str(file.relative_to(self.root)),
                        'size': file.stat().st_size if file.is_file() else 0,
                        'type': pattern
                    })
    
    def _find_empty_files(self):
        """查找空文件"""
        for file in self.root.rglob('*.py'):
            if 'node_modules' in str(file) or '.git' in str(file):
                continue
            
            try:
                content = file.read_text(encoding='utf-8').strip()
                # 只有注释或空白的文件
                lines = [l for l in content.split('\n') if l.strip() and not l.strip().startswith('#')]
                if len(lines) < 3:
                    self.results['empty_files'].append({
                        'path': str(file.relative_to(self.root)),
                        'lines': len(lines)
                    })
            except Exception:
                pass
    
    def _analyze_imports(self):
        """分析Python导入"""
        for file in self.root.rglob('*.py'):
            if 'node_modules' in str(file) or '.git' in str(file) or 'archive' in str(file):
                continue
            
            try:
                content = file.read_text(encoding='utf-8')
                tree = ast.parse(content)
                
                imports = set()
                used_names = set()
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            name = alias.asname or alias.name.split('.')[0]
                            imports.add(name)
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            for alias in node.names:
                                name = alias.asname or alias.name
                                imports.add(name)
                    elif isinstance(node, ast.Name):
                        used_names.add(node.id)
                
                unused = imports - used_names
                if unused and len(unused) < len(imports):  # 避免误报
                    self.results['unused_imports'].append({
                        'file': str(file.relative_to(self.root)),
                        'unused': list(unused)[:5]  # 最多显示5个
                    })
            except Exception:
                pass
    
    def _calculate_stats(self):
        """计算统计信息"""
        py_files = list(self.root.rglob('*.py'))
        vue_files = list(self.root.rglob('*.vue'))
        ts_files = list(self.root.rglob('*.ts'))
        
        # 排除node_modules和archive
        py_files = [f for f in py_files if 'node_modules' not in str(f) and 'archive' not in str(f)]
        vue_files = [f for f in vue_files if 'node_modules' not in str(f)]
        ts_files = [f for f in ts_files if 'node_modules' not in str(f)]
        
        total_py_lines = 0
        total_vue_lines = 0
        total_ts_lines = 0
        
        for f in py_files:
            try:
                total_py_lines += len(f.read_text(encoding='utf-8').split('\n'))
            except:
                pass
        
        for f in vue_files:
            try:
                total_vue_lines += len(f.read_text(encoding='utf-8').split('\n'))
            except:
                pass
        
        for f in ts_files:
            try:
                total_ts_lines += len(f.read_text(encoding='utf-8').split('\n'))
            except:
                pass
        
        self.results['stats'] = {
            'python_files': len(py_files),
            'python_lines': total_py_lines,
            'vue_files': len(vue_files),
            'vue_lines': total_vue_lines,
            'ts_files': len(ts_files),
            'ts_lines': total_ts_lines,
            'total_files': len(py_files) + len(vue_files) + len(ts_files),
            'total_lines': total_py_lines + total_vue_lines + total_ts_lines
        }


class ProjectOptimizer:
    """项目优化器"""
    
    def __init__(self, project_root: Path, mode: str = 'report'):
        self.root = project_root
        self.mode = mode
        self.analyzer = CodeAnalyzer(project_root)
        self.cleaned_files = []
        self.cleaned_size = 0
    
    def run(self):
        """运行优化"""
        print("\n" + "="*60)
        print("   微博情感分析系统 - 项目优化工具")
        print("="*60)
        print(f"   模式: {self.mode}")
        print(f"   时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60 + "\n")
        
        # 分析
        results = self.analyzer.analyze()
        
        # 生成报告
        self._generate_report(results)
        
        # 根据模式执行清理
        if self.mode == 'auto':
            self._auto_clean(results)
        elif self.mode == 'interactive':
            self._interactive_clean(results)
        
        # 生成总结
        self._generate_summary()
    
    def _generate_report(self, results: Dict):
        """生成分析报告"""
        print("\n📊 分析报告")
        print("-" * 40)
        
        stats = results['stats']
        print(f"\n【代码统计】")
        print(f"  Python文件: {stats['python_files']} 个, {stats['python_lines']} 行")
        print(f"  Vue文件: {stats['vue_files']} 个, {stats['vue_lines']} 行")
        print(f"  TypeScript文件: {stats['ts_files']} 个, {stats['ts_lines']} 行")
        print(f"  总计: {stats['total_files']} 个文件, {stats['total_lines']} 行代码")
        
        print(f"\n【冗余文件】({len(results['redundant_files'])} 个)")
        for item in results['redundant_files'][:10]:
            print(f"  - {item['path']} ({item['size']} bytes)")
        if len(results['redundant_files']) > 10:
            print(f"  ... 还有 {len(results['redundant_files']) - 10} 个")
        
        print(f"\n【空/极小文件】({len(results['empty_files'])} 个)")
        for item in results['empty_files'][:5]:
            print(f"  - {item['path']} ({item['lines']} 行有效代码)")
        
        print(f"\n【可能未使用的导入】({len(results['unused_imports'])} 个文件)")
        for item in results['unused_imports'][:5]:
            print(f"  - {item['file']}: {', '.join(item['unused'][:3])}")
    
    def _auto_clean(self, results: Dict):
        """自动清理"""
        print("\n🧹 自动清理模式")
        print("-" * 40)
        
        # 清理__pycache__
        for item in results['redundant_files']:
            if '__pycache__' in item['path'] or item['path'].endswith('.pyc'):
                full_path = self.root / item['path']
                if full_path.exists():
                    try:
                        if full_path.is_dir():
                            shutil.rmtree(full_path)
                        else:
                            full_path.unlink()
                        self.cleaned_files.append(item['path'])
                        self.cleaned_size += item['size']
                        print(f"  ✓ 删除: {item['path']}")
                    except Exception as e:
                        print(f"  ✗ 失败: {item['path']} - {e}")
    
    def _interactive_clean(self, results: Dict):
        """交互式清理"""
        print("\n🧹 交互式清理模式")
        print("-" * 40)
        
        for item in results['redundant_files'][:20]:
            response = input(f"  删除 {item['path']}? (y/n/q): ").strip().lower()
            if response == 'q':
                break
            elif response == 'y':
                full_path = self.root / item['path']
                if full_path.exists():
                    try:
                        if full_path.is_dir():
                            shutil.rmtree(full_path)
                        else:
                            full_path.unlink()
                        self.cleaned_files.append(item['path'])
                        self.cleaned_size += item['size']
                        print(f"    ✓ 已删除")
                    except Exception as e:
                        print(f"    ✗ 失败: {e}")
    
    def _generate_summary(self):
        """生成总结"""
        print("\n" + "="*60)
        print("   优化总结")
        print("="*60)
        
        if self.cleaned_files:
            print(f"\n  清理文件数: {len(self.cleaned_files)}")
            print(f"  释放空间: {self.cleaned_size / 1024:.2f} KB")
        else:
            print("\n  本次未执行清理操作")
        
        print("\n  建议后续操作:")
        print("  1. 运行 pytest 验证功能正常")
        print("  2. 运行 python scripts/demo_showcase.py 验证演示流程")
        print("  3. 提交 Git 保存更改")
        
        print("\n" + "="*60)


def main():
    parser = argparse.ArgumentParser(description="项目优化工具")
    parser.add_argument(
        '--mode',
        choices=['report', 'interactive', 'auto'],
        default='report',
        help='运行模式: report(只读), interactive(交互), auto(自动)'
    )
    
    args = parser.parse_args()
    
    optimizer = ProjectOptimizer(PROJECT_ROOT, args.mode)
    optimizer.run()


if __name__ == '__main__':
    main()
