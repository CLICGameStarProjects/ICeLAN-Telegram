import logging
from typing import List, Union

from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    ContextTypes,
    filters
)

keys = dict(line.split(',') for line in open('.keys', 'r').readlines())

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

PLAYER, PLAYER_REPLY, ANIM, POINTS, POINTS_REPLY = range(5)


class Storage:

    def __init__(self, path='./storage.csv'):
        self.path = path
        with open(path, 'r') as src:
            # TODO read as nested dicts
            self.storage = src

    def save(self):
        with open(self.path, 'w') as dest:
            # TODO write as nested dicts
            dest.write(self.storage)

    def write(self, anim, player, points):
        try:
            self.storage[anim][player] = points
        except:
            logger.error('Invalid keys:', anim, player)

    def read(self, anim=None, player=None):
        if anim is None:
            if player is None:
                return list(self.storage.keys())
            else:
                return [anim for anim in self.storage if player in self.storage[anim]]
        else:
            if player is None:
                return list(self.storage[anim].values())
            else:
                return self.storage[anim][player]

    @staticmethod
    def dummy():
        _storage = Storage()
        _storage.storage = {
            str(p): { str(a): 0 for a in range(10, 20) }
            for p in range(10)
        }
        return _storage


storage = Storage.dummy()


def build_menu(
    buttons: List[InlineKeyboardButton],
    n_cols: int,
    header_buttons: Union[InlineKeyboardButton, List[InlineKeyboardButton]]=None,
    footer_buttons: Union[InlineKeyboardButton, List[InlineKeyboardButton]]=None
) -> List[List[InlineKeyboardButton]]:
    menu = [buttons[i:i + n_cols] for i in range(0, len(buttons), n_cols)]
    if header_buttons:
        menu.insert(0, header_buttons if isinstance(header_buttons, list) else [header_buttons])
    if footer_buttons:
        menu.append(footer_buttons if isinstance(footer_buttons, list) else [footer_buttons])
    return menu


async def help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Please start the bot and enter animation points with /start')


async def enter_points(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        player = context.user_data['player']
        animation = context.user_data['animation']
    except:
        update.message.reply_text('Failed to find player and animation')
        return ConversationHandler.END
    
    update.message.reply_text(f'Please enter the points received by {player} for animation {animation}:')

    return POINTS_REPLY


async def pick_player(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text('Please enter the player\'s username:', quote=False)

    return PLAYER_REPLY


async def pick_anim(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    keyboard = build_menu([
        InlineKeyboardButton(animation, callback_data=animation)
        for animation in storage.read()
    ], 2)
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text('Please pick your animation of choice', reply_markup=reply_markup, quote=False)

    return POINTS


async def pick_player_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    player = update.message.text
    context.user_data.update({'player': player})

    return ANIM


async def pick_anim_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    animation = query.answer()
    context.user_data.update({'animation': animation})

    return POINTS


def enter_points_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reply = update.message.text
    try:
        points = int(reply)
        storage.write(**context.user_data, points=points)
    except:
        logger.error('Points must be integers')
    finally:
        return ConversationHandler.END


async def list_anims(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    anims = storage.read()
    anims = '\n'.join(', '.join(line for line in zip(anims[::2], anims[1::2])))
    await update.message.reply_text(anims)


async def list_points(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) >= 2:
        players_points = storage.read(context.args[0])
        message = '\n'.join(f'{player} - {anim}' for player, anim in players_points.items())
    else:
        message = 'Please provide an animation ID and a player ID'
    await update.message.reply_text(message)


async def list_players(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) >= 1:
        message = '\n'.join(storage.read(context.args[0]))
    else:
        message = 'Please provide an animation ID'
    await update.message.reply_text(message)


def main() -> None:
    application = Application.builder().token(keys['token']).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', pick_player)],
        states={
            PLAYER_REPLY: [MessageHandler(filters=filters.TEXT, callback=pick_player_reply)],
            ANIM: [MessageHandler(filters=filters.TEXT, callback=pick_anim)],
            POINTS: [MessageHandler(filters=filters.TEXT, callback=enter_points)],
            POINTS_REPLY: [MessageHandler(filters=filters.TEXT, callback=enter_points_reply)]
        },
        fallbacks=[]
    )
    application.add_handler(conv_handler)

    application.run_polling()


if __name__ == "__main__":
    main()
