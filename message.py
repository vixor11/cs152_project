import json

class Message:
    def __init__(self, priority, id, author, victim, reporter, message_content, report_amount, algorithm_flag, created_at, edited_at):
        self.priority = priority # int
        self.id = id # string
        self.author = author # string
        self.victims = [victim] # string
        self.reporters = [reporter] # array of strings
        self.message_content = message_content # string
        self.report_amount = report_amount # int
        self.algorithm_flag = algorithm_flag # boolean
        self.created_at = created_at # datetime
        self.edited_at = edited_at # datetime

    def toJSON(self):
        # json.dumps(self, default=lambda x: x.__dict__)
        # return json.dumps(self.__dict__)
        return json.dumps(self, default=lambda o: o.__dict__, 
            sort_keys=True, indent=4)

