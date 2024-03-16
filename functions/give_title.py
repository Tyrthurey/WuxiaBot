import os
import json
from nextcord.ext import commands
from nextcord import Embed
from functions.initialize import supabase, bot, get_event_channel
import asyncio


# Function to check and give title
async def give_title(user_id: int, title_id: int):
  user = await bot.fetch_user(user_id)  # Resolve Discord user

  # Fetch user's titles from the database
  user_data = await asyncio.get_event_loop().run_in_executor(
      None, lambda: supabase.table('Inventory').select('titles').eq(
          'id', user_id).execute())
  user_titles = user_data.data[0]['titles'] if user_data.data else []

  # Check if the user already has the title
  if not any(title['title_id'] == title_id for title in user_titles):
    # Fetch title data from the database
    title_data = await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table('Titles').select('*').eq(
            'title_id', title_id).execute())
    if title_data.data:
      title = title_data.data[0]

      # Send the user a DM with the title
      embed = Embed(title=":tada: Title Gained: " + title['title_name'] +
                    " :tada:",
                    description=title['title_desc'],
                    color=0x00ff00)
      await user.send(embed=embed)

      # Notify in the event channel about the title gain
      event_channel = await get_event_channel()
      print(f"Event channel: {event_channel}")

      title_gain_embed = Embed(
          title="A Cultivator Has Gained a New Title",
          description=
          f"**{user.name}** has been bestowed with the title **{title['title_name']}**.",
          color=0x00ff00)
      await event_channel.send(embed=title_gain_embed)

      # Add the title to the user's titles and update the database
      user_titles.append({'title_id': title_id})
      await asyncio.get_event_loop().run_in_executor(
          None,
          lambda: supabase.table('Inventory').update({
              'titles': user_titles
          }).eq('id', user_id).execute())

      return True  # title successfully given
    else:
      return False  # title ID not found
  else:
    return False  # User already has the title
