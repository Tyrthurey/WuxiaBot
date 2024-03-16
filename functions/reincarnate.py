import nextcord
from nextcord.ext import commands
from nextcord.ui import View, Button, Modal, TextInput
from nextcord import ButtonStyle, Embed, Interaction, ui
from typing import Dict
import asyncio
from functions.initialize import supabase, bot, generate_sect_name
from functions.give_title import give_title
from functions.give_achievement import give_achievement
from functions.initialize import active_menus


class TalentsView(ui.View):

  def __init__(self, player, talent_ids):
    super().__init__(timeout=180)
    self.player_talents = talent_ids
    self.player = player
    self.user_id = player.id

  async def fetch_talent_info(self, talent_id):
    response = await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table('Talents').select('*').eq(
            'talent_id', talent_id).execute())
    data = response.data
    if data:
      return {
          "talent_id": data[0]['talent_id'],
          "talent_name": data[0]['talent_name'],
          "talent_description": data[0]['talent_description'],
          "karma_price": data[0]['karma_price'],
          "unlocked": True
      }
    return {"talent_id": talent_id, "unlocked": False}

  async def fetch_talents(self, user_id):
    response = await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table('Inventory').select('talents').eq(
            'id', user_id).execute())
    data = response.data
    talents_info = []
    if data:
      talents = data[0].get("talents", [])
      for talent in talents:
        talent_info = await self.fetch_talent_info(talent['talent_id'])
        talents_info.append(talent_info)
    return talents_info

  async def on_more_info(self, interaction: nextcord.Interaction):
    print(interaction.data)
    talent_id = interaction.data['components'][0]['components'][0]['value']
    # Fetch talent information from Supabase
    talent_info = await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table('Talents').select('*').eq(
            'talent_id', int(talent_id)).execute())

    if talent_info.data:
      talent = talent_info.data[
          0]  # Assuming the query returns at least one match
      description = f"ID: {talent['talent_id']} - {talent['talent_name']}: {talent['talent_description']}"
      await interaction.response.send_message(description, ephemeral=True)
    else:
      await interaction.response.send_message("Talent not found.",
                                              ephemeral=True)

  async def on_talent_chosen(self, interaction: nextcord.Interaction,
                             original_interaction):
    # Check if the interaction user matches the stored player ID
    if interaction.user.id != self.user_id:
      await interaction.response.send_message(
          "Let others make their own decisions, bleh. Use your own menu!",
          ephemeral=True)
      return  # Stop execution if the user is not authorized

    if self.player.karma == 0:
      await interaction.response.send_message(
          "You do not have any Karma Points.", ephemeral=True)
      return
    talent_id = interaction.data['components'][0]['components'][0]['value']

    if int(talent_id) in self.player_talents:
      await interaction.response.send_message(
          "You have already unlocked this talent.", ephemeral=True)
      return

    # Fetch talent information from Supabase
    talent_info = await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table('Talents').select('*').eq(
            'talent_id', int(talent_id)).execute())

    if talent_info.data:
      talent = talent_info.data[0]
      if talent['prerequisite_id'] not in self.player_talents:
        embed = nextcord.Embed(
            title="Prerequisites Not Met",
            description=
            f"You need to unlock the talent with `ID {talent['prerequisite_id']}` if you want to buy this one.",
            color=nextcord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

      if int(talent['karma_price']) > self.player.karma:
        embed = nextcord.Embed(
            title="Not Enough Karma Points",
            description=
            f"You need **{talent['karma_price']} KP** to unlock this talent, but you only have **{self.player.karma} KP**.",
            color=nextcord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

      embed = nextcord.Embed(
          title="Buy Talent: " + talent['talent_name'],
          description=
          f"**Cost:** {talent['karma_price']} KP\n{talent['talent_description']}\n\n**Are you sure you want to buy this talent?**",
          color=nextcord.Color.green())

      view = nextcord.ui.View()
      view.add_item(
          nextcord.ui.Button(label="Yes",
                             style=nextcord.ButtonStyle.green,
                             custom_id="confirm_purchase"))
      await interaction.response.send_message(embed=embed,
                                              view=view,
                                              ephemeral=True)

      def check(event):
        return event.user.id == interaction.user.id and event.data[
            'custom_id'] == "confirm_purchase"

      confirmation = await bot.wait_for('interaction', check=check)
      if confirmation:
        self.player.karma -= int(talent['karma_price'])

        response = await asyncio.get_event_loop().run_in_executor(
            None, lambda: supabase.table('Inventory').select('talents').eq(
                'id', self.player.id).execute())
        data = response.data

        # Add the selected talent_id to the player's talents
        new_talent = {'talent_id': int(talent_id)}
        if not data[0].get('talents'):
          data[0]['talents'] = [new_talent]
        else:
          data[0]['talents'].append(new_talent)

        # Update the player's talents in Supabase
        await asyncio.get_event_loop().run_in_executor(
            None, lambda: supabase.table('Inventory').update({
                'talents':
                data[0]['talents']
            }).eq('id', self.player.id).execute())

        await self.player.save_data()

        talents = await self.fetch_talents(self.player.id)

        response = await asyncio.get_event_loop().run_in_executor(
            None, lambda: supabase.table('Talents').select('*').execute())
        all_talents = response.data

        embed = Embed(
            title="Karma Points",
            description=
            f"**Available KP:** {self.player.karma}\nChoose a talent to spend your points on."
        )
        talent_ids = [talent['talent_id'] for talent in talents]
        talents_list = '\n'.join([
            f"`ID: {talent['talent_id']}` - **{talent['talent_name']}**  {':white_check_mark:' if talent['talent_id'] in talent_ids else ':x:'}  {'(' + str(talent['karma_price']) + ' KP)' if talent['talent_id'] not in talent_ids else ''}"
            for talent in sorted(
                all_talents, key=lambda x: x['talent_id'], reverse=True)
        ])
        embed.add_field(name="Talents", value=talents_list, inline=False)

        # Replace this view with one that has the talent options and buttons
        await original_interaction.edit_original_message(embed=embed,
                                                         view=TalentsView(
                                                             self.player,
                                                             talent_ids))

        # Update the embed with new player data after purchasing a talent
        updated_embed = nextcord.Embed(
            title="Talent Purchased Successfully!",
            description=
            f"Congratulations, **{self.player.name}**! You have successfully purchased the talent: **{talent['talent_name']}**.\n\nYou now have **{self.player.karma}** Karma Points left.",
            color=nextcord.Color.green())
        await interaction.edit_original_message(embed=updated_embed, view=None)

        if talent_id == '5':
          await give_title(self.player.id, 100)

  @nextcord.ui.button(label="Buy Talent", style=nextcord.ButtonStyle.green)
  async def choose_talent(self, button: Button,
                          interaction: nextcord.Interaction):
    # Open a modal to choose a talent
    modal = TalentSelectionModal(
        title="Buy Talent",
        callback=lambda i: self.on_talent_chosen(i, interaction))
    await interaction.response.send_modal(modal)

  @nextcord.ui.button(label="More Information",
                      style=nextcord.ButtonStyle.blurple)
  async def more_info(self, button: Button, interaction: nextcord.Interaction):
    # Open a modal to get more information about a talent
    modal = TalentSelectionModal(title="More Information",
                                 callback=lambda i: self.on_more_info(i))
    await interaction.response.send_modal(modal)

  @nextcord.ui.button(label="Back", style=nextcord.ButtonStyle.red)
  async def back(self, button: Button, interaction: nextcord.Interaction):
    view = ReincarnationView(self.player)
    embed = nextcord.Embed(
        title="You have died.",
        description=
        f"Hello, **{self.player.name}**. Ready to reincarnate?\n\nYou have **{self.player.karma}** Karma Points.",
        color=nextcord.Color.green())
    await interaction.response.edit_message(view=view, embed=embed)


class TalentSelectionModal(Modal):

  def __init__(self, title: str, callback):
    super().__init__(title=title, timeout=180)
    self.callback = callback
    self.add_item(
        TextInput(label="Talent ID",
                  placeholder="Enter the ID of the talent."))

  async def on_submit(self, interaction: nextcord.Interaction):
    await self.callback(interaction, self.children[0].value)


class ReincarnationView(ui.View):

  def __init__(self, player):
    super().__init__(timeout=180)  # Timeout for view interaction
    self.user_id = player.id
    self.player = player

  async def interaction_check(self, interaction: Interaction) -> bool:
    return interaction.user.id == self.user_id

  @ui.button(label="Reincarnate", style=ButtonStyle.green)
  async def reincarnate(self, button: ui.Button, interaction: Interaction):
    sect_name = generate_sect_name()

    # Add active talents here

    self.player.current_sect = sect_name
    self.player.bal = 100  #starter funds
    self.player.heart_demons = 0
    self.player.cultivation_level = 0
    self.player.years_spent = 0
    self.player.dead = False

    # Creating an embed for the reincarnation process
    reincarnation_embed = nextcord.Embed(
        title="Reincarnating...",
        description=
        f"The Heavens greet the young reincarnator, **{self.player.name}**.\n\n"
        "Your spirit channels are… **Chalk tier**\n"
        f"You are the lowest tier disciple of the **{sect_name}**\n"
        "Your cultivation realm is… **Mortal**\n"
        "Beware of Heart Demons.",
        color=nextcord.Color.blue())

    await self.player.save_data()

    await interaction.response.edit_message(embed=reincarnation_embed,
                                            view=None)

    await give_title(self.player.id, 0)

  @ui.button(label="Spend Karma", style=ButtonStyle.blurple)
  async def spend_talent_points(self, button: ui.Button,
                                interaction: Interaction):
    talents = await self.fetch_talents(self.user_id)
    all_talents = await self.fetch_all_talents()
    embed = Embed(
        title="Karma Points",
        description=
        f"**Available KP:** {self.player.karma}\nChoose a talent to spend your points on."
    )
    talent_ids = [talent['talent_id'] for talent in talents]
    talents_list = '\n'.join([
        f"`ID: {talent['talent_id']}` - **{talent['talent_name']}**  {':white_check_mark:' if talent['talent_id'] in talent_ids else ':x:'}  {'(' + str(talent['karma_price']) + ' KP)' if talent['talent_id'] not in talent_ids else ''}"
        for talent in sorted(
            all_talents, key=lambda x: x['talent_id'], reverse=True)
    ])
    embed.add_field(name="Talents", value=talents_list, inline=False)

    # Replace this view with one that has the talent options and buttons
    await interaction.response.edit_message(embed=embed,
                                            view=TalentsView(
                                                self.player, talent_ids))

  async def fetch_talents(self, user_id):
    response = await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table('Inventory').select('talents').eq(
            'id', user_id).execute())
    data = response.data
    talents_info = []
    if data:
      talents = data[0].get("talents", [])
      for talent in talents:
        talent_info = await self.fetch_talent_info(talent['talent_id'])
        talents_info.append(talent_info)
    return talents_info

  async def fetch_all_talents(self):
    response = await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table('Talents').select('*').execute())
    data = response.data
    return data

  async def fetch_talent_info(self, talent_id):
    response = await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table('Talents').select('*').eq(
            'talent_id', talent_id).execute())
    data = response.data
    if data:
      return {
          "talent_id": data[0]['talent_id'],
          "talent_name": data[0]['talent_name'],
          "talent_description": data[0]['talent_description'],
          "karma_price": data[0]['karma_price'],
          "unlocked": True
      }
    return {"talent_id": talent_id, "unlocked": False}


async def disable_previous_menu(user_id):
  """Removes all buttons from the user's previous active menu."""
  if user_id in active_menus:
    previous_menu = active_menus[user_id]
    previous_menu.clear_items()  # Remove all buttons from the view
    try:
      await previous_menu.message.edit(view=previous_menu)
    except Exception as e:
      print(f"Error updating message: {e}")
      del active_menus[
          user_id]  # Remove all entries from active_menus with that user_id


async def reincarnate_process(interaction, player, reply_message):
  # If it's a text command, get the author from the context
  if isinstance(interaction, commands.Context):
    print("ITS A CTX COMMAND!")

    # Check for default profile picture
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
    # Check for default profile picture
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

  await disable_previous_menu(player.id)
  view = ReincarnationView(player)
  embed = nextcord.Embed(
      title="You have died.",
      description=
      f"Hello, **{player.name}**. Ready to reincarnate?\n\nYou have **{player.karma}** Karma Points.",
      color=nextcord.Color.green())
  view.message = await reply_message(embed=embed, view=view)
  active_menus[player.id] = view  # Update the active menu for this user


# The implementation details for modal callbacks (on_talent_chosen and on_more_info) and fetching talents data need to be completed based on your application logic.
