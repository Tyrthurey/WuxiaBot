import os
import json
from nextcord.ext import commands
from nextcord import Embed
from functions.initialize import supabase, bot, get_event_channel
import asyncio


# Function to check and give achievement
async def give_achievement(user_id: int, achievement_id: int):
  user = await bot.fetch_user(user_id)  # Resolve Discord user

  # Fetch user's achievements from the database
  user_data = await asyncio.get_event_loop().run_in_executor(
      None, lambda: supabase.table('Inventory').select('achievements').eq(
          'id', user_id).execute())
  user_achievements = user_data.data[0][
      'achievements'] if user_data.data else []

  # Check if the user already has the achievement
  if not any(ach['ach_id'] == achievement_id for ach in user_achievements):
    # Fetch achievement data from the database
    achievement_data = await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table('Achievements').select('*').eq(
            'ach_id', achievement_id).execute())
    if achievement_data.data:
      achievement = achievement_data.data[0]

      # Send the user a DM with the achievement
      embed = Embed(title=":tada::unlock: Achievement Gained: " +
                    achievement['ach_name'] + " :unlock::tada:",
                    description=achievement['ach_desc'],
                    color=0x00ff00)
      await user.send(embed=embed)

      
      # Notify in the event channel about the achievement gain
      event_channel = await get_event_channel()
      print(f"Event channel: {event_channel}")

      achievement_gain_embed = Embed(
          title="A Cultivator Has Gained a New Achievement",
          description=
          f"**{user.name}** has unlocked the achievement **{achievement['ach_name']}**.",
          color=0x00ff00)
      await event_channel.send(embed=achievement_gain_embed)

      # Add the achievement to the user's achievements and update the database
      user_achievements.append({'ach_id': achievement_id})
      await asyncio.get_event_loop().run_in_executor(
          None, lambda: supabase.table('Inventory').update({
              'achievements':
              user_achievements
          }).eq('id', user_id).execute())

      return True  # Achievement successfully given
    else:
      return False  # Achievement ID not found
  else:
    return False  # User already has the achievement
