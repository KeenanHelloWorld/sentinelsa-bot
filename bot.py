import requests
import re
import time

class Bot:
    def __init__(self):
        self.base_url = 'http://example.com/api'

    def fetch_data(self):
        try:
            response = requests.get(self.base_url, timeout=10)
            response.raise_for_status()  # Raise an error for bad responses
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            print(f'HTTP error occurred: {http_err}')
        except requests.exceptions.Timeout:
            print('The request timed out')
        except requests.exceptions.RequestException as err:
            print(f'An error occurred: {err}')
        return None

    def process_data(self, data):
        if data:
            pattern = re.compile(r'\b\d{3}\b')  # Example regex pattern
            for item in data:
                if pattern.search(item['field']):
                    print(f'Match found: {item}')  
                else:
                    print('No match found')

# Example usage
if __name__ == '__main__':
    bot = Bot()
    data = bot.fetch_data()
    bot.process_data(data)