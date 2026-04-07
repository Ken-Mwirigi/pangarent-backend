import os
import base64
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

# Force load the .env file so we know the keys aren't empty!
load_dotenv()

def get_mpesa_access_token():
    consumer_key = os.getenv('MPESA_CONSUMER_KEY')
    consumer_secret = os.getenv('MPESA_CONSUMER_SECRET')
    
    # Quick sanity check in your terminal
    print(f"DEBUG: Consumer Key is loaded? {'YES' if consumer_key else 'NO - Check .env file!'}")

    api_url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    
    try:
        r = requests.get(api_url, auth=HTTPBasicAuth(consumer_key, consumer_secret))
        
        # If Daraja doesn't return 200 OK, print their exact error message
        if r.status_code != 200:
            print(f"DARAJA AUTH REJECTION [{r.status_code}]: {r.text}")
            return None
            
        return r.json().get('access_token')
    except Exception as e:
        print(f"Error getting token: {e}")
        return None

def generate_mpesa_password(shortcode, passkey, timestamp):
    data_to_encode = shortcode + passkey + timestamp
    encoded_string = base64.b64encode(data_to_encode.encode())
    return encoded_string.decode('utf-8')

def format_phone_number(phone):
    """Ensures phone number is in 2547XXXXXXXX format for Daraja"""
    phone = str(phone).strip()
    if phone.startswith('+'):
        phone = phone[1:]
    if phone.startswith('0'):
        phone = '254' + phone[1:]
    if phone.startswith('7') or phone.startswith('1'):
        phone = '254' + phone
    return phone

