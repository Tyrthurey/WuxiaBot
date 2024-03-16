from nextcord.ext import commands
from nextcord.ext import menus
import nextcord
from nextcord import slash_command, SlashOption
from pydantic import aliases
from nextcord.ui import Button, View
import asyncio
from functions.initialize import supabase


class ButtonConfirm(menus.ButtonMenu):

  def __init__(self, msg, user_id, followup_message, reply_message):
    super().__init__(timeout=30.0, clear_buttons_after=True)
    self.reply_message = reply_message
    self.followup_message = followup_message
    self.user_id = user_id
    self.msg = msg
    self.result = None

  async def send_initial_message(self, ctx, channel):
    embed = nextcord.Embed(title="Admin Interface")
    embed.add_field(name="Field 1", value="Dummy Value 1", inline=False)
    embed.add_field(name="Field 2", value="Dummy Value 2", inline=False)
    embed.add_field(name="Field 3", value="Dummy Value 3", inline=False)
    embed.add_field(name="Field 4", value="Dummy Value 4", inline=False)
    return await self.reply_message(embed=embed, view=self)

  @nextcord.ui.button(emoji="1️⃣")
  async def do_one(self, button, interaction):
    if interaction.user.id != self.user_id:
      await interaction.response.send_message(
          "You are not allowed to interact with this.", ephemeral=True)
      return
    self.result = 1
    await self.followup_message(f"{self.result}")

  @nextcord.ui.button(emoji="2️⃣")
  async def do_two(self, button, interaction):
    if interaction.user.id != self.user_id:
      await interaction.response.send_message(
          "You are not allowed to interact with this.", ephemeral=True)
      return
    self.result = 2
    await self.followup_message(f"{self.result}")

  @nextcord.ui.button(emoji="❌")
  async def do_deny(self, button, interaction):
    if interaction.user.id != self.user_id:
      await interaction.response.send_message(
          "You are not allowed to interact with this.", ephemeral=True)
      return
    self.result = 0
    await self.followup_message(f"{self.result}")

  async def prompt(self, ctx, type):
    if type == "ctx":
      await menus.Menu.start(self, ctx, wait=True)
    elif type == "interaction":
      await menus.Menu.start(self, interaction=ctx, wait=True)
    # return self.result


class Admin(commands.Cog, name="Developer"):
  """Opens the admin panel. Developer use only"""

  def __init__(self, bot):
    self.bot = bot

  @slash_command(name="admin", description="Makes you an admin!")
  async def command_slash(self, interaction: nextcord.Interaction):
      await self.command(interaction)

  @commands.command(name="admin", aliases=["dev"], help="Makes you an admin!")
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
      menu = ButtonConfirm("Admin Interface", user_id, followup_message,
                           reply_message).prompt(interaction, "ctx")
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
      menu = ButtonConfirm("Admin Interface", user_id, followup_message,
                           reply_message).prompt(interaction, "interaction")
    else:
      print("SOMETHING BROKE HORRIBLY")

    response = await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table('Players').select('id').eq('admin', True).
        execute())

    # Assuming response.data is a list of dictionaries with helper 'id'
    all_admin_ids = [admin['id'] for admin in response.data]

    if user_id not in all_admin_ids:
      await reply_message('Nope, nice try tho!')
      return

    await menu

    # await followup_message(f"You said: {confirm}")


# Export the command function to be imported in main.py
def setup(bot):
  bot.add_cog(Admin(bot))
