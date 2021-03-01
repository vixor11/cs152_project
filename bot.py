# bot.py
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
import asyncio
import threading

# Message class

if "messages" not in db:
  db["messages"] = []
if "our_users" not in db:
  db["our_users"] = []
# if "running" not in db:
#     db["running"] = True

# Set up logging to the console
logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(
    filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter(
    '%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

# There should be a file called 'tokens.json' inside the same folder as this file
token_path = 'tokens.json'
if not os.path.isfile(token_path):
    raise Exception(f"{token_path} not found!")
with open(token_path) as f:
    # If you get an error here, it means your token is formatted incorrectly. Did you put it in quotes?
    tokens = json.load(f)
    discord_token = tokens['discord']
    perspective_key = tokens['perspective']


class ModBot(discord.Client):
    def __init__(self, key):
        intents = discord.Intents.default()
        intents.members = True
        client = discord.Client(intents=intents)
        super().__init__(command_prefix='.', intents=intents)
        self.group_num = None
        self.mod_channels = {}  # Map from guild to the mod channel id for that guild
        self.channel = None
        self.reports = {}  # Map from user IDs to the state of their report
        self.perspective_key = key

    async def on_ready(self):
        print(f'{self.user.name} has connected to Discord! It is these guilds:')
        for guild in self.guilds:
            print(f' - {guild.name}')
        print('Press Ctrl-C to quit.')

        # Parse the group number out of the bot's name
        match = re.search('[gG]roup (\d+) [bB]ot', self.user.name)
        if match:
            self.group_num = match.group(1)
        else:
            raise Exception(
                "Group number not found in bot's name. Name format should be \"Group # Bot\".")
        # t = threading.Thread(target=self.cronjob,args=(x,))
        # t.start()

        # Find the mod channel in each guild that this bot should report to
        current_users = db["our_users"]
        for guild in self.guilds:
            for channel in guild.text_channels:
                if channel.name == f'group-{self.group_num}-mod':
                    self.mod_channels[guild.id] = channel
                    self.channel_id = guild.id
                if channel.name == f'group-{self.group_num}':
                    self.channel = channel
                    for user_in_question in channel.members:
                        in_current_users = False
                        for existing_user in current_users:
                            if json.loads(existing_user)['id'] == user_in_question.id:
                                in_current_users = True
                        if user_in_question.name != f'Group {self.group_num} Bot' and not in_current_users:
                            current_users.append(User(user_in_question.id, user_in_question.name, 0, 0, 0).toJSON())

        # iterate through the current_users in the channel and set all their scores to 0
        db["our_users"] = current_users

    
    async def on_message(self, message):
        '''
        This function is called whenever a message is sent in a channel that the bot can see (including DMs). 
        Currently the bot is configured to only handle messages that are sent over DMs or in your group's "group-#" channel. 
        '''
        # Ignore messages from us
        if message.author.id == self.user.id:
            return

        # Check if this message was sent in a server ("guild") or if it's a DM
        if message.guild:
            await self.handle_channel_message(message, False)
        else:
            await self.handle_dm(message)

    async def on_message_edit(self, before, after):
        '''
        This function is called whenever a message is edited in a channel that the bot can see (including DMs). 
        '''
        # Ignore messages from us
        if before.author.id == self.user.id:
            return

        # Check if this message was sent in a server ("guild") or if it's a DM
        if before.guild:
            await self.handle_channel_message(after, True)
        else:
            await self.handle_dm(after)

    async def handle_dm(self, message):
        # Handle a help message
        print("top of handle dm")
        if message.content == Report.HELP_KEYWORD:
            reply = "Use the `report` command to begin the reporting process.\n"
            reply += "Use the `cancel` command to cancel the report process.\n"
            await message.channel.send(reply)
            return

        author_id = message.author.id
        responses = []

        # Only respond to messages if they're part of a reporting flow
        if author_id not in self.reports and not message.content.startswith(Report.START_KEYWORD):
            print("not part of a reporting flow")
            return

        # If we don't currently have an active report for this user, add one
        if author_id not in self.reports:
            print("adding to part of concurrent reports")
            self.reports[author_id] = Report(self)

        # Let the report class handle this message; forward all the messages it returns to us
        responses = await self.reports[author_id].handle_message(message)
        for r in responses:
            await message.channel.send(r)

        # If the report is complete or cancelled, remove it from our map
        if await self.reports[author_id].report_complete():
            self.reports.pop(author_id)

    async def handle_channel_message(self, message, is_edited):
    
        # Handling messages sent in the mod channel
        if message.channel.name == f'group-{self.group_num}-mod':

            if message.content == "next":
                mod_channel = self.mod_channels[self.channel_id]
                
                messy_messages = db["messages"]
                messy_messages.sort(key=lambda s: json.loads(s)['priority'])
                if len(messy_messages) == 0:
                    await mod_channel.send("All messages have been reviewed!")
                else:
                    actual_message = json.loads(messy_messages[0])
                    await mod_channel.send(self.code_format(json.dumps(actual_message, indent=2)))

            channel = self.mod_channels[self.channel_id]
            if message.reference is not None:
                mod_channel = self.mod_channels[self.channel_id]
                main_channel = self.channel
                m = await channel.fetch_message(message.reference.message_id)
                string_length = len(m.content)
                new_string = m.content[3:len(m.content) - 3]
                parsed_message = json.loads(new_string)

                users = db["our_users"]
                new_messages = db["messages"]
                pop_flag = False
                index_pop = 0
                for i in range(len(new_messages)):
                    print(new_messages[i])
                    message_to_delete = new_messages[i]
                    if json.loads(message_to_delete)["id"] == parsed_message["id"]:
                        pop_flag = True
                if len(new_messages) > 0:
                    new_messages.pop(index_pop)
                author = None
                victims = []
                reporters = []

                review_message = await self.channel.fetch_message(int(parsed_message["id"]))

                if message.content == "delete 1":
                    await review_message.delete()
                    for i in range(len(users)):
                        actual_user = json.loads(users[i])
                        if actual_user["name"] == parsed_message["author"]:
                            actual_user["perpetrator_score"] += 1
                            users[i] = json.dumps(actual_user)
                            if (actual_user["perpetrator_score"] >= 15):
                                await mod_channel.send(f'You just submitted a ticket that set the perpetrator score of {actual_user["name"]} to {actual_user["perpetrator_score"]}. Because of this, they have been banned from the channel.')
                                await main_channel.send(f'{actual_user["name"]} has been banned from this server for promoting suicidal content.')
                        if actual_user["name"] in parsed_message["victims"]:
                            actual_user["victim_score"] += 1
                            users[i] = json.dumps(actual_user)
                            if (actual_user["victim_score"] >= 15):
                                await mod_channel.send(f'Heads up {actual_user["name"]} now has a victim score of  {actual_user["victim_score"]}. This might mean this person is suicidal. We recommend you connect them to a suicide prevention hotline.')
                        if actual_user["name"] in parsed_message["reporters"]:
                            actual_user["reporter_score"] -= 1
                            users[i] = json.dumps(actual_user)
                elif message.content == "delete 2":
                    await review_message.delete()
                    for i in range(len(users)):
                        actual_user = json.loads(users[i])
                        if actual_user["name"] == parsed_message["author"]:
                            actual_user["perpetrator_score"] += 2
                            users[i] = json.dumps(actual_user)
                            if (actual_user["perpetrator_score"] >= 15):
                                await mod_channel.send(f'You just submitted a ticket that set the perpetrator score of {actual_user["name"]} to {actual_user["perpetrator_score"]}. Because of this, they have been banned from the channel.')
                                await main_channel.send(f'{actual_user["name"]} has been banned from this server for promoting suicidal content.')
                        if actual_user["name"] in parsed_message["victims"]:
                            actual_user["victim_score"] += 2
                            users[i] = json.dumps(actual_user)
                            if (actual_user["victim_score"] >= 15):
                                await mod_channel.send(f'Heads up {actual_user["name"]} now has a victim score of  {actual_user["victim_score"]}. This might mean this person is suicidal. We recommend you connect them to a suicide prevention hotline.')
                        if actual_user["name"] in parsed_message["reporters"]:
                            actual_user["reporter_score"] -= 2
                            users[i] = json.dumps(actual_user)
                elif message.content == "delete 3":
                    await review_message.delete()
                    for i in range(len(users)):
                        actual_user = json.loads(users[i])
                        if actual_user["name"] == parsed_message["author"]:
                            actual_user["perpetrator_score"] += 3
                            users[i] = json.dumps(actual_user)
                            if (actual_user["perpetrator_score"] >= 15):
                                await mod_channel.send(f'You just submitted a ticket that set the perpetrator score of {actual_user["name"]} to {actual_user["perpetrator_score"]}. Because of this, they have been banned from the channel.')
                                await main_channel.send(f'{actual_user["name"]} has been banned from this server for promoting suicidal content.')
                        if actual_user["name"] in parsed_message["victims"]:
                            actual_user["victim_score"] += 3
                            users[i] = json.dumps(actual_user)
                            if (actual_user["victim_score"] >= 15):
                                await mod_channel.send(f'Heads up {actual_user["name"]} now has a victim score of  {actual_user["victim_score"]}. This might mean this person is suicidal. We recommend you connect them to a suicide prevention hotline.')
                        if actual_user["name"] in parsed_message["reporters"]:
                            actual_user["reporter_score"] -= 3
                            users[i] = json.dumps(actual_user)
                elif message.content == "ignore":
                    if len(parsed_message["reporters"]) < 0:
                        return
                    for i in range(len(users)):
                        actual_user = json.loads(users[i])
                        if actual_user["name"] in parsed_message["reporters"]:
                            actual_user["reporter_score"] += 3
                            users[i] = json.dumps(actual_user)
                elif message.content == "smh":
                    for i in range(len(users)):
                        actual_user = json.loads(users[i])
                        if actual_user["name"] == parsed_message["author"]:
                            actual_user["perpetrator_score"] += 1
                            users[i] = json.dumps(actual_user)
                            if (actual_user["perpetrator_score"] >= 15):
                                await mod_channel.send(f'You just submitted a ticket that set the perpetrator score of {actual_user["name"]} to {actual_user["perpetrator_score"]}. Because of this, they have been banned from the channel.')
                                await main_channel.send(f'{actual_user["name"]} has been banned from this server for promoting suicidal content.')
                        if actual_user["name"] in parsed_message["reporters"]:
                            actual_user["reporter_score"] -= 1
                            users[i] = json.dumps(actual_user)
                        if actual_user["name"] in parsed_message["victims"]:
                            actual_user["victim_score"] += 2
                            users[i] = json.dumps(actual_user)
                            if (actual_user["victim_score"] >= 15):
                                await mod_channel.send(f'Heads up {actual_user["name"]} now has a victim score of  {actual_user["victim_score"]}. This might mean this person is suicidal. We recommend you connect them to a suicide prevention hotline.')

                
                db["our_users"] = users
                db["messages"] = new_messages
            
            mod_channel = self.mod_channels[self.channel_id]
            for user in db["our_users"]:
                actual_user = json.loads(user)
                if actual_user["name"] == message.content:
                    await mod_channel.send(self.code_format(json.dumps(actual_user, indent=2)))

            return

        # Handling messages sent in the actual channel that is being moderated
        if message.channel.name == f'group-{self.group_num}':
            scores = self.eval_text(message)

            # TODO NADINE AND MARIA EXPAND THIS SECTION
            # USES PROFANITY API TO FIND ALTERNATE SPELLING OF COMMON SLURS
            # POPULATE THE ARRAY  HERE WITH NASTY WORDS YOU THINK ARE HARMFUL 
            # STUDY THESE NEXT 6 LINES OF CODE
            swear_words = ["kill", "die", "kill yourself", "fuck", "kys", "kill myself", "hate myself", "hate life", "suicide", "bitch", "no one cares", "shit", "bullshit", "i want to die", "anorexia", "bulimia", "jump off", "cut yourself", "noose", "hang yourself", "hang myself", "overdose", "end me", "no shits", "kmn", "kill me now", "shoot myself", "kill me", "shoot you", "shoot my", "blow brains", "lost cause", "lost hope", "don't want to live", "suicidal", "end it", "hopeless", "alone", "i need help", "slit my wrist", "slit my neck"]
            profanity.load_censor_words(swear_words)

            # returns boolean
            toxic = profanity.contains_profanity(message)
            
            # add "and" statements to this filter 
            # ATTENTION NADINE AND MARIA: USE THE BOOLEAN GENERATED ABOVE IN THE IF STATEMENT
            if scores['SEVERE_TOXICITY'] >= 0.1 or scores['TOXICITY'] >= 0.2 or scores['PROFANITY'] >= 0.2 or scores['IDENTITY_ATTACK'] >= 0.1 or scores['THREAT'] >= 0.15:
                print("just added a message")
                if not is_edited:
                    message_struct = Message(3, message.id, message.author.name, None, None, message.content, 0, True, message.created_at.isoformat(), None)
                    currentMessages = db["messages"]
                    if message not in db["messages"]:
                        currentMessages.append(message_struct.toJSON())
                    db["messages"] = currentMessages
                else: 
                    message_struct = Message(3, message.id, message.author.name, None, None, message.content, 0, True, message.created_at.isoformat(), message.edited_at.isoformat())
                    currentMessages = db["messages"]
                    for i in range(len(currentMessages)):
                        if json.loads(currentMessages[i])['id'] == message.id:
                            currentMessages[i] = message_struct.toJSON()
                    db["messages"] = currentMessages

                # Forward the message to the mod channel only if certain thresholds are passed
                # mod_channel = self.mod_channels[message.guild.id]
                # await mod_channel.send(f'Forwarded message:\n{message.author.name}: "{message.content}"')
                # await mod_channel.send(self.code_format(json.dumps(scores, indent=2)))

    def eval_text(self, message):
        '''
        Given a message, forwards the message to Perspective and returns a dictionary of scores.
        '''
        PERSPECTIVE_URL = 'https://commentanalyzer.googleapis.com/v1alpha1/comments:analyze'

        url = PERSPECTIVE_URL + '?key=' + self.perspective_key
        data_dict = {
            'comment': {'text': message.content},
            'languages': ['en'],
            'requestedAttributes': {
                'SEVERE_TOXICITY': {}, 'PROFANITY': {},
                'IDENTITY_ATTACK': {}, 'THREAT': {},
                'TOXICITY': {}, 'FLIRTATION': {}
            },
            'doNotStore': True
        }
        response = requests.post(url, data=json.dumps(data_dict))
        response_dict = response.json()

        scores = {}
        for attr in response_dict["attributeScores"]:
            scores[attr] = response_dict["attributeScores"][attr]["summaryScore"]["value"]

        return scores

    def code_format(self, text):
        return "```" + text + "```"


client = ModBot(perspective_key)
client.run(discord_token)