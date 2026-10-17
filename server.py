from telethon import TelegramClient, events
from telethon.errors.rpcerrorlist import (
    PhoneNumberBannedError, PeerFloodError, UserPrivacyRestrictedError,
    ChatAdminRequiredError, ChatWriteForbiddenError, UserBannedInChannelError,
    UserAlreadyParticipantError, FloodWaitError
)
from telethon.tl.functions.channels import InviteToChannelRequest
import os, random, asyncio
from threading import Thread
from flask import Flask
from colorama import init, Fore

init()
app = Flask(__name__)

# Colors
n = Fore.RESET
lg = Fore.LIGHTGREEN_EX
r = Fore.RED
w = Fore.WHITE
cy = Fore.CYAN
ye = Fore.YELLOW
info = f'{lg}[{w}i{lg}]{n}'
error = f'{lg}[{r}!{lg}]{n}'
success = f'{w}[{lg}*{w}]{n}'

# --- ENV VARIABLES - RENDER ---
APP_ID = int(os.environ["APP_ID"])
APP_HASH = os.environ["APP_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]

client = TelegramClient('bot_session_v2', APP_ID, APP_HASH)

scraped_grp = None
target_link = None
process_started = False

@app.route('/')
def index():
    return "Crypto Hub Arb Bot is running ✅"

def start_method():
    return "👋 Welcome to Crypto Hub Arb Adder Bot!\n\nSend SOURCE group link first (https://t.me/...)\nThen send TARGET group link\nThen send /process\n\nCommands:\n/start - Start\n/process - Start adding\n/stop - Stop adding\n/reset - Reset links"

def source_method(group_link):
    global scraped_grp
    scraped_grp = group_link
    return f"✅ Source group set to: {scraped_grp}\n\nNow, please provide the target group link."

def target_method(target):
    global target_link
    target_link = target
    return f"✅ Target group set to: {target_link}\n\nNow, use /process to start adding members."

async def process_method(event):
    global scraped_grp, target_link, process_started
    if not scraped_grp or not target_link:
        return "❌ Please set both source and target groups first."
    
    process_started = True
    await event.reply(f"🚀 Starting the process...\n\nSource Group: {scraped_grp}\nTarget Group: {target_link}\n\nPlease wait...")
    
    try:
        source_entity = await client.get_entity(scraped_grp)
        target_entity = await client.get_entity(target_link)
        members = await client.get_participants(source_entity, aggressive=True)
        total_members = len(members)
        await event.reply(f"🔍 Found {total_members} members in the source group.")
        
        added_count = 0
        skipped_count = 0
        
        for i, user in enumerate(members):
            if not process_started:
                break
            try:
                if not user or not hasattr(user, 'id') or not user.id:
                    skipped_count += 1
                    continue
                
                await client(InviteToChannelRequest(target_entity, [user]))
                added_count += 1
                print(f"{success} Added {user.first_name} ({user.id})")
                await asyncio.sleep(random.uniform(8, 15))
                
            except UserPrivacyRestrictedError:
                skipped_count += 1
            except UserAlreadyParticipantError:
                skipped_count += 1
            except PeerFloodError:
                await event.reply("❌ PeerFloodError - Too many requests. Bot stopped. Wait 1 hour.")
                break
            except FloodWaitError as e:
                await event.reply(f"⏳ Flood control: Waiting {e.seconds} seconds...")
                await asyncio.sleep(e.seconds)
                continue
            except Exception as e:
                skipped_count += 1
                print(f"{error} Error adding {user.id}: {e}")
                continue
            
            if (i + 1) % 10 == 0 or (i + 1) == total_members:
                progress = int((i + 1) / total_members * 100)
                await event.reply(f"⏳ Progress: {progress}% ({i+1}/{total_members})\n✅ Added: {added_count} | ❌ Skipped: {skipped_count}")
        
        process_started = False
        return f"🎉 Process completed!\n✅ Successfully added: {added_count} members\n❌ Skipped: {skipped_count} members\n📊 Total processed: {total_members} members"
    
    except Exception as e:
        process_started = False
        return f"❌ An error occurred: {e}"

@client.on(events.NewMessage)
async def handle_message(event):
    global process_started, scraped_grp, target_link
    sender = await event.get_sender()
    message = event.message.message.strip()
    print(f"{lg}[+] Received from {getattr(sender, 'username', 'unknown')}: {message}{n}")
    
    if message.startswith('/start'):
        await event.reply(start_method())
    elif message.startswith('/stop'):
        process_started = False
        await event.reply("🛑 Process stopped by you.")
    elif message.startswith('/reset'):
        scraped_grp = None
        target_link = None
        process_started = False
        await event.reply("🔄 Reset done! Send SOURCE group link again.")
    elif message.startswith('/process'):
        if process_started:
            await event.reply("🔄 The process is already running. Please wait.")
        else:
            response = await process_method(event)
            await event.reply(response)
    elif message.startswith('https://t.me/'):
        if scraped_grp is None:
            await event.reply(source_method(message))
        elif target_link is None:
            await event.reply(target_method(message))
        else:
            await event.reply("✅ Both source and target groups are already set. Use /process to start.")
    else:
        await event.reply("❌ Unknown command. Send /start to begin.")

async def main():
    print(f"{lg}[+] Connecting to Telegram as BOT...{n}")
    await client.start(bot_token=BOT_TOKEN)
    print(f"{lg}[+] Bot is running as Crypto Hub Arb...{n}")
    await client.run_until_disconnected()

if __name__ == '__main__':
    PORT = int(os.environ.get("PORT", 5000))
    Thread(target=lambda: app.run(host='0.0.0.0', port=PORT)).start()
    client.loop.run_until_complete(main())
