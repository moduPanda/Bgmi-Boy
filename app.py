from flask import Flask, jsonify
import os

app = Flask(__name__)

@app.route('/')
def home():
    return "Telegram Bot Web Service is running"

@app.route('/ping')
def ping():
    return jsonify({"status": "ok", "service": "telegram-bot"})

@app.route('/status')
def status():
    return jsonify({
        "status": "active",
        "bot": "running",
        "environment": os.getenv("ENVIRONMENT", "development")
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
