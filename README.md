# ICeLAN-Telegram

ICeLAN participants and admins can interact with this bot to monitor animation scores and registrations (via _read_ commands).

ICeLAN admins have access to more commands, knwon as _write_ commands: add a user to an animation, create an animation, enter scores, remove a player from an animation, etc.

## Dependencies

`pip install python-telegram-bot==20.0a6`

## Config files

The `.keys` file must exist and contain the following lines:
- `token,<TOKEN>` where `<TOKEN>` is your Telegram bot token;
- `code,<CODE>` where `<CODE>` is the event's secret code for NFC cards.

The `.admins` file is optional and contains the list of Telegram user IDs (one per line) that are considered as administrators.
If the file exists and is non-empty, then _write_ commands will be restricted to the specified admin users.
Otherwise, _write_ commands are publicly available.

The `.code` file contains the event's edition secret code for NFC cards.

## Commands

### _Read_ commands

- `/anims`: list all existing animations
- `/anims <player>`: list all animations that `player` joined
- `/players <anim>`: list all players that joined `anim`
- `/points <anim>`: list all players in `anim` with their scores
- `/points <anim> <player>`: return the score of `player` in `anim`

### _Write_ commands

These commands are restricted to the admins specified in `.admins`. If `.admins` is empty, these commands are not restricted.

- `/start`: enter the points for a given player and a given animation
- `/register`: add a player to the database and/or enroll them in an animation
- `/remove`: remove a player from the database or unenroll a player from an animation