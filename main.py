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
from functions.give_title import give_title
from nextcord.ext import tasks
from pathlib import Path
from datetime import datetime, timedelta, timezone
from bs4 import BeautifulSoup
import requests
import json

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

        await asyncio.sleep(2)  # Prevent rate limiting

  # top_players_response = await asyncio.get_event_loop().run_in_executor(
  #     None, lambda: supabase.table('Players').select('*').order(
  #         'fastest_year_score', desc=False).limit(3).execute())

  # if top_players_response:
  #   top_players = top_players_response.data
  #   for index, player in enumerate(top_players, start=101):
  #     logging.info(f'Username Awarded: {player["username"]} - Index: {index}')
  #     player_id = player['id']
  #     # player_id = 243351582052188170  # for testing
  #     await give_title(player_id, index)
  #     await asyncio.sleep(1)  # Prevent rate limiting


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

  # If the message starts with any capitalization variation of 'wux', process it
  if message.content.lower().startswith(prefix):
    print(f"Message received: {message.content}")
    message.content = prefix.lower() + message.content[len(prefix):]
    print(f"Message content after processing: {message.content}")
  else:
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


previous_data = {}

# Based on GMT time
set_hour = 12
set_minute = 00



@tasks.loop(hours=24)
async def scrape_and_send_data():
  true = True
  # This function runs every 24 hours at 1pm GMT
  current_time = datetime.utcnow()
  if current_time.hour == set_hour:  # Check if it's 1pm GMT
    logging.info("Scraping data...")
    print("Scraping and sending data...")
    fiction_ids = [77238, 71319, 82770, 83298]
    for fiction_id in fiction_ids:
      logging.info(f"Scraping data for fiction ID {fiction_id}...")
      print(f"Scraping data for fiction ID: {fiction_id}")
      url = f'https://www.royalroad.com/fiction/{fiction_id}/'
      response = requests.get(url)

      if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        data_elements = soup.find_all('li',
                                      class_='bold uppercase font-red-sunglo')
        data_values = [element.text.strip() for element in data_elements]
        data_keys = [
            'TOTAL VIEWS', 'AVERAGE VIEWS', 'FOLLOWERS', 'FAVORITES',
            'RATINGS', 'PAGES'
        ]
        data = dict(zip(data_keys, data_values))

        # Extract the title
        title_element = soup.find('h1', class_='font-white')
        if title_element:
          title_text = title_element.text.strip()
          data['TITLE'] = title_text
        else:
          data['TITLE'] = 'Title not found'

        print(f"Data for fiction ID {fiction_id}: {data}")
        logging.info(f"Data for fiction ID {fiction_id}: {data}")

        overall_score_element = soup.find('li',
                                          class_='bold uppercase list-item',
                                          text='Overall Score')
        if overall_score_element:
          overall_score_span = overall_score_element.find_next_sibling(
              'li').find('span', class_='popovers')
          overall_score = overall_score_span[
              'data-content'] if overall_score_span else 'N/A'
          overall_score = overall_score.split('/')[0].strip()

        data['OVERALL SCORE'] = overall_score

        # Check if the text file exists, if not, create it
        if not os.path.exists(f'fic_data/scraped_data_{fiction_id}.txt'):
          with open(f'fic_data/scraped_data_{fiction_id}.txt', 'w') as file:
            file.write('{}')  # Create an empty JSON object in the file

        # Load previous data from the text file
        with open(f'fic_data/scraped_data_{fiction_id}.txt', 'r') as file:
          previous_data = json.load(file)

        change = 0

        outcome = [{"type": "text", "text": "No changes."}]
        for key in data:
          if key == "FOLLOWERS":
            if key in previous_data and data[key] != previous_data[key]:
              previous_value = previous_data[key]
              current_value = data[key]
              try:
                # Convert values to numbers for comparison
                previous_number = int(previous_value.replace(',', ''))
                current_number = int(current_value.replace(',', ''))
                change = current_number - previous_number
                if change > 0:
                  outcome = [{
                      "type": "text",
                      "text": "FOLLOWERS",
                      "style": {
                          "bold": true
                      }
                  }, {
                      "type": "text",
                      "text": " — "
                  }, {
                      "type": "text",
                      "text": "INCREASE",
                      "style": {
                          "bold": true
                      }
                  }, {
                      "type": "text",
                      "text": f": +{change}"
                  }]

                elif change < 0:
                  outcome = [{
                      "type": "text",
                      "text": "FOLLOWERS",
                      "style": {
                          "bold": true
                      }
                  }, {
                      "type": "text",
                      "text": " — "
                  }, {
                      "type": "text",
                      "text": "DECREASE",
                      "style": {
                          "bold": true
                      }
                  }, {
                      "type": "text",
                      "text": f": -{change}"
                  }]

              except ValueError:
                # Handle non-numeric data (like OVERALL SCORE)
                if previous_value != current_value:
                  print("Error")

        # Save new data to text file
        with open(f'fic_data/scraped_data_{fiction_id}.txt', 'w') as file:
          file.write(json.dumps(data, indent=4))

        payload = {
            "attachments": [{
                "color":
                "#36a64f",
                "blocks": [{
                    "type":
                    "rich_text",
                    "elements": [{
                        "type":
                        "rich_text_section",
                        "elements": [{
                            "type": "text",
                            "text": f"{data['TITLE']} — Statistics",
                            "style": {
                                "bold": true
                            }
                        }]
                    }]
                }, {
                    "type": "divider"
                }, {
                    "type":
                    "rich_text",
                    "elements": [{
                        "type":
                        "rich_text_list",
                        "style":
                        "bullet",
                        "indent":
                        0,
                        "border":
                        0,
                        "elements": [{
                            "type":
                            "rich_text_section",
                            "elements": [{
                                "type": "text",
                                "text": "TOTAL VIEWS",
                                "style": {
                                    "bold": true
                                }
                            }, {
                                "type": "text",
                                "text": f": {data['TOTAL VIEWS']}"
                            }]
                        }, {
                            "type":
                            "rich_text_section",
                            "elements": [{
                                "type": "text",
                                "text": "FOLLOWERS",
                                "style": {
                                    "bold": true
                                }
                            }, {
                                "type": "text",
                                "text": f": {data['FOLLOWERS']}"
                            }]
                        }, {
                            "type":
                            "rich_text_section",
                            "elements": [{
                                "type": "text",
                                "text": "FAVORITES",
                                "style": {
                                    "bold": true
                                }
                            }, {
                                "type": "text",
                                "text": f": {data['FAVORITES']}"
                            }]
                        }]
                    }]
                }, {
                    "type": "divider"
                }, {
                    "type":
                    "rich_text",
                    "elements": [{
                        "type": "rich_text_section",
                        "elements": outcome
                    }]
                }]
            }]
        }

        # Send message to Slack via webhook
        webhook_url = "https://hooks.slack.com/services/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"
        # # (for testing)
        # webhook_url = "https://hooks.slack.com/services/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"
        response = requests.post(webhook_url, json=payload)
        if response.status_code != 200:
          logging.info(
              f"Failed to send message to Slack. Status code: {response.status_code}"
          )
          print(
              f"Error sending message to Slack: {response.status_code} {response.text}"
          )

        await asyncio.sleep(10)
      else:
        logging.info(f"Failed to retrieve data for fiction ID {fiction_id}")
        print('Failed to retrieve the webpage')


@scrape_and_send_data.before_loop
async def before_scheduled_task():
  await bot.wait_until_ready()
  current_time = datetime.utcnow()
  target_time = current_time.replace(hour=set_hour,
                                     minute=set_minute,
                                     second=10,
                                     microsecond=0)
  if current_time.hour >= set_hour:  # If it's past 12pm GMT, schedule for the next day
    target_time += timedelta(days=1)
  seconds_until_start = (target_time - current_time).total_seconds()
  minutes_until_start = seconds_until_start / 60
  hours_until_start = minutes_until_start / 60
  print("TIME (SECONDS) UNTIL START: ", seconds_until_start)
  print("TIME (MINUTES) UNTIL START: ", minutes_until_start)
  print(f"TIME (HOURS) UNTIL START: {hours_until_start:.2f}")
  logging.info(f"TIME (HOURS) UNTIL START: {hours_until_start:.2f}")
  logging.info("Starting the scheduled task...")
  await asyncio.sleep(seconds_until_start)


scrape_and_send_data.start()

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
    bot.load_extension("commands.menu")
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
