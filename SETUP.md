# RMH-BOT — Setup & 24/7 Hosting Guide

## 1. Edit your config

Open `config.json` and fill in:

- `bot_token`  -> your Telegram bot token from @BotFather
- `admin_ids`  -> Telegram numeric user IDs allowed to control the bot
                  (get your ID from @userinfobot). Add as many as you want,
                  separated by commas.
- `sending_time` -> minutes between each forwarding cycle

Example:
{
    "bot_token": "1234567890:ABCdefGHIjklMNOpqrs",
    "admin_ids": [6802846284, 7229880874],
    "sending_time": 10
}

You can also add/remove admins WITHOUT restarting: just edit config.json
and save. The bot re-reads it on every command.

## 2. Run on a DigitalOcean server (24/7)

SSH into your droplet, then:

    sudo apt update && sudo apt install -y python3 python3-pip git
    git clone https://github.com/i-RanaMHaseeb/RMH-BOT.git
    cd RMH-BOT
    pip3 install -r requirements.txt

Now edit config.json on the server:

    nano config.json      # paste your token + admin IDs, save with Ctrl+O, Ctrl+X

Keep it running 24/7 with pm2:

    sudo apt install -y nodejs npm
    sudo npm install -g pm2
    pm2 start app.py --name rmh-bot --interpreter python3
    pm2 save
    pm2 startup           # run the command it prints, to survive reboots

Useful commands:
    pm2 logs rmh-bot      # see live output
    pm2 restart rmh-bot   # restart after editing config
    pm2 stop rmh-bot      # stop the bot

## 3. Security

- NEVER commit config.json to GitHub (.gitignore already blocks it).
- If your token ever leaks, revoke it in @BotFather and put the new one
  in config.json.
