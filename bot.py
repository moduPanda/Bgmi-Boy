import socket
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext, JobQueue

# Dictionary to track active monitoring jobs for each user
active_monitors = {}

def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Commands:\n"
        "/monitor <IP> <PORT> <MINUTES> - Monitor a port for X minutes\n"
        "/stop - Stop monitoring"
    )

def monitor_port(update: Update, context: CallbackContext):
    if len(context.args) != 3:
        update.message.reply_text("Usage: /monitor <IP> <PORT> <MINUTES>")
        return

    ip, port, minutes = context.args[0], context.args[1], context.args[2]

    # Validate input
    try:
        port = int(port)
        if not (1 <= port <= 65535):
            update.message.reply_text("Port must be between 1-65535.")
            return
    except ValueError:
        update.message.reply_text("Port must be a number.")
        return

    try:
        minutes = int(minutes)
        if minutes < 1:
            update.message.reply_text("Time must be at least 1 minute.")
            return
    except ValueError:
        update.message.reply_text("Time must be a number.")
        return

    # Schedule the monitoring job
    chat_id = update.message.chat_id
    job_name = f"{chat_id}_monitor"
    end_time = datetime.now() + timedelta(minutes=minutes)

    # Remove existing job if it exists
    if chat_id in active_monitors:
        active_monitors[chat_id].schedule_removal()
        del active_monitors[chat_id]

    # Define the job to run every 10 seconds until end_time
    def check_port_job(context: CallbackContext):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(5)
                result = s.connect_ex((ip, port))
                status = "open ✅" if result == 0 else "closed ❌"
                context.bot.send_message(
                    chat_id=chat_id,
                    text=f"Port {port} on {ip} is {status} at {datetime.now().strftime('%H:%M:%S')}"
                )
        except Exception as e:
            context.bot.send_message(chat_id=chat_id, text=f"Error: {str(e)}")

    # Schedule the job
    job = context.job_queue.run_repeating(
        check_port_job,
        interval=10,  # Check every 10 seconds
        first=0,
        last=end_time,
        name=job_name,
    )

    active_monitors[chat_id] = job
    update.message.reply_text(
        f"Monitoring port {port} on {ip} for {minutes} minutes. Use /stop to end early."
    )

def stop_monitor(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    if chat_id in active_monitors:
        active_monitors[chat_id].schedule_removal()
        del active_monitors[chat_id]
        update.message.reply_text("Monitoring stopped.")
    else:
        update.message.reply_text("No active monitor to stop.")

def main():
    updater = Updater("7162766052:AAEd0eVt61bezP2Ld95GK9atteWppolKJGw")
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("monitor", monitor_port))
    dispatcher.add_handler(CommandHandler("stop", stop_monitor))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()