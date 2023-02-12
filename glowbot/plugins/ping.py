async def on_message(client, message):
    if message.author == client.user:
        return
    
    if message.content == 'ping':
        await message.channel.send('pong')