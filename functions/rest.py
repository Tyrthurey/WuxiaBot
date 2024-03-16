# functions/rest.py
import random


async def rest(player):
  player.years_spent += 1

  # Decrease Heart Demons by one rank
  if player.heart_demons >= 20:
    player.heart_demons -= 20
  else:
    player.heart_demons = 0

  # Determine Splurge Spree trigger chance based on spirit stones
  tiers = [(0, 0), (1, 99), (100, 299), (300, 699), (700, 1299), (1300, 4999),
           (5000, float('inf'))]
  chances = [0, 5, 15, 30, 50, 85, 99]
  for (lower, upper), chance in zip(tiers, chances):
    if lower <= player.bal <= upper:
      splurge_chance = chance / 100
      break
  else:
    splurge_chance = 0

  # Check for Splurge Spree trigger
  splurge_roll = random.random()
  if splurge_roll <= splurge_chance:
    spent_bal = int(player.bal * 0.3)
    player.bal = int(player.bal * 0.7)  # Spend 30% of wealth
    # Decrease an additional rank for Heart Demons if possible
    if player.heart_demons >= 20:
      player.heart_demons -= 20
    else:
      player.heart_demons = 0

  # Save changes to the player (ensure your player class has a method to save the data)
  await player.save_data()

  # Return a message indicating the result of resting
  if splurge_chance > 0 and splurge_roll <= splurge_chance:
    return f"You indulged much in the past year, enjoying the delights of the world. Your Heart Demons have decreased by **two** ranks.\n\nSpent **{spent_bal}** spirit stones."
  else:
    return "You take the year off and rest, enjoying the delights of the world. Your Heart Demons decrease by a rank."
