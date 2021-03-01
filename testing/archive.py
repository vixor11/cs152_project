    async def actual_job(self, x):
        while True:
            time.sleep(10)
            mod_channel = self.mod_channels[self.guild_id]
            await mod_channel.send('-------------\n-------------\n-------------\n-------------\n-------------\n-------------\n-------------\n-------------\n-------------\n-------------\n-------------\n-------------\n-------------\n-------------\n-------------\n')
            for message in db["messages"]:
                actual_message = json.loads(message)
                await mod_channel.send(f'Forwarded message:\n{actual_message.author.name}: "{actual_message.content}"')
        

    def cronjob(self, x):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.actual_job(x))
        loop.close()
    
    # await mod_channel.send("----------\n----------\n----------\n----------\n----------\n----------\n----------\n----------\n----------\n----------\n----------\n----------\n----------\n----------\n----------\n")
                # await mod_channel.send(f'{actual_message["id"]}\nMessage author: {actual_message["author"]}\nMessage content: {actual_message["message_content"]} \nPriority: {actual_message["priority"]} \nFlagged by the algorithm? {actual_message["algorithm_flag"]} \nMessage sent on: {actual_message["created_at"]} \nHow many times has this message been reported: {actual_message["report_amount"]}')