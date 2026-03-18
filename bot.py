import logging
import signal
import sys
import feedparser
import os
import json

TOKEN = '8667405332:AAGCSc68ZbvYof0EZ63WTghIOgAAMTGWDQo'
STATE_FILE = 'data/state.json'

logging.basicConfig(level=logging.INFO)

class PersistentState:
    def __init__(self, filename):
        self.filename = filename
        self.state = self.load_state()

    def load_state(self):
        if os.path.exists(self.filename):
            with open(self.filename, 'r') as f:
                return json.load(f)
        return {}

    def save_state(self):
        with open(self.filename, 'w') as f:
            json.dump(self.state, f)

state = PersistentState(STATE_FILE)

def handle_signal(signal, frame):
    logging.info("Graceful shutdown.")
    state.save_state()
    sys.exit(0)

def monitor_gauteng_security_incidents():
    url = 'https://gauteng.gov.za/security-incidents'
    feed = feedparser.parse(url, agent='SentinelSA Bot', timeout=10)
    for entry in feed.entries:
        # Implement your monitoring logic here
        logging.info(f'Incident found: {entry.title}')

if __name__ == '__main__':
    signal.signal(signal.SIGINT, handle_signal)
    logging.info("Starting SentinelSA Telegram bot.")
    while True:
        monitor_gauteng_security_incidents()