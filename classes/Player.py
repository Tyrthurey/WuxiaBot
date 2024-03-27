from functions.initialize import supabase
import logging
import asyncio
import random
import math
import os


class Player:

  def __init__(self, discord_user, response):
    self.discord_user = discord_user
    self.response = response
    self.load_data()

  def load_data(self):
    data = self.response.data[0] if self.response.data else {}

    self.deaths = data.get('deaths', 0)
    self.dead = data.get('dead', True)
    self.user_id = self.discord_user.id
    self.bal = data.get('bal', 0)
    self.chosen_talents = data.get('chosen_talents', ["0"])
    self.chosen_talent_names = data.get('chosen_talent_names',
                                        ["Chalk Spirit Channels"])

    self.ascensions = data.get('ascensions', 0)

    self.revived = data.get('revived', False)

    self.year_of_reincarnation = data.get('year_of_reincarnation', 0)

    self.total_bal = data.get('total_bal', 0)
    self.total_insights = data.get('total_insights', 0)
    self.total_wavering_hearts = data.get('total_wavering_hearts', 0)

    self.id = data.get('id', 0)

    self.demonic_ascensions = data.get('demonic_ascensions', 0)
    self.orthodox_ascensions = data.get('orthodox_ascensions', 0)

    self.lifeforce = data.get('lifeforce', 140)
    self.demonic = data.get('demonic', False)

    self.years_spent = data.get('years_spent', 0)
    self.fastest_year_score = data.get('fastest_year_score', None)

    self.current_sect = data.get('current_sect', 'None')

    self.karma = data.get('karma', 0)

    self.kills = data.get('kills', 0)

    self.cultivation_level = data.get('cultivation_level', 0)
    self.max_cultivation_attained = data.get('max_cultivation_attained', 0)
    self.heart_demons = data.get('heart_demons', 0)

    self.using_command = data.get('using_command', False)
    self.dm_cmds = data.get('dm_cmds', False)
    self.helper = data.get('helper', False)
    self.moderator = data.get('moderator', False)
    self.admin = data.get('admin', False)
    self.tutorial = data.get('tutorial', False)
    self.finished_tutorial = data.get('finished_tutorial', False)

    created_at_raw = data.get('created_at', None)
    if created_at_raw:
      from datetime import datetime
      created_at_datetime = datetime.strptime(created_at_raw,
                                              '%Y-%m-%dT%H:%M:%S.%f%z')
      self.created_at = created_at_datetime.strftime('%d/%m/%Y - %H:%M UTC')
    else:
      self.created_at = None

    self.displayname = data.get('displayname', 'Default')
    try:
      self.name = self.displayname if self.displayname != 'Default' else self.discord_user.name
    except AttributeError:
      try:
        self.name = self.discord_user.username
      except AttributeError:
        self.name = self.displayname

  async def update_bal(self):
    await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table('Players').update({
            'bal': self.bal
        }).eq('id', self.discord_user.id).execute())

  async def update_talents(self):
    await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table('Players').update(
            {
                'chosen_talents': self.chosen_talents,
                'chosen_talent_names': self.chosen_talent_names
            }).eq('id', self.id).execute())

  async def save_data(self):
    response = await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table('Players').update(
            {
                'orthodox_ascensions': self.orthodox_ascensions,
                'demonic_ascensions': self.demonic_ascensions,
                'demonic': self.demonic,
                'revived': self.revived,
                'lifeforce': self.lifeforce,
                'year_of_reincarnation': self.year_of_reincarnation,
                'deaths': self.deaths,
                'years_spent': self.years_spent,
                'dead': self.dead,
                'heart_demons': self.heart_demons,
                'current_sect': self.current_sect,
                'karma': self.karma,
                'bal': self.bal,
                'cultivation_level': self.cultivation_level,
                'total_bal': self.total_bal,
                'total_insights': self.total_insights,
                'total_wavering_hearts': self.total_wavering_hearts
            }).eq('id', self.discord_user.id).execute())
    if not response:
      raise Exception('Failed to update player save_data.')

  async def save_score(self):
    response = await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table('Players').update(
            {
                'orthodox_ascensions': self.orthodox_ascensions,
                'demonic_ascensions': self.demonic_ascensions,
                'deaths': self.deaths,
                'years_spent': self.years_spent,
                'ascensions': self.ascensions,
                'dead': self.dead,
                'heart_demons': self.heart_demons,
                'current_sect': self.current_sect,
                'karma': self.karma,
                'bal': self.bal,
                'fastest_year_score': self.fastest_year_score,
                'cultivation_level': self.cultivation_level
            }).eq('id', self.discord_user.id).execute())
    if not response:
      raise Exception('Failed to update player save_data.')

  async def download_player_talents(self, user_id):
    response = await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table('Inventory').select('settings').eq(
            'id', user_id).execute())
    if not response:
      raise Exception('Failed to download player talents.')
    return response

  async def download_player_settings(self, user_id):
    response = await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table('Inventory').select('settings').eq(
            'id', user_id).execute())
    if not response:
      raise Exception('Failed to download player settings.')
    return response

  async def download_player_unlocks(self, user_id):
    response = await asyncio.get_event_loop().run_in_executor(
        None,
        lambda: supabase.table('Inventory').select('unlocked_cosmetics').eq(
            'id', user_id).execute())
    if not response:
      raise Exception('Failed to download player unlocked cosmetics.')
    return response
