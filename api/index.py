from flask import Flask, request, jsonify, send_file
import google.generativeai as genai
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
from datetime import datetime
import json

app = Flask(__name__)

# --- Environment Config ---
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
GMAIL_EMAIL = os.environ.get('GMAIL_EMAIL')
GMAIL_APP_PASSWORD = os.environ.get('GMAIL_APP_PASSWORD')
GOOGLE_SHEETS_CREDS = os.environ.get('GOOGLE_SHEETS_CREDS')
SHEET_NAME = os.environ.get('SHEET_NAME', 'Lead Tracker')

# --- Configure Gemini ---
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)


@app.route('/')
def home():
    return send_file('form.html')


@app.route('/api/submit', methods=['POST'])
def submit_form():
    try:
        data = request.json
        name = data.get('name')
        email = data.get('email')
        phone = data.get('phone')
        message = data.get('message')

        # 1️⃣ Generate AI response
        model = genai.GenerativeModel('gemini-flash-latest')
        prompt = f"""You are a friendly and professional business assistant. 
A potential customer just submitted a contact form. Write a warm, personalized 
response (2-3 sentences) thanking them for reaching out and letting them know 
someone will follow up within 24 hours.

Customer Name: {name}
Customer Email: {email}
Customer Phone: {phone}
Their Message: {message}"""

        response = model.generate_content(prompt)
        ai_message = response.text.strip() if response.text else "Thanks for reaching out! We'll be in touch soon."

        # 2️⃣ Send email
        send_email(email, name, ai_message)

        # 3️⃣ Save to Google Sheets (non-fatal if it fails)
        try:
            save_to_sheets(name, email, phone, message)
        except Exception as e:
            print(f"⚠️ Warning: Failed to save to Sheets — {e}")

        print("✅ Form processed successfully.")
        return jsonify({'success': True, 'message': 'Form submitted successfully!'})

    except Exception as e:
        print(f"❌ Server error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


def send_email(to_email, name, ai_message):
    """Send email using Gmail SMTP"""
    try:
        msg = MIMEMultipart()
        msg['From'] = GMAIL_EMAIL
        msg['To'] = to_email
        msg['Subject'] = 'Thanks for reaching out!'

        body = f"{ai_message}\n\nBest regards,\nYour Business Name\n555-1234\nyourwebsite.com"
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(GMAIL_EMAIL, GMAIL_APP_PASSWORD)
        server.send_message(msg)
        server.quit()

        print(f"📧 Email sent to {to_email}")
    except Exception as e:
        print(f"❌ Email error: {e}")
        raise


def save_to_sheets(name, email, phone, message):
    """Save lead to Google Sheets"""
    creds_dict = json.loads(GOOGLE_SHEETS_CREDS)
    scope = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive'
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    sheet = client.open(SHEET_NAME).sheet1

    row = [
        name,
        email,
        phone,
        message,
        datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'New Lead'
    ]
    sheet.append_row(row)
    print(f"📝 Saved to Google Sheets: {name}")


if __name__ == '__main__':
    app.run()
