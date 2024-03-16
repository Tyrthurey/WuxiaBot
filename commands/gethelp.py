from nextcord.ext import commands
from nextcord import Interaction, SlashOption, ui, slash_command
import nextcord
import asyncio
from random import shuffle
from functions.initialize import supabase, bot, guild_id
import datetime
from nextcord.ext import tasks
import os


class FeedbackView(nextcord.ui.View):

  def __init__(self, ticket_id, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.timeout = 600  # 10 minutes
    self.ticket_id = ticket_id

  async def on_feedback(self, interaction: nextcord.Interaction, rating: int):
    # Update the ticket in the database with the received rating
    await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table('Tickets').update({
            'rating': rating
        }).eq('ticket_id', self.ticket_id).execute())

    # Send a confirmation message to the user
    await interaction.response.send_message(
        f"Thank you for your feedback! You rated this support as: {rating}/5")

    guild = bot.get_guild(guild_id)

    if not guild:
      print(f"Guild with ID {guild_id} not found.")
      return False

    log_channel_name = "log"  # Change this as needed
    log_channel = nextcord.utils.get(guild.text_channels,
                                     name=log_channel_name)
    await log_channel.send(
        "-------------------------------------\n"
        f"**Ticket #{self.ticket_id}** received a rating of **{rating}**/**5**"
    )

    # Disable the buttons after feedback is given
    for item in self.children:
      item.disabled = True
    await interaction.message.edit(view=self)
    self.stop()

  @nextcord.ui.button(label="1",
                      style=nextcord.ButtonStyle.danger,
                      custom_id="feedback_1")
  async def feedback_1(self, button: nextcord.ui.Button,
                       interaction: nextcord.Interaction):
    await self.on_feedback(interaction, 1)

  @nextcord.ui.button(label="2",
                      style=nextcord.ButtonStyle.secondary,
                      custom_id="feedback_2")
  async def feedback_2(self, button: nextcord.ui.Button,
                       interaction: nextcord.Interaction):
    await self.on_feedback(interaction, 2)

  @nextcord.ui.button(label="3",
                      style=nextcord.ButtonStyle.secondary,
                      custom_id="feedback_3")
  async def feedback_3(self, button: nextcord.ui.Button,
                       interaction: nextcord.Interaction):
    await self.on_feedback(interaction, 3)

  @nextcord.ui.button(label="4",
                      style=nextcord.ButtonStyle.secondary,
                      custom_id="feedback_4")
  async def feedback_4(self, button: nextcord.ui.Button,
                       interaction: nextcord.Interaction):
    await self.on_feedback(interaction, 4)

  @nextcord.ui.button(label="5",
                      style=nextcord.ButtonStyle.success,
                      custom_id="feedback_5")
  async def feedback_5(self, button: nextcord.ui.Button,
                       interaction: nextcord.Interaction):
    await self.on_feedback(interaction, 5)


class HelperView(ui.View):

  def __init__(self, issue, user_id, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.issue = issue
    self.user_id = user_id
    self.result = asyncio.Future()

  @ui.button(label="Yes", style=nextcord.ButtonStyle.green)
  async def yes_button(self, button: ui.Button, interaction: Interaction):
    self.result.set_result(True)
    self.stop()

  @ui.button(label="No", style=nextcord.ButtonStyle.red)
  async def no_button(self, button: ui.Button, interaction: Interaction):
    self.result.set_result(False)
    self.stop()

  async def ask(self):
    return await self.result


class HelpSystem(commands.Cog):

  def __init__(self, bot):
    self.bot = bot
    self.channel = {}
    self.issues = {}
    self.active_tickets = {}
    self.active_requests = {}
    self.active_tickets_info = {}
    self.helper_responses = {}
    self.help_requests_queue = []
    self.message_histories = {}
    self.check_help_requests_queue.start()

  def cog_unload(self):
    self.check_help_requests_queue.cancel(
    )  # Cancel the background task when the cog is unloaded

  @tasks.loop(minutes=20)
  async def check_help_requests_queue(self):
    if not self.help_requests_queue:
      return  # Exit early if the queue is empty

    guild = self.bot.get_guild(guild_id)

    if not guild:
      print(f"Guild with ID {guild_id} not found.")
      return False

    helpers = await self.query_helpers()
    if not helpers:
      return  # Exit early if no helpers are available

    shuffle(helpers)

    # Get the first request without removing it
    request = self.help_requests_queue[0]
    user = await self.bot.fetch_user(request["user_id"])
    log_channel = await self.get_log_channel()

    for helper_id in helpers:
      if not self.help_requests_queue:
        break  # Exit the loop if the queue becomes empty

      helper = await self.bot.fetch_user(helper_id)

      response = await self.ask_helper(helper, request['issue'], user)
      if response:
        self.help_requests_queue.pop(0)
        self.active_tickets[request["user_id"]] = helper_id
        await user.send(f"A helper has connected to your ticket: {helper}")
        await helper.send(
            f"You have accepted the ticket for issue: {request['issue']}")
        log_channel = await self.get_log_channel()
        await log_channel.send(
            "-------------------------------------\n"
            f"Assigned queued help request from **{user}** to **{helper}** with issue: **{request['issue']}**"
        )
        break
      elif response is False:
        if helper.id in [
            request['helper_id'] for request in self.active_requests.values()
        ]:
          print(f"Helper with ID {helper.id} has an active request pending.")
        else:
          member = guild.get_member(helper.id)
          if not member:
            print(f"Helper with ID {helper.id} not found in guild.")
            continue

          if member.status in [
              nextcord.Status.offline, nextcord.Status.invisible,
              nextcord.Status.dnd
          ]:
            print(
                f"Helper {helper} is not available (Status: {member.status}).")
            continue
          else:
            await log_channel.send("-------------------------------------\n"
                                   f"**{helper}** declined or timed out.")
        continue  # Move to the next helper if the current one declined

  @check_help_requests_queue.before_loop
  async def before_check_help_requests_queue(self):
    await self.bot.wait_until_ready()

  @commands.Cog.listener()
  async def on_message(self, message):
    if message.author == self.bot.user:
      return  # Ignore bot's own messages

    # Check if the message is from the ticket channel and relay it accordingly
    for ticket_info in self.active_tickets_info.values():
      # Check if this message is from the dedicated ticket channel
      if message.channel.id == ticket_info['channel_id']:
        # Fetch the user and helper objects
        user = await self.bot.fetch_user(ticket_info['user_id'])
        helper = await self.bot.fetch_user(ticket_info['helper_id'])

        await user.send(f"**{message.author}**: {message.content}")
        await helper.send(f"**{message.author}**: {message.content}")

        # Initialize history list if not exists
        self.message_histories.setdefault(ticket_info['channel_id'], [])
        # Append the message to the history
        self.message_histories[ticket_info['channel_id']].append({
            "username":
            str(message.author),
            "message":
            message.content,
            "timestamp":
            int(message.created_at.timestamp()),
            "message_id":
            message.id
        })

        # No need to proceed further as message is already handled
        return

    user_id = message.author.id

    if user_id in self.active_tickets:
      helper_id = self.active_tickets[user_id]
      helper = await self.bot.fetch_user(helper_id)
      await helper.send(f"**{message.author}**: {message.content}")
      await self.channel[user_id].send(
          f"**{message.author}**: {message.content}")
    elif user_id in self.active_tickets.values():
      user_id = [k for k, v in self.active_tickets.items() if v == user_id][0]
      user = await self.bot.fetch_user(user_id)
      await user.send(f"**{message.author}**: {message.content}")
      await self.channel[user_id].send(
          f"**{message.author}**: {message.content}")

    # New code to store message history
    if message.author.id in self.active_tickets or any(
        message.author.id == val for val in self.active_tickets.values()):
      if message.channel.type == nextcord.ChannelType.private:
        # Initialize history list if not exists
        self.message_histories.setdefault(message.author.id, [])
        # Append the message to the history
        self.message_histories[message.author.id].append({
            "username":
            str(message.author),
            "message":
            message.content,
            "timestamp":
            int(message.created_at.timestamp()),
            "message_id":
            message.id
        })

  @slash_command(name="gethelp",
                 description="Request help with an issue. Opens a ticket.")
  async def get_help(
      self,
      interaction: Interaction,
      issue: str = SlashOption(description="Describe your issue")):

    # Check if the user already has an active ticket
    if interaction.user.id in self.active_tickets:
      await interaction.response.send_message(
          "You already have an open ticket. Please `/close` your current ticket before opening a new one.",
          ephemeral=True)
      return

    # Check if the user's request is already in the help_requests_queue
    for request in self.help_requests_queue:
      if request["user_id"] == interaction.user.id:
        await interaction.response.send_message(
            "You already have a help request in the queue. Please wait for a helper to accept.",
            ephemeral=True)
        return

    # Check if the user's request is already in self.active_requests
    if interaction.user.id in self.active_requests:
      await interaction.response.send_message(
          "You have already made a ticket. Please wait.", ephemeral=True)
      return

    await interaction.response.send_message(
        "Your help request has been sent! Please wait for a helper to accept.",
        ephemeral=True)

    await interaction.user.send(
        "We have received your ticket. A helper will connect with you shortly."
    )

    # Inside your get_help method, after confirming the help request is valid
    log_channel = await self.get_log_channel()
    await log_channel.send(
        "-------------------------------------\n"
        f"**{interaction.user}** has requested help with issue: **{issue}**")

    helpers = await self.query_helpers()
    if not helpers:
      await interaction.user.send("There are no helpers in the database.")
      return

    shuffle(helpers)

    for helper_id in helpers:
      helper = await self.bot.fetch_user(helper_id)
      if await self.ask_helper(helper, issue, interaction.user):
        self.active_tickets[interaction.user.id] = helper_id
        await interaction.user.send(
            f"A helper has been connected to your ticket: {helper}")
        await helper.send(f"You have accepted the ticket.")
        self.issues[interaction.user.id] = {"issue": issue}
        log_channel = await self.get_log_channel()
        await log_channel.send(
            "-------------------------------------\n"
            f"**{helper}** has accepted the ticket from **{interaction.user}** with issue: **{issue}**"
        )
        break
    else:
      # Add the help request to the queue instead of sending "no available helpers" message
      self.help_requests_queue.append({
          "user_id": interaction.user.id,
          "issue": issue,
          "interaction": interaction
      })
      await interaction.user.send(
          "There are no helpers currently available.\nWe have added your request to our queue and will connect you with a helper as soon as possible."
      )

  async def get_log_channel(self):
    guild = self.bot.get_guild(guild_id)

    if not guild:
      print(f"Guild with ID {guild_id} not found.")
      return False

    log_channel_name = "log"  # Change this as needed
    log_channel = nextcord.utils.get(guild.text_channels,
                                     name=log_channel_name)

    if not log_channel:
      # If the log channel does not exist, create it
      category = nextcord.utils.get(guild.categories, name="Tickets")

      if not category:
        category = await guild.create_category("Tickets")
      log_channel = await guild.create_text_channel(log_channel_name,
                                                    category=category)

    return log_channel

  async def create_ticket_channel(self, guild, user, helper, issue):
    # Find or create the "Tickets" category
    category = nextcord.utils.get(guild.categories, name="Tickets")
    if not category:
      # Create the category if it doesn't exist
      category = await guild.create_category("Tickets")

    # Format channel name
    channel_name = f"{user.name}-{helper.name}".lower()

    # Create the channel under the "Tickets" category
    channel = await guild.create_text_channel(name=channel_name,
                                              category=category)

    # Optional: Send an initial message in the channel
    await channel.send(
        f"Ticket channel created for **{user.display_name}**. Helper: **{helper.display_name}**.\nIssue: {issue}"
    )

    # Return the created channel for further use
    return channel

  async def query_helpers(self):
    # Fetch all helpers who are not currently busy with a ticket
    response = await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table('Players').select('id').eq(
            'helper', True).execute())

    # Assuming response.data is a list of dictionaries with helper 'id'
    all_helper_ids = [helper['id'] for helper in response.data]

    # Filter out helpers who are currently handling a ticket
    available_helper_ids = [
        id for id in all_helper_ids if id not in self.active_tickets.values()
    ]

    return available_helper_ids

  async def ask_helper(self, helper, issue, user):
    guild = self.bot.get_guild(guild_id)
    log_channel = await self.get_log_channel()

    if not guild:
      print(f"Guild with ID {guild_id} not found.")
      return False

    if helper.id in [
        request['helper_id'] for request in self.active_requests.values()
    ]:
      print(f"Helper with ID {helper.id} has an active request pending.")
      return False

    member = guild.get_member(helper.id)
    if not member:
      print(f"Helper with ID {helper.id} not found in guild.")
      return False

    if member.status in [
        nextcord.Status.offline, nextcord.Status.invisible, nextcord.Status.dnd
    ]:
      print(f"Helper {helper} is not available (Status: {member.status}).")
      return False

    view = HelperView(issue, helper.id)
    await log_channel.send("-------------------------------------\n"
                           f"Ticket sent to: **{helper}**.")

    # Store necessary information in active_tickets
    self.active_requests[user.id] = {
        "helper_id": helper.id,
        "user_id": user.id
    }

    message = await helper.send(
        f"**Do you want to accept this ticket?**\n**Issue:** {issue}",
        view=view)

    try:
      await asyncio.wait_for(view.wait(),
                             timeout=600)  # 600 seconds = 10 minutes
    except asyncio.TimeoutError:

      await log_channel.send("-------------------------------------\n"
                             f"**Timeout**: No response from {helper}.")
      response = False

    else:
      response = view.result.result() if view.result.done() else False

    await message.edit(view=None)  # Remove the buttons from the message

    if response:
      # Proceed to create the ticket channel and notify the user and helper
      channel = await self.create_ticket_channel(guild, user, helper, issue)

      # Store necessary information in active_tickets
      self.active_tickets_info[user.id] = {
          "helper_id": helper.id,
          "user_id": user.id,
          "channel_id": channel.id
      }

      self.channel[user.id] = channel
    else:
      # Edit necessary information in active_tickets
      self.active_requests[user.id] = {"helper_id": 0, "user_id": user.id}

    return response

  @slash_command(name="close_ticket", description="Close the current ticket.")
  async def close_help(self, interaction: Interaction):
    user_id = interaction.user.id
    channel_id = 0
    channel_cmd = False

    # First, check if the command was used inside an active ticket channel
    for ticket_info in self.active_tickets_info.values():
      if interaction.channel.id == ticket_info['channel_id']:
        user_id = ticket_info['user_id']
        helper_id = ticket_info['helper_id']
        channel_cmd = True
        break

    if not channel_cmd:
      # Check if the user is in an active ticket
      if user_id not in self.active_tickets and user_id not in self.active_tickets.values(
      ):
        await interaction.response.send_message(
            "You are not in an active help session.", ephemeral=True)
        return

      # Identify if the initiator is a user or a helper
      if user_id in self.active_tickets:  # User initiated the close
        helper_id = self.active_tickets[user_id]
      elif user_id in self.active_tickets.values(
      ):  # Helper initiated the close
        helper_id = user_id
        user_id = next(k for k, v in self.active_tickets.items()
                       if v == helper_id)
      else:
        await interaction.response.send_message(
            "Could not find an active session associated with you.",
            ephemeral=True)
        return

    # Fetch usernames
    user = await self.bot.fetch_user(user_id)
    helper = await self.bot.fetch_user(helper_id)

    # Retrieve issue name safely
    issue_name = self.issues.get(user_id, {}).get('issue', 'Unknown Issue')

    for ticket_info in self.active_tickets_info.values():
      # Check if this message is from the dedicated ticket channel
      if user_id == ticket_info['user_id']:
        channel_id = ticket_info['channel_id']
        channel = self.channel[user_id]
        self.channel[user_id] = None

        await channel.delete(reason="Help session closed.")

    log_channel = await self.get_log_channel()
    await log_channel.send(
        "-------------------------------------\n"
        f"**{interaction.user}** has closed the ticket with issue: **{issue_name}**"
    )

    await interaction.response.send_message(
        "The help session has been successfully closed.", ephemeral=True)

    # Fetch message histories of both user and helper, and combine them chronologically
    user_messages = self.message_histories.get(user_id, [])
    helper_messages = self.message_histories.get(helper_id, [])
    channel_messages = self.message_histories.get(channel_id, [])
    combined_messages = sorted(user_messages + helper_messages +
                               channel_messages,
                               key=lambda x: x['timestamp'])

    # Save to the Tickets table
    latest_ticket_response = await asyncio.get_event_loop().run_in_executor(
        None,
        lambda: supabase.table('Tickets').insert({
            "user_id": f"{user_id}",
            "issue": f"{issue_name}",
            "username": str(user),
            "helper_id": f"{helper_id}",
            "helper_username": str(helper),
            "messages": combined_messages
        }).execute())

    ticket_id = 0

    # # Get the latest row from the Tickets table where the helper id matches helper_id
    # latest_ticket_response = await asyncio.get_event_loop().run_in_executor(
    #     None, lambda: supabase.table('Tickets').select('ticket_id').eq(
    #         'helper_id', helper_id).order('created_at', desc=True).limit(1).
    #     execute())

    latest_ticket = latest_ticket_response.data[
        0] if latest_ticket_response.data else None

    # Assuming the insertion was successful, retrieve the ID of the newly created row

    ticket_id = latest_ticket.get(
        'ticket_id')  # Retrieve the ID of the new ticket

    # Send confirmation messages
    await user.send("The help session has been closed.")
    await helper.send("The help session has been closed.")

    # Inside your close_help method, after compiling the message history
    log_content = "\n".join(
        f"{datetime.datetime.utcfromtimestamp(msg['timestamp']).strftime('%Y-%m-%d %H:%M:%S')} - {msg['username']}: {msg['message']}"
        for msg in combined_messages)

    # Save log content to a temporary file
    with open(f"ticket_{ticket_id}_log.txt", "w") as log_file:
      log_file.write("---------------------------------------------\n"
                     "TICKET LOG\n"
                     f"Helper: {helper.name}\n"
                     f"Ticket Creator: {user.name}\n"
                     f"Ticket ID: #{ticket_id}\n"
                     "---------------------------------------------\n")
      log_file.write(log_content)

    # Send the file to the log channel
    log_channel = await self.get_log_channel()
    await log_channel.send(
        "-------------------------------------\n"
        "**TICKET CLOSED**\n"
        f"**Issue:** {issue_name}\n"
        f"**Ticket ID:** {ticket_id}\n"
        "-------------------------------------\n"
        f"**Helper:** {helper} (<@{helper_id}>)\n"
        f"**Ticket Creator:** {user} (<@{user_id}>)\n"
        f"**User ID:** {user_id}",
        file=nextcord.File(f"ticket_{ticket_id}_log.txt"))

    # Delete the log file after sending it
    os.remove(f"ticket_{ticket_id}_log.txt")

    # Send the feedback request to the user
    feedback_embed = nextcord.Embed(
        title="Ticket Feedback",
        description=
        "Please rate the support you received on a scale of **1** to **5**.",
        color=nextcord.Color.blurple())
    await user.send(embed=feedback_embed,
                    view=FeedbackView(ticket_id=ticket_id))

    # Clean up
    self.active_tickets.pop(user_id, None)
    self.active_tickets_info.pop(user_id, None)
    self.message_histories.pop(user_id, None)
    self.message_histories.pop(helper_id, None)
    self.message_histories.pop(channel_id, None)
    self.issues.pop(user_id, None)
    self.active_requests.pop(user_id, None)

    # Ensure to remove the user's entry from the issues dictionary after the session is closed
    if user_id in self.issues:
      del self.issues[user_id]


def setup(bot):
  bot.add_cog(HelpSystem(bot))
