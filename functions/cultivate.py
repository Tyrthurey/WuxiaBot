import random
import asyncio


async def cultivate(player):
  # Increase the year and Heart Demons by default
  player.years_spent += 1

  # Combined Heart Check and Insight Check
  roll = random.random()
  if roll <= 0.10:
    player.heart_demons += 25  # Increase Heart Demons by additional 25
    return {'result': 'wavering_heart'}
  elif roll <= 0.15:  # 5% chance for Insight, only if Wavering Heart did not trigger
    player.heart_demons += 15
    player.cultivation_level += 2  # Advance cultivation by an additional level
    return {'result': 'insight'}

  # If neither Wavering Heart nor Insight triggered, simply advance cultivation by 1
  player.cultivation_level += 1
  player.heart_demons += 15
  return {'result': 'normal'}



