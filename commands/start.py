from nextcord.ext import commands
from functions.initialize import supabase
import nextcord
from nextcord import slash_command
from nextcord.ui import Button, View
import asyncio
from functions.initialize import bot, prefix, tutorial_embeds
import random
from functions.give_achievement import give_achievement
import logging
import requests

logging.basicConfig(level=logging.INFO)


class TutorialView(nextcord.ui.View):

  def __init__(self, interaction, tutorial_embeds, bot, author):
    super().__init__(timeout=300)
    self.author = author
    self.interaction = interaction
    self.bot = bot
    self.tutorial_embeds = tutorial_embeds
    self.current_index = 0
    self.tutorial_done = asyncio.Event()

  async def disable_buttons(self):
    for item in self.children:
      if isinstance(item, Button):
        item.disabled = True

  async def interaction_check(self, interaction):
    return interaction.user == self.author

  @nextcord.ui.button(label="Continue", style=nextcord.ButtonStyle.green)
  async def continue_button(self, button: nextcord.ui.Button,
                            interaction: nextcord.Interaction):
    # Move to the next tutorial message
    self.current_index += 1
    if self.current_index < len(self.tutorial_embeds):
      await interaction.message.edit(
          embed=self.tutorial_embeds[self.current_index], view=self)
    else:
      # End of tutorial, remove buttons
      await interaction.message.edit(
          content=":tada: Tutorial completed! :tada: ", view=None)
      self.tutorial_done.set()  # Signal that the tutorial is done
      # Here you can call your dungeon logic or any other post-tutorial logic


class StartCog(commands.Cog):

  def __init__(self, bot):
    self.bot = bot

  @slash_command(
      name="start",
      description=
      "Starts the game and creates a profile for you if it doesn't exist.")
  async def start_slash(self, interaction: nextcord.Interaction):
    await self.start(interaction)

  @commands.command(
      name="start",
      help="Starts the game and creates a profile for you if it doesn't exist."
  )
  async def start_text(self, ctx):
    await self.start(ctx)

  async def start(self, interaction):
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
        None, lambda: supabase.table('Players').select('id').eq('id', user_id).
        execute())

    if response.data:
      await reply_message(
          "You have already started the game and your profile exists. Use `/help` to see available commands."
      )
    else:
      print("---------------------------------------")
      print("A NEW HAND HAS TOUCHED THE BEACON")
      print(f"ALL HAIL THE NEWBIE: {author}")
      print("---------------------------------------")
      admin_id = 243351582052188170
      admin = await bot.fetch_user(admin_id)
      guild = interaction.guild if hasattr(
          interaction, 'guild') and interaction.guild else "DMs"
      guild_id = interaction.guild.id if hasattr(
          interaction, 'guild') and interaction.guild else None
      await admin.send(
          f"A NEW HAND HAS TOUCHED THE BEACON\nALL HAIL THE NEWBIE <@{user_id}> (**{author}**) JOINING FROM **{guild}** ({guild_id})."
      )

      true = True

      payload = {
          "attachments": [{
              "color":
              "#36a64f",
              "blocks": [{
                  "type":
                  "rich_text",
                  "elements": [{
                      "type":
                      "rich_text_section",
                      "elements": [{
                          "type": "text",
                          "text": f"{author}",
                          "style": {
                              "bold": true
                          }
                      }, {
                          "type":
                          "text",
                          "text":
                          " has joined the cultivation race from "
                      }, {
                          "type": "text",
                          "text": f"{guild}",
                          "style": {
                              "bold": true
                          }
                      }, {
                          "type": "text",
                          "text": f" ({guild_id})."
                      }]
                  }]
              }]
          }]
      }

      # Send message to Slack via webhook
      webhook_url = "https://hooks.slack.com/services/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"
      response = requests.post(webhook_url, json=payload)
      if response.status_code != 200:
        logging.info(
            f"Failed to send message to Slack. Status code: {response.status_code}"
        )
        print(
            f"Error sending message to Slack: {response.status_code} {response.text}"
        )

      initial_data = {
          'id': user_id,
          'str_id': f'{user_id}',
          'username': author.name,
          'using_command': True
      }
      await asyncio.get_event_loop().run_in_executor(
          None,
          lambda: supabase.table('Players').insert(initial_data).execute())

      view = TutorialView(interaction, tutorial_embeds, self.bot, author)
      await reply_message(content="", embed=tutorial_embeds[0], view=view)
      await view.tutorial_done.wait()  # Wait for the tutorial to finish

      await asyncio.get_event_loop().run_in_executor(
          None,
          lambda: supabase.table('Players').update({
              'using_command': False,
              'open_dms': True,
              'finished_tutorial': True
          }).eq('id', user_id).execute())

      try:
        await give_achievement(user_id, 0)
      except nextcord.Forbidden:

        class TestPermissionsView(nextcord.ui.View):

          def __init__(self, channel, user_id):
            super().__init__(timeout=300)
            self.user_id = user_id
            self.channel = channel

          @nextcord.ui.button(label="Test DM Permissions",
                              style=nextcord.ButtonStyle.blurple)
          async def test_permissions_button(self, button: nextcord.ui.Button,
                                            interaction: nextcord.Interaction):
            try:
              await interaction.user.send("Testing DM permissions... Nice! :)")
              await self.channel.send(
                  f"{interaction.user.mention}, DM permissions tested successfully!"
              )
              await give_achievement(user_id, 0)
            except nextcord.Forbidden:
              await asyncio.get_event_loop().run_in_executor(
                  None,
                  lambda: supabase.table('Players').update({
                      'open_dms': False
                  }).eq('id', interaction.user.id).execute())
              await self.channel.send(
                  f"{interaction.user.mention}, it seems like I still can't send DMs to you. Please use </gethelp:1217148607237722293> to seek further assistance."
              )

        test_permissions_view = TestPermissionsView(channel, user_id)
        await channel_send(
            content=
            f"{interaction.user.mention}, it seems like I can't send DMs to you. Please check your **DM settings** and ensure you __**allow**__ Direct Messages from server members, then press 'Test DM Permissions'.\n\nIf the issue persists please use </gethelp:1217148607237722293> to seek further assistance.",
            view=test_permissions_view)


def setup(bot):
  bot.add_cog(StartCog(bot))
