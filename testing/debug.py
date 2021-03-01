from replit import db
from datetime import datetime
import json


our_users = db.get("our_users")
messages = db.get("messages")


# print("users")
# for user in our_users:
#     print(user)

print("messages")
for i in range(len(messages)):
    print(messages[i])



# to access the datetime docs: https://docs.python.org/3/library/datetime.html#datetime.datetime

# stored = datetime.fromisoformat('2021-02-19 21:53:46.929000')
# now = datetime.now()

# if stored > now:
#   print(7)
# else:
#   print(now)