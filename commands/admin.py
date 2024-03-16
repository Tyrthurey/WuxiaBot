import nextcord
from nextcord.ext import commands
from nextcord import Interaction
from nextcord.ui import Button, View, Modal, TextInput
import asyncio
from functions.initialize import supabase, bot, active_menus


async def disable_previous_menu(user_id):
  """Removes all buttons from the user's previous active menu."""
  print("Disabling menu...")
  print(active_menus)
  if (user_id) in active_menus:
    previous_menu = active_menus[user_id]
    print(f"Previous menu: {previous_menu}")
    previous_menu.clear_items()  # Remove all buttons from the view
    try:
      await previous_menu.message.edit(view=previous_menu)
    except Exception as e:
      print(f"Error updating message: {e}")
      del active_menus[
          user_id]  # Remove all entries from active_menus with that user_id


# Setup the commands extension
class AdminCommands(commands.Cog):

  def __init__(self, bot):
    self.bot = bot

  async def admin_check(self, user_id):
    response = await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table('Players').select('id').eq('admin', True).
        execute())
    all_admin_ids = [admin['id'] for admin in response.data]
    return user_id in all_admin_ids

  @nextcord.slash_command(name='admin', description='Makes you an admin!')
  async def admin_menu(self, interaction: Interaction):
    if not await self.admin_check(interaction.user.id):
      await interaction.response.send_message("Nope, nice try tho!",
                                              ephemeral=True)
      return
    embed = nextcord.Embed(title="Admin Menu",
                           description=f"Welcome, **{interaction.user}**.",
                           color=nextcord.Color.blue())
    embed.add_field(
        name="Edit Player",
        value="__Player Information:__\n*displayname*\n"
        "__Cultivation Stats:__\n*cultivation_level, bal, qi*\n"
        "__Player Status:__\n*using_command, tutorial, finished_tutorial, dead*\n"
        "__Miscellaneous:__\n*deaths, dm_cmds, open_dms, helper, moderator, admin, heart_demons, karma, current_sect, years_spent, fastest_year_score, max_cultivation_attained, ascensions*",
        inline=False)
    await interaction.response.send_message(embed=embed,
                                            view=AdminView(self),
                                            ephemeral=True)


class EditPlayerStatModal(Modal):

  def __init__(self, cog, *args, **kwargs):
    super().__init__(*args, **kwargs, title="Edit Player Stat")
    self.cog = cog
    self.add_item(TextInput(label="Player ID"))
    self.add_item(TextInput(label="Stat to Edit"))
    self.add_item(TextInput(label="Change in Stat"))

  async def callback(self, interaction: nextcord.Interaction):
    player_id = int(self.children[0].value)
    stat_to_edit = self.children[
        1].value  # Changed from select to text for compatibility
    change_in_stat = self.children[2].value

    response = await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table('Players').select('*').eq(
            'id', player_id).execute())

    if not response:
      await interaction.response.send_message(
          f"Player with ID {player_id} not found.", ephemeral=True)
      return

    player_data = response.data[0] if response.data else None
    if not player_data:
      await interaction.response.send_message(
          f"Player with ID {player_id} not found.", ephemeral=True)
      return

    stat = player_data.get(stat_to_edit, None)
    print(f"statname : {stat_to_edit}, stat: {stat}")
    player_name = player_data.get('username', 'None')
    if stat is None:
      await interaction.response.send_message(
          f"Stat '{stat_to_edit}' not found for player with ID {player_id}.",
          ephemeral=True)
      return

    try:
      stat_numeric = float(stat)
      is_numeric = True
    except ValueError:
      is_numeric = False

    if change_in_stat.lower() == "true":
      new_value = True
    elif change_in_stat.lower() == "false":
      new_value = False
    elif change_in_stat.lower() == "null":
      new_value = None
    else:
      new_value = int(stat) + int(
          change_in_stat) if is_numeric else change_in_stat

    await disable_previous_menu(player_id)

    await asyncio.get_event_loop().run_in_executor(
        None,
        lambda: supabase.table('Players').update({
            f'{stat_to_edit}': new_value
        }).eq('id', player_id).execute())

    # Here, add your logic to update the player's stat in your database
    await interaction.response.send_message(
        f"Updated **{stat_to_edit}** for **{player_name}**.\nChange: **{change_in_stat}**.\nNew Value: **{new_value}**"
    )


class AdminView(View):

  def __init__(self, cog, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.cog = cog

  @nextcord.ui.button(label="Edit Player",
                      style=nextcord.ButtonStyle.green,
                      custom_id="edit_player")
  async def edit_player_button(self, button: Button,
                               interaction: nextcord.Interaction):
    if not await self.cog.admin_check(interaction.user.id):
      await interaction.response.send_message("Nope, nice try tho!",
                                              ephemeral=True)
      return
    await interaction.response.send_modal(EditPlayerStatModal(self.cog))


def setup(bot):
  bot.add_cog(AdminCommands(bot))
