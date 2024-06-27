from flask import Flask, request, send_file, jsonify
import pandas as pd
from fuzzywuzzy import process
import requests
import io
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build

app = Flask(__name__, static_url_path='', static_folder='static')

# Load the prompts from CSV file
def load_prompts_from_csv(file_path):
    df = pd.read_csv(file_path, delimiter='|')
    return df

prompts_df = load_prompts_from_csv('prompt.csv')

# Google Drive API setup
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
SERVICE_ACCOUNT_FILE = 'diesel-ring-340909-0005e45c56b4.json'

credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)

service = build('drive', 'v3', credentials=credentials)

def find_google_drive_id(file_name):
    results = service.files().list(
        q=f"name='{file_name}' and trashed=false",
        fields="files(id, name)").execute()
    items = results.get('files', [])
    if not items:
        return None
    return items[0]['id']

def find_best_match(input_prompt, prompts_df):
    choices = prompts_df['prompt'].tolist()
    best_match, score = process.extractOne(input_prompt, choices)
    print(best_match, score)
    if score > 70:  # Threshold for a good match
        match_row = prompts_df[prompts_df['prompt'] == best_match].iloc[0]
        return match_row['video_id']
    return None

@app.route('/generate', methods=['POST'])
def generate_video():
    try:
        data = request.json
        prompt = data.get('prompt')

        if not prompt:
            return jsonify({"error": "Prompt is required"}), 400

        video_id = "mixkit_v2_" + find_best_match(prompt, prompts_df) 

        print(video_id)

        if not video_id:
            return jsonify({"error": "No matching video found"}), 404

        google_drive_id = find_google_drive_id(video_id)

        if not google_drive_id:
            return jsonify({"error": "Failed to find video on Google Drive"}), 404

    
        google_drive_url = f"https://drive.google.com/uc?export=download&id={google_drive_id}"
        response = requests.get(google_drive_url)
        
        if response.status_code != 200:
            print("Failed here")
            return jsonify({"error": "Failed to retrieve video from Google Drive"}), 500

        video_stream = io.BytesIO(response.content)

        return send_file(
            video_stream,
            mimetype='video/mp4',
            as_attachment=True,
            download_name=video_id
        )
    except Exception as e:
        print("or failed here")
        print(str(e))
        return jsonify({"error": str(e)}), 500

@app.route('/')
def index():
    return send_file('static/index.html')


if __name__ == '__main__':
    app.run(debug=True, port=5006)
