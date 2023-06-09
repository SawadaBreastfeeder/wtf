import os

import requests

import time

import threading

from telegram import ChatAction, InputFile

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

# Global variables

download_chunk_size = 1024 * 1024  # 1MB

upload_chunk_size = 1024 * 16  # 16KB

send_as_document = True

# Handler function for the /start command

def start(update, context):

    context.bot.send_message(chat_id=update.effective_chat.id,

                             text="Welcome! This bot can download files from direct download links and upload them to Telegram with a rename feature.")

# Handler function for the /toggle command

def toggle(update, context):

    global send_as_document

    send_as_document = not send_as_document

    mode = "Document" if send_as_document else "Media"

    context.bot.send_message(chat_id=update.effective_chat.id, text=f"Send files as: {mode}")

# Handler function for the /help command

def help_command(update, context):

    help_text = "Commands:\n" \

                "/start - Start the bot\n" \

                "/toggle - Toggle between sending files as Document or Media\n" \

                "/help - Show help information\n" \

                "/download [direct_download_link] - Download and upload a file\n" \

                "/rename [new_file_name] - Rename a file"

    context.bot.send_message(chat_id=update.effective_chat.id, text=help_text)

# Function to download the file from a direct download link

def download_file(download_link):

    try:

        response = requests.get(download_link, stream=True)

        response.raise_for_status()

        total_size = int(response.headers.get('content-length', 0))

        downloaded_size = 0

        start_time = time.time()

        with open("downloaded_file", 'wb') as file:

            for chunk in response.iter_content(chunk_size=download_chunk_size):

                if chunk:

                    file.write(chunk)

                    downloaded_size += len(chunk)

                    # Calculate download speed and update progress

                    elapsed_time = time.time() - start_time

                    download_speed = downloaded_size / elapsed_time

                    progress = (downloaded_size / total_size) * 100

                    # Send progress message

                    progress_message = f"Downloading... {progress:.2f}%\nSpeed: {download_speed:.2f} B/s"

                    context.bot.send_message(chat_id=update.effective_chat.id, text=progress_message)

        return "downloaded_file"

    except Exception as e:

        print(e)

        return None

# Function to upload the file to Telegram

def upload_file(chat_id, file_path):

    try:

        with open(file_path, 'rb') as file:

            total_size = os.path.getsize(file_path)

            uploaded_size = 0

            start_time = time.time()

            while True:

                chunk = file.read(upload_chunk_size)

                if not chunk:

                    break

                if send_as_document:

                    context.bot.send_document(chat_id=chat_id, document=InputFile(file, filename=file_path),

                                              progress=uploaded_size, progress_args=(total_size,),

                                              caption="Uploading...")

                else:

                    context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.UPLOAD_DOCUMENT)

                    context.bot.send_video(chat_id=chat_id, video=InputFile(file, filename=file_path),

                                           supports_streaming=False)

                uploaded_size += len(chunk)

                # Calculate upload speed and update progress

                elapsed_time = time.time() - start_time

                upload_speed = uploaded_size / elapsed_time

                progress = (uploaded_size / total_size) * 100

                # Send progress message

                progress_message = f"Uploading... {progress:.2f}%\nSpeed: {upload_speed:.2f} B/s"

                context.bot.send_message(chat_id=update.effective_chat.id, text=progress_message)

    except Exception as e:

        print(e)

# Handler function for the /download command

def download_command(update, context):

    download_link = context.args[0]

    if download_link.startswith("http"):

        context.bot.send_message(chat_id=update.effective_chat.id, text="Downloading file...")

        file_path = download_file(download_link)

        if file_path:

            context.bot.send_message(chat_id=update.effective_chat.id, text="Uploading file...")

            upload_thread = threading.Thread(target=upload_file, args=(update.effective_chat.id, file_path))

            upload_thread.start()

        else:

            context.bot.send_message(chat_id=update.effective_chat.id, text="Failed to download the file.")

    else:

        context.bot.send_message(chat_id=update.effective_chat.id, text="Please provide a direct download link.")

# Handler function for the /rename command

def rename_command(update, context):

    new_file_name = context.args[0]

    file_id = update.message.document.file_id

    new_file_name += os.path.splitext(update.message.document.file_name)[1]

    # Get the file from Telegram by file_id

    file_info = context.bot.get_file(file_id)

    file_path = file_info.file_path

    # Download the file from Telegram

    downloaded_file = context.bot.download_file(file_path)

    with open(downloaded_file, 'wb') as file:

        file.write(downloaded_file)

    # Rename the file

    renamed_file_path = os.path.join(os.getcwd(), new_file_name)

    os.rename(downloaded_file, renamed_file_path)

    # Upload the renamed file to Telegram

    context.bot.send_document(chat_id=update.effective_chat.id, document=open(renamed_file_path, 'rb'))

    # Delete the temporary files

    os.remove(downloaded_file)

    os.remove(renamed_file_path)

# Handler function for handling unknown commands

def unknown_command(update, context):

    context.bot.send_message(chat_id=update.effective_chat.id, text="Sorry, I didn't understand that command.")

def main():

    # Load environment variables from .env file

    dotenv_path = os.path.join(os.path.dirname(__file__), '.env')

    if os.path.exists(dotenv_path):

        from dotenv import load_dotenv

        load_dotenv(dotenv_path)

    # Set up the Telegram bot

    updater = Updater(token=os.environ.get("TELEGRAM_BOT_TOKEN"), use_context=True)

    dispatcher = updater.dispatcher

    # Register command handlers

    dispatcher.add_handler(CommandHandler("start", start))

    dispatcher.add_handler(CommandHandler("toggle", toggle))

    dispatcher.add_handler(CommandHandler("help", help_command))

    dispatcher.add_handler(CommandHandler("download", download_command))

    dispatcher.add_handler(CommandHandler("rename", rename_command))

    # Register unknown command handler

    dispatcher.add_handler(MessageHandler(Filters.command, unknown_command))

    # Start the bot

    updater.start_polling()

    updater.idle()

if __name__ == '__main__':

    main()

