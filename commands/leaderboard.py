import asyncio
import nextcord
from nextcord import slash_command, SlashOption
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

  def __init__(self, bot, author_id, type, page):
    super().__init__(timeout=120)
    self.bot = bot
    self.page = page
    self.type = type
    self.author_id = author_id

  async def on_timeout(self):
    for item in self.children:
      item.disabled = True  # Disable all buttons when the view times out
    # This assumes there's a message to edit; adapt as necessary for your setup
    await self.message.edit(view=self)

  async def interaction_check(self, interaction: nextcord.Interaction) -> bool:
    if interaction.user.id != self.author_id:
      # Send an ephemeral message if someone else tries to click the button
      await interaction.response.send_message("These buttons are not for you!",
                                              ephemeral=True)
      return False
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
        f"**{self.page * 10 + idx + 1}.** `{player['username']}` - {self.format_ranking(player)}"
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


class Leaderboard(commands.Cog):

  def __init__(self, bot):
    self.bot = bot

  @slash_command(name="leaderboard", description="View the Heaven's rankings.")
  async def command_slash(
      self,
      interaction: nextcord.Interaction,
      type: str = SlashOption(
          description="Choose the ranking type",
          default="immortal",
          choices=["mortal", "immortal", "ascended", "deceased"]),
      page: int = SlashOption(description="Page number", default=0)):
    await self.command(interaction, type, page)

  @commands.command(name="leaderboard",
                    aliases=["lb"],
                    help="View the Heaven's rankings.")
  async def command_text(self, ctx, *args):
    # Parsing arguments for text command
    leaderboard_types = ["mortal", "immortal", "ascended", "deceased"]
    type_arg = None
    page_arg = 0  # Default page

    if len(args) >= 1:
      type_input = args[0].lower()
      # Check for partial matches (at least 60% matching)
      for t in leaderboard_types:
        if t.startswith(type_input[:max(2, int(len(t) * 0.6))]):
          type_arg = t
          break

    if len(args) >= 2:
      try:
        # Interpret "2" as page 6, for example
        page_input = int(args[1]) - 1  # Convert to zero-based index
        page_arg = max(0, page_input)  # Ensure non-negative
      except ValueError:
        pass  # Ignore if the second argument is not an integer

    if not type_arg:
      type_arg = "immortal"

    await self.command(ctx, type_arg, page_arg)

  async def command(self, interaction, type, page):
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
      view = LeaderboardView(bot, author_id=user_id, type=type, page=page)
      embed = await view.get_page()  # You will implement this method

      # Determine how to send the message based on the type of command
      if isinstance(interaction, commands.Context):  # Text command
        message = await interaction.send(embed=embed, view=view)
        view.message = message
      elif isinstance(interaction, nextcord.Interaction):  # Slash command
        await interaction.response.send_message(embed=embed, view=view)
        view.message = await interaction.original_message()
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
  bot.add_cog(Leaderboard(bot))
