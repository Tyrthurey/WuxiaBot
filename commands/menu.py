from nextcord.ext import commands
from nextcord.ext import menus
import nextcord
from nextcord import slash_command, SlashOption
from pydantic import aliases
from nextcord.ui import Button, View
from nextcord import Interaction, ui, Embed, ButtonStyle
import asyncio
from functions.initialize import supabase
import random
from classes.Player import Player
from functions.reincarnate import reincarnate_process
from functions.cultivate import cultivate
from functions.cooldown_manager import cooldown_manager_instance as cooldowns
from functions.rest import rest
from functions.adventure import adventure
from functions.you_die import send_death_message, send_ascend_message
from functions.give_achievement import give_achievement
from functions.initialize import active_menus, get_event_channel, bot


async def adventureresult(player, embed_description, pre_stage_info,
                          post_stage_info, pre_heart_demons, post_heart_demons,
                          interaction, post_cultivation_level):
  heart_demon_status_pre = "None" if pre_heart_demons == 0 else "Negligible" if pre_heart_demons < 20 else "Very Low" if pre_heart_demons < 40 else "Low" if pre_heart_demons < 60 else "High" if pre_heart_demons < 80 else "Peak" if pre_heart_demons < 100 else "Consumed"

  heart_demon_status_post = "None" if post_heart_demons == 0 else "Negligible" if post_heart_demons < 20 else "Very Low" if post_heart_demons < 40 else "Low" if post_heart_demons < 60 else "High" if post_heart_demons < 80 else "Peak" if post_heart_demons < 100 else "Consumed"

  if heart_demon_status_post == "Consumed":
    response_message = "Your heart demons have consumed you... **You have died.**"
    embed = nextcord.Embed(title="Cultivation Update",
                           description=response_message,
                           color=nextcord.Color.red())
    await interaction.response.edit_message(embed=embed, view=None)
    player.dead = True
    player.deaths += 1
    if player.cultivation_level < 15:
      reason = "Death due to suicide."
    else:
      reason = "Death by miscalculation."
    await send_death_message(player, reason)
    await player.save_data()
    return False

  if heart_demon_status_pre != heart_demon_status_post:
    embed_description += f"\n\nHeart Demons: **{heart_demon_status_pre}** --> **{heart_demon_status_post}**."

  if pre_stage_info != post_stage_info and post_cultivation_level < 65:
    embed_description += f"\n\nYou are now on the {post_stage_info}."

  if post_cultivation_level >= 65:
    embed_description += "\n\n**You have achieved immortality!**\n\nCongratulations! You gain **+1 Karma**.\nThis world cannot hold you any longer. You ascend."
    player.dead = True
    player.ascensions += 1
    if player.demonic:
      player.demonic_ascensions += 1
    else:
      player.orthodox_ascensions += 1
    await send_ascend_message(player)
    player.karma += 1

    player.cultivation_level = 0

    if player.fastest_year_score is not None:
      if player.years_spent < player.fastest_year_score:
        player.fastest_year_score = player.years_spent
    else:
      player.fastest_year_score = player.years_spent
    await player.save_score()
    embed = nextcord.Embed(title="Ascension!",
                           description=embed_description,
                           color=nextcord.Color.blue())
    await interaction.response.edit_message(embed=embed, view=None)

    return False

  return embed_description


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


class CultivationMenu(ui.View):

  def __init__(self, player, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.player = player
    self.timeout = 180

  # Add a check to ensure only the matching user can press the button
  async def check_user(self, button: ui.Button, interaction: Interaction):
    if interaction.user.id != self.player.id:
      await interaction.response.send_message("Use your own menu!",
                                              ephemeral=True)
      return False  # Return False to indicate unauthorized access
    return True  # Return True to indicate authorized access

  # Add this method
  async def on_timeout(self):
    user_id = self.player.id
    # Remove all buttons from the view
    self.clear_items()
    # Attempt to update the message to reflect the timeout (remove buttons)
    try:
      if hasattr(self, 'message'):  # Check if the message attribute exists
        await self.message.edit(view=self)
    except Exception as e:
      print(f"Failed to edit menu on timeout: {e}")
    finally:
      # Remove the menu from active_menus
      if user_id in active_menus:
        del active_menus[user_id]

  async def cooldown(self, user_id, reply_message):
    command_name = 'menu'
    cooldown_remaining = cooldowns.get_cooldown(user_id, command_name)

    if cooldown_remaining > 0:
      # Using an embed for cooldown message
      cooldown_embed = nextcord.Embed(
          title="Cooldown Alert!",
          description=
          f"This command is on cooldown. You can use it again in `{cooldown_remaining:.2f}` seconds.",
          color=nextcord.Color.red())
      msg = await reply_message(embed=cooldown_embed)

      await asyncio.sleep(cooldown_remaining)
      await msg.delete()
      return False
    else:

      cooldown = 3
      # Set the cooldown for the hunt command
      cooldowns.set_cooldown(user_id, command_name, cooldown)
      return True

  async def command(self, interaction):

    user_id = interaction.user.id
    # Check for default profile picture
    avatar_url = interaction.user.avatar.url if interaction.user.avatar else interaction.user.default_avatar.url
    author = interaction.user
    channel = interaction.channel
    edit_message = interaction.edit_original_message
    edit_after_defer = interaction.response.edit_message
    delete_message = interaction.delete_original_message
    followup_message = interaction.followup.send
    reply_message = interaction.response.send_message
    channel_send = interaction.channel.send
    send_message = interaction.response.send_message

    response = await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table('Players').select('*').eq('id', user_id).
        execute())

    player = Player(author, response)

    # Check if the player is dead
    if player.dead:
      print("Player is dead, triggering reincarnation process.")
      menu = CultivationMenu(player)
      await reincarnate_process(interaction, player, menu)
      return

    if player.years_spent >= player.lifeforce:
      if 103 in self.player.chosen_talents and not self.player.revived:
        self.player.revived = True
        await self.player.save_data()
      else:
        if player.lifeforce <= 0:
          response_message = "Your body has failed you. **You have died.**"
          embed = nextcord.Embed(title="Cultivation Update",
                                 description=response_message,
                                 color=nextcord.Color.red())
          await followup_message(embed=embed)
          player.dead = True
          player.deaths += 1
          reason = "Death by natural causes."
          await send_death_message(player, reason)
          await player.save_data()
          return
        # Calculate the chance of death based on years spent
        years_over = player.years_spent - player.lifeforce
        death_chance = years_over // 10 * 5  # Increase by 5% every 10 years over 140

        roll = random.randint(1, 100)
        print("Years Spent:", player.years_spent)
        print("Lifeforce:", player.lifeforce)
        print("RNG:", roll)
        print("Death Chance:", death_chance)

        if roll < death_chance:
          response_message = "Your age has failed you. **You have died.**"
          embed = nextcord.Embed(title="Cultivation Update",
                                 description=response_message,
                                 color=nextcord.Color.red())
          await followup_message(embed=embed, view=None)
          player.dead = True
          player.deaths += 1
          reason = "Death by natural causes."
          await send_death_message(player, reason)
          await player.save_data()
          return

    color = nextcord.Color.red() if player.demonic else nextcord.Color.blue()

    player_cultivation_status = get_cultivation_stage(player.cultivation_level)

    # Constructing the embed message
    heart_demon_status = "None" if player.heart_demons == 0 else "Negligible" if player.heart_demons < 20 else "Very Low" if player.heart_demons < 40 else "Low" if player.heart_demons < 60 else "High" if player.heart_demons < 80 else "Peak" if player.heart_demons < 100 else "Consumed"

    if 100 in player.chosen_talents:
      heart_demon_status = f"{min(player.heart_demons, 100)}%"
    elif 101 in player.chosen_talents:
      heart_demon_status = f"{player.heart_demons}%"

    embed = nextcord.Embed(
        title="",
        description=
        f"Hello, **{player.name}** of **{player.current_sect}**.\nYou have spent **{player.years_spent} year(s)** in this world.\n\nYou are at the {player_cultivation_status}\nHeart Demons: **{heart_demon_status}**\nSpirit Stones: **{player.bal}**\n\nWhat do you want to do this year?",
        color=color)
    embed.set_author(name=interaction.user.display_name, icon_url=avatar_url)

    await disable_previous_menu(user_id)

    # Before sending the new menu, save it to the active_menus dictionary
    menu = CultivationMenu(player)
    # Ensure the menu object has a way to access the message it's attached to (for editing it later)
    menu.message = await followup_message(
        embed=embed,
        view=menu)  # Save the message object to the menu for later access
    active_menus[user_id] = menu  # Update the active menu for this user

  @ui.button(label="Cultivate",
             style=ButtonStyle.green,
             custom_id="cultivate_btn")
  async def cultivate_button(self, button: ui.Button,
                             interaction: Interaction):

    # Check if the user pressing the button is the same as the one associated with the menu
    if not await self.check_user(button, interaction):
      return  # Stop execution if the user is not authorized

    cooldown_bool = await self.cooldown(self.player.id,
                                        interaction.response.send_message)
    if not cooldown_bool:
      return

    pre_cultivation_level = self.player.cultivation_level
    pre_heart_demons = self.player.heart_demons
    result = await cultivate(self.player)

    await self.player.save_data()

    color = nextcord.Color.red(
    ) if self.player.demonic else nextcord.Color.blue()

    post_cultivation_level = self.player.cultivation_level
    post_heart_demons = self.player.heart_demons

    pre_stage_info = get_cultivation_stage(pre_cultivation_level)
    post_stage_info = get_cultivation_stage(post_cultivation_level)

    heart_demon_status_pre = "None" if pre_heart_demons == 0 else "Negligible" if pre_heart_demons < 20 else "Very Low" if pre_heart_demons < 40 else "Low" if pre_heart_demons < 60 else "High" if pre_heart_demons < 80 else "Peak" if pre_heart_demons < 100 else "Consumed"

    heart_demon_status_post = "None" if post_heart_demons == 0 else "Negligible" if post_heart_demons < 20 else "Very Low" if post_heart_demons < 40 else "Low" if post_heart_demons < 60 else "High" if post_heart_demons < 80 else "Peak" if post_heart_demons < 100 else "Consumed"

    response_message = f"A year has passed.\nYou have been in this world for **{self.player.years_spent}** years.\n\nYour cultivation has {('not ' if result['result'] == 'wavering_heart' else '')}risen."

    if self.player.years_spent >= self.player.lifeforce:
      if 103 in self.player.chosen_talents and not self.player.revived:
        self.player.revived = True
        await self.player.save_data()
      else:
        # Existing else logic here
        if self.player.lifeforce <= 0:
          response_message = "Your body has failed you. **You have died.**"
          embed = nextcord.Embed(title="Cultivation Update",
                                 description=response_message,
                                 color=nextcord.Color.red())
          try:
            await reply_message(embed=embed)
          except nextcord.errors.InteractionResponded:
            await followup_message(embed=embed)
          self.player.dead = True
          self.player.deaths += 1
          reason = "Death by natural causes."
          await send_death_message(self.player, reason)
          await self.player.save_data()
          return
        # Calculate the chance of death based on years spent
        years_over = self.player.years_spent - self.player.lifeforce
        death_chance = years_over // 10 * 5  # Increase by 5% every 10 years over 140

        roll = random.randint(1, 100)
        print("Years Spent:", self.player.years_spent)
        print("Lifeforce:", self.player.lifeforce)
        print("RNG:", roll)
        print("Death Chance:", death_chance)

        if roll < death_chance:
          response_message = "Your age has failed you. **You have died.**"
          embed = nextcord.Embed(title="Cultivation Update",
                                 description=response_message,
                                 color=nextcord.Color.red())
          try:
            await reply_message(embed=embed, view=None)
          except nextcord.errors.InteractionResponded:
            await followup_message(embed=embed, view=None)
          self.player.dead = True
          self.player.deaths += 1
          reason = "Death by natural causes."
          await send_death_message(self.player, reason)
          await self.player.save_data()
          return

    if self.player.heart_demons >= 100:
      print("Chosen talents are: ", self.player.chosen_talents)
      if 102 in self.player.chosen_talents:
        response_message = "Your heart demons have consumed you... **But you are somehow still alive.**\n\nYou use Demonic Conversion and burn your lifeforce in order to be rid of the heart demons.\n\n**You have become a Demonic Cultivator.**\n\nYour cultivation has risen five times."
        self.player.cultivation_level += 5
        self.player.heart_demons = 0
        self.player.lifeforce -= 30
        self.player.demonic = True
        post_cultivation_level = self.player.cultivation_level
        heart_demon_status_pre = "Consumed"
        heart_demon_status_post = "None"
        color = nextcord.Color.red()
        await self.player.save_data()
      elif 103 in self.player.chosen_talents and not self.player.revived:
        self.player.revived = True
        self.player.heart_demons = 0
        await self.player.save_data()
      else:
        response_message = "Your heart demons have consumed you... **You have died.**"
        embed = nextcord.Embed(title="Cultivation Update",
                               description=response_message,
                               color=nextcord.Color.red())
        await interaction.response.edit_message(embed=embed, view=None)
        self.player.dead = True
        self.player.deaths += 1
        if self.player.cultivation_level < 15:
          reason = "Death due to suicide."
        else:
          reason = "Death by miscalculation."
        await send_death_message(self.player, reason)
        await self.player.save_data()
        return

    if heart_demon_status_pre != heart_demon_status_post:
      response_message += f"\n\nHeart Demons: **{heart_demon_status_pre}** --> **{heart_demon_status_post}**."
    if result['result'] == 'wavering_heart':
      response_message += "\nYour wavering Heart has affected your cultivation..."
    elif result['result'] == 'insight':
      response_message += "\n\n**Insight** has led you to a qualitative advance of your cultivation!"

    if pre_stage_info != post_stage_info and post_cultivation_level < 65:
      response_message += f"\n\nYou are now on the {post_stage_info}."

    if post_cultivation_level >= 65:
      response_message += "\n\n**You have achieved immortality!**\n\nCongratulations! You gain **+1 Karma**.\nThis world cannot hold you any longer. You ascend."
      self.player.dead = True
      self.player.ascensions += 1

      if self.player.demonic:
        self.player.demonic_ascensions += 1
      else:
        self.player.orthodox_ascensions += 1

      await send_ascend_message(self.player)
      self.player.karma += 1

      self.player.cultivation_level = 0

      if self.player.fastest_year_score is not None:
        if self.player.years_spent < self.player.fastest_year_score:
          self.player.fastest_year_score = self.player.years_spent
      else:
        self.player.fastest_year_score = self.player.years_spent
      await self.player.save_score()
      embed = nextcord.Embed(title="Ascension!",
                             description=response_message,
                             color=nextcord.Color.blue())
      await interaction.response.edit_message(embed=embed, view=None)

      return

    embed = nextcord.Embed(title="Cultivation Update",
                           description=response_message,
                           color=color)

    # Check for default profile picture
    avatar_url = interaction.user.avatar.url if interaction.user.avatar else interaction.user.default_avatar.url
    embed.set_author(name=interaction.user.display_name, icon_url=avatar_url)

    await interaction.response.edit_message(embed=embed, view=None)

    await self.command(interaction)

  @ui.button(label="Adventure",
             style=ButtonStyle.blurple,
             custom_id="adventure_btn",
             disabled=False)
  async def adventure_button(self, button: ui.Button,
                             interaction: Interaction):
    # Check if the user pressing the button is the same as the one associated with the menu
    if not await self.check_user(button, interaction):
      return  # Stop execution if the user is not authorized

    cooldown_bool = await self.cooldown(self.player.id,
                                        interaction.response.send_message)
    if not cooldown_bool:
      return

    pre_cultivation_level = self.player.cultivation_level
    pre_heart_demons = self.player.heart_demons

    # Placeholder for adventure logic
    response_embed, embed_description = await adventure(self.player)

    post_cultivation_level = self.player.cultivation_level
    post_heart_demons = self.player.heart_demons

    pre_stage_info = get_cultivation_stage(pre_cultivation_level)
    post_stage_info = get_cultivation_stage(post_cultivation_level)

    adventure_result = await adventureresult(self.player, embed_description,
                                             pre_stage_info, post_stage_info,
                                             pre_heart_demons,
                                             post_heart_demons, interaction,
                                             post_cultivation_level)

    if not adventure_result:
      return

    response_embed.description = adventure_result

    # Check for default profile picture
    avatar_url = interaction.user.avatar.url if interaction.user.avatar else interaction.user.default_avatar.url
    response_embed.set_author(name=interaction.user.display_name,
                              icon_url=avatar_url)

    await interaction.response.edit_message(embed=response_embed, view=None)

    await self.command(interaction)

  @ui.button(label="Rest", style=ButtonStyle.grey, custom_id="rest_btn")
  async def rest_button(self, button: ui.Button, interaction: Interaction):
    # Check if the user pressing the button is the same as the one associated with the menu
    if not await self.check_user(button, interaction):
      return  # Stop execution if the user is not authorized

    cooldown_bool = await self.cooldown(self.player.id,
                                        interaction.response.send_message)
    if not cooldown_bool:
      return

    print(self.player.heart_demons)
    response_message = await rest(self.player)
    print(self.player.heart_demons)
    embed = nextcord.Embed(title="Rest",
                           description=response_message,
                           color=nextcord.Color.blue())

    # Check for default profile picture
    avatar_url = interaction.user.avatar.url if interaction.user.avatar else interaction.user.default_avatar.url
    embed.set_author(name=interaction.user.display_name, icon_url=avatar_url)
    await interaction.response.edit_message(embed=embed, view=None)

    await self.command(interaction)


def get_ordinal(n):
  if 10 <= n % 100 <= 20:
    suffix = 'th'
  else:
    suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
  return str(n) + suffix


def get_cultivation_stage(cultivation):
  if cultivation == 0:
    return "**Mortal** Realm."
  elif 1 <= cultivation <= 64:
    stages = [
        "Earth Flesh",
        "Wood Skin",
        "Water Lung",
        "Fire Eye",  # Foundation
        "Blue Ocean",
        "Bedrock Island",
        "Forever Garden",
        "Eternal Bonfire",  # Consecration
        "Broken Lord",
        "Full Lord",
        "True Lord",
        "Perfect Lord",  # Lord
        "Earth",
        "Wood",
        "Water",
        "Fire"
    ]  # Ruler
    realms = [
        "Foundation", "Foundation", "Foundation", "Foundation", "Consecration",
        "Consecration", "Consecration", "Consecration", "Lord", "Lord", "Lord",
        "Lord", "Ruler", "Ruler", "Ruler", "Ruler"
    ]
    index = (cultivation - 1) // 4  # Every stage has four ranks
    rank = get_ordinal((cultivation - 1) % 4 + 1)
    return f"**{rank}** Rank, **{stages[index]}** Stage, of the **{realms[index]}** Realm."
  elif cultivation >= 65:
    return "**Eternal** Realm, **Immortal** Stage."


class Menu(commands.Cog):
  """The menu for the year."""

  def __init__(self, bot):
    self.bot = bot

  @slash_command(name="me",
                 description="View your status and options for this year.")
  async def command_slash(self, interaction: nextcord.Interaction):
    await self.command(interaction)

  @commands.command(name="me",
                    help="View your status and options for this year.")
  async def command_text(self, ctx):
    await self.command(ctx)

  async def command(self, interaction):
    print("COMMAND TRIGGERED")
    author = "Unknown"
    user_id = 0
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

    command_name = 'menu'
    cooldown_remaining = cooldowns.get_cooldown(user_id, command_name)

    if cooldown_remaining > 0:
      # Using an embed for cooldown message
      cooldown_embed = nextcord.Embed(
          title="Cooldown Alert!",
          description=
          f"This command is on cooldown. You can use it again in `{cooldown_remaining:.2f}` seconds.",
          color=nextcord.Color.red())
      try:
        msg = await reply_message(embed=cooldown_embed)
      except nextcord.errors.InteractionResponded:
        msg = await followup_message(embed=cooldown_embed)

      await asyncio.sleep(cooldown_remaining)
      await msg.delete()

      return

    await disable_previous_menu(user_id)

    cooldown = 3
    # Set the cooldown for the hunt command
    cooldowns.set_cooldown(user_id, command_name, cooldown)

    response = await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table('Players').select('*').eq('id', user_id).
        execute())

    player = Player(author, response)

    # Check if the player is dead
    if player.dead:
      print("Player is dead, triggering reincarnation process.")
      # Before sending the new menu, save it to the active_menus dictionary
      menu = CultivationMenu(player)
      await reincarnate_process(interaction, player, menu)
      return

    # if player.years_spent >= player.lifeforce:
    #   if 103 in player.chosen_talents and not player.revived:
    #     player.revived = True
    #     await player.save_data()
    #   else:
    #     # Existing else logic here
    #     if player.lifeforce <= 0:
    #       response_message = "Your body has failed you. **You have died.**"
    #       embed = nextcord.Embed(title="Cultivation Update",
    #                              description=response_message,
    #                              color=nextcord.Color.red())
    #       try:
    #         await reply_message(embed=embed)
    #       except nextcord.errors.InteractionResponded:
    #         await followup_message(embed=embed)
    #       player.dead = True
    #       player.deaths += 1
    #       reason = "Death by natural causes."
    #       await send_death_message(player, reason)
    #       await player.save_data()
    #       return
    #     # Calculate the chance of death based on years spent
    #     years_over = player.years_spent - player.lifeforce
    #     death_chance = years_over // 10 * 5  # Increase by 5% every 10 years over 140

    #     roll = random.randint(1, 100)
    #     print("Years Spent:", player.years_spent)
    #     print("Lifeforce:", player.lifeforce)
    #     print("RNG:", roll)
    #     print("Death Chance:", death_chance)

    #     if roll < death_chance:
    #       response_message = "Your age has failed you. **You have died.**"
    #       embed = nextcord.Embed(title="Cultivation Update",
    #                              description=response_message,
    #                              color=nextcord.Color.red())
    #       try:
    #         await reply_message(embed=embed, view=None)
    #       except nextcord.errors.InteractionResponded:
    #         await followup_message(embed=embed, view=None)
    #       player.dead = True
    #       player.deaths += 1
    #       reason = "Death by natural causes."
    #       await send_death_message(player, reason)
    #       await player.save_data()
    #       return

    player_cultivation_status = get_cultivation_stage(player.cultivation_level)

    color = nextcord.Color.red() if player.demonic else nextcord.Color.blue()

    # Constructing the embed message
    heart_demon_status = "None" if player.heart_demons == 0 else "Negligible" if player.heart_demons < 20 else "Very Low" if player.heart_demons < 40 else "Low" if player.heart_demons < 60 else "High" if player.heart_demons < 80 else "Peak" if player.heart_demons < 100 else "Consumed"

    if 100 in player.chosen_talents:
      heart_demon_status = f"{min(player.heart_demons, 100)}%"
    elif 101 in player.chosen_talents:
      heart_demon_status = f"{player.heart_demons}%"

    embed = nextcord.Embed(
        title="",
        description=
        f"Hello, **{player.name}** of **{player.current_sect}**.\nYou have spent **{player.years_spent} year(s)** in this world.\n\nYou are at the {player_cultivation_status}\nHeart Demons: **{heart_demon_status}**\nSpirit Stones: **{player.bal}**\n\nWhat do you want to do this year?",
        color=color)

    embed.set_author(name=player.name, icon_url=avatar_url)

    # Before sending the new menu, save it to the active_menus dictionary
    menu = CultivationMenu(player)
    # Ensure the menu object has a way to access the message it's attached to (for editing it later)
    try:
      menu.message = await reply_message(
          embed=embed,
          view=menu)  # Save the message object to the menu for later access
    except nextcord.errors.InteractionResponded:
      menu.message = await followup_message(
          embed=embed,
          view=menu)  # Save the message object to the menu for later access
    active_menus[user_id] = menu  # Update the active menu for this user


# Export the command function to be imported in main.py
def setup(bot):
  bot.add_cog(Menu(bot))
