from flask import Flask, render_template, jsonify
import requests
import time
import threading
import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

app = Flask(__name__)

latest_result = {"bus_count": 0, "last_checked": "Not yet checked"}
last_sent_count = 0  # To track previous bus count and prevent duplicate emails

def send_email(subject, body, to_email):
    """Send an email notification."""
    from_email = "raihanulkarim5@gmail.com"
    from_password = "ildi byvd qslm fvot"  # Consider using environment variables for security

    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(from_email, from_password)
        server.sendmail(from_email, to_email, msg.as_string())
        server.quit()
        print("Email sent successfully!")
    except Exception as e:
        print(f"Failed to send email: {e}")

def find_token(from_city, to_city, date_of_journey):
    """Retrieve authentication token using Selenium."""
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    url = f"https://www.shohoz.com/bus-tickets/booking/bus/search?fromcity={from_city}&tocity={to_city}&doj={date_of_journey}&dor="
    driver.get(url)

    try:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "some_element_id")))
    except:
        pass

    cookies = driver.get_cookies()
    driver.quit()

    for cookie in cookies:
        if cookie['name'] == 'token':
            return cookie['value']
    return None

def find_nested_keys(d, key):
    """Recursively search for a key in a nested dictionary."""
    if key in d:
        return d[key]
    for _, v in d.items():
        if isinstance(v, dict):
            result = find_nested_keys(v, key)
            if result is not None:
                return result
    return None

def get_bus_details():
    """Fetch bus details continuously and send email if buses are available."""
    global latest_result, last_sent_count
    from_city = "Dhaka"
    to_city = "Naogaon"
    date_of_journey = "28-Feb-2025"

    while True:
        token = find_token(from_city, to_city, date_of_journey)
        if not token:
            latest_result = {"bus_count": 0, "last_checked": "Token not found"}
            time.sleep(5)
            continue

        url = "https://webapi.shohoz.com/v1.0/web/booking/bus/search-trips"
        headers = {"Authorization": f"Bearer {token}", "User-Agent": "Mozilla/5.0", "Accept": "application/json"}
        params = {"from_city": from_city, "to_city": to_city, "date_of_journey": date_of_journey}

        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                trips_data = find_nested_keys(data, 'trips')
                bus_count = trips_data.get('total', 0) if trips_data else 0
                latest_result = {"bus_count": bus_count, "last_checked": time.strftime("%Y-%m-%d %H:%M:%S")}

                # Send email only if buses are available and it hasn't been sent before
                if bus_count > 0 and bus_count != last_sent_count:
                    subject = "Bus Available Alert!"
                    body = f"{bus_count} buses are available from {from_city} to {to_city} on {date_of_journey}."
                    send_email(subject, body, "rabsah5@gmail.com")
                    last_sent_count = bus_count  # Update last sent count to prevent duplicate emails

            else:
                latest_result = {"bus_count": 0, "last_checked": f"Error {response.status_code}"}

        except requests.exceptions.RequestException:
            latest_result = {"bus_count": 0, "last_checked": "API request failed"}

        time.sleep(5)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/bus_status")
def bus_status():
    return jsonify(latest_result)

if __name__ == "__main__":
    thread = threading.Thread(target=get_bus_details, daemon=True)
    thread.start()
    app.run(debug=True)
