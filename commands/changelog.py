import nextcord
from nextcord import ButtonStyle
from nextcord.ext import commands
from nextcord.ui import Button, View
from functions.initialize import supabase
import asyncio
from datetime import datetime, timezone


class ChangelogView(View):

  def __init__(self, cog, changelog_id, max_changelog_id):
    super().__init__(timeout=180)  # Adjust timeout as needed
    self.cog = cog
    self.changelog_id = changelog_id
    self.max_changelog_id = max_changelog_id

  @nextcord.ui.button(label="Previous", style=ButtonStyle.gray)
  async def previous(self, button: Button, interaction: nextcord.Interaction):
    if self.changelog_id > 1:
      self.changelog_id -= 1
      changelog = await self.cog.get_changelog_by_number(self.changelog_id)
      await self.cog.edit_changelog_embed(interaction,
                                          changelog,
                                          max_id=self.max_changelog_id,
                                          view=self)

    else:
      await interaction.response.send_message(
          "This is the first changelog entry.", ephemeral=True)

  @nextcord.ui.button(label="Next", style=ButtonStyle.gray)
  async def next(self, button: Button, interaction: nextcord.Interaction):
    if self.changelog_id < self.max_changelog_id:
      self.changelog_id += 1
      changelog = await self.cog.get_changelog_by_number(self.changelog_id)
      await self.cog.edit_changelog_embed(interaction,
                                          changelog,
                                          max_id=self.max_changelog_id,
                                          view=self)
    else:
      await interaction.response.send_message(
          "This is the latest changelog entry.", ephemeral=True)


class ChangelogCog(commands.Cog):

  def __init__(self, bot):
    self.bot = bot
    self.supabase = supabase

  async def get_changelog_by_number(self, number):
    response = await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table('Changelog').select('*').eq('id', number).
        execute())
    if response:
      data = response.data
      if data:
        return data[0]
    return None

  async def changelog_handler(self, context):
    result = await self.get_latest_changelog()

    if result:
      max_id = result.get('id', 1)
      await self.send_changelog_embed(context, result, max_id)
    else:
      await self.send_message(context, content="No changelog found.")

  @nextcord.slash_command(name="changelog",
                          description="View the changelog entries")
  async def changelog_slash(self, interaction: nextcord.Interaction):
    await self.changelog_handler(interaction)

  @commands.command()
  async def changelog(self, ctx):
    await self.changelog_handler(ctx)

  async def send_changelog_embed(self, context, changelog, max_id, view=None):
    embed = nextcord.Embed(title=changelog['title'],
                           description=changelog['description'],
                           color=nextcord.Color.blue())
    timestamp = datetime.fromisoformat(
        changelog['date']).replace(tzinfo=timezone.utc).timestamp()
    embed.add_field(name="Date", value=f"<t:{int(timestamp)}:f>", inline=False)
    embed.set_footer(text=f"Cultivating Insanity Changelog #{changelog['id']}")
    if view is None:
      # If max_id is not None, it means we have navigation capability
      if max_id is not None:
        view = ChangelogView(self,
                             changelog_id=changelog['id'],
                             max_changelog_id=max_id)
    await self.send_message(context, embed=embed, view=view)

  async def edit_changelog_embed(self, context, changelog, max_id, view=None):
    embed = nextcord.Embed(title=changelog['title'],
                           description=changelog['description'],
                           color=nextcord.Color.blue())
    timestamp = datetime.fromisoformat(
        changelog['date']).replace(tzinfo=timezone.utc).timestamp()
    embed.add_field(name="Date", value=f"<t:{int(timestamp)}:f>", inline=False)
    embed.set_footer(text=f"Cultivating Insanity Changelog #{changelog['id']}")
    if view is None:
      # If max_id is not None, it means we have navigation capability
      if max_id is not None:
        view = ChangelogView(self,
                             changelog_id=changelog['id'],
                             max_changelog_id=max_id)
    await self.edit_message(context, embed=embed, view=view)

  async def get_latest_changelog(self):
    response = await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table('Changelog').select('*').order(
        'date', desc=True).limit(1).execute())
    data = response.data
    return data[0] if data else None

  async def send_message(self, context, content=None, embed=None, view=None):
    if isinstance(context, commands.Context):
      await context.send(content=content, embed=embed, view=view)
    elif isinstance(context, nextcord.Interaction):
      await context.response.send_message(content=content,
                                          embed=embed,
                                          view=view,
                                          ephemeral=False)

  async def edit_message(self, context, content=None, embed=None, view=None):
    if isinstance(context, commands.Context):
      await context.edit(content=content, embed=embed, view=view)
    elif isinstance(context, nextcord.Interaction):
      await context.response.edit_message(content=content,
                                          embed=embed,
                                          view=view)


def setup(bot):
  bot.add_cog(ChangelogCog(bot))
