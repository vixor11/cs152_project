from enum import Enum, auto
import discord
import re


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
    RISK_KEYWORD = "someone is at risk"
    SUICIDE_KEYWORD = "encourages suicide"

    def __init__(self, client):
        self.state = State.REPORT_START
        self.client = client
        self.message = None

    async def handle_message(self, message):
        '''
        This function makes up the meat of the user-side reporting flow. It defines how we transition between states and what
        prompts to offer at each of those states. You're welcome to change anything you want; this skeleton is just here to
        get you started and give you a model for working with Discord.
        '''

        if message.content == self.CANCEL_KEYWORD:
            self.state = State.REPORT_COMPLETE
            return ["Report cancelled."]

        if self.state == State.REPORT_START:
            reply = "Thank you for starting the reporting process. "
            reply += "Say `help` at any time for more information.\n\n"
            reply += "Please copy paste the link to the message you want to report.\n"
            reply += "You can obtain this link by right-clicking the message and clicking `Copy Message Link`."
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

            # Here we've found the message - it's up to you to decide what to do next!
            self.state = State.AWAITING_YES
            return ["I found this message:", "```" + message.author.name + ": " + message.content + "```",
                    "Is this the message you are reporting for suicidal content? Type `yes` to confirm or `no` if you'd like to report a different message."]

        if self.state == State.AWAITING_YES:
            if message.content == self.YES_KEYWORD:
                self.state = State.MESSAGE_IDENTIFIED
                return ["Your message has been identified.\n Type `someone is at risk` if you believe someone is at risk.\n If this is content that generally encourages suicide, type `encourages suicide`."]
            if message.content == self.NO_KEYWORD:
                self.state = State.AWAITING_LINK
                reply = "Uh oh! To find the message to report, right click the message and click `Copy Message Link`.\n"
                return [reply]

        if self.state == State.MESSAGE_IDENTIFIED:
            if message.content == self.SUICIDE_KEYWORD:
                self.state == State.REPORT_COMPLETE
                reply = "Thank you for reporting this message!\n"
                reply += "If you know anyone who might be negatively affected by viewing content like this, you should encourage them to report this message as well."
                return [reply]
            if message.content == self.RISK_KEYWORD:
                self.state == State.USER_IDENTIFIED
                reply = "Please tell us who you think is put at risk by this message.\n"
                reply += "It could be that they are expressing interest in committing suicide, or that someone else is encouraging them to do so, or you just generally think they are unwell."
                reply += "Type their username and hash below with the following format: `sample_user #0000`."
                return [reply]

        if self.state == State.USER_IDENTIFIED:
            self.state == State.REPORT_COMPLETE
            reply = "Thank you for reporting this message!\n"
            reply += "Your actions help keep our community safe."
            return [reply]

        return []

    def report_complete(self):
        return self.state == State.REPORT_COMPLETE


# Who is this content harming? If it just generally encourages suicide, type @Group 8 Bot#6841 , if not, @ the user that you think is negatively affected.
