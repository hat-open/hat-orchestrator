"""UI web server"""

import contextlib
import functools
import importlib.resources
import logging
import typing
import urllib

from hat import aio
from hat import json
from hat import juggler
import hat.orchestrator.component


mlog: logging.Logger = logging.getLogger(__name__)
"""Module logger"""

autoflush_delay: float = 0.2
"""Jugler autoflush delay"""


async def create(conf: json.Data,
                 components: typing.List[hat.orchestrator.component.Component]
                 ) -> 'WebServer':
    """Create ui for monitoring and controlling components

    Args:
        conf: configuration defined by
            ``hat-orchestrator://orchestrator.yaml#/definitions/ui``
        components: components

    """
    srv = WebServer()
    srv._components = components

    exit_stack = contextlib.ExitStack()
    try:
        ui_path = exit_stack.enter_context(
            importlib.resources.path(__package__, 'ui'))

        state = json.Storage({'components': []})
        for component_id, component in enumerate(components):
            update_state = functools.partial(
                _update_component_state, state, component_id, component)
            exit_stack.enter_context(
                component.register_change_cb(update_state))
            update_state()

        addr = urllib.parse.urlparse(conf['address'])
        srv._srv = await juggler.listen(host=addr.hostname,
                                        port=addr.port,
                                        request_cb=srv._on_request,
                                        static_dir=ui_path,
                                        autoflush_delay=autoflush_delay,
                                        state=state)

        try:
            srv.async_group.spawn(aio.call_on_cancel, exit_stack.close)

        except BaseException:
            await aio.uncancellable(srv.async_close())
            raise

    except BaseException:
        exit_stack.close()
        raise

    return srv


class WebServer(aio.Resource):
    """WebServer

    For creating new instance of this class see `create` coroutine.

    """

    @property
    def async_group(self) -> aio.Group:
        """Async group"""
        return self._srv.async_group

    async def _on_request(self, conn, name, data):
        if name == 'start':
            component = self._components[data['id']]
            component.start()

        elif name == 'stop':
            component = self._components[data['id']]
            component.stop()

        elif name == 'revive':
            component = self._components[data['id']]
            component.set_revive(bool(data['value']))

        else:
            raise Exception('received invalid message type')


def _update_component_state(state, component_id, component):
    data = {'id': component_id,
            'name': component.name,
            'delay': component.delay,
            'revive': component.revive,
            'status': component.status.name}
    state.set(['components', component_id], data)
