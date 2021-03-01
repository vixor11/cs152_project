import discord
from discord.ext import commands
import os
import json
import logging
import re
import requests
from report import Report
from user import User
from message import Message
from datetime import datetime
from replit import db
from better_profanity import profanity
import schedule
import time

x = 0

# function to be run
def job(x):
    # clear mod channel
    messages = db["messages"]

    for guild in self.guilds:
        print(guild)
        for channel in guild.text_channels:
            if channel.name == f'group-{self.group_num}-mod':
                self.guild_id = guild.id

    for message in messages:
        await mod_channel.send(f'Forwarded message:\n{message.author.name}: "{message.content}"')
    # sort messages
    # send messages to the mod channel
    print(x)

schedule.every(1).seconds.do(lambda: job(x))

while True:
    schedule.run_pending()
    time.sleep(1)
    x += 1




# run = "python3 bot.py & python3 cronjob"