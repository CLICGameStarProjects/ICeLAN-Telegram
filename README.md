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
- `/points <player> <anim>`: return points obtained by `player` in `anim`
- `/points <player>`: return all anims joined by `player` along with the points they obtained
- `/status <anim>`: list players enrolled in `anim` along with their points

### _Write_ commands

These commands are restricted to the admins specified in `.admins`. If `.admins` is empty, these commands are not restricted.

- `/start`: enter the points for a given player and a given animation
- `/register`: add a player to the database and/or enroll them in an animation
- `/remove`: remove a player from the database or unenroll a player from an animation
