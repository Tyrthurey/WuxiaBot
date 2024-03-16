import asyncio
import nextcord
from nextcord import slash_command
from nextcord.ext import commands
from nextcord.ui import Button, View
from functions.initialize import supabase, bot


async def get_players_data(type, page):
  data = await asyncio.get_event_loop().run_in_executor(
      None, lambda: supabase.table('Players').select('*').execute())

  if type == 'mortal':
    sorted_data = sorted(data.data,
                         key=lambda x: x['cultivation_level'],
                         reverse=True)
  elif type == 'immortal':
    sorted_data = sorted(
        [d for d in data.data if d['fastest_year_score'] is not None],
        key=lambda x: x['fastest_year_score'])
  elif type == 'ascended':
    sorted_data = sorted([d for d in data.data if d.get('ascensions')],
                         key=lambda x: x.get('ascensions', 0),
                         reverse=True)
  elif type == 'deceased':
    sorted_data = sorted([d for d in data.data if d.get('deaths')],
                         key=lambda x: x.get('deaths', 0),
                         reverse=True)

  # Paginate
  page_data = sorted_data[page * 10:(page + 1) * 10]
  return page_data


class LeaderboardView(View):

  def __init__(self, bot, type='immortal', page=0):
    super().__init__()
    self.bot = bot
    self.page = page
    self.type = type

  async def interaction_check(self, interaction: nextcord.Interaction) -> bool:
    # You can add checks here if necessary, like ensuring the user interacting is the one who asked for the leaderboard
    return True

  @nextcord.ui.button(label='Previous', style=nextcord.ButtonStyle.blurple)
  async def previous_button_callback(self, button, interaction):
    if self.page > 0:
      self.page -= 1
      await interaction.response.edit_message(embed=await self.get_page(),
                                              view=self)

  @nextcord.ui.button(label='Next', style=nextcord.ButtonStyle.blurple)
  async def next_button_callback(self, button, interaction):
    self.page += 1
    # This will be a non-blocking call, updating the message
    await interaction.response.edit_message(embed=await self.get_page(),
                                            view=self)

  @nextcord.ui.button(label='Toggle Rankings',
                      style=nextcord.ButtonStyle.green)
  async def toggle_rankings_button_callback(self, button, interaction):
    if self.type == 'mortal':
      self.type = 'immortal'
    elif self.type == 'immortal':
      self.type = 'ascended'
    elif self.type == 'ascended':
      self.type = 'deceased'
    else:  # 'deceased'
      self.type = 'mortal'
    self.page = 0  # Reset to the first page
    await interaction.response.edit_message(embed=await self.get_page(),
                                            view=self)

  async def get_page(self):
    players_data = await get_players_data(self.type, self.page)
    title = f"{self.type.capitalize()} Rankings"
    description = '\n'.join([
        f"**{idx+1}.** {player['username']} - {self.format_ranking(player)}"
        for idx, player in enumerate(players_data)
    ])
    embed = nextcord.Embed(title=title,
                           description=description or 'No players to show.',
                           color=nextcord.Color.blue())
    return embed

  def format_ranking(self, player):
    if self.type == 'mortal':
      return f"Cultivation: {player['cultivation_level']}"
    elif self.type == 'immortal':
      return f"Fastest Year: {player['fastest_year_score']}"
    elif self.type == 'ascended':
      return f"Ascensions: {player.get('ascensions', 0)}"
    elif self.type == 'deceased':
      return f"Deaths: {player.get('deaths', 0)}"


class MyBot(commands.Cog):

  def __init__(self, bot):
    self.bot = bot

  @slash_command(name="leaderboard", description="View the Heaven's rankings.")
  async def command_slash(self, interaction: nextcord.Interaction):
    await self.command(interaction)

  @commands.command(name="leaderboard", help="View the Heaven's rankings.")
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

    try:
      view = LeaderboardView(bot)
      embed = await view.get_page()  # You will implement this method

      # Determine how to send the message based on the type of command
      if isinstance(interaction, commands.Context):  # Text command
        await interaction.send(embed=embed, view=view)
      elif isinstance(interaction, nextcord.Interaction):  # Slash command
        await interaction.response.send_message(embed=embed, view=view)
      else:
        print("Command type not recognized.")
    except Exception as e:
      print(f"An error occurred: {e}")
      # If there's an error, send a simple message (you can replace this with more sophisticated error handling)
      if isinstance(interaction, commands.Context):
        await interaction.send(
            "An error occurred while trying to display the leaderboard.")
      elif isinstance(interaction, nextcord.Interaction):
        await interaction.response.send_message(
            "An error occurred while trying to display the leaderboard.")


# Remember to add your cog to the bot
def setup(bot):
  bot.add_cog(MyBot(bot))
