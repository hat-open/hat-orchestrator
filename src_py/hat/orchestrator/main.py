"""Orchestrator main"""

from pathlib import Path
import argparse
import asyncio
import contextlib
import importlib.resources
import logging.config
import sys

import appdirs

from hat import aio
from hat import json

import hat.orchestrator.component
import hat.orchestrator.process
import hat.orchestrator.ui


user_conf_dir: Path = Path(appdirs.user_config_dir('hat'))
"""User configuration directory"""

with importlib.resources.as_file(importlib.resources.files(__package__) /
                                 'json_schema_repo.json') as _path:
    json_schema_repo: json.SchemaRepository = json.merge_schema_repositories(
        json.json_schema_repo,
        json.decode_file(_path))
    """JSON schema repository"""


def create_argument_parser() -> argparse.ArgumentParser:
    """Create argument parser"""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--conf', metavar='PATH', type=Path, default=None,
        help="configuration defined by hat-orchestrator://orchestrator.yaml "
             "(default $XDG_CONFIG_HOME/hat/orchestrator.{yaml|yml|toml|json})")  # NOQA
    return parser


def main():
    """Orchestrator"""
    parser = create_argument_parser()
    args = parser.parse_args()
    conf = json.read_conf(args.conf, user_conf_dir / 'orchestrator')
    sync_main(conf)


def sync_main(conf: json.Data):
    """Sync main"""
    aio.init_asyncio()

    validator = json.DefaultSchemaValidator(json_schema_repo)
    validator.validate('hat-orchestrator://orchestrator.yaml', conf)

    log_conf = conf.get('log')
    if log_conf:
        logging.config.dictConfig(log_conf)

    with contextlib.suppress(asyncio.CancelledError):
        aio.run_asyncio(async_main(conf))


async def async_main(conf: json.Data):
    """Async main"""
    async_group = aio.Group()
    async_group.spawn(aio.call_on_cancel, asyncio.sleep, 0.1)

    try:
        if sys.platform == 'win32':
            win32_job = hat.orchestrator.process.Win32Job()
            _bind_resource(async_group, win32_job)
        else:
            win32_job = None

        components = []
        for component_conf in conf.get('components', []):
            component = hat.orchestrator.component.Component(component_conf,
                                                             win32_job)
            _bind_resource(async_group, component)
            components.append(component)

        ui_conf = conf.get('ui')
        if ui_conf:
            htpasswd = (Path(ui_conf['htpasswd']) if 'htpasswd' in ui_conf
                        else None)
            ui = await hat.orchestrator.ui.create(host=ui_conf['host'],
                                                  port=ui_conf['port'],
                                                  components=components,
                                                  htpasswd=htpasswd)
            _bind_resource(async_group, ui)

        await async_group.wait_closing()

    finally:
        await aio.uncancellable(async_group.async_close())


def _bind_resource(async_group, resource):
    async_group.spawn(aio.call_on_cancel, resource.async_close)
    async_group.spawn(aio.call_on_done, resource.wait_closing(),
                      async_group.close)


if __name__ == '__main__':
    sys.argv[0] = 'hat-orchestrator'
    sys.exit(main())
