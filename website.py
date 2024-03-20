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

website = "f92e22d0-556f-460b-96d7-a2bc3920a4e6-00-1eyvu4gm9ri3.worf.replit.dev"

redirect_uri = f"https://{website}/oauth/callback"

oath_url = f"https://discord.com/oauth2/authorize?client_id=530708819458654219&response_type=code&redirect_uri=https%3A%2F%2F{website}%2Foauth%2Fcallback&scope=identify+email"

token = os.getenv("TOKEN") or ""
client_secret = os.getenv("CLIENT_SECRET") or ""

app = Flask(__name__,
            template_folder='frontend/build',
            static_folder='frontend/build/static')

client = APIClient(token, client_secret=client_secret)

app.config["SECRET_KEY"] = "verysecret"


@app.route('/')
def homepage():
  servers_response = supabase.table('Servers').select('*').execute()
  servercount = len(servers_response.data)

  players_response = supabase.table('Players').select('*').execute()
  playercount = len(players_response.data)

  achievements_response = supabase.table('Achievements').select('*').execute()
  achievementcount = len(achievements_response.data)

  if 'token' in session:
    bearer_client = APIClient(session.get('token'), bearer=True)
    current_user = bearer_client.users.get_current_user()
    if current_user.discriminator == "0":
      print(f"[*] Logged in as: {current_user.username}")
    else:
      print(
          f"[*] Logged in as: {current_user.username}#{current_user.discriminator}"
      )
  else:
    current_user = "guest"

  return render_template('index.html',
                         current_user=current_user,
                         servercount=servercount,
                         playercount=playercount,
                         achievementcount=achievementcount)


@app.route('/api/data')
def api_data():
  servers_response = supabase.table('Servers').select('*').execute()
  servercount = len(servers_response.data)

  players_response = supabase.table('Players').select('*').execute()
  playercount = len(players_response.data)

  achievements_response = supabase.table('Achievements').select('*').execute()
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
  else:
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

  # Continue with your logic to get servercount, playercount, and achievementcount...

  sent_data = {
      'current_user': current_user,
      'servercount': servercount,
      'playercount': playercount,
      'achievementcount': achievementcount
  }
  print("This is: ", sent_data)

  return sent_data


# # Serve React index.html as the home page
# @app.route('/')
# def serve_react_app():
#     return send_from_directory('frontend/build', 'index.html')


@app.route('/discord')
def discord():
  return redirect("https://discord.gg/7JkkXRA3nf")


@app.route('/patreon')
def patreon():
  return redirect("https://www.patreon.com/Cultivatinginsanity")


@app.route("/invite")
def invite():
  return redirect(
      "https://discord.com/oauth2/authorize?client_id=1217236373208039504&permissions=517543938112&scope=bot+applications.commands"
  )


@app.route('/oauth/callback')
def callback():
  code = request.args['code']
  access_token = client.oauth.get_access_token(code, redirect_uri).access_token
  session['token'] = access_token
  return redirect("/")


@app.route("/logout")
def logout():
  session.clear()
  return redirect("/")


@app.route("/login")
def login():
  return redirect(oath_url)


@app.route('/<path:path>')
def catch_all(path):
  if path != "" and os.path.exists(app.static_folder + '/' + path):
    return send_from_directory(app.static_folder, path)
  else:
    return render_template(
        'index.html')  # Render the React entry point HTML for other routes


def run_webserver():
  print("[*] Starting webserver...")
  serve(app, host='0.0.0.0', port=8080)
