from functions.initialize import bot, supabase, prefix, tutorial_embeds, event_channel_name
import nextcord
import os
from nextcord.ext.commands import CommandNotFound
from difflib import get_close_matches
import asyncio
from commands.start import TutorialView
from threading import Thread
from website import run_webserver  # Import the Flask app runner
from datetime import datetime, timezone
import logging

logging.basicConfig(level=logging.INFO)

# Cache for storing the lock state
locked = False


# Bot event for when the bot is ready
@bot.event
async def on_ready():
  global level_progression_data

  # try:
  #   supabase.table('Users').update({
  #       'using_command': False
  #   }).neq('discord_id', 0).execute()
  # except Exception as e:
  #   print(f'An error occurred while resetting using_command field: {e}')

  # print(f'Logged in as {bot.user.name}')
  logging.info(f'Logged in as {bot.user.name}')

  new = False

  response = await asyncio.get_event_loop().run_in_executor(
      None, lambda: supabase.table('Changelog').select('*').order(
          'date', desc=True).limit(1).execute())

  if response:
    changelog = response.data[0]
    new = changelog.get('new', False)

    timestamp = datetime.fromisoformat(
        changelog['date']).replace(tzinfo=timezone.utc).timestamp()

    embed = nextcord.Embed(title=changelog['title'],
                           description=changelog['description'],
                           color=nextcord.Color.blue())
    embed.add_field(name="Date", value=f"<t:{int(timestamp)}:f>", inline=False)

    embed.set_footer(text=f"Cultivating Insanity Changelog #{changelog['id']}")

  # Loop through all the guilds the bot is a member of
  for guild in bot.guilds:
    if guild is not None:
      existing = await bot.loop.run_in_executor(
          None,
          lambda guild=guild: supabase.table('Servers').select('*').eq(
              'server_id', guild.id).execute())

      if not existing.data:
        await bot.loop.run_in_executor(
            None,
            lambda guild=guild: supabase.table('Servers').insert(
                {
                    'server_id': guild.id,
                    'server_id_str': f"{guild.id}",
                    'server_name': guild.name,
                    'members': guild.member_count
                }).execute())
        logging.info(f"New Server: {guild.name}")
      else:
        logging.info(f"Existing Server: {guild.name}")
        if new:
          response = await asyncio.get_event_loop().run_in_executor(
              None,
              lambda guild=guild: supabase.table('Log').select('*').eq(
                  'server_id_str', str(guild.id)).order('timestamp', desc=True
                                                        ).limit(1).execute())
          if response:
            data = response.data[0]
            channel_id = data.get('channel_id', 0)

            # Check if there is a channel called 'bot-events'
            bot_events_channel = nextcord.utils.get(guild.text_channels,
                                                    name=event_channel_name)
            content = ""

            if bot_events_channel is not None:
              logging.info("Event channel detected")
              channel = bot_events_channel
              content = "# :tada: A new update is out! :tada:"

            elif channel_id != 0:
              channel = bot.get_channel(channel_id)

              # Check if channel is a thread and get parent if it is
              if isinstance(channel, nextcord.Thread):
                logging.info(f'Channel is a thread. Getting parent channel.')
                channel = channel.parent  # Getting the parent channel of the thread

              logging.info(f'Channel Name: {channel.name}')
              content = f"# :tada: A new update is out! :tada:\n(This message gets automatically sent to the last channel where a command was run. If you want to have a dedicated channel for bot announcements and other events, please create one named `{event_channel_name}`)"
            else:
              channel = None

            # Send the message if a channel was found
            if channel:
              try:
                await channel.send(content=content, embed=embed)
              except nextcord.Forbidden:
                logging.info(
                    f"Could not send changelog to {guild.name}: insufficient permissions."
                )
              except Exception as e:
                logging.info(f"Could not send changelog to {guild.name}: {e}")

            else:
              logging.info(f"No suitable channel found in {guild.name}.")

        await bot.loop.run_in_executor(
            None,
            lambda guild=guild: supabase.table('Servers').update(
                {
                    'server_name': guild.name,
                    'members': guild.member_count
                }).eq('server_id', guild.id).execute())

        await asyncio.sleep(3)  # Prevent rate limiting


@bot.event
async def on_command_error(ctx, error):
  # Check if the command was not found
  if isinstance(error, CommandNotFound):
    # Get the invoked command
    invoked_command = ctx.invoked_with

    # Extract a list of all command names
    command_names = [command.name for command in bot.commands]

    # Find the closest match to the invoked command
    closest_match = get_close_matches(invoked_command,
                                      command_names,
                                      n=1,
                                      cutoff=0.6)

    # If a close match was found
    if closest_match:
      # Ask user if they meant the closest matching command
      await ctx.send(
          f"Command '{invoked_command}' not found. Did you mean '{closest_match[0]}'?"
      )
    else:
      # If no close match, just inform the user the command was not found
      await ctx.send(
          f"Command '{invoked_command}' not found. Use `wux help` for a list of commands."
      )

  # else:
  #     # If the error is not CommandNotFound, handle other errors (existing error handling logic)
  #     # ...


last_tutorial_views = {}


@bot.event
async def on_message(message):
  # Avoid responding to the bot's own messages
  if message.author == bot.user:
    return

  # If the message does not start with the bot prefix, ignore it
  if not message.content.startswith(prefix):
    return

  # If the message is sent in DMs, inform the user that the bot cannot be used in DMs and provide an invite link
  if isinstance(
      message.channel,
      nextcord.DMChannel) and message.author.id != 243351582052188170:
    await message.channel.send(
        "Sorry, only certain support commands can be used in DMs.\nPlease invite the bot to your own server, or join our Discord server here:\nhttps://discord.gg/N7AAZrhumR"
    )
    return

  # Check if the bot is locked
  if locked:
    response = await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table('Players').select('id').eq('admin', True).
        execute())

    # Assuming response.data is a list of dictionaries with helper 'id'
    all_admin_ids = [admin['id'] for admin in response.data]

    if message.author.id not in all_admin_ids:
      await message.channel.send(
          ":lock: The bot is currently locked. :lock:\nDon't worry, this usually means some sort of update, or a restart, and it will be unlocked in **`1-3 minutes`**."
      )
      return

  response = await asyncio.get_event_loop().run_in_executor(
      None, lambda: supabase.table(
          'Players').select('finished_tutorial', 'using_command').eq(
              'id', message.author.id).execute())

  if not response.data and message.content.split()[1].lower() != 'start':
    await message.reply(
        "Please use </start:1211522428455354398> begin your cultivation journey!"
    )
    return

  elif response.data and not response.data[0]['finished_tutorial']:
    # Disable buttons of the previous profile view for the user if it exists
    last_view = last_tutorial_views.get(message.author.id)

    view = TutorialView(message, tutorial_embeds, bot, message.author)

    if last_view:
      await last_view.disable_buttons()
      await last_view.message.edit(view=last_view)

    message_embed = await message.reply(content="Please finish the tutorial!",
                                        embed=tutorial_embeds[0],
                                        view=view)
    if view:
      view.message = message_embed  # Store the message in the view
      last_tutorial_views[ctx.author.id] = view

    await view.tutorial_done.wait()  # Wait for the tutorial to finish

    await asyncio.get_event_loop().run_in_executor(
        None,
        lambda: supabase.table('Players').update({
            'using_command': False,
            'open_dms': True,
            'finished_tutorial': True
        }).eq('id', message.author.id).execute())
    return

  if response.data:
    if response.data[0]['using_command']:
      await message.reply(
          "You are already in a command! Please finish it first!")
      return

  # Make the first word lowercase (assuming it's the prefix)
  content = message.content.split(' ', 1)
  if len(content) > 1:
    message.content = content[0].lower() + ' ' + content[1]

  # Process commands
  await bot.process_commands(message)

  # Remove the prefix from the message and save the command without the prefix to message_content
  # Extract the main command from the message content
  # Extract the command or alias from the message content if there are at least two words
  if len(message.content.split()) > 1:
    message_content = message.content.split()[1]
    command_aliases = {
        'dev': 'admin',
        'adv': 'adventure',
        'a': 'adventure',
        'cul': 'cultivate',
        'recipe': 'recipes',
        'me': 'me',
        'p': 'profile'
        # Add more aliases and their corresponding commands here
    }
    # Replace alias with the main command name if an alias is detected
    message_content = command_aliases.get(message_content, message_content)
    print("This is: ", message_content)
    if message_content in command_aliases.values(
    ) or message_content in bot.commands:
      # If the command is executed in a server/guild, add the guild/server name
      server_name = message.guild.name if message.guild else 'DMs'
      server_id = message.guild.id if message.guild else 0
      channel_id = message.channel.id

      data = {
          'user_id': message.author.id,
          'user_id_str': f'{message.author.id}',
          'username': message.author.name,
          'command_used': message_content,
          'server_name': server_name,
          'channel_id': channel_id,
          'server_id_str': f"{server_id}"
      }
      await bot.loop.run_in_executor(
          None, lambda: supabase.table('Log').insert(data).execute())


@bot.event
async def on_interaction(interaction: nextcord.Interaction):

  # Check if the interaction is a slash command and not in a guild
  if interaction.type == nextcord.InteractionType.application_command and not interaction.guild and interaction.user.id != 243351582052188170:
    if interaction.data['name'] == 'gethelp' or interaction.data[
        'name'] == 'close_ticket':
      await bot.process_application_commands(interaction)
    else:
      await interaction.response.send_message(
          "Sorry, only certain support commands can be  used in DMs.\nPlease invite the bot to your own server, or join our Discord server here:\nhttps://discord.gg/N7AAZrhumR"
      )
    return

  # Check if the bot is locked
  if locked and interaction.user.id != 243351582052188170:
    await interaction.response.send_message(
        ":lock: The bot is currently locked. :lock:\nDon't worry, this usually means some sort of update, or a restart, and it will be unlocked in **`1-3 minutes`**."
    )
    return

  if interaction.type == nextcord.InteractionType.application_command:
    response = await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table('Players').
        select('finished_tutorial', 'using_command').eq(
            'id', interaction.user.id).execute())

    if not response.data and interaction.data['name'] != 'start':
      await interaction.response.send_message(
          "Please use </start:1211522428455354398> or `wux start` begin your cultivation journey!"
      )
      return

    elif response.data and not response.data[0]['finished_tutorial']:
      # Disable buttons of the previous profile view for the user if it exists
      last_view = last_tutorial_views.get(interaction.user.id)

      view = TutorialView(interaction, tutorial_embeds, bot, interaction.user)

      if last_view:
        await last_view.disable_buttons()
        await last_view.message.edit(view=last_view)

      message_embed = await interaction.response.send_message(
          content="Please finish the tutorial!",
          embed=tutorial_embeds[0],
          view=view)
      if view:
        view.message = message_embed  # Store the message in the view
        last_tutorial_views[interaction.user.id] = view

      await view.tutorial_done.wait()  # Wait for the tutorial to finish

      await asyncio.get_event_loop().run_in_executor(
          None,
          lambda: supabase.table('Players').update({
              'using_command': False,
              'open_dms': True,
              'finished_tutorial': True
          }).eq('id', interaction.user.id).execute())
      return

    elif response.data and response.data[0]['using_command']:
      await interaction.response.send_message(
          "You are already in a command! Please finish it first!")
      return

  await bot.process_application_commands(interaction)

  # Handling Command Interactions
  if interaction.type == nextcord.InteractionType.application_command:
    # Adapted code for logging interaction data
    command_name = interaction.data[
        'name'] if 'name' in interaction.data else 'unknown_command'

    # If the interaction is executed in a server/guild, add the guild/server name
    server_name = interaction.guild.name if interaction.guild else 'DMs'
    server_id = interaction.guild.id if interaction.guild else 0
    channel_id = interaction.channel.id
    print("This is: ", command_name)
    data = {
        'user_id': interaction.user.id,
        'user_id_str': f"{interaction.user.id}",
        'username': interaction.user.name,
        'command_used': command_name,
        'server_name': server_name,
        'channel_id': channel_id,
        'server_id_str': f"{server_id}"
    }
    await bot.loop.run_in_executor(
        None, lambda: supabase.table('Log').insert(data).execute())

    # # Get server ID and cached settings
    # server_id = interaction.guild_id
    # settings = get_settings_cache(server_id) if server_id else None

    # if settings:
    #   operation_channel_id = settings.get('channel_id')
    #   # Check if the interaction is in the designated channel
    #   if operation_channel_id and interaction.channel_id != operation_channel_id:
    #     await interaction.response.send_message(
    #         f"This isnt the designated channel. Please use <#{operation_channel_id}>"
    #     )
    #     return


@bot.command(name="lock",
             help="Locks down the bot. Only usable by the bot owner.")
async def lock(ctx):
  global locked
  if ctx.author.id == 243351582052188170:
    locked = not locked
    state = ":lock: locked" if locked else ":unlock: unlocked"
    await ctx.send(f"Bot is now {state}.")
  else:
    await ctx.send("You do not have permission to use this command.")


if __name__ == '__main__':
  try:
    # Start the Flask app in a new thread
    flask_thread = Thread(target=run_webserver)
    flask_thread.start()

    token = os.getenv("TOKEN") or ""
    if token == "":
      raise Exception("Please add your token to the Secrets pane.")
    bot.load_extension("commands.admin")
    bot.load_extension("commands.help")
    # bot.load_extension("commands.recipes")
    bot.load_extension("commands.start")
    bot.load_extension("commands.gethelp")
    # bot.load_extension("commands.cultivate")
    bot.load_extension("commands.menu")
    # bot.load_extension("commands.adventure")
    bot.load_extension("commands.leaderboard")
    bot.load_extension("commands.bug")
    bot.load_extension("commands.suggest")
    bot.load_extension("commands.changelog")
    bot.run(token)

  except nextcord.HTTPException as e:
    if e.status == 429:
      print(
          "The Discord servers denied the connection for making too many requests"
      )
      print(
          "Get help from https://stackoverflow.com/questions/66724687/in-discord-py-how-to-solve-the-error-for-toomanyrequests"
      )
    else:
      raise e
