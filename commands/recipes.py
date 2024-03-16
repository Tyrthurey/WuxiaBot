import nextcord
from nextcord.ext import commands, menus
from nextcord import ui, slash_command


class RecipesPagination(ui.View):

  def __init__(self, data, timeout=100):
    super().__init__(timeout=timeout)
    self.data = data
    self.current_page = 0
    self.max_pages = len(data)
    self.update_buttons()

  async def send_current_page(self, interaction):
    current_recipe = self.data[self.current_page]
    embed = nextcord.Embed(title=current_recipe['title'],
                           description=current_recipe['description'],
                           color=nextcord.Color.blue())
    # Dynamically add unique fields for each recipe
    for field in current_recipe['fields']:
      embed.add_field(name=field['name'], value=field['value'], inline=False)
    embed.set_footer(text=f"Page {self.current_page + 1}/{self.max_pages}")
    await interaction.response.edit_message(embed=embed, view=self)

  def update_buttons(self):
    self.previous.disabled = self.current_page == 0
    self.next.disabled = self.current_page == self.max_pages - 1

  @ui.button(label="Previous", style=nextcord.ButtonStyle.grey)
  async def previous(self, button: ui.Button,
                     interaction: nextcord.Interaction):
    self.current_page -= 1
    self.update_buttons()
    await self.send_current_page(interaction)

  @ui.button(label="Next", style=nextcord.ButtonStyle.grey)
  async def next(self, button: ui.Button, interaction: nextcord.Interaction):
    self.current_page += 1
    self.update_buttons()
    await self.send_current_page(interaction)

  async def on_timeout(self):
    for item in self.children:
      item.disabled = True
    await self.message.edit(view=self)


class RecipesCog(commands.Cog):

  def __init__(self, bot):
    self.bot = bot

  @slash_command(name="recipes",
                 description="Crafting recipes and information.")
  async def recipes_slash(self, interaction: nextcord.Interaction):
    await self.recipes(interaction)

  @commands.command(name="recipes",
                    aliases=["recipe"],
                    help="Crafting recipes and information.")
  async def recipes_text(self, ctx):
    await self.recipes(ctx)

  async def recipes(self, interaction):
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

    # Updated dummy_recipes structure to include unique titles and fields
    dummy_recipes = [{
        "title":
        "Recipe 1 Title",
        "description":
        "Recipe 1: Dummy value",
        "fields": [{
            "name": "Ingredient 1",
            "value": "2 cups of flour"
        }, {
            "name": "Cooking Time",
            "value": "45 minutes"
        }]
    }, {
        "title":
        "Recipe 2 Title",
        "description":
        "Recipe 2: Dummy value",
        "fields": [{
            "name": "Ingredient 2",
            "value": "2 cups of flour"
        }, {
            "name": "Cooking Time 12",
            "value": "45 minutes"
        }]
    }]
    pagination_view = RecipesPagination(dummy_recipes, timeout=100)
    # Initialize the embed with the first recipe's title and description
    first_recipe_embed = nextcord.Embed(
        title=dummy_recipes[0]['title'],
        description=dummy_recipes[0]['description'],
        color=nextcord.Color.blue())
    # Dynamically add unique fields for each recipe
    current_recipe = dummy_recipes[0]
    max_pages = len(dummy_recipes)
    for field in current_recipe['fields']:
      first_recipe_embed.add_field(name=field['name'],
                                   value=field['value'],
                                   inline=False)
    first_recipe_embed.set_footer(text=f"Page 1/{max_pages}")
    # Send the message with the first recipe embed and the pagination view
    message = await reply_message(embed=first_recipe_embed,
                                  view=pagination_view)
    pagination_view.message = message


def setup(bot):
  bot.add_cog(RecipesCog(bot))
