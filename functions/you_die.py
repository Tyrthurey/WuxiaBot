import asyncio
import nextcord
from nextcord.ext import commands
from functions.initialize import bot, supabase, get_event_channel


def get_ordinal(n):
  if 10 <= n % 100 <= 20:
    suffix = 'th'
  else:
    suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
  return str(n) + suffix


def get_cultivation_stage(cultivation):
  if cultivation == 0:
    return "**Mortal** Realm."
  elif 1 <= cultivation <= 64:
    stages = [
        "Earth Flesh",
        "Wood Skin",
        "Water Lung",
        "Fire Eye",  # Foundation
        "Blue Ocean",
        "Bedrock Island",
        "Forever Garden",
        "Eternal Bonfire",  # Consecration
        "Broken Lord",
        "Full Lord",
        "True Lord",
        "Perfect Lord",  # Lord
        "Earth",
        "Wood",
        "Water",
        "Fire"
    ]  # Ruler
    realms = [
        "Foundation", "Foundation", "Foundation", "Foundation", "Consecration",
        "Consecration", "Consecration", "Consecration", "Lord", "Lord", "Lord",
        "Lord", "Ruler", "Ruler", "Ruler", "Ruler"
    ]
    index = (cultivation - 1) // 4  # Every stage has four ranks
    rank = get_ordinal((cultivation - 1) % 4 + 1)
    return f"{rank} Rank, {stages[index]} Stage, of the {realms[index]} Realm."
  elif cultivation >= 65:
    return "Eternal Realm, Immortal Stage."


# Function to send a DM message to a user
async def send_death_message(player):
  try:
    user = await bot.fetch_user(player.id)

    player_cultivation_status = get_cultivation_stage(player.cultivation_level)

    # Constructing the embed message
    heart_demon_status = "None" if player.heart_demons == 0 else "Negligible" if player.heart_demons < 20 else "Very Low" if player.heart_demons < 40 else "Low" if player.heart_demons < 60 else "High" if player.heart_demons < 80 else "Very High" if player.heart_demons < 100 else "You Are Consumed"

    # Opens a DM channel with the user if it doesn't already exist
    dm_channel = await user.create_dm()

    # Create an embed message for death notification
    embed = nextcord.Embed(
        title="You Died!",
        description="Hopefully you will do better next time...",
        color=nextcord.Color.red())

    embed.add_field(name="__Stats Upon Death__",
                    value=f"**Sect:** {player.current_sect}\n"
                    f"**Years Spent:** {player.years_spent}\n"
                    f"**Spirit Stones Gathered:** {player.bal}\n"
                    f"**Cultivation:** {player_cultivation_status}\n"
                    f"**Heart Demons:** {heart_demon_status}",
                    inline=False)

    # dm the user an embed
    await dm_channel.send(embed=embed)

    await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table('Players').update({
            'max_cultivation_attained':
            player.cultivation_level,
        }).eq('id', player.id).execute())

    event_channel = await get_event_channel()
    print(f"Event channel: {event_channel}")

    death_embed = nextcord.Embed(
        title="A Cultivator Has Fallen",
        description=
        f"**{player.name}** from **{player.current_sect}** has met their demise...\n\n"
        f"**Years Spent:** {player.years_spent}\n"
        f"**Cultivation:** {player_cultivation_status}\n"
        f"**Deaths:** {player.deaths}",
        color=nextcord.Color.red())
    await event_channel.send(embed=death_embed)

  except Exception as e:
    print(f"An error occurred while sending DM: {e}")


# Function to send a DM message to a user
async def send_ascend_message(player):
  try:
    user = await bot.fetch_user(player.id)

    player_cultivation_status = get_cultivation_stage(player.cultivation_level)

    # Constructing the embed message
    heart_demon_status = "None" if player.heart_demons == 0 else "Negligible" if player.heart_demons < 20 else "Very Low" if player.heart_demons < 40 else "Low" if player.heart_demons < 60 else "High" if player.heart_demons < 80 else "Very High" if player.heart_demons < 100 else "You Are Consumed"

    # Opens a DM channel with the user if it doesn't already exist
    dm_channel = await user.create_dm()

    # Create an embed message for death notification
    embed = nextcord.Embed(
        title="You Ascended!",
        description=
        "The Heavens watch on with pride. You may now compete on the leaderboard. Use your **Karma** well.",
        color=nextcord.Color.green())

    embed.add_field(name="__Stats Upon Ascension__",
                    value=f"**Sect:** {player.current_sect}\n"
                    f"**Years Spent:** {player.years_spent}\n"
                    f"**Spirit Stones Gathered:** {player.bal}\n"
                    f"**Cultivation:** {player_cultivation_status}\n"
                    f"**Heart Demons:** {heart_demon_status}",
                    inline=False)

    # dm the user an embed
    await dm_channel.send(embed=embed)

    event_channel = await get_event_channel()
    print(f"Event channel: {event_channel}")

    ascend_embed = nextcord.Embed(
        title="Ascension Announcement",
        description=
        f"**{player.name}** from **{player.current_sect}** has ascended!\n\n"
        f"**Years Spent:** {player.years_spent}\n"
        f"**Ascensions:** {player.ascensions}",
        color=nextcord.Color.green())
    await event_channel.send(embed=ascend_embed)

    if player.max_cultivation_attained < player.cultivation_level:

      await asyncio.get_event_loop().run_in_executor(
          None, lambda: supabase.table('Players').update({
              'max_cultivation_attained':
              player.cultivation_level,
          }).eq('id', player.id).execute())

  except Exception as e:
    print(f"An error occurred while sending DM: {e}")
