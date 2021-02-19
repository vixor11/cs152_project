class User:
    def __init__(self, username, hash_number, victim_score, perpetrator_score, reporter_score):
        self.username = username
        self.hash_number = hash_number
        self.victim_score = victim_score
        self.perpetrator_score = perpetrator_score
        self.reporter_score = reporter_score