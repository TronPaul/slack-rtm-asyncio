import asyncio
import json
import logging
import signal
import websockets
import yaml
from websockets.client import WebSocketClientProtocol
from slacker import Slacker


class SlackWebsocketProtocol(WebSocketClientProtocol):
    async def recv(self):
        return json.loads(await super().recv())

    async def send(self, data):
        await super().send(json.dumps(data))


async def connect(access_token):
    slack = Slacker(access_token)
    resp = await slack.rtm.start()
    return await websockets.connect(resp.body['url'], klass=SlackWebsocketProtocol).client


class Bot(object):
    def __init__(self, access_token):
        self.log = logging.getLogger()
        self.log.setLevel(logging.DEBUG)
        self.access_token = access_token
        self.loop = asyncio.get_event_loop()
        self.handlers = {}

    def create_connection(self):
        t = asyncio.Task(connect(self.access_token), loop=self.loop)
        t.add_done_callback(self.connection_made)
        return self.loop

    def add_signal_handlers(self):
        self.loop.add_signal_handler(signal.SIGINT, self.SIGINT)

    def SIGINT(self):
        asyncio.ensure_future(self.websocket.close(), loop=self.loop)
        self.loop.stop()

    def add_listener(self):
        self.loop.create_task(self.listener())

    async def listener(self):
        while True:
            msg = await self.websocket.recv()
            type_ = msg.get('type', None)
            if type_:
                handlers = handlers.get(type_, None)
                for h in handlers:
                    if asyncio.iscoroutinefunction(h):
                        await h(self, msg)
                    else:
                        h(self, msg)

    def connection_made(self, f):
        if getattr(self, 'websocket', None):
            self.websocket.close()
        websocket = f.result()
        self.websocket = websocket
        self.log.info('Connected')
        self.add_listener()

    def run(self):
        loop = self.create_connection()
        self.add_signal_handlers()
        loop.run_forever()

    def send(self, data):
        self.websocket.send(json.dumps(data))

    def add_handler(self, type_, func):
        handlers = self.handlers.setdefault(type_, [])
        handlers.append(func)


if __name__ == '__main__':
    with open('config.yml') as fp:
        access_token = yaml.load(fp)['access_token']
    bot = Bot(access_token)
    bot.run()
