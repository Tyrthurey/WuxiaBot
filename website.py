from flask import Flask, render_template, jsonify, request, session, redirect
import threading
import asyncio
from supabase import create_client, Client
from waitress import serve
from zenora import APIClient

# token = os.getenv("TOKEN") or ""

# redirect_uri = "https://3d679f0f-06d3-46a3-b645-8cf309d1be3f-00-z6h7j9fc522a.worf.replit.dev/oauth/callback"

# oath_url = "https://discord.com/api/oauth2/authorize?client_id=530708819458654219&response_type=code&redirect_uri=https%3A%2F%2F3d679f0f-06d3-46a3-b645-8cf309d1be3f-00-z6h7j9fc522a.worf.replit.dev%2Foauth%2Fcallback&scope=identify+email"

# client_secret = os.getenv("CLIENT_SECRET") or ""

app = Flask(__name__,
            template_folder='website',
            static_folder='website/static')

# client = APIClient(token, client_secret=client_secret)

app.config["SECRET_KEY"] = "verysecret"

app = Flask(__name__)


@app.route('/')
def home():
  return 'Hello World!'

@app.route('/discord')
def discord():
  return redirect("https://discord.gg/7JkkXRA3nf")


@app.route("/invite")
def invite():
  return redirect(
      "https://discord.com/oauth2/authorize?client_id=1217236373208039504&permissions=517543938112&scope=bot+applications.commands"
  )

def run_webserver():
  print("[*] Starting webserver...")
  serve(app, host='0.0.0.0', port=8080)
