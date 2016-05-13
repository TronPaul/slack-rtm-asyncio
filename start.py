#!/usr/bin/env python3
import slack_rtm
import yaml

with open('config.yml') as fp:
    cfg = yaml.load(fp)
    access_token = cfg['access_token']
    includes = cfg['includes']
bot = slack_rtm.Bot(access_token, includes)
bot.run()

