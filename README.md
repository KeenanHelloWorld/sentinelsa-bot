# Sentinelsa Bot

## Setup Instructions for Activating and Running the Telegram Bot

### Prerequisites
1. **Node.js**: Ensure you have Node.js installed. You can download it from the [official Node.js website](https://nodejs.org/).
2. **Telegram Account**: You need a Telegram account to create and manage your bot.

### Steps to Set Up the Bot

1. **Create a New Bot on Telegram**:
    - Open your Telegram app.
    - Search for the **BotFather** in the search bar and start a chat.
    - Use the `/newbot` command and follow the instructions to create a new bot.
    - You will receive a **token** for your new bot. Keep this token safe, as you will need it later.

2. **Clone the Repository**:
   ```bash
   git clone https://github.com/KeenanHelloWorld/sentinelsa-bot.git
   cd sentinelsa-bot
   ```

3. **Install Dependencies**:
   ```bash
   npm install
   ```

4. **Create a Configuration File** (`config.js`):  
   In the root of your project directory, create a file named `config.js` and add the following content:
   ```javascript
   module.exports = {
       telegramToken: 'YOUR_TELEGRAM_BOT_TOKEN'
   };
   ```
   Replace `'YOUR_TELEGRAM_BOT_TOKEN'` with the token you received from the BotFather.

5. **Run the Bot**:
   ```bash
   node bot.js
   ```

6. **Interact with Your Bot**:  
   Open Telegram and send a message to your bot. You should see responses based on the code in your bot.

### Additional Information
- You can modify the behavior of the bot by editing the `bot.js` file and adding new features.
- For further customization, consider checking the [Telegraf documentation](https://telegraf.js.org/) for more advanced options.

### Troubleshooting
- Ensure Node.js is installed correctly by running `node -v` in your terminal.
- If you encounter any issues regarding dependencies, try deleting the `node_modules` folder and running `npm install` again.

---