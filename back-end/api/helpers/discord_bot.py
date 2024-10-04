import requests
import os

def send_discord_message(message):
    print(message)
    response = requests.post(os.getenv('DISCORD_WEBHOOK'), json={'content': message})

    if response.status_code == 204:
        print("Message sent successfully.")
    else:
        print(f"Failed to send message. Status code: {response.status_code}")
