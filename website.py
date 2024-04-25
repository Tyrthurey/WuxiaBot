from flask import Flask, render_template, jsonify, request, session, redirect, send_from_directory
import threading
from threading import Thread
import asyncio
from waitress import serve
from zenora import APIClient
import datetime
import time
import os
import json
from zenora import APIClient
from functions.initialize import supabase
from classes.Player import Player
import requests

# website = "cultivatinginsanity.com"
# client_id = "1217236373208039504"

# dev site
website = "f92e22d0-556f-460b-96d7-a2bc3920a4e6-00-1eyvu4gm9ri3.worf.replit.dev"
# dev client
client_id = "530708819458654219"

redirect_uri = f"https://{website}/oauth/callback"

oath_url = f"https://discord.com/oauth2/authorize?client_id={client_id}&response_type=code&redirect_uri=https%3A%2F%2F{website}%2Foauth%2Fcallback&scope=identify+email"

token = os.getenv("TOKEN") or ""
client_secret = os.getenv("CLIENT_SECRET") or ""

app = Flask(__name__,
            template_folder='frontend/build',
            static_folder='frontend/build/static')

client = APIClient(token, client_secret=client_secret)

app.config["SECRET_KEY"] = "verysecret"


@app.route('/')
async def homepage():
  return render_template('index.html')


@app.route('/api/leaderboard')
async def api_leaderboard():
  # Function to get and sort players data for each category
  async def get_players_data(category):
    response = await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table('Players').select('*').execute())

    data = response.data

    if category == 'mortal':
      sorted_data = sorted(data,
                           key=lambda x: x['cultivation_level'],
                           reverse=True)
      sorted_data = [{
          "rank": rank + 1,
          "name": x['username'],
          "cultivation_level": x['cultivation_level']
      } for rank, x in enumerate(sorted_data)]
    elif category == 'immortal':
      sorted_data = sorted(
          [d for d in data if d['fastest_year_score'] is not None],
          key=lambda x: x['fastest_year_score'])
      sorted_data = [{
          "rank": rank + 1,
          "name": x['username'],
          "fastest_year_score": x['fastest_year_score']
      } for rank, x in enumerate(sorted_data)]
    elif category == 'ascended':
      sorted_data = sorted([d for d in data if d.get('ascensions')],
                           key=lambda x: x.get('ascensions', 0),
                           reverse=True)
      sorted_data = [{
          "rank": rank + 1,
          "name": x['username'],
          "ascensions": x.get('ascensions', 0)
      } for rank, x in enumerate(sorted_data)]
    elif category == 'deceased':
      sorted_data = sorted([d for d in data if d.get('deaths')],
                           key=lambda x: x.get('deaths', 0),
                           reverse=True)
      sorted_data = [{
          "rank": rank + 1,
          "name": x['username'],
          "deaths": x.get('deaths', 0)
      } for rank, x in enumerate(sorted_data)]
    else:
      sorted_data = []

    return sorted_data

  # Asynchronously gather sorted data for all categories
  mortal_rankings, immortal_rankings, ascended_rankings, deceased_rankings = await asyncio.gather(
      get_players_data('mortal'), get_players_data('immortal'),
      get_players_data('ascended'), get_players_data('deceased'))

  # Combine all rankings into a single JSON response
  leaderboard_data = {
      "mortal": mortal_rankings,
      "immortal": immortal_rankings,
      "ascended": ascended_rankings,
      "deceased": deceased_rankings
  }

  return jsonify(leaderboard_data)


@app.route('/api/data')
async def api_data():
  current_user = {
      "avatar_url": "none",
      "discriminator": "0",
      "email": "guest@example.com",
      "has_mfa_enabled": False,
      "id": "0",
      "is_verified": False,
      "locale": "en-US",
      "username": "guest"
  }

  player = {
      "id": "0",
      "username": "guest",
      "displayname": "Guest",
      "cultivation_level": 0,
      "bal": 0,
      "using_command": False,
      "tutorial": False,
      "finished_tutorial": False,
      "created_at": "N/A",
      "deaths": 0,
      "dm_cmds": False,
      "helper": False,
      "moderator": False,
      "admin": False,
      "heart_demons": 0,
      "karma": 0,
      "current_sect": "None",
      "dead": False,
      "years_spent": 0,
      "fastest_year_score": 0,
      "max_cultivation_attained": 0,
      "ascensions": 0
  }

  servers_response = await asyncio.get_event_loop().run_in_executor(
      None, lambda: supabase.table('Servers').select('*').execute())
  servercount = len(servers_response.data)

  players_response = await asyncio.get_event_loop().run_in_executor(
      None, lambda: supabase.table('Players').select('*').execute())
  playercount = len(players_response.data)

  achievements_response = await asyncio.get_event_loop().run_in_executor(
      None, lambda: supabase.table('Achievements').select('*').execute())
  achievementcount = len(achievements_response.data)

  if 'token' in session:
    bearer_client = APIClient(session.get('token'), bearer=True)
    user = bearer_client.users.get_current_user()
    if user.discriminator == "0":
      print(f"[*] Logged in as: {user.username}")
    else:
      print(f"[*] Logged in as: {user.username}#{user.discriminator}")
    # Manually extract the needed fields from the user object
    current_user = {
        "avatar_url": user.avatar_url,
        "discriminator": user.discriminator,
        "email": user.email,
        "has_mfa_enabled": user.has_mfa_enabled,
        "id": user.id,
        "is_verified": user.is_verified,
        "locale": user.locale,
        "username": user.username
    }

    response = await asyncio.get_event_loop().run_in_executor(
        None, lambda: supabase.table('Players').select('*').eq('id', user.id).
        execute())

    if response:

      player_data = Player(user, response)

      player = {
          "id": player_data.id,
          "username": player_data.name,
          "displayname": player_data.displayname,
          "cultivation_level": player_data.cultivation_level,
          "bal": player_data.bal,
          "using_command": player_data.using_command,
          "tutorial": player_data.tutorial,
          "finished_tutorial": player_data.finished_tutorial,
          "created_at": player_data.created_at,
          "deaths": player_data.deaths,
          "dm_cmds": player_data.dm_cmds,
          "helper": player_data.helper,
          "moderator": player_data.moderator,
          "admin": player_data.admin,
          "heart_demons": player_data.heart_demons,
          "karma": player_data.karma,
          "current_sect": player_data.current_sect,
          "dead": player_data.dead,
          "years_spent": player_data.years_spent,
          "fastest_year_score": player_data.fastest_year_score,
          "max_cultivation_attained": player_data.max_cultivation_attained,
          "ascensions": player_data.ascensions
      }

  sent_data = {
      'player': player,
      'current_user': current_user,
      'servercount': servercount,
      'playercount': playercount,
      'achievementcount': achievementcount
  }
  # print(f"This is: ", sent_data)

  return sent_data


# # Serve React index.html as the home page
# @app.route('/')
# def serve_react_app():
#     return send_from_directory('frontend/build', 'index.html')


@app.route('/discord')
async def discord():
  return redirect("https://discord.gg/7JkkXRA3nf")


@app.route('/patreon')
async def patreon():
  return redirect("https://www.patreon.com/Cultivatinginsanity")


@app.route('/story')
async def story():
  # Log the request details for analytics
  user_agent = request.headers.get('User-Agent')
  # Determine device type based on User-Agent
  device_type = "Mobile" if "Mobi" in user_agent else "Desktop"

  data = {
      'user_id': 0,
      'user_id_str': "0",
      'username': "website",
      'command_used': "story",
      'server_name': device_type,
      'channel_id': 0,
      'server_id_str': "0"
  }
  await asyncio.get_event_loop().run_in_executor(
      None, lambda: supabase.table('Log').insert(data).execute())
  # Redirect to the story URL
  return redirect(
      "https://www.royalroad.com/fiction/82770/cultivating-insanity-a-xianxia-story"
  )


@app.route("/invite")
async def invite():
  return redirect(
      "https://discord.com/oauth2/authorize?client_id=1217236373208039504&permissions=517543938112&scope=bot+applications.commands"
  )


@app.route('/oauth/callback')
async def callback():
  code = request.args['code']
  access_token = client.oauth.get_access_token(code, redirect_uri).access_token
  session['token'] = access_token
  return redirect("/")


@app.route("/logout")
async def logout():
  session.clear()
  return redirect("/")


@app.route("/login")
async def login():
  return redirect(oath_url)


@app.route('/<path:path>')
async def catch_all(path):
  if path != "" and os.path.exists(app.static_folder + '/' + path):
    return send_from_directory(app.static_folder, path)
  else:
    return render_template(
        'index.html')  # Render the React entry point HTML for other routes


def run_webserver():
  print("[*] Starting webserver...")
  serve(app, host='0.0.0.0', port=8080)
