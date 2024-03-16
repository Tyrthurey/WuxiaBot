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


class Suggestion(commands.Cog):

  def __init__(self, bot):
    self.bot = bot

  async def submit_suggestion(self, ctx, user_id, username, suggestion):
    response = await ctx.bot.loop.run_in_executor(
        None,
        lambda: supabase.table('Suggestions').insert({
            'user_id': user_id,
            'username': username,
            'suggestion': suggestion
        }).execute())

    if response:
      await ctx.send("Your suggestion has been submitted successfully!")
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
                                          "content": suggestion
                                      }
                                  }]
                              },
                              "Category": {
                                  "select": {
                                      "name": "Suggestions"
                                  }
                              }
                          })
    else:
      await ctx.send("There was an error submitting your suggestion.")

  async def confirm_suggestion(self, ctx, suggestion):
    avatar_url = ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url
    embed_color = nextcord.Color.blue()
    embed = nextcord.Embed(title=":notepad_spiral: Suggestion Confirmation",
                           description=f"**Your Suggestion:**\n{suggestion}",
                           color=embed_color)
    embed.set_author(name=ctx.author.display_name, icon_url=avatar_url)

    view = View()

    async def yes_callback(interaction):
      if interaction.user != ctx.author:
        await interaction.response.send_message(
            "You are not allowed to do this.", ephemeral=True)
        return
      await self.submit_suggestion(ctx, ctx.author.id, str(ctx.author),
                                   suggestion)
      view.stop()

    async def no_callback(interaction):
      if interaction.user != ctx.author:
        await interaction.response.send_message(
            "You are not allowed to do this.", ephemeral=True)
        return
      await interaction.response.send_message("Suggestion cancelled.",
                                              ephemeral=False)
      view.stop()

    yes_button = Button(style=nextcord.ButtonStyle.green, label="Yes")
    yes_button.callback = yes_callback
    view.add_item(yes_button)

    no_button = Button(style=nextcord.ButtonStyle.red, label="No")
    no_button.callback = no_callback
    view.add_item(no_button)

    await ctx.send(embed=embed, view=view)

  @slash_command(name="suggest",
                 description="Submit a suggestion to the server.")
  async def suggest_command_slash(self, interaction: nextcord.Interaction,
                                  suggestion: str):
    await self.confirm_suggestion(interaction, suggestion)

  @commands.command(
      name="suggest",
      aliases=["suggestion", "sugg"],
      help="Submit a suggestion.\n\nUsage: `suggest <suggestion>`")
  async def suggest_command_text(self, ctx, *, suggestion):
    await self.confirm_suggestion(ctx, suggestion)


def setup(bot):
  bot.add_cog(Suggestion(bot))
