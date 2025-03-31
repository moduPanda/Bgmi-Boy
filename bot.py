import os
import socket
import requests
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    CallbackContext,
    JobQueue
)

# Dictionary to track active monitoring jobs
active_monitors = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message with instructions"""
    await update.message.reply_text(
        "🔍 Port Monitor Bot\n\n"
        "Commands:\n"
        "/monitor <IP> <PORT> <MINUTES> - Check port status\n"
        "/stop - Cancel monitoring\n\n"
        "Note: Maximum monitoring duration is 60 minutes"
    )

async def monitor_port(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start monitoring a specific port"""
    if len(context.args) != 3:
        await update.message.reply_text("Usage: /monitor <IP> <PORT> <MINUTES>")
        return

    ip, port, minutes = context.args[0], context.args[1], context.args[2]

    # Validate port input
    try:
        port = int(port)
        if not (1 <= port <= 65535):
            await update.message.reply_text("Port must be between 1-65535.")
            return
    except ValueError:
        await update.message.reply_text("Port must be a number.")
        return

    # Validate time input
    try:
        minutes = int(minutes)
        if minutes < 1:
            await update.message.reply_text("Time must be at least 1 minute.")
            return
        if minutes > 60:  # Limit to 1 hour max
            await update.message.reply_text("Maximum monitoring time is 60 minutes.")
            return
    except ValueError:
        await update.message.reply_text("Time must be a number.")
        return

    # Schedule monitoring
    chat_id = update.message.chat_id
    end_time = datetime.now() + timedelta(minutes=minutes)

    # Remove existing job if exists
    if chat_id in active_monitors:
        active_monitors[chat_id].schedule_removal()
        del active_monitors[chat_id]

    async def check_port_job(context: ContextTypes.DEFAULT_TYPE):
        """Job that runs periodically to check port status"""
        try:
            # Method 1: Try direct socket connection
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(3)
                    result = s.connect_ex((ip, port))
                    if result == 0:
                        status = "open ✅"
                    else:
                        status = f"closed ❌ (error {result})"
            except:
                # Method 2: Fallback to external service if socket fails
                try:
                    response = requests.get(
                        f"https://api.hackertarget.com/nmap/?q={ip}:{port}",
                        timeout=5
                    )
                    if "open" in response.text.lower():
                        status = "open ✅ (via proxy)"
                    else:
                        status = "closed ❌ (via proxy)"
                except:
                    status = "status unknown (scan failed)"

            await context.bot.send_message(
                chat_id=chat_id,
                text=f"Port {port} on {ip}:\n"
                     f"Status: {status}\n"
                     f"Time: {datetime.now().strftime('%H:%M:%S')}"
            )
        except Exception as e:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"⚠️ Error checking port: {str(e)}"
            )

    job = context.job_queue.run_repeating(
        check_port_job,
        interval=30,  # Check every 30 seconds to avoid rate limits
        first=0,
        last=end_time.timestamp(),
        chat_id=chat_id,
        name=f"monitor_{chat_id}"
    )

    active_monitors[chat_id] = job
    await update.message.reply_text(
        f"🔍 Monitoring port {port} on {ip} for {minutes} minutes\n"
        f"Next check in 30 seconds\n"
        "Use /stop to cancel early."
    )

async def stop_monitor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stop active monitoring"""
    chat_id = update.message.chat_id
    if chat_id in active_monitors:
        active_monitors[chat_id].schedule_removal()
        del active_monitors[chat_id]
        await update.message.reply_text("🛑 Monitoring stopped.")
    else:
        await update.message.reply_text("⚠️ No active monitoring to stop.")

def main():
    # Get token from environment variable
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise ValueError("No BOT_TOKEN environment variable set")

    # Create application
    application = Application.builder().token(token).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("monitor", monitor_port))
    application.add_handler(CommandHandler("stop", stop_monitor))

    # Start the bot
    print("Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()
