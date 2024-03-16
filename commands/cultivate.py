from nextcord.ext import commands
from nextcord.ext import menus
import nextcord
from nextcord import slash_command, SlashOption
from pydantic import aliases
from nextcord.ui import Button, View
import asyncio
from functions.initialize import supabase
import random


class CultivateCog(commands.Cog, name="Cultivate"):
  """Cultivate!"""

  def __init__(self, bot):
    self.bot = bot
    self.realm_stages = [
        ("Foundation", ["Earth Flesh", "Wood Skin", "Water Lung", "Fire Eye"]),
        ("Consecration",
         ["Blue Ocean", "Bedrock Island", "Forever Garden", "Copper Roof"]),
        ("Lord", ["Broken Lord", "Full Lord", "True Lord", "Perfect Lord"]),
        ("Ruler", ["Earth", "Wood", "Water",
                   "Fire"]), ("Eternal", ["Immortal"])
    ]

  async def get_realm_stage(self, level):
    realm_index = level // 25  # Determine the realm index
    stage_index = (level %
                   25) // 5  # Determine the stage index within the realm
    rank_index = (level % 5) + 1  # Determine the rank within the stage

    realm, stages = self.realm_stages[realm_index]
    stage = stages[stage_index] if stage_index < len(stages) else "Immortal"

    return realm, stage, rank_index

  @slash_command(name="cultivate", description="Cultivate!")
  async def command_slash(self, interaction: nextcord.Interaction):
    await self.command(interaction)

  @commands.command(name="cultivate", aliases=["cul"], help="cultivate!")
  async def command_text(self, ctx):
    await self.command(ctx)

  async def command(self, interaction):
    print("COMMAND TRIGGERED")
    author = "Unknown"
    user_id = 0
    # If it's a text command, get the author from the context
    if isinstance(interaction, commands.Context):
      print("ITS A CTX COMMAND!")
      user_id = interaction.author.id
      author = interaction.author
      channel = interaction.channel
      channel_send = interaction.send
      edit_message = None
      edit_after_defer = None
      reply_message = interaction.reply
      delete_message = None
      followup_message = interaction.reply
      send_message = interaction.send
    # If it's a slash command, get the author from the interaction
    elif isinstance(interaction, nextcord.Interaction):
      print("ITS AN INTERACTION!")
      user_id = interaction.user.id
      author = interaction.user
      channel = interaction.channel
      edit_message = interaction.edit_original_message
      edit_after_defer = interaction.response.edit_message
      delete_message = interaction.delete_original_message
      followup_message = interaction.followup.send
      reply_message = interaction.response.send_message
      channel_send = interaction.channel.send
      send_message = interaction.response.send_message
    else:
      print("SOMETHING BROKE HORRIBLY")

    response = await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table('Players').select('*').eq('id', user_id).
        execute())

    if not response.data:
      await reply_message(
          "You are not registered. Please use </start:1211522428455354398>")

    # Extract cultivation level from the response
    cultivation_level = response.data[0].get('cultivation_level', 0)

    heart_demons = response.data[0].get('heart_demons', 0)

    # Determine if the cultivator gains an extra level due to insight
    # 80% chance for 1 level, 20% chance for 2 levels
    level_increase = 1 if random.random() < 0.8 else 2

    # Determine if the cultivator's heart demon score increases by 5 or 15
    # 70% chance for 5 points, 30% chance for 15 points
    heart_demon_increase = 5 if random.random() < 0.7 else 15

    if cultivation_level == 100:
      await reply_message(
          "You have achieved the pinnacle of cultivation, transcending into the realm of the Immortals. Congratulations!"
      )
    else:
      cultivation_level += level_increase
      heart_demons += heart_demon_increase

      # Update the player's cultivation level and heart demon score in the database
      await asyncio.get_event_loop().run_in_executor(
          None,
          lambda: supabase.table('Players').update({
              'cultivation_level': cultivation_level,
              'heart_demons': heart_demons
          }).eq('id', user_id).execute())

      realm, stage, rank = await self.get_realm_stage(cultivation_level)

      if heart_demon_increase == 15:
        demon_msg = f"\n**Stress!** You overtaxed yourself and suffered backlash!  **+15** heart demons.\nYour heart demons are now **{heart_demons}**."
      else:
        demon_msg = f"\nYour heart demons are now **{heart_demons}**."

      if cultivation_level >= 100:
        msg = f"**Breakthrough!** You have broken through into the **Eternal** Realm! Congratulations on your ascension!"
      elif level_increase == 2:
        msg = f"**Insight!** You've gained **{level_increase}** insight!\nYou achieved **{realm}** Realm, **{stage}** Stage, Rank **{rank}**."
      else:
        msg = f"You've gained **{level_increase}** insight.\nYou achieved **{realm}** Realm, **{stage}** Stage, Rank **{rank}**."

      msg = msg + demon_msg
      await reply_message(msg)


# Export the command function to be imported in main.py
def setup(bot):
  bot.add_cog(CultivateCog(bot))
