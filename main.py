import os

import requests

import threading

import time

from telegram import ChatAction, InputFile, InputMediaDocument

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

# Global variables

send_as_document = True  # Toggle for sending files as documents or media

download_chunk_size = 1024 * 1024  # Chunk size for downloading files (1MB)

upload_chunk_size = 1024 * 64  # Chunk size for uploading files (64KB)

# Handler function for the '/start' command

def start(update, context):

    context.bot.send_message(chat_id=update.effective_chat.id, text="Welcome to the File Downloader Bot!")

# Handler function for the '/toggle' command

def toggle(update, context):

    global send_as_document

    send_as_document = not send_as_document

    context.bot.send_message(chat_id=update.effective_chat.id, text=f"Send as {'Document' if send_as_document else 'Media'}")

# Handler function for the '/help' command

def help_command(update, context):

    help_text = """

    Available commands:

    /start - Start the bot

    /toggle - Toggle between sending files as documents or media

    /help - Display help information

    """

    context.bot.send_message(chat_id=update.effective_chat.id, text=help_text)

# Handler function for downloading and uploading files

def download_and_upload_file(update, context):

    # Check if a direct download link is provided

    if not context.args:

        context.bot.send_message(chat_id=update.effective_chat.id, text="Please provide a direct download link.")

        return

    download_link = context.args[0]

    file_name = context.args[1] if len(context.args) > 1 else ''

    try:

        # Start the download

        context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_DOCUMENT)

        with requests.get(download_link, stream=True) as response:

            response.raise_for_status()

            total_size = int(response.headers.get('Content-Length', 0))

            downloaded_size = 0

            start_time = time.time()

            # Create a unique filename if not provided

            if not file_name:

                file_extension = os.path.splitext(response.url)[1]

                file_name = f"downloaded_file{file_extension}"

            # Save the downloaded file

            file_path = f"./{file_name}"

            with open(file_path, 'wb') as file:

                for chunk in response.iter_content(chunk_size=download_chunk_size):

                    if chunk:

                        file.write(chunk)

                        downloaded_size += len(chunk)

                        # Calculate download speed and update progress

                        elapsed_time = time.time() - start_time

                        download_speed = downloaded_size / elapsed_time

                        progress = (downloaded_size / total_size) * 100

                        context.bot.send_message(chat_id=update.effective_chat.id,

                                                 text=f"Downloading... {progress:.2f}%\nSpeed: {download_speed:.2f} B/s")

        # Start the upload

        context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_DOCUMENT)

        # Create a separate thread for uploading

        upload_thread = threading.Thread(target=upload_file, args=(update.effective_chat.id, file_path))

        upload_thread.start()

    except Exception as e:

        context.bot.send_message(chat_id=update.effective_chat.id, text="Error occurred while downloading or uploading the file.")

        print(e)

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

                context.bot.send_document(chat_id=chat_id, document=InputFile(file, filename=file_path),

                                          progress=uploaded_size, progress_args=(total_size,),

                                          caption="Uploading...")

                uploaded_size += len(chunk)

                # Calculate upload speed and update progress

                elapsed_time = time.time() - start_time

                upload_speed = uploaded_size / elapsed_time

                progress = (uploaded_size / total_size) * 100

                context.bot.send_message(chat_id=chat_id,

                                         text=f"Uploading... {progress:.2f}%\nSpeed: {upload_speed:.2f} B/s")

        # Delete the file after uploading

        os.remove(file_path)

    except Exception as e:

        context.bot.send_message(chat_id=chat_id, text="Error occurred while uploading the file.")

        print(e)

# Handler function for renaming files

def rename_file(update, context):

    # Check if a file is attached

    if not update.message.document:

        context.bot.send_message(chat_id=update.effective_chat.id, text="Please attach a file to rename.")

        return

    new_file_name = context.args[0] if len(context.args) > 0 else ''

    old_file_name = update.message.document.file_name

    try:

        # Start the rename

        context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

        # Download the file

        file_path = context.bot.get_file(update.message.document).download()

        

        # Rename the file

        new_file_path = os.path.join(os.path.dirname(file_path), new_file_name)

        os.rename(file_path, new_file_path)

        # Upload the renamed file

        context.bot.send_document(chat_id=update.effective_chat.id, document=InputFile(new_file_path))

        # Delete the old file

        os.remove(new_file_path)

    except Exception as e:

        context.bot.send_message(chat_id=update.effective_chat.id, text="Error occurred while renaming or uploading the file.")

        print(e)

# Create an instance of the Telegram Updater

updater = Updater(token='YOUR_BOT_TOKEN', use_context=True)

# Get the dispatcher to register handlers

dispatcher = updater.dispatcher

# Register command handlers

dispatcher.add_handler(CommandHandler('start', start))

dispatcher.add_handler(CommandHandler('toggle', toggle))

dispatcher.add_handler(CommandHandler('help', help_command))

# Register message handler for file downloads

dispatcher.add_handler(MessageHandler(Filters.command & Filters.regex(r'^/download'), download_and_upload_file))

# Register message handler for file renaming

dispatcher.add_handler(MessageHandler(Filters.command & Filters.regex(r'^/rename'), rename_file))

# Start the bot

updater.start_polling()

