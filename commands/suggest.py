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

  async def submit_suggestion(self, followup_message, user_id, username, suggestion):
    response = await asyncio.get_event_loop().run_in_executor(
        None,
        lambda: supabase.table('Suggestions').insert({
            'user_id': user_id,
            'username': username,
            'suggestion': suggestion
        }).execute())

    if response:
      await followup_message("Your suggestion has been submitted successfully!")
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
      await followup_message("There was an error submitting your suggestion.")

  async def confirm_suggestion(self, interaction, suggestion):
    author = "Unknown"
    user_id = 0
    # If it's a text command, get the author from the context
    if isinstance(interaction, commands.Context):
      print("ITS A CTX COMMAND!")
      avatar_url = interaction.author.avatar.url if interaction.author.avatar else interaction.author.default_avatar.url
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
      avatar_url = interaction.user.avatar.url if interaction.user.avatar else interaction.user.default_avatar.url
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
      
    embed_color = nextcord.Color.blue()
    embed = nextcord.Embed(title=":notepad_spiral: Suggestion Confirmation",
                           description=f"**Your Suggestion:**\n{suggestion}",
                           color=embed_color)
    embed.set_author(name=author.name, icon_url=avatar_url)

    view = View()

    async def yes_callback(interaction):
      if interaction.user != author:
        await interaction.response.send_message(
            "You are not allowed to do this.", ephemeral=True)
        return
      await self.submit_suggestion(followup_message, author.id, str(author),
                                   suggestion)
      view.stop()

    async def no_callback(interaction):
      if interaction.user != author:
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

    await reply_message(embed=embed, view=view)

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
