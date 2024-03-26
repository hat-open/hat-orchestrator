from pathlib import Path
import subprocess

import doit

from hat.doit import common
from hat.doit.docs import build_sphinx
from hat.doit.js import (ESLintConf,
                         run_eslint)
from hat.doit.py import (get_task_build_wheel,
                         get_task_run_pytest,
                         get_task_create_pip_requirements,
                         run_flake8)


__all__ = ['task_clean_all',
           'task_node_modules',
           'task_build',
           'task_check',
           'task_test',
           'task_create_ui_dir',
           'task_docs',
           'task_ts',
           'task_static',
           'task_json_schema_repo',
           'task_pip_requirements']


build_dir = Path('build')
src_py_dir = Path('src_py')
src_js_dir = Path('src_js')
src_static_dir = Path('src_static')
pytest_dir = Path('test_pytest')
docs_dir = Path('docs')
schemas_json_dir = Path('schemas_json')
node_modules_dir = Path('node_modules')

build_py_dir = build_dir / 'py'
build_docs_dir = build_dir / 'docs'

ui_dir = src_py_dir / 'hat/orchestrator/ui'
json_schema_repo_path = src_py_dir / 'hat/orchestrator/json_schema_repo.json'


def task_clean_all():
    """Clean all"""
    return {'actions': [(common.rm_rf, [build_dir,
                                        ui_dir,
                                        json_schema_repo_path])]}


def task_node_modules():
    """Install node_modules"""
    return {'actions': ['npm install --silent --progress false']}


def task_build():
    """Build"""
    return get_task_build_wheel(src_dir=src_py_dir,
                                build_dir=build_py_dir,
                                task_dep=['ts',
                                          'static',
                                          'json_schema_repo'])


def task_check():
    """Check with flake8"""
    return {'actions': [(run_flake8, [src_py_dir]),
                        (run_flake8, [pytest_dir]),
                        (run_eslint, [src_js_dir, ESLintConf.TS])],
            'task_dep': ['node_modules']}


def task_test():
    """Test"""
    return get_task_run_pytest(task_dep=['json_schema_repo',
                                         'create_ui_dir'])


def task_create_ui_dir():
    """Create empty ui directory"""
    return {'actions': [(common.mkdir_p, [ui_dir])]}


def task_docs():
    """Docs"""

    def build():
        build_sphinx(src_dir=docs_dir,
                     dst_dir=build_docs_dir,
                     project='hat-orchestrator',
                     extensions=['sphinxcontrib.programoutput'])

    return {'actions': [build],
            'task_dep': ['create_ui_dir',
                         'json_schema_repo']}


def task_ts():
    """Build TypeScript"""

    def build(args):
        args = args or []
        subprocess.run(['npx', 'tsc', *args],
                       check=True)

    return {'actions': [build],
            'pos_arg': 'args',
            'task_dep': ['node_modules']}


@doit.create_after('node_modules')
def task_static():
    """Copy static files"""
    src_dst_dirs = [(src_static_dir,
                     ui_dir),
                    (node_modules_dir / '@hat-open/juggler',
                     ui_dir / 'script/@hat-open/juggler'),
                    (node_modules_dir / '@hat-open/renderer',
                     ui_dir / 'script/@hat-open/renderer'),
                    (node_modules_dir / '@hat-open/util',
                     ui_dir / 'script/@hat-open/util'),
                    (node_modules_dir / 'snabbdom/build',
                     ui_dir / 'script/snabbdom')]

    for src_dir, dst_dir in src_dst_dirs:
        for src_path in src_dir.rglob('*'):
            if not src_path.is_file():
                continue

            dst_path = dst_dir / src_path.relative_to(src_dir)

            yield {'name': str(dst_path),
                   'actions': [(common.mkdir_p, [dst_path.parent]),
                               (common.cp_r, [src_path, dst_path])],
                   'file_dep': [src_path],
                   'targets': [dst_path],
                   'task_dep': ['node_modules']}


def task_json_schema_repo():
    """Generate JSON Schema Repository"""
    return common.get_task_json_schema_repo(schemas_json_dir.rglob('*.yaml'),
                                            json_schema_repo_path)


def task_pip_requirements():
    """Create pip requirements"""
    return get_task_create_pip_requirements()
