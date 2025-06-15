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
You are StartupGPT, a startup co-pilot AI. You will receive a startup idea and must respond ONLY with valid JSON. 
Do not include markdown formatting, ```json blocks, or any commentary. All quotes must be escaped properly.

Only return a valid JSON response like this:
{{
  "pitch": "...",
  "landing_page_html": "...",
  "tech_stack": "...",
  "core_features": ["...", "...", "..."]
}}

Startup Idea: {idea}
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
        "temperature": 0.7
    }

    try:
        response = requests.post(GROQ_API_URL, headers=HEADERS, json=payload)
        response.raise_for_status()

        groq_response = response.json()
        content = groq_response["choices"][0]["message"]["content"]

        print("🔍 RAW GROQ RESPONSE:\n", content)

        result = json.loads(content)  # Safely parse JSON

        # Add metadata
        result["idea"] = idea
        result["timestamp"] = datetime.utcnow()

        # Save to MongoDB
        collection.insert_one(result)

        return jsonify(result)

    except json.JSONDecodeError as je:
        print("❌ JSON PARSE ERROR:", je)
        print("⚠️ Full Groq response object:", response.text)
        return jsonify({
            "error": "Failed to parse Groq response as JSON",
            "details": str(je)
        }), 500

    except Exception as e:
        print("❌ Other error:", e)
        return jsonify({
            "error": "Failed to generate or parse Groq response",
            "details": str(e)
        }), 500

if __name__ == "__main__":
    app.run(debug=True)
