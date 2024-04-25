import os
from nextcord.ext import commands
import nextcord
from supabase import create_client, Client
import random

intents = nextcord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True

prefix = "wux "

bot = commands.Bot(command_prefix=prefix,
                   intents=intents,
                   help_command=None,
                   case_insensitive=True)

# #the main bot guild
# guild_id = 1137866165570506927

# testing guild:
guild_id = 556783971136962566

event_channel_name = "wux-events"
secret_log_channel_name = "wux-secret-log"


async def get_event_channel():
  guild = bot.get_guild(guild_id)
  if not guild:
    print(f"Guild with ID {guild_id} not found.")
    event_channel = None
  else:
    event_channel = nextcord.utils.get(guild.text_channels,
                                       name=event_channel_name)
  return event_channel


active_menus = {}

# Supabase Database Initialization
SUPABASE_URL = os.getenv("SUPABASE_URL") or ""
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or ""
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Send a message with the tutorial
tutorial_embeds = [
    nextcord.Embed(
        title="Hello, young one.",
        description=
        "**To cultivate is to have courage. To spill blood. To venture into heavens or hell. To fight through the nine skies for the path to eternity.**\n\n"
        "Welcome!\n"
        "Wandering souls sometimes find themselves in **Zaipei**. You happen to be one of them. To return to your home world, you must reincarnate as a cultivator and reach the end of the path to eternity.\n\n"
        "You’ll pass through four cultivation realms on your path: **Foundation**, **Consecration**, **Lord**, and **Ruler**. Each journey adds to your strength, helping you go further in your next reincarnation until to finally reach eternity."
    ),
    nextcord.Embed(
        title="What is this?",
        description=
        "**Talent paves the path to eternity. And you have legendary Jade tier spirit channels.**\n\n"
        "With an incredibly long lifespan, cultivators measure time in terms of years. At the start of each year, you’ll decide your plan for the cycle.\n\n"
        "**Cultivate** and increase your strength.\n"
        "**Adventure** in search of treasures.\n"
        "**Rest** to hold the heart demons at bay.\n\n"
        "Every decade, countless cultivators succumb to their heart demons and lose themselves in the insanity. The sects hope that you aren’t one of them."
    ),
    nextcord.Embed(
        title="Your Goal",
        description="**The goal of every cultivator is to become immortal.**\n\n"
        "There are four cultivation realms: **Foundation**, **Consecration**, **Lord**, and **Ruler**. Within each realm are **four** smaller **stages**, and each stage has **four ranks**.\n"
    ),
    nextcord.Embed(
        title="Helpful Commands",
        description=
        "You can use the </gethelp:1211702095695183904> command if you encoutnered an issue.\n\n"
        "For everything else use </me:1214579088094928926>.")
    # Add more embeds as needed...
]

SECT_PREFIXES = [
    'Heavenly', 'Mystic', 'Dragon', 'Tiger', 'Phoenix', 'Celestial', 'Jade',
    'Golden', 'Silver', 'Crimson', 'Azure', 'Emerald', 'Scarlet', 'Divine',
    'Shadow', 'Ethereal', 'Infernal', 'Radiant', 'Frozen', 'Storm', 'Serpent',
    'Lotus', 'Fiery', 'Star', 'Moon', 'Sun', 'Eclipse', 'Wind', 'Thunder',
    'Void', 'Spirit', 'Soul', 'Flame', 'Water', 'Earth', 'Metal', 'Wood',
    'Light', 'Dark', 'Ocean', 'River', 'Mountain', 'Forest', 'Desert', 'Sky',
    'Island', 'Thunder', 'Lunar', 'Solar', 'Twilight', 'Dawn', 'Dusk', 'Night',
    'Day', 'Blazing', 'Burning', 'Chilling', 'Freezing', 'Blooming', 'Wilting',
    'Falling', 'Rising', 'Eternal', 'Ancient', 'Primal', 'Arcane', 'Mystical',
    'Supreme', 'Infinite', 'Limitless', 'Boundless', 'Elder', 'Primeval',
    'Sage', 'Sovereign', 'Imperial', 'Royal', 'Noble', 'Exalted', 'Wondrous',
    'Marvelous', 'Glorious', 'Resplendent', 'Luminous', 'Brilliant',
    'Illuminated', 'Enlightened', 'Harmonious', 'Tranquil', 'Serene',
    'Peaceful', 'Wrathful', 'Furious', 'Ruthless'
]

SECT_MIDDLES = [
    'Palm', 'Fist', 'Sword', 'Lotus', 'Heart', 'Spirit', 'Flame', 'River',
    'Mountain', 'Forest', 'Cloud', 'Mist', 'Thunder', 'Wind', 'Star', 'Moon',
    'Sun', 'Light', 'Dark', 'Void', 'Peak', 'Lake', 'Sea', 'Frost', 'Snow',
    'Sky', 'Orchid', 'Bamboo', 'Pine', 'Willow', 'Jade', 'Gold', 'Silver',
    'Iron', 'Steel', 'Copper', 'Bronze', 'Emerald', 'Ruby', 'Sapphire',
    'Amber', 'Diamond', 'Quartz', 'Crystal', 'Blossom', 'Leaf', 'Root',
    'Branch', 'Vine', 'Petal', 'Dragon', 'Tiger', 'Phoenix', 'Turtle', 'Crane',
    'Leopard', 'Serpent', 'Eagle', 'Wolf', 'Lion', 'Hawk', 'Falcon', 'Raven',
    'Bear', 'Ox', 'Elephant', 'Horse', 'Deer', 'Rabbit', 'Fox', 'Mirror',
    'Whip', 'Spear', 'Arrow', 'Shield', 'Mantle', 'Veil', 'Crown', 'Ring',
    'Chain'
]

SECT_SUFFIXES = [
    'Sect', 'Clan', 'Pavilion', 'Palace', 'Temple', 'Grove', 'Peak', 'Valley',
    'Island', 'Sanctuary', 'Fortress', 'City', 'Garden', 'Cavern', 'Spring',
    'Lake', 'River', 'Mountain', 'Forest', 'School', 'Hall', 'Chamber', 'Gate',
    'Path', 'Way', 'Shrine', 'Tower', 'Castle', 'Catacomb', 'Labyrinth',
    'Library', 'Archive', 'Academy', 'Institute', 'Order', 'Circle', 'Guild',
    'Fellowship', 'Society', 'Brotherhood', 'Sisterhood', 'Assembly',
    'Gathering', 'Faction', 'Syndicate', 'Network', 'Association',
    'Organization', 'Group', 'Band', 'Force', 'Legion', 'Constellation',
    'Galaxy', 'Nebula', 'Realm', 'Domain', 'Empire', 'Kingdom', 'Dynasty',
    'Era', 'Age', 'Epoch'
]


def generate_sect_name():
  prefix = random.choice(SECT_PREFIXES)
  middle = random.choice(SECT_MIDDLES)
  suffix = random.choice(SECT_SUFFIXES)
  return f"{prefix} {middle} {suffix}"


ADVENTURE_OUTCOMES = [
    {
        "type":
        "insight_treasure",
        "chance":
        5,
        "message":
        "You found an Insight boosting treasure!\n\nYour cultivation has risen by **two**."
    },
    {
        "type":
        "wandering_master",
        "chance":
        4,
        "message":
        "A wandering master imparts you Insight in exchange for Spirit Stones.\n\nYour cultivation has risen by **two**.\nYou spent **300** Spirit Stones."
    },
    {
        "type": "killed",
        "chance": 1,
        "message": "You were killed during your adventure.\n\n**Game Over**"
    },
    {
        "type":
        "spirit_stones_large",
        "chance":
        2,
        "message":
        "You found a large amount of Spirit Stones!\n\n**+400** Spirit Stones"
    },
    {
        "type":
        "spirit_stones_low",
        "chance":
        28,
        "message":
        "You found a low amount of Spirit Stones.\n\n**+150** Spirit Stones"
    },
    {
        "type":
        "spirit_stones_decent",
        "chance":
        10,
        "message":
        "You found a decent amount of Spirit Stones.\n\n**+270** Spirit Stones"
    },
    {
        "type":
        "50_life_force",
        "chance":
        15,
        "message":
        "You found something that can increase your lifeforce!\n\n**+50 Years of Lifeforce**"
    },
    {
        "type":
        "80_life_force",
        "chance":
        5,
        "message":
        "You found something that can increase your lifeforce!\n\n**+80 Years of Lifeforce**"
    },
    {
        "type": "nothing",
        "chance": 30,
        "message": "**You gained nothing from your adventure.**"
    },
]
