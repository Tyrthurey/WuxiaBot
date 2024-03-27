import asyncio
import nextcord
from nextcord.ext import commands
from functions.initialize import bot, supabase, get_event_channel
from functions.give_achievement import give_achievement
from functions.give_title import give_title


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
async def send_death_message(player, reason):
  try:
    user = await bot.fetch_user(player.id)

    player_cultivation_status = get_cultivation_stage(player.cultivation_level)

    # Constructing the embed message
    heart_demon_status = "None" if player.heart_demons == 0 else "Negligible" if player.heart_demons < 20 else "Very Low" if player.heart_demons < 40 else "Low" if player.heart_demons < 60 else "High" if player.heart_demons < 80 else "Very High" if player.heart_demons < 100 else "You Are Consumed"

    # Opens a DM channel with the user if it doesn't already exist
    dm_channel = await user.create_dm()

    info_data = await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table('Info').select('*').execute())

    info_data = info_data.data[0]

    old_date = info_data['year']
    old_deaths = info_data['total_deaths']
    old_demonic_deaths = info_data['demonic_deaths']
    old_orthodox_deaths = info_data['orthodox_deaths']
    new_date = player.year_of_reincarnation + player.years_spent

    if player.demonic:
      allegiance = "Demonic"
      new_demonic_deaths = old_demonic_deaths + 1
      new_orthodox_deaths = old_orthodox_deaths
    else:
      allegiance = "Orthodox"
      new_demonic_deaths = old_demonic_deaths
      new_orthodox_deaths = old_orthodox_deaths + 1

    # Create an embed message for death notification
    embed = nextcord.Embed(
        title="You Died!",
        description="Hopefully you will do better next time...",
        color=nextcord.Color.red())

    embed.add_field(name="__Cause of Death__", value=reason, inline=False)

    embed.add_field(
        name="__Stats Upon Death__",
        value=f"**Sect:** {player.current_sect}\n"
        f"**Years Spent:** {player.years_spent}\n"
        f"**Current Year:** {new_date}\n"
        f"**Total Spirit Stones Gathered:** {player.total_bal}\n"
        f"**Total Insights:** {player.total_insights}\n"
        f"**Total Wavering Hearts:** {player.total_wavering_hearts}\n"
        f"**Cultivation:** {player_cultivation_status}\n"
        f"**Allegiance:** {allegiance}\n"
        f"**Heart Demons:** {heart_demon_status}",
        inline=False)

    if player.cultivation_level < 40:
      embed.add_field(
          name="__ERROR__",
          value="You were not powerful enough to advance history. It reverts.",
          inline=False)

    set_year = new_date if new_date > old_date else old_date

    if player.cultivation_level >= 40:
      await asyncio.get_event_loop().run_in_executor(
          None, lambda: supabase.table('Info').update(
              {
                  'year': set_year,
                  'total_deaths': old_deaths + 1,
                  'demonic_deaths': new_demonic_deaths,
                  'orthodox_deaths': new_orthodox_deaths
              }).eq('id', 1).execute())

      event_desc = f"{allegiance} Cultivator **{player.name}** died on Year **{new_date}** with a cultivation of **{player_cultivation_status}** ({player.cultivation_level}) and **{player.heart_demons}** heart demons."

      await asyncio.get_event_loop().run_in_executor(
          None,
          lambda: supabase.table('History').insert({
              'event_user': player.name,
              'event_user_id': player.id,
              'event_name': 'Death',
              'event_description': event_desc,
              'event_year': new_date
          }).execute())

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
        f"{reason}\n\n"
        f"**Years Spent:** {player.years_spent}\n"
        f"**Cultivation:** {player_cultivation_status}\n"
        f"**Allegiance:** {allegiance}\n"
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

    info_data = await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table('Info').select('*').execute())

    info_data = info_data.data[0]

    old_date = info_data['year']
    old_ascensions = info_data['total_ascensions']
    old_demonic_ascensions = info_data['demonic_ascensions']
    old_orthodox_ascensions = info_data['orthodox_ascensions']
    new_date = player.year_of_reincarnation + player.years_spent

    if player.demonic:
      allegiance = "Demonic"
      new_demonic_ascensions = old_demonic_ascensions + 1
      new_orthodox_ascensions = old_orthodox_ascensions
    else:
      allegiance = "Orthodox"
      new_demonic_ascensions = old_demonic_ascensions
      new_orthodox_ascensions = old_orthodox_ascensions + 1

    # Create an embed message for death notification
    embed = nextcord.Embed(
        title="You Ascended!",
        description=
        "The Heavens watch on with pride. You may now compete on the leaderboard. Use your **Karma** well.",
        color=nextcord.Color.green())

    embed.add_field(
        name="__Stats Upon Ascension__",
        value=f"**Sect:** {player.current_sect}\n"
        f"**Years Spent:** {player.years_spent}\n"
        f"**Current Year:** {new_date}\n"
        f"**Total Spirit Stones Gathered:** {player.total_bal}\n"
        f"**Total Insights:** {player.total_insights}\n"
        f"**Total Wavering Hearts:** {player.total_wavering_hearts}\n"
        f"**Cultivation:** {player_cultivation_status}\n"
        f"**Allegiance:** {allegiance}\n"
        f"**Heart Demons:** {heart_demon_status}",
        inline=False)

    set_year = new_date if new_date > old_date else old_date

    await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table('Info').update(
            {
                'year': set_year,
                'total_ascensions': old_ascensions + 1,
                'demonic_ascensions': new_demonic_ascensions,
                'orthodox_ascensions': new_orthodox_ascensions,
            }).eq('id', 1).execute())

    event_desc = f"{allegiance} Cultivator **{player.name}** ascended on Year **{new_date}**."

    await asyncio.get_event_loop().run_in_executor(
        None,
        lambda: supabase.table('History').insert({
            'event_user': player.name,
            'event_user_id': player.id,
            'event_name': 'Ascension',
            'event_description': event_desc,
            'event_year': new_date
        }).execute())

    # dm the user an embed
    await dm_channel.send(embed=embed)

    await give_title(player.id, 2)

    if player.demonic:
      await give_title(player.id, 3)

    if player.years_spent < 100:
      await give_achievement(player.id, 1)

    if player.years_spent > 1000:
      await give_achievement(player.id, 2)

    event_channel = await get_event_channel()
    print(f"Event channel: {event_channel}")

    ascend_embed = nextcord.Embed(
        title="Ascension Announcement",
        description=
        f"**{player.name}** from **{player.current_sect}** has ascended!\n\n"
        f"**Allegiance:** {allegiance}\n"
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
