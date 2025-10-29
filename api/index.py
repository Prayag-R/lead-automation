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

# Configuration - We'll set these as environment variables in Vercel
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
GMAIL_EMAIL = os.environ.get('GMAIL_EMAIL')
GMAIL_APP_PASSWORD = os.environ.get('GMAIL_APP_PASSWORD')
GOOGLE_SHEETS_CREDS = os.environ.get('GOOGLE_SHEETS_CREDS')
SHEET_NAME = os.environ.get('SHEET_NAME', 'Lead Tracker')

# Configure Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

@app.route('/')
def home():
    return send_file('form.html')

@app.route('/api/submit', methods=['POST'])
def submit_form():
    try:
        # Get form data
        data = request.json
        name = data.get('name')
        email = data.get('email')
        phone = data.get('phone')
        message = data.get('message')
        
        # 1. Generate AI response with Gemini
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        prompt = f"""You are a friendly and professional business assistant. A potential customer just submitted a contact form. Write a warm, personalized response (2-3 sentences) thanking them for reaching out and letting them know someone will follow up within 24 hours.

Customer Name: {name}
Customer Email: {email}
Customer Phone: {phone}
Their Message: {message}"""
        
        response = model.generate_content(prompt)
        ai_message = response.text
        
        # 2. Send email via Gmail
        send_email(email, name, ai_message)
        
        # 3. Save to Google Sheets
        save_to_sheets(name, email, phone, message)
        
        return jsonify({'success': True, 'message': 'Form submitted successfully!'})
    
    except Exception as e:
        print(f"Error: {str(e)}")
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
        
        print(f"Email sent to {to_email}")
    except Exception as e:
        print(f"Email error: {str(e)}")
        raise

def save_to_sheets(name, email, phone, message):
    """Save lead to Google Sheets"""
    try:
        # Parse credentials from environment variable
        creds_dict = json.loads(GOOGLE_SHEETS_CREDS)
        
        scope = ['https://spreadsheets.google.com/feeds',
                 'https://www.googleapis.com/auth/drive']
        
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        # Open the sheet
        sheet = client.open(SHEET_NAME).sheet1
        
        # Append row
        row = [name, email, phone, message, datetime.now().strftime('%Y-%m-%d'), 'New Lead']
        sheet.append_row(row)
        
        print(f"Saved to Google Sheets: {name}")
    except Exception as e:
        print(f"Sheets error: {str(e)}")
        raise

if __name__ == '__main__':
    app.run()