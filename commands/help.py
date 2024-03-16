import nextcord
from nextcord.ext import commands
from nextcord.ui import View, Button


class Help(commands.Cog):

  def __init__(self, bot):
    self.bot = bot

  async def send_help_embed(self, ctx_or_interaction):
    embed = nextcord.Embed(
        title="Help",
        description=
        "Here are some commands you can use:\n</me:1217238385555410984> - View your information and available actions\n</gethelp:1217238298695696504> - Get help with the bot from a helper",
        color=nextcord.Color.blue())
    if isinstance(ctx_or_interaction, commands.Context):
      await ctx_or_interaction.send(embed=embed)
    elif isinstance(ctx_or_interaction, nextcord.Interaction):
      await ctx_or_interaction.response.send_message(embed=embed)

  @commands.command(name="help")
  async def help_command(self, ctx):
    await self.send_help_embed(ctx)

  @nextcord.slash_command(name="help", description="Show help commands")
  async def help_slash_command(self, interaction: nextcord.Interaction):
    await self.send_help_embed(interaction)


def setup(bot):
  bot.add_cog(Help(bot))
