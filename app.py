from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
import os
import requests
import json
from datetime import datetime

app = Flask(__name__)
CORS(app)

# MongoDB connection
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["StartUp_History"]
collection = db["Idea_History"]

# Groq API setup
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama3-8b-8192"

HEADERS = {
    "Authorization": f"Bearer {GROQ_API_KEY}",
    "Content-Type": "application/json"
}

PROMPT_TEMPLATE = """
You are StartupGPT, a startup co-pilot AI. The user will give you an app or startup idea.
Based on the idea, generate strictly valid and escaped JSON:
1. A 2-3 sentence elevator pitch.
2. A simple landing page in HTML (with inline CSS; ensure all quotes are escaped).
3. A recommended tech stack.
4. 3 unique core feature suggestions.

Idea: {idea}

Respond ONLY in this JSON format:
{{
  "pitch": "...",
  "landing_page_html": "...",
  "tech_stack": "...",
  "core_features": ["...", "...", "..."]
}}
"""

@app.route("/generate", methods=["POST"])
def generate():
    data = request.json
    idea = data.get("idea")

    if not idea:
        return jsonify({"error": "Missing 'idea' field"}), 400

    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {
                "role": "user",
                "content": PROMPT_TEMPLATE.format(idea=idea)
            }
        ],
        "temperature": 0.8
    }

    try:
        response = requests.post(GROQ_API_URL, headers=HEADERS, json=payload)
        response.raise_for_status()

        content = response.json()["choices"][0]["message"]["content"]
        result = json.loads(content)  # ✅ Safe JSON parsing

        # Add metadata
        result["idea"] = idea
        result["timestamp"] = datetime.utcnow()

        # Save to MongoDB
        collection.insert_one(result)

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": "Failed to generate or parse Groq response", "details": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
