import random
import asyncio


async def cultivate(player):
  # Increase the year and Heart Demons by default
  player.years_spent += 1
  insight_range = 0.15
  heart_demon_range = 0.10

  # Adjust insight_range based on chosen talents
  talent_insight_mapping = {
      5: 0.55,
      4: 0.35,
      3: 0.30,
      2: 0.25,
      1: 0.20,
      0: 0.15
  }
  for talent, range_value in talent_insight_mapping.items():
    if talent in player.chosen_talents:
      insight_range = range_value
      break

  # Adjust heart_demon_range based on the amount of heart demons
  if player.heart_demons < 50:
    heart_demon_range += (player.heart_demons / 500)
  else:
    heart_demon_range += 0.10 + (0.90 * ((player.heart_demons - 50) / 50)**2)

  # Ensure the sum of insight_range and heart_demon_range does not exceed 100%
  total_range = insight_range + heart_demon_range
  if total_range > 1.0:
    excess = total_range - 1.0
    insight_range -= (insight_range / total_range) * excess
    heart_demon_range -= (heart_demon_range / total_range) * excess

  # Ensure heart_demon_range does not exceed the maximum limit
  heart_demon_range = min(heart_demon_range, 1.0 - insight_range)

  # Combined Heart Check and Insight Check
  roll = random.random()

  print(f"Roll: {roll}")
  print(f"Insight Range: {insight_range}")
  print(f"Heart Demon Range: {heart_demon_range}")

  if roll <= heart_demon_range:
    player.heart_demons += 25
    player.total_wavering_hearts += 1
    return {'result': 'wavering_heart'}
  elif roll <= insight_range + heart_demon_range:
    player.heart_demons += 15
    player.cultivation_level += 2
    player.total_insights += 1
    return {'result': 'insight'}

  # If neither Wavering Heart nor Insight triggered, simply advance cultivation by 1
  player.cultivation_level += 1
  player.heart_demons += 15
  return {'result': 'cultivation'}
