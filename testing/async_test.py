import asyncio
import time
import threading

# BLOCK 1
async def inner(x):
    for i in range(1000):
        print("inner: " + str(x))
        await asyncio.sleep(1)

def in_between(x):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    loop.run_until_complete(inner(x))
    loop.close()

def main():
    t = threading.Thread(target=in_between, args=(0,))
    t.start() 
    for i in range(1000):
        time.sleep(1)
        print("outer: " + str(i))

if __name__ == "__main__":
    main()

# BLOCK 2
# async def periodic(x):
#     print("inner: " + str(x))
#     await asyncio.sleep(1)

# async def hello():
#     x = 0
#     while True:
#         await periodic(x)
#         x += 1