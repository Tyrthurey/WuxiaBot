from flask import Flask, render_template, jsonify, request, session, redirect, send_from_directory
import threading
from threading import Thread
import asyncio
from supabase import create_client, Client
from waitress import serve
from zenora import APIClient
import datetime
import time
import os

app = Flask(__name__,
            template_folder='frontend/build',
            static_folder='frontend/build/static')

app.config["SECRET_KEY"] = "verysecret"


@app.route('/')
def home():
  return render_template('index.html')  # Render the React entry point HTML

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


x = datetime.datetime.now()


@app.route('/time')
def get_current_time():
  return {'time': time.time()}


@app.route('/data')
def get_time():
  return {
      'Name': "geek",
      "Age": "22",
      "Date": x.strftime("%Y-%m-%d"),
      "programming": "python"
  }


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
