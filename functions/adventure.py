from functions.initialize import ADVENTURE_OUTCOMES
from functions.you_die import send_death_message
import asyncio
import random
import nextcord


def select_adventure_outcome():
  outcomes = []
  for outcome in ADVENTURE_OUTCOMES:
    outcomes.extend([outcome] * outcome["chance"])
  selected_outcome = random.choice(outcomes)
  return selected_outcome


async def adventure(player):

  # Select an adventure outcome
  outcome = select_adventure_outcome()

  # Create an embed for the outcome message
  outcome_embed = nextcord.Embed(color=nextcord.Color.blue())

  if player.bal < 300 and outcome['type'] == 'wandering_master':
    # Reroll outcome if player.bal less than 300 and outcome is wandering master
    outcome = select_adventure_outcome()
    while outcome['type'] == 'wandering_master':
      outcome = select_adventure_outcome()

  if player.heart_demons < 40 and outcome['type'] == 'killed':
    # Reroll outcome if player.heart_demons less than 40 and outcome is killed
    outcome = select_adventure_outcome()
    while outcome['type'] == 'killed':
      outcome = select_adventure_outcome()
  elif player.heart_demons >= 40 and outcome['type'] == 'killed':
    demon_chance = min(100, max(0, (player.heart_demons - 40)**2 / 36))
    if random.randint(1, 100) <= demon_chance:
      outcome['type'] = 'killed'
      outcome[
          'message'] = "Despite your efforts, the heart demons consume you.\n\n**Game Over**"
    else:
      while outcome['type'] == 'killed':
        outcome = select_adventure_outcome()

  player.years_spent += 1

  description = ""

  # Example if-then logic for each outcome type
  if outcome['type'] == 'insight_treasure':
    outcome_embed.title = "Fortunate Discovery!"
    description = outcome['message']
    player.cultivation_level += 2

  elif outcome['type'] == 'wandering_master':
    outcome_embed.title = "Mysterious Encounter!"
    description = outcome['message']
    player.cultivation_level += 2
    player.bal -= 300

  elif outcome['type'] == 'killed':
    outcome_embed.title = "Perilous Fate!"
    description = outcome['message']
    player.dead = True

    reason = "Death by adventure. Died to the 1% and heart demons."
    await send_death_message(player, reason)

  elif outcome['type'] == 'spirit_stones_large':
    outcome_embed.title = "Tremendous Wealth!"
    description = outcome['message']
    player.bal += 400
    player.total_bal += 400

  elif outcome['type'] in 'spirit_stones_low':
    outcome_embed.title = "Spirit Stones Found!"
    description = outcome['message']
    player.bal += 150
    player.total_bal += 150

  elif outcome['type'] in 'spirit_stones_decent':
    outcome_embed.title = "Spirit Stones Found!"
    description = outcome['message']
    player.bal += 270
    player.total_bal += 270

  elif outcome['type'] == '50_life_force':
    outcome_embed.title = "Lifeforce Boost!"
    description = outcome['message']
    player.lifeforce += 50

  elif outcome['type'] == '80_life_force':
    outcome_embed.title = "Major Lifeforce Boost!"
    description = outcome['message']
    player.lifeforce += 80

  elif outcome['type'] == 'nothing':
    outcome_embed.title = "Unfortunate Journey"
    description = outcome['message']
    # Additional logic for nothing outcome

  # Save player data
  await player.save_data()

  return outcome_embed, description
