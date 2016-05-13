import asyncio
import datetime
import json
import logging
import importlib
import re
import signal
import time
import websockets
import venusian
import yaml
from websockets.client import WebSocketClientProtocol
from slacker import Slacker


def maybedotted(name):
    """Resolve dotted names:
    .. code-block:: python
        >>> maybedotted('irc3.config')
        <module 'irc3.config' from '...'>
        >>> maybedotted('irc3.utils.IrcString')
        <class 'irc3.utils.IrcString'>
    ..
    """
    if not name:
        raise LookupError(
            'Not able to resolve %s' % name)
    if not hasattr(name, '__name__'):
        try:
            mod = importlib.import_module(name)
        except ImportError:
            attr = None
            if '.' in name:
                names = name.split('.')
                attr = names.pop(-1)
                try:
                    mod = maybedotted('.'.join(names))
                except LookupError:
                    attr = None
                else:
                    attr = getattr(mod, attr, None)
            if attr is not None:
                return attr
            raise LookupError(
                'Not able to resolve %s' % name)
        else:
            return mod
    return name


class SlackWebsocketProtocol(WebSocketClientProtocol):
    async def recv(self):
        return json.loads(await super().recv())

    async def send(self, data):
        await super().send(json.dumps(data))


async def connect(access_token):
    slack = Slacker(access_token)
    resp = await slack.rtm.start()
    return await websockets.connect(resp.body['url'], klass=SlackWebsocketProtocol).client, resp.body


class Registry(object):
    """Store (and hide from api) events and stuff"""

    def __init__(self):
        self.reset()

    def reset(self):
        self.events = {}

        self.scanned = []
        self.includes = set()

    def get_event_matches(self, data):
        return self.events.get(data['type'], [])


class Bot(object):
    venusian = venusian
    venusian_categories = ['slack.rtm']

    def __init__(self, access_token, includes=None):
        self.log = logging.getLogger()
        self.log.setLevel(logging.DEBUG)
        self.access_token = access_token
        self.loop = asyncio.get_event_loop()
        self.handlers = {}
        self.message_counter = 0
        self.registry = Registry()
        if includes:
            self.include(*includes)

    def create_connection(self):
        t = asyncio.Task(connect(self.access_token), loop=self.loop)
        t.add_done_callback(self.connection_made)
        return self.loop

    def add_signal_handlers(self):
        self.loop.add_signal_handler(signal.SIGINT, self.SIGINT)

    def SIGINT(self):
        asyncio.ensure_future(self.websocket.close(), loop=self.loop)
        self.loop.stop()

    def include(self, *modules, **kwargs):
        reg = self.registry
        categories = kwargs.get('venusian_categories',
                                self.venusian_categories)
        scanner = self.venusian.Scanner(context=self)
        for module in modules:
            if module in reg.includes:
                self.log.warn('%s included twice', module)
            else:
                reg.includes.add(module)
                module = maybedotted(module)
                reg.scanned.append((module.__name__, categories))
                scanner.scan(module, categories=categories)

    def attach_events(self, *events, **kwargs):
        """Attach one or more events to the bot instance"""
        reg = self.registry
        for e in events:
            cur_events = reg.events.setdefault(e.message_type, [])
            cur_events.append(e)

    def add_listener(self):
        self.loop.create_task(self.listener())

    async def listener(self):
        while True:
            msg = await self.websocket.recv()
            for e in self.registry.get_event_matches(msg):
                e.callback(self, msg)

    def connection_made(self, f):
        if getattr(self, 'websocket', None):
            self.websocket.close()
        websocket, start_resp = f.result()
        self.name = start_resp['self']['name']
        self.websocket = websocket
        self.log.info('Connected')
        self.add_listener()

    def run(self):
        loop = self.create_connection()
        self.add_signal_handlers()
        loop.run_forever()

    async def send(self, data):
        self.message_counter += 1
        data['id'] = self.message_counter
        await self.websocket.send(data)

    def add_handler(self, type_, func):
        handlers = self.handlers.setdefault(type_, [])
        handlers.append(func)


if __name__ == '__main__':
    with open('config.yml') as fp:
        access_token = yaml.load(fp)['access_token']
    bot = Bot(access_token)
    bot.add_handler('message', acen_countdown)
    bot.run()
