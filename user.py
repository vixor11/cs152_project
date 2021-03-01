import json

class User:
    def __init__(self, id, name, victim_score, perpetrator_score, reporter_score):
        self.id = id
        self.name = name
        self.victim_score = victim_score
        self.perpetrator_score = perpetrator_score
        self.reporter_score = reporter_score
    
    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__, 
            sort_keys=True, indent=4)