import os
import asyncio
import socket
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ( 
    Application, 
    CommandHandler, 
    ContextTypes 
)

# Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(id) for id in os.getenv("ADMIN_IDS", "").split(",") if id.isdigit()]
MAX_CONNECTIONS = 50
MAX_TEST_SECONDS = 300

def validate_port(port: int) -> bool:
    return 1 <= port <= 65535

async def test_port(ip: str, port: int, duration: int):
    results = {
        'success': 0,
        'timeouts': 0,
        'refused': 0,
        'other_errors': 0,
        'response_times': []
    }
    
    end_time = datetime.now() + timedelta(seconds=duration)
    
    async def run_test():
        while datetime.now() < end_time:
            try:
                start = datetime.now()
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(2.0)
                    s.connect((ip, port))
                    results['success'] += 1
                    results['response_times'].append((datetime.now() - start).total_seconds())
            except socket.timeout:
                results['timeouts'] += 1
            except ConnectionRefusedError:
                results['refused'] += 1
            except Exception:
                results['other_errors'] += 1
    
    tasks = [asyncio.create_task(run_test()) for _ in range(min(MAX_CONNECTIONS, duration // 2))]
    await asyncio.gather(*tasks)
    return results

async def start_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Admins only")
        return
    
    try:
        ip, port, duration = context.args[0], int(context.args[1]), min(int(context.args[2]), MAX_TEST_SECONDS) if len(context.args) > 2 else 10
        if not validate_port(port):
            raise ValueError("Invalid port range")
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /test <IP> <PORT> <SECONDS> (Max: 5 min)")
        return
    
    msg = await update.message.reply_text(f"🔌 Testing {ip}:{port} for {duration} seconds...")
    results = await test_port(ip, port, duration)
    
    avg_time = sum(results['response_times']) / len(results['response_times']) if results['response_times'] else 0
    total_attempts = results['success'] + results['timeouts'] + results['refused'] + results['other_errors']
    success_rate = (results['success'] / total_attempts) * 100 if total_attempts else 0
    
    await msg.edit_text(
        f"📊 Port Test Results for {ip}:{port}\n"
        f"⏱ Duration: {duration}s | Concurrent: {MAX_CONNECTIONS}\n"
        f"✅ Successful: {results['success']}\n"
        f"⌛ Timeouts: {results['timeouts']}\n"
        f"🚫 Refused: {results['refused']}\n"
        f"❌ Other Errors: {results['other_errors']}\n"
        f"📈 Success Rate: {success_rate:.1f}%\n"
        f"⏱ Avg Response: {avg_time:.3f}s"
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📡 Port Stress Tester Bot\n\n"
        "Commands:\n"
        "/test <IP> <PORT> <SECONDS>\n"
        "Example: /test 192.168.1.1 80 30\n\n"
        f"⚠️ Max duration: {MAX_TEST_SECONDS // 60} minutes"
    )

def main():
    if not BOT_TOKEN:
        print("❌ Missing BOT_TOKEN in environment")
        return
    
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("test", start_test))
    
    print("🟢 Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Error: {e}")
