import asyncio
import json
import logging
import signal
import websockets
import yaml
from slacker import Slacker


async def connect(access_token):
    slack = Slacker(access_token)
    resp = await slack.rtm.start()
    return websockets.connect(resp.body['url'])


class Bot(object):
    def __init__(self, access_token):
        self.log = logging.getLogger()
        self.log.setLevel(logging.DEBUG)
        self.access_token = access_token
        self.loop = asyncio.get_event_loop()

    def create_connection(self):
        t = asyncio.Task(connect(self.access_token), loop=self.loop)
        t.add_done_callback(self.connection_made)
        return self.loop

    def add_signal_handlers(self):
        self.loop.add_signal_handler(signal.SIGINT, self.SIGINT)

    def SIGINT(self):
        self.loop.stop()

    def connection_made(self, f):
        self.log.info('Connected')

    def run(self):
        loop = self.create_connection()
        self.add_signal_handlers()
        loop.run_forever()


if __name__ == '__main__':
    with open('config.yml') as fp:
        access_token = yaml.load(fp)['access_token']
    bot = Bot(access_token)
    bot.run()
