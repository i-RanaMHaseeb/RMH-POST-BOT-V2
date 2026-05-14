import telebot
import json
import os
import threading
import time
import re
import datetime

# ----------------------------
# Utility: Logging Errors to log.json
# ----------------------------
def log_error(error_message):
    log_data = []
    if os.path.exists("log.json"):
        try:
            with open("log.json", "r", encoding="utf-8") as f:
                log_data = json.load(f)
        except Exception:
            log_data = []
    log_entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "error": error_message
    }
    log_data.append(log_entry)
    with open("log.json", "w", encoding="utf-8") as f:
        json.dump(log_data, f, indent=4)
    print(f"[LOG] {log_entry}")

# ----------------------------
# Utility: JSON File Initialization and Read/Write
# ----------------------------
def init_json(file_name, default_data):
    if not os.path.exists(file_name):
        with open(file_name, 'w', encoding="utf-8") as f:
            json.dump(default_data, f, indent=4)
        print(f"[INIT] Created {file_name} with default data.")

init_json('config.json', {
    "bot_token": "YOUR_BOT_TOKEN_HERE",  # Replace with your bot token
    "admin_ids": [],                     # Add admin user IDs here (as integers)
    "sending_time": 15                   # Default sending time (in minutes)
})
init_json('messages.json', [])
init_json('groups.json', [])

def read_json(file_name):
    try:
        with open(file_name, 'r', encoding="utf-8") as f:
            data = json.load(f)
        print(f"[READ] {file_name} read successfully.")
        return data
    except FileNotFoundError:
        print(f"[ERROR] {file_name} not found.")
        raise
    except json.JSONDecodeError as e:
        print(f"[ERROR] {file_name} has invalid JSON: {e}")
        raise

def write_json(file_name, data):
    with open(file_name, 'w', encoding="utf-8") as f:
        json.dump(data, f, indent=4)
    print(f"[WRITE] {file_name} updated successfully.")

# ----------------------------
# Bot Initialization
# ----------------------------
config = read_json('config.json')
bot_token = config.get("bot_token")
if not bot_token or bot_token == "PUT_YOUR_BOT_TOKEN_HERE":
    raise SystemExit("[ERROR] Please set your real bot_token in config.json before running.")
bot = telebot.TeleBot(bot_token)

# ----------------------------
# Global Variables & States
# ----------------------------
admin_states = {}         # Mapping of admin_id -> state (awaiting input)
forwarding_active = False # Flag for message forwarding
forwarding_thread = None  # Thread for forwarding process

# ----------------------------
# Helper: Back Button Keyboard
# ----------------------------
def back_keyboard():
    keyboard = telebot.types.InlineKeyboardMarkup()
    keyboard.add(telebot.types.InlineKeyboardButton("🔙 Back", callback_data="back"))
    return keyboard

# ----------------------------
# Admin Main Menu
# ----------------------------
def admin_menu(message):
    keyboard = telebot.types.InlineKeyboardMarkup()
    keyboard.row(
        telebot.types.InlineKeyboardButton("Set Group ➕", callback_data="set_group"),
        telebot.types.InlineKeyboardButton("Remove Group ➖", callback_data="remove_group")
    )
    keyboard.row(
        telebot.types.InlineKeyboardButton("All Groups 📋", callback_data="all_groups"),
        telebot.types.InlineKeyboardButton("Add Message 💬", callback_data="add_message")
    )
    keyboard.row(
        telebot.types.InlineKeyboardButton("Edit Message 📝", callback_data="edit_message"),
        telebot.types.InlineKeyboardButton("Edit Time ⏰", callback_data="edit_time")
    )
    keyboard.row(
        telebot.types.InlineKeyboardButton("Start ▶️", callback_data="start"),
        telebot.types.InlineKeyboardButton("Stop ⏹", callback_data="stop")
    )
    bot.send_message(message.chat.id, "**Admin Menu**", reply_markup=keyboard, parse_mode="Markdown")

# ----------------------------
# /admin Command Handler
# ----------------------------
@bot.message_handler(commands=['admin'])
def handle_admin(message):
    user_id = message.from_user.id
    config = read_json('config.json')
    if user_id not in config.get("admin_ids", []):
        bot.reply_to(message, "🚫 You are not authorized!")
        return
    admin_menu(message)

# ----------------------------
# Callback Query Handler (Inline Buttons)
# ----------------------------
@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    global forwarding_active, forwarding_thread
    config = read_json('config.json')

    # Debug print for callback data
    print(f"[DEBUG] Callback data received: {call.data}")

    if call.from_user.id not in config.get("admin_ids", []):
        bot.answer_callback_query(call.id, "🚫 Not authorized!")
        return

    if call.data == "set_group":
        bot.send_message(call.message.chat.id, "Enter group IDs (comma separated):")
        admin_states[call.from_user.id] = "set_group"
    elif call.data == "remove_group":
        bot.send_message(call.message.chat.id, "Enter group IDs to remove (comma separated):")
        admin_states[call.from_user.id] = "remove_group"
    elif call.data == "all_groups":
        groups = read_json('groups.json')
        groups_str = "\n".join(groups) if groups else "No groups found."
        with open("groups.txt", "w", encoding="utf-8") as f:
            f.write(groups_str)
        bot.send_document(call.message.chat.id, open("groups.txt", "rb"))
    elif call.data == "add_message":
        bot.send_message(call.message.chat.id, "Enter message link (e.g., https://t.me/ByRanaMHaseeb/155):")
        admin_states[call.from_user.id] = "add_message"
    elif call.data == "edit_message":
        messages_list = read_json("messages.json")
        messages_str = "\n".join(messages_list)
        with open("messages_edit.txt", "w", encoding="utf-8") as f:
            f.write(messages_str)
        bot.send_document(call.message.chat.id, open("messages_edit.txt", "rb"))
        bot.send_message(call.message.chat.id, "Upload a new TXT file to update message links or type /terminate to cancel.")
        admin_states[call.from_user.id] = "edit_message"
    elif call.data == "edit_time":
        bot.send_message(call.message.chat.id, "Enter new sending time (in minutes):")
        admin_states[call.from_user.id] = "edit_time"
    elif call.data == "start":
        if not forwarding_active:
            forwarding_active = True
            forwarding_thread = threading.Thread(target=forward_messages)
            forwarding_thread.daemon = True
            forwarding_thread.start()
            bot.send_message(call.message.chat.id, "✅ Forwarding started.")
        else:
            bot.send_message(call.message.chat.id, "🔄 Forwarding is already running.")
    elif call.data == "stop":
        if forwarding_active:
            forwarding_active = False
            bot.send_message(call.message.chat.id, "⏹ Forwarding stopped.")
        else:
            bot.send_message(call.message.chat.id, "Forwarding is not running.")
    elif call.data == "back":
        admin_menu(call.message)

    bot.answer_callback_query(call.id)

# ----------------------------
# Admin Input Handler (Text & Document Uploads)
# ----------------------------
@bot.message_handler(
    func=lambda m: m.from_user.id in read_json('config.json').get("admin_ids", []),
    content_types=["text","document","photo","audio","video","voice","sticker","any"]
)
def handle_admin_input(message):
    print(f"[DEBUG] handle_admin_input triggered. content_type={message.content_type}")
    user_id = message.from_user.id
    print(f"[DEBUG] admin_states before processing: {admin_states}")

    if user_id not in admin_states:
        return  # Not expecting any input from this user right now

    state = admin_states.pop(user_id)
    print(f"[DEBUG] Handling state='{state}' for user={user_id}")

    if state == "set_group":
        groups_to_add = [grp.strip() for grp in message.text.split(",") if grp.strip()]
        groups = read_json('groups.json')
        for grp in groups_to_add:
            if grp not in groups:
                groups.append(grp)
        write_json('groups.json', groups)
        bot.send_message(message.chat.id, "✅ Groups added.", reply_markup=back_keyboard())

    elif state == "remove_group":
        groups_to_remove = [grp.strip() for grp in message.text.split(",") if grp.strip()]
        groups = read_json('groups.json')
        groups = [grp for grp in groups if grp not in groups_to_remove]
        write_json('groups.json', groups)
        bot.send_message(message.chat.id, "✅ Groups removed.", reply_markup=back_keyboard())

    elif state == "add_message":
        message_link = message.text.strip()
        messages_list = read_json('messages.json')
        messages_list.append(message_link)
        write_json('messages.json', messages_list)
        bot.send_message(message.chat.id, "✅ Message link added.", reply_markup=back_keyboard())

    elif state == "edit_time":
        try:
            new_time = int(message.text.strip())
            config = read_json('config.json')
            config["sending_time"] = new_time
            write_json('config.json', config)
            bot.send_message(message.chat.id, f"✅ Sending time updated to {new_time} minutes.", reply_markup=back_keyboard())
        except Exception as e:
            log_error(f"Edit Time Error: {e}")
            bot.send_message(message.chat.id, "❌ Invalid input. Please enter a number.", reply_markup=back_keyboard())

    elif state == "edit_message":
        print(f"[DEBUG] Received admin input in 'edit_message' state from user {user_id}.")
        # If user typed /terminate, cancel
        if message.text and message.text.strip() == "/terminate":
            print("[DEBUG] Termination command received for edit_message.")
            bot.send_message(message.chat.id, "Editing cancelled.", reply_markup=back_keyboard())

        # If user uploaded a document
        elif message.document:
            print(f"[DEBUG] Document received: {message.document.file_name}")
            try:
                file_info = bot.get_file(message.document.file_id)
                print(f"[DEBUG] File info: {file_info}")
                downloaded_file = bot.download_file(file_info.file_path)
                print(f"[DEBUG] File downloaded successfully, size: {len(downloaded_file)} bytes")
                file_content = downloaded_file.decode("utf-8")
                print("[DEBUG] File content decoded successfully.")
                new_links = [line.strip() for line in file_content.splitlines() if line.strip()]
                print(f"[DEBUG] Extracted links: {new_links}")
                write_json("messages.json", new_links)
                print("[DEBUG] messages.json has been updated with new message links.")
                bot.send_message(message.chat.id, "✅ Message links updated.", reply_markup=back_keyboard())
            except Exception as e:
                print(f"[ERROR] Processing document failed: {e}")
                log_error(f"Edit Message File Error: {e}")
                bot.send_message(message.chat.id, "❌ Failed to update message links. Try again or type /terminate.", reply_markup=back_keyboard())

        else:
            # If the user sends something else (like text or photo)
            print("[DEBUG] No document uploaded in edit_message state; prompting user again.")
            bot.send_message(message.chat.id, "Please upload a TXT file or type /terminate.", reply_markup=back_keyboard())

# ----------------------------
# Message Forwarding Functionality
# ----------------------------
def forward_messages():
    while forwarding_active:
        try:
            config = read_json('config.json')
            sending_time = config.get("sending_time", 15)
            groups = read_json('groups.json')
            messages_list = read_json('messages.json')
        except Exception as e:
            log_error(f"Reading JSON Error: {e}")
            time.sleep(60)
            continue

        for message_link in messages_list:
            try:
                # Process private channel pattern: https://t.me/c/<channel_id>/<message_id>
                match_private = re.search(r'https://t\.me/c/(\d+)/(\d+)', message_link)
                if match_private:
                    channel_id_numeric = match_private.group(1)
                    message_id = int(match_private.group(2))
                    source_channel = int("-100" + channel_id_numeric)
                else:
                    # Process public channel pattern: https://t.me/<username>/<message_id>
                    match_public = re.search(r'https://t\.me/([^/]+)/(\d+)', message_link)
                    if match_public:
                        channel_username = match_public.group(1)
                        message_id = int(match_public.group(2))
                        source_channel = "@" + channel_username
                    else:
                        continue

                # Check source channel access (if error, skip this message)
                try:
                    bot.get_chat(source_channel)
                except Exception as e:
                    log_error(f"Source Channel Access Error for {source_channel}: {e}")
                    continue

                for group in groups:
                    try:
                        group_id = int(group)
                        bot.forward_message(group_id, source_channel, message_id)
                    except Exception as e:
                        log_error(f"Forwarding Error (group {group}): {e}")
            except Exception as e:
                log_error(f"Processing Error for link {message_link}: {e}")

        time.sleep(sending_time * 60)

# ----------------------------
# Start Bot Polling
# ----------------------------
# Infinity Polling with Restart Mechanism
try:
    bot_info = bot.get_me()
    bot_name = bot_info.first_name
    print(f"✅ Bot '{bot_name}' has started successfully!")
except Exception as e:
    bot_name = "UnknownBot"
    print(f"⚠️ Error getting bot name: {e}")

def start_polling():
    while True:
        try:
            bot.polling()
        except Exception as e:
            print(f"⚠️ Polling Exception: {e}")
            config = read_json('config.json')
            admin_ids = config.get("admin_ids", [])
            for admin in admin_ids:
                try:
                    bot.send_message(admin, f"Please start again, I have been restarted! Bot name: {bot_name}")
                except Exception as e2:
                    print(f"⚠️ Error notifying admin {admin}: {e2}")
            time.sleep(5)

start_polling()
