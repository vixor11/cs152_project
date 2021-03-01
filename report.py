from enum import Enum, auto
import discord
import re
from message import Message
from replit import db
import json
from user import User
#import asyncio


class State(Enum):
    REPORT_START = auto()
    AWAITING_LINK = auto()
    AWAITING_YES = auto()
    MESSAGE_IDENTIFIED = auto()
    SOMEONE_AT_RISK = auto()
    ENCOURAGES_SUICIDE = auto()
    USER_IDENTIFIED = auto()
    REPORT_COMPLETE = auto()


class Report:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"
    YES_KEYWORD = "yes"
    NO_KEYWORD = "no"
    RISK_KEYWORD = "is at risk"
    SUICIDE_KEYWORD = "encourages suicide"

    def __init__(self, client):
        self.state = State.REPORT_START
        self.client = client
        self.message = None
        self.victim = None
        self.reporter = None 

    async def handle_message(self, message):
        '''
        This function makes up the meat of the user-side reporting flow. It defines how we transition between states and what
        prompts to offer at each of those states. You're welcome to change anything you want; this skeleton is just here to
        get you started and give you a model for working with Discord.
        '''
        if message.content == self.CANCEL_KEYWORD:
            print("cancel")
            self.state = State.REPORT_COMPLETE
            self.message = self.CANCEL_KEYWORD
            return ["Report cancelled."]

        if self.state == State.REPORT_START:
            reply = "Thank you for starting the reporting process. "
            reply += "Say `help` at any time for more information.\n\n"
            reply += "Please copy paste the link to the message you want to report.\n"
            reply += "You can obtain this link by right-clicking the message and clicking `Copy Message Link`."
            self.reporter = message.author.name
            self.state = State.AWAITING_LINK
            return [reply]

        if self.state == State.AWAITING_LINK:
            # Parse out the three ID strings from the message link
            m = re.search('/(\d+)/(\d+)/(\d+)', message.content)
            if not m:
                return ["I'm sorry, I couldn't read that link. Please try again or say `cancel` to cancel."]
            guild = self.client.get_guild(int(m.group(1)))
            if not guild:
                return ["I cannot accept reports of messages from guilds that I'm not in. Please have the guild owner add me to the guild and try again."]
            channel = guild.get_channel(int(m.group(2)))
            if not channel:
                return ["It seems this channel was deleted or never existed. Please try again or say `cancel` to cancel."]
            try:
                message = await channel.fetch_message(int(m.group(3)))
            except discord.errors.NotFound:
                return ["It seems this message was deleted or never existed. Please try again or say `cancel` to cancel."]

            self.state = State.AWAITING_YES
            self.message = message
            return ["I found this message:", "```" + message.author.name + ": " + message.content + "```",
                    "Is this the message you are reporting for suicidal content? Type `yes` to confirm or `no` if you'd like to report a different message."]

        if self.state == State.AWAITING_YES:
            if message.content == self.YES_KEYWORD:
                self.state = State.MESSAGE_IDENTIFIED
                return ["Your message has been identified.\n Type `is at risk` if you believe someone is at risk.\n If this is content that generally encourages suicide, type `encourages suicide`."]
            if message.content == self.NO_KEYWORD:
                self.state = State.AWAITING_LINK
                reply = "Uh oh! To find the message to report, right click the message and click `Copy Message Link`.\n"
                return [reply]

        if self.state == State.MESSAGE_IDENTIFIED:
            if message.content == self.SUICIDE_KEYWORD:
                self.state = State.REPORT_COMPLETE
                reply = "Thank you for reporting this message!\n"
                reply += "If you know anyone who might be negatively affected by viewing content like this, you should encourage them to report this message as well."
                return [reply]
            if message.content == self.RISK_KEYWORD:
                self.state = State.USER_IDENTIFIED
                reply = "Please tell us who you think is put at risk by this message.\n"
                reply += "It could be that they are expressing interest in committing suicide, or that someone else is encouraging them to do so, or you just generally think they are unwell."
                reply += "Type their username below with the following format: `sample_username`. Do NOT use an '@' to tag them."
                return [reply]

        if self.state == State.USER_IDENTIFIED:
            self.victim = message.content
            self.state = State.REPORT_COMPLETE
            reply = "Thank you for reporting this message!\n"
            reply += "Your actions help keep our community safe."
            return [reply]

        return []

    async def report_complete(self):
        if self.state != State.REPORT_COMPLETE:
            return False
        if self.message == self.CANCEL_KEYWORD:
            return self.state == State.REPORT_COMPLETE

        current_reported_messages = db["messages"]
        users = db["our_users"]
        previous_report = None
        j = 0
        for i in range(len(current_reported_messages)):
            if json.loads(current_reported_messages[i])['id'] == self.message.id:
                previous_report = current_reported_messages[i]
                j = i
        
        priority = 0
        report_amount = 1            

        if previous_report != None:
            jsonified_message = json.loads(previous_report)
            new_victims = jsonified_message["victims"]
            if self.victim not in new_victims:
                new_victims.append(self.victim)
            if self.reporter in jsonified_message["reporters"]:
                return True
            report_amount = jsonified_message['report_amount'] + 1
            if jsonified_message['algorithm_flag'] and jsonified_message['report_amount'] == 0:
                priority = 1
                # Priority 1, algo flag and 1 report
            elif not jsonified_message['algorithm_flag'] and jsonified_message['report_amount'] > 0:
                priority = 1
                # Priority 1, algo no flag and 2+ report, specific or generic
            elif not jsonified_message['algorithm_flag'] and jsonified_message['report_amount'] > 0 and self.victim == None:
                priority = 3
                # Priority 3, algo no flag and 1 report, generic risk
            elif jsonified_message['algorithm_flag'] and jsonified_message['report_amount'] > 0:
                priority = 0
                # await self.message.delete()
                for user in users:
                    actual_user = json.loads(user)
                    if actual_user["name"] in jsonified_message["reporters"]:
                        actual_user["reporter_score"] -= 3
                    if actual_user["name"] == self.message.author.name:
                        actual_user["perpetrator_score"] += 3
                # Priority 4, ban content and wait to unban
            message_struct = Message(priority, self.message.id, self.message.author.name, new_victims, self.reporter, self.message.content, report_amount, jsonified_message['algorithm_flag'], jsonified_message['created_at'], jsonified_message['edited_at'])
            current_reported_messages[j] = message_struct.toJSON()
        else:
            if self.victim != None:
                priority = 2
                # Priority 2, algo no flag and 1 report, specific user at risk
            else:
                priority = 3
                # Priority 3, algo no flag and 1 report, generic user
            if self.message.edited_at == None:
                message_id = self.message.id
                author = self.message.author.name
                victim = self.victim
                reporter = self.reporter
                content = self.message.content 
                created_at = self.message.created_at
                edited_at = self.message.edited_at
                message_struct = Message(priority, message_id, author, victim, reporter, content, 1, False, created_at.isoformat(), None)
            else:
                message_struct = Message(priority, message_id, author, victim, reporter, content, 1, False, created_at.isoformat(), edited_at.isoformat())

            current_reported_messages.append(message_struct.toJSON())
        
        db["messages"] = current_reported_messages
        self.victim = None
        self.reporter = None 
        self.message = None

        return self.state == State.REPORT_COMPLETE

    

