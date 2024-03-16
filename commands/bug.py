import asyncio
import logging
import os
import nextcord
from nextcord import slash_command
from nextcord.ext import commands
from nextcord.ui import Button, View
from functions.initialize import supabase, bot
from notion_client import Client

notion = Client(auth=os.getenv("NOTION_SECRET") or "")

project_board_id = "5acfaa5525724577b25004b74e9a22b0"
logging.basicConfig(level=logging.INFO)


class BugReport(commands.Cog):

  def __init__(self, bot):
    self.bot = bot

  # Helper function to handle the bug submission
  async def submit_bug(self, ctx, user_id, username, bug_description):
    # Insert the bug into the Supabase database
    response = await ctx.bot.loop.run_in_executor(
        None, lambda: supabase.table('BugReports').insert(
            {
                'user_id': user_id,
                'username': username,
                'bug_description': bug_description
            }).execute())

    if response:
      await ctx.send("Your bug report has been submitted successfully!")
      notion.pages.create(parent={"database_id": project_board_id},
                          properties={
                              "Name": {
                                  "title": [{
                                      "text": {
                                          "content": username
                                      }
                                  }]
                              },
                              "UserID": {
                                  "rich_text": [{
                                      "text": {
                                          "content": str(user_id)
                                      }
                                  }]
                              },
                              "Description": {
                                  "rich_text": [{
                                      "text": {
                                          "content": bug_description
                                      }
                                  }]
                              },
                              "Category": {
                                  "select": {
                                      "name": "Bug Reports"
                                  }
                              }
                          })
    else:
      await ctx.send("There was an error submitting your bug report.")

  # Function to create the confirmation embed
  async def confirm_bug(self, ctx, bug_description):
    avatar_url = ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url
    embed_color = nextcord.Color.blue()
    embed = nextcord.Embed(
        title="Bug Report Confirmation",
        description=f"**Your Bug Report:**\n{bug_description}",
        color=embed_color)
    embed.set_author(name=ctx.author.display_name, icon_url=avatar_url)

    view = View()

    async def yes_callback(interaction):
      if interaction.user != ctx.author:
        await interaction.response.send_message(
            "You are not allowed to do this.", ephemeral=True)
        return
      await self.submit_bug(ctx, ctx.author.id, str(ctx.author),
                            bug_description)
      view.stop()

    async def no_callback(interaction):
      if interaction.user != ctx.author:
        await interaction.response.send_message(
            "You are not allowed to do this.", ephemeral=True)
        return
      await interaction.response.send_message("Bug report cancelled.",
                                              ephemeral=True)
      view.stop()

    yes_button = Button(style=nextcord.ButtonStyle.green, label="Yes")
    yes_button.callback = yes_callback
    view.add_item(yes_button)

    no_button = Button(style=nextcord.ButtonStyle.red, label="No")
    no_button.callback = no_callback
    view.add_item(no_button)

    await ctx.send(embed=embed, view=view)

  @slash_command(name="bug", description="Report a bug to the developers.")
  async def bug_command_slash(self, interaction: nextcord.Interaction,
                              bug: str):
    await self.confirm_bug(interaction, bug)

  @commands.command(
      name="bug",
      help="Report a bug to the developers.\n\nUsage: `!bug <bug description>`"
  )
  async def bug_command_text(self, ctx, *, bug):
    await self.confirm_bug(ctx, bug)


# Export the command function to be imported in main.py
def setup(bot):
  bot.add_cog(BugReport(bot))
