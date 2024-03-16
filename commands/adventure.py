from nextcord.ext import commands
from nextcord.ext import menus
import nextcord
from nextcord import slash_command, SlashOption
from pydantic import aliases
from nextcord.ui import Button, View
import asyncio
from functions.initialize import supabase
from functions.cooldown_manager import cooldown_manager_instance as cooldowns
import random
from classes.Player import Player
from functions.initialize import ADVENTURE_OUTCOMES



def select_adventure_outcome():
  outcomes = []
  for outcome in ADVENTURE_OUTCOMES:
    outcomes.extend([outcome] * outcome["chance"])
  selected_outcome = random.choice(outcomes)
  return selected_outcome


class Adventure(commands.Cog):
  """Go on an adventure for the year!"""

  def __init__(self, bot):
    self.bot = bot

  @slash_command(name="adventure", description="Go on an adventure!")
  async def command_slash(self, interaction: nextcord.Interaction):
    await self.command(interaction)

  @commands.command(name="adventure",
                    aliases=["adv", "a"],
                    help="Go on an adventure!")
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

    command_name = 'adventure'
    cooldown_remaining = cooldowns.get_cooldown(user_id, command_name)

    if cooldown_remaining > 0:
      # Using an embed for cooldown message
      cooldown_embed = nextcord.Embed(
          title="Cooldown Alert!",
          description=
          f"This command is on cooldown. You can use it again in `{cooldown_remaining:.2f}` seconds.",
          color=nextcord.Color.red())
      await reply_message(embed=cooldown_embed)
      return

    cooldown = 10
    # Set the cooldown for the hunt command
    cooldowns.set_cooldown(user_id, command_name, cooldown)

    response = await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table('Players').select('*').eq('id', user_id).
        execute())

    
    player = Player(author, response)

    # Select an adventure outcome
    outcome = select_adventure_outcome()

    # Create an embed for the outcome message
    outcome_embed = nextcord.Embed(color=nextcord.Color.blue())

    # Example if-then logic for each outcome type
    if outcome['type'] == 'insight_treasure':
      outcome_embed.title = "Fortunate Discovery!"
      outcome_embed.description = outcome['message']
      # Additional logic for insight_treasure outcome

    elif outcome['type'] == 'wandering_master':
      outcome_embed.title = "Mysterious Encounter!"
      outcome_embed.description = outcome['message']
      # Additional logic for wandering_master outcome

    elif outcome['type'] == 'killed':
      outcome_embed.title = "Perilous Fate!"
      outcome_embed.description = outcome['message']
      # Additional logic for killed outcome

    elif outcome['type'] == 'spirit_stones_large':
      outcome_embed.title = "Tremendous Wealth!"
      outcome_embed.description = outcome['message']
      # Additional logic for spirit_stones_large outcome

    elif outcome['type'] in 'spirit_stones_low':
      outcome_embed.title = "Spirit Stones Found!"
      outcome_embed.description = outcome['message']
      # Additional logic for spirit_stones outcomes

    elif outcome['type'] in 'spirit_stones_decent':
      outcome_embed.title = "Spirit Stones Found!"
      outcome_embed.description = outcome['message']

    elif outcome['type'] == 'nothing':
      outcome_embed.title = "Unfortunate Journey"
      outcome_embed.description = outcome['message']
      # Additional logic for nothing outcome

    # Save player data
    await player.save_data()

    # Send the outcome message to the player
    await reply_message(embed=outcome_embed)


# Export the command function to be imported in main.py
def setup(bot):
  bot.add_cog(Adventure(bot))
