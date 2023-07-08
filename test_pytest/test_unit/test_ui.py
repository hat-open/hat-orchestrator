import collections
import functools

import pytest

from hat import aio
from hat import juggler
from hat import util

from hat.orchestrator.component import Status
import hat.orchestrator.ui


class Component(aio.Resource):

    def __init__(self, name, delay=0, revive=False):
        self._name = name
        self._delay = delay
        self._revive = revive

        self._async_group = aio.Group()
        self._status = Status.DELAYED if self._delay else Status.STOPPED
        self._started_queue = aio.Queue()
        self._change_cbs = util.CallbackRegistry()

    @property
    def async_group(self):
        return self._async_group

    @property
    def status(self):
        return self._status

    @property
    def name(self):
        return self._name

    @property
    def delay(self):
        return self._delay

    @property
    def revive(self):
        return self._revive

    @property
    def started_queue(self):
        return self._started_queue

    def register_change_cb(self, cb):
        return self._change_cbs.register(cb)

    def set_status(self, status):
        self._status = status
        self._change_cbs.notify()

    def set_revive(self, revive):
        self._revive = revive
        self._change_cbs.notify()

    def start(self):
        self._started_queue.put_nowait(True)

    def stop(self):
        self._started_queue.put_nowait(False)


@pytest.fixture
def patch_autoflush_delay(monkeypatch):
    monkeypatch.setattr(hat.orchestrator.ui, 'autoflush_delay', 0)


@pytest.fixture
def port():
    return util.get_unused_tcp_port()


@pytest.fixture
def conf(port):
    return {'address': f'http://127.0.0.1:{port}'}


@pytest.fixture
async def connect(port):
    return functools.partial(juggler.connect, f'ws://127.0.0.1:{port}/ws')


async def test_create(patch_autoflush_delay, conf):
    ui = await hat.orchestrator.ui.create(conf, [])
    assert ui.is_open

    await ui.async_close()
    assert ui.is_closed


@pytest.mark.parametrize("client_count", [1, 2, 5])
@pytest.mark.parametrize("component_count", [0, 1, 2, 5])
async def test_connect(patch_autoflush_delay, conf, connect, client_count,
                       component_count):
    components = [Component(str(i))
                  for i in range(component_count)]
    ui = await hat.orchestrator.ui.create(conf, components)

    clients = collections.deque()
    for i in range(client_count):
        client = await connect()
        clients.append(client)

    state = {'components': [{'id': i,
                             'name': component.name,
                             'delay': component.delay,
                             'revive': component.revive,
                             'status': component.status.name}
                            for i, component in enumerate(components)]}

    for client in clients:
        if client.state.data is None:
            queue = aio.Queue()
            with client.state.register_change_cb(queue.put_nowait):
                await queue.get()

        assert client.state.data == state

    await ui.async_close()

    for client in clients:
        await client.wait_closed()


async def test_status(patch_autoflush_delay, conf, connect):
    state_queue = aio.Queue()
    component = Component('name')
    ui = await hat.orchestrator.ui.create(conf, [component])
    client = await connect()
    client.state.register_change_cb(state_queue.put_nowait)
    if client.state.data is not None:
        state_queue.put_nowait(client.state.data)

    state = await state_queue.get()
    assert state['components'][0]['status'] == 'STOPPED'

    for status in (i for i in Status if i != Status.STOPPED):
        component.set_status(status)
        state = await state_queue.get()
        assert state['components'][0]['status'] == status.name

    await client.async_close()
    await ui.async_close()


async def test_revive(patch_autoflush_delay, conf, connect):
    state_queue = aio.Queue()
    component = Component('name')
    ui = await hat.orchestrator.ui.create(conf, [component])
    client = await connect()
    client.state.register_change_cb(state_queue.put_nowait)
    if client.state.data is not None:
        state_queue.put_nowait(client.state.data)

    state = await state_queue.get()
    assert state['components'][0]['revive'] is False

    for revive in [True, False, True, False]:
        await client.send('revive', {'id': 0,
                                     'value': revive})
        state = await state_queue.get()
        assert state['components'][0]['revive'] == revive

    await client.async_close()
    await ui.async_close()


async def test_start_stop(patch_autoflush_delay, conf, connect):
    component = Component('name')
    ui = await hat.orchestrator.ui.create(conf, [component])
    client = await connect()

    assert component.started_queue.empty()

    for i in ['start', 'stop', 'start', 'stop']:
        await client.send(i, {'id': 0})

    for i in [True, False, True, False]:
        value = await component.started_queue.get()
        assert value == i

    assert component.started_queue.empty()

    await client.async_close()
    await ui.async_close()
