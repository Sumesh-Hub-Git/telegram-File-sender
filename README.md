# Telegram File Sender

A small Windows-friendly desktop app for sending files to a Telegram chat using a Telegram bot. Add files with the file picker or drag them into the app, edit their captions, and reorder the send queue before starting.

## Features

- Send any file type that Telegram's Bot API accepts as a document.
- Send JPG, JPEG, and PNG images as photos when they are no larger than 10 MB; other files and larger images are sent as documents.
- Add multiple files through the picker or by dragging files from your file manager onto the app.
- Reorder the queue by dragging rows, or use the Move Up and Move Down buttons.
- Edit captions, pause or stop sending, and configure the delay between files.

Telegram Bot API upload size limits still apply (currently up to 50 MB for documents). Telegram may also apply additional restrictions to particular media types.

## Requirements

- Python 3.8 or newer
- A Telegram bot token and the destination chat ID
- The dependencies listed in `requirements.txt`

## Setup and run

1. Create a bot with [@BotFather](https://t.me/BotFather) and copy its token.
2. Install dependencies:

   ```powershell
   py -m pip install -r requirements.txt
   ```

3. Start the app:

   ```powershell
   py telegram_file_sender.py
   ```

4. Enter the bot token and chat ID, select or drop files, and press **Start**.

The bot must be able to access the destination chat. Keep the bot token private and do not commit it to source control.
