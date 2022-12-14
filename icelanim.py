import logging
import os
import base64
from typing import List
from operator import itemgetter

from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    ContextTypes,
    filters
)

keys = dict(line.split(",") for line in open(".keys", "r").read().splitlines())
if os.path.exists(".admins"):
    admins = set(int(line) for line in open(".admins", "r").read().splitlines())
else:
    admins = set()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# enter points for a given player and anim
PLAYER, ANIM, CREATE_ANIM, ADD_TO_ANIM, POINTS, SAVE = range(6)
# add a new player or register a player to an anim
REGISTER_PLAYER, ADD_ANIM, ADD_ANIM_REPLY, REGISTER_ANIM = range(4)
# wipe a player's record, or remove them from a single anim
REMOVE, REMOVE_PROCEED, REMOVE_REPLY, REMOVE_PLAYER, REMOVE_ANIM_1, REMOVE_ANIM_2 = range(6)

 
def sanitize_player(player: str) -> str:
    return player.replace(",", "").replace(" ", "")


def sanitize_anim(anim: str) -> str:
    return anim.replace(",", "").strip()


class Storage:

    def __init__(self, path: str="./storage.csv"):
        self.path = path
        with open(path, "r") as src:
            self.storage = {}
            self.anims = set()
            self.players = set()
            for line in src.read().splitlines():
                data = line.split(",")
                if len(data) >= 1:
                    player = data[0]
                    if player not in self.storage:
                        self.players.add(player)
                        self.storage[player] = {}
                if len(data) >= 2:
                    anim = data[1]
                    if anim not in self.anims:
                        self.anims.add(anim)
                    if anim not in self.storage[player]:
                        self.storage[player] = {anim: 0}
                if len(data) >= 3:
                    points = data[2]
                    self.storage[player][anim] = points


    def save(self) -> None:
        with open(self.path, "w") as dest:
            for player, anims_points in self.storage.items():
                data = list(anims_points.items())
                if len(data) == 0:
                    dest.write(player + "\n")
                else:
                    for anim, points in data:
                        dest.write(",".join((player, anim, str(points))) + "\n")


    def add(self, player: str, anim: str=None, points: int=None) -> None:
        if (
            not isinstance(player, str) or
            anim != None and not isinstance(anim, str)
        ):
            raise TypeError("Expected strings")

        if player not in self.players:
            self.players.add(player)
            self.storage[player] = {}
        if anim != None:
            if anim not in self.storage[player]:
                if anim not in self.anims:
                    self.anims.add(anim)
                self.storage[player][anim] = points or 0
            elif points != None:
                self.storage[player][anim] += points


    def remove(self, player: str, anim: str=None) -> None:
        if (
            not isinstance(player, str) or
            anim != None and not isinstance(anim, str)
        ):
            raise TypeError("Expected strings")
        
        if player in self.players:
            if anim == None:
                self.players.remove(player)
                self.storage.pop(player)
            else:
                self.storage[player].pop(anim)
                count = len(set(p for p in self.players if anim in self.storage[p]))
                if count == 0:
                    self.anims.remove(anim)


    def read(self, player: str=None, anim: str=None):
        if (
            anim != None and not isinstance(anim, str) or
            player != None and not isinstance(player, str)
        ):
            raise TypeError("Expected strings")

        if (
            anim != None and anim not in self.anims or
            player != None and player not in self.players
        ):
            raise TypeError("Expected strings")

        if anim != None:
            if player != None:
                return self.storage[player][anim]
            else:
                return {p: self.storage[p][anim] for p in self.storage if anim in self.storage[p]}
        else:
            if player != None:
                return self.storage[player]
            else:
                raise Exception("At least one arg must be specified")


storage = Storage()


def build_keyboard(buttons: List[str], n_cols: int) -> List[List[str]]:
    return [buttons[i:i + n_cols] for i in range(0, len(buttons), n_cols)]


async def help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = """
/players
    Renvoie la liste de tous les joueurs

/anims
    Renvoie la liste de toutes les animations

/info <player> <animation | None>
    - Renvoie la liste des points obtenus par un joueur au sein d'une animation, ou
    - Renvoie la liste des points obtenus par un joueur au sein de toutes les animations

/status <animation>
    Renvoie la liste des points obtenus par tous les joueurs inscrits ?? l'animation"""
    if update.message.from_user.id in admins:
        message += """

=== COMMANDES R??SERV??ES AUX ADMINS ===

/start:
    Entrer des points pour un joueur et une animation donn??s

/register:
    - Ajoute un joueur ?? la base de donn??e, ou
    - Inscrit un joueur ?? une animation

/remove
    - Supprime un joueur de la base de donn??e, ou
    - D??sinscrit un joueur d'une animation
    """
    await update.message.reply_text(message)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.from_user.id not in admins:
        return ConversationHandler.END
    if len(context.args) == 1:
        player, code = base64.b64decode(context.args[0]).decode().split()
        if code != keys["code"]:
            await update.message.reply_text("La carte contient un code erron??.")
            return ConversationHandler.END

        player = sanitize_player(player)

        await update.message.reply_text(f"La carte appartient ?? {player}.")

        if player not in storage.players:
            storage.add(player)
            storage.save()
            await update.message.reply_text(
                f"{player} n'existait pas dans la base de donn??e, il vient d'y ??tre ajout??."
            )

        context.user_data["player"] = player

        player_anims = list(storage.read(player=player).keys())

        if len(player_anims) > 0:

            keyboard = build_keyboard(player_anims, 2)
            reply_markup = ReplyKeyboardMarkup(keyboard)

            await update.message.reply_text(
                f"{player} est inscrit aux ANIMATIONS suivantes.\n\n> Tu peux choisir une de ces ANIMATIONS ou entrer le nom d'une autre ANIMATION et choisir d'y inscrire le joueur.",
                reply_markup=reply_markup
            )

            context.user_data["existing_anim"] = True
            return POINTS

        else:

            keyboard = build_keyboard(["Oui", "Non"], 2)

            await update.message.reply_text(
                f"??? {player} n'est inscrit ?? aucune ANIMATION ???\n\n> Veux-tu l'inscrire ?? une ANIMATION ? Si l'ANIMATION rentr??e n'existe pas encore, elle sera cr????e ?? la vol??e.",
                reply_markup=ReplyKeyboardMarkup(keyboard)
            )

            context.user_data["player"] = player

            return CREATE_ANIM

    else:
        await update.message.reply_text("> Entrer le nom du JOUEUR :")
        return ANIM


async def pick_anim(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    player = sanitize_player(update.message.text)
    if player in storage.players:
        context.user_data["player"] = player

        player_anims = list(storage.read(player=player).keys())        

        if len(list(storage.read(player=player).keys())) > 0:

            keyboard = build_keyboard(player_anims, 2)
            reply_markup = ReplyKeyboardMarkup(keyboard)

            context.user_data["existing_anim"] = True

            await update.message.reply_text(
                f"{player} est inscrit aux ANIMATIONS suivantes.\n\n> Tu peux choisir une de ces animations ou entrer le nom d'une autre animation et choisir d'y inscrire le joueur.",
                reply_markup=reply_markup
            )

            return POINTS
        
        else:

            keyboard = build_keyboard(["Oui", "Non"], 2)

            await update.message.reply_text(
                f"??? {player} n'est inscrit ?? aucune ANIMATION ! ???\n\n> Veux-tu l'inscrire ?? une animation ? Si l'animation rentr??e n'existe pas encore, elle sera cr????e ?? la vol??e.",
                reply_markup=ReplyKeyboardMarkup(keyboard)
            )

            return CREATE_ANIM

    else:
        await update.message.reply_text(
            f"??? {player} n'existe pas encore dans la base de donn??e ! ???\n\nTu peux l'ajouter manuellement avec la commande /register."
        )

        return ConversationHandler.END


async def create_anim(update, context):
    if update.message.text.lower() == "oui":
        player = context.user_data["player"]
        await update.message.reply_text(f"> Entrer le nom de l'ANIMATION ?? laquelle inscrire {player} :")
        return POINTS
    else:
        await update.message.reply_text(f"???? {player} n'a ??t?? inscrit ?? aucune ANIMATION ????")
        return ConversationHandler.END


async def add_to_anim(update, context):
    if update.message.text.lower() == "oui":
        player = context.user_data["player"]
        anim = context.user_data["anim"]
        await update.message.reply_text(f"???? {player} a ??t?? inscrit ?? l'ANIMATION {anim} ????", reply_markup=ReplyKeyboardRemove())
        await update.message.reply_text(f"> Entrer les points re??us par {player} ?? l'ANIMATION {anim} :")
        return SAVE
    else:
        await update.message.reply_text(f"{player} n'a pas ??t?? inscrit ?? l'animation. Rien n'a ??t?? fait.")
        return ConversationHandler.END
        

async def enter_points(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    player = context.user_data["player"]
    anim = sanitize_anim(update.message.text)
    context.user_data["anim"] = anim

    if anim not in storage.read(player):
        if context.user_data.get("existing_anim", False):
            context.user_data["existing_anim"] = False
            keyboard = build_keyboard(["Oui", "Non"], 2)

            await update.message.reply_text(
                f"??? {player} n'est pas inscrit ?? l'ANIMATION {anim} ???\n\n> Veux-tu l'inscrire ?? l'ANIMATION ?",
                reply_markup=ReplyKeyboardMarkup(keyboard)
            )

            return ADD_TO_ANIM
        else:
            storage.add(player, anim)
            storage.save()

            await update.message.reply_text(
                f"???? {player} a ??t?? ajout?? ?? l'ANIMATION {anim} ????",
                reply_markup=ReplyKeyboardMarkup(keyboard)
            )
    
    await update.message.reply_text(
        f"Entrer les points re??us par {player} ?? de l'ANIMATION {anim} :",
        reply_markup=ReplyKeyboardRemove()
    )

    return SAVE


async def save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        points = int(update.message.text.strip())
    except:
        await update.message.reply_text("??? Les points doivent ??tre des nombres ???\n\n> Re-rentrer les points :")
        return SAVE
    player = context.user_data["player"]
    anim = context.user_data["anim"]
    storage.add(player, anim, points)
    storage.save()
    total_points = storage.read(player, anim)
    await update.message.reply_text(
        f"???? Les r??sultats ont ??t?? sauv??s avec succ??s ????\n\n[{anim}] {player} - {total_points}pts"
    )
    return ConversationHandler.END


async def list_players(update, context):
    players = list(storage.players)
    if len(players):
        message = "???? Liste des JOUEURS ????\n\n"
        message += "\n".join(",  ".join(line) for line in zip(players[::2], players[1::2]))
        if len(players) % 2 == 1:
            message += f"\n{players[-1]}"
    else:
        message = "??? Aucun JOUEUR n'a encore ??t?? enregistr??e ! ???"
    await update.message.reply_text(message)


async def list_anims(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    anims = list(set(a for a_p in storage.storage.values() for a in a_p.keys()))
    if len(anims):
        message = "???? Liste des ANIMATIONS ????\n\n"
        message += "\n".join(",  ".join(line) for line in zip(anims[::2], anims[1::2]))
        if len(anims) % 2 == 1:
            if len(anims) > 1:
                message += "\n"
            message += anims[0]
    else:
        message = "??? Aucune ANIMATION n'a encore ??t?? enregistr??e ???"
    await update.message.reply_text(message)


async def status(update, context):
    if len(context.args) > 0:
        anim = sanitize_anim(' '.join(context.args))
        if anim not in storage.anims:
            message = "??? L'ANIMATION n'a pas encore ??t?? enregistr??e ???"
        else:
            players_points = list(storage.read(anim=anim).items())
            players_points.sort(key=itemgetter(1), reverse=True)
            ranking = [f"{idx + 1}. {player} - {points}pts" for idx, (player, points) in enumerate(players_points)]
            medals = ["????",  "????", "????"]
            fancy_ranking = [f"{rank} {medal}" for medal, rank in zip(medals, ranking[:3])] + ranking[3:]
            message = f"???? [{anim}] Classement ????\n\n"
            message += "\n".join(fancy_ranking)
    else:
        message = "??? Il faut sp??cifier une ANIMATION ???"
    await update.message.reply_text(message)


async def info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) > 0:
        player = sanitize_player(context.args[0])
        if player not in storage.players:
            message = f"??? {player} n'existe pas encore dans la base de donn??e ???"
        else:
            if len(context.args) > 1:
                anim = sanitize_anim(' '.join(context.args[1:]))
                if anim not in storage.anims:
                    message = f"??? L'ANIMATION {anim} n'existe pas ???"
                elif anim not in storage.read(player):
                    message = f"??? {player} n'est pas inscrit ?? l'ANIMATION {anim} ???"
                else:
                    points = storage.read(player, anim)
                    message = f"[{anim}] {player} - {points}pts"
            else:
                anims_points = list(storage.read(player).items())
                if len(anims_points):
                    message = f"???? ANIMATIONS et POINTS de {player} ????\n\n"
                    message += "\n".join(f"[{a}] {points}pts" for a, points in anims_points)
                else:
                    message = f"??? {player} n'est inscrit ?? aucune ANIMATION ???"
    else:
        message = "??? Il faut sp??cifier un JOUEUR et (??ventuellement) une ANIMATION ???"
    await update.message.reply_text(message)


async def register_player(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message.from_user.id not in admins:
        return ConversationHandler.END
    await update.message.reply_text("Entrer le nom du JOUEUR :")

    return ADD_ANIM


async def add_anim(update, context):
    player = sanitize_player(update.message.text)
    context.user_data["register"] = player

    keyboard = build_keyboard(["Oui", "Non"], 2)
    if player not in storage.players:
        storage.add(player)
        storage.save()
        await update.message.reply_text(
            f"???? Le joueur {player} a ??t?? ajout?? ?? la base de donn??e avec succ??s ????\n\n> Veux-tu l'inscrire ?? une animation par la m??me occasion ? L'animation n'a pas besoin de d??j?? exister.",
            reply_markup=ReplyKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_text(
            f"???? Le joueur {player} existe d??j?? ????\n\n> Veux-tu l'inscrire ?? une animation ? L'animation n'a pas besoin d'exister.",
            reply_markup=ReplyKeyboardMarkup(keyboard)
        )

    return ADD_ANIM_REPLY


async def add_anim_reply(update, context):
    if update.message.text.lower() == "oui":
        await update.message.reply_text(
            "> Entrer le nom de l'ANIMATION :",
            reply_markup=ReplyKeyboardRemove()
        )
        return REGISTER_ANIM
    else:
        await update.message.reply_text(
            f"???? Le JOUEUR n'a ??t?? ajout?? ?? aucune ANIMATION. Il te faudra rappeler cette commande afin de pouvoir l'inscrire ?? une ANIMATION ????",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END


async def register_anim(update, context):
    anim = sanitize_anim(update.message.text)
    player = context.user_data["register"]
    storage.add(player, anim)
    storage.save()

    await update.message.reply_text(
        f"???? {player} a ??t?? ajout?? ?? l'ANIMATION {anim} avec succ??s ! ????\n\nTu peux maintenant lui ajouter des points avec la commande /start.",
        reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END


async def remove(update, context):
    if update.message.from_user.id not in admins:
        return ConversationHandler.END
    keyboard = build_keyboard(["Oui", "Non"], 2)
    await update.message.reply_text(
        """
???? ATTENTION ????
Cette commande est dangereuse ! Continue seulement si tu sais ce que tu fais. Contacter Hugo (@billjobs42) ou Stache (@Stache) en cas de besoin.

> Continuer malgr?? tout?
        """,
        reply_markup=ReplyKeyboardMarkup(keyboard)
    )

    return REMOVE_PROCEED

async def remove_proceed(update, context):
    if update.message.text.lower() == "oui":
        keyboard = build_keyboard(["Joueur", "Inscription"], 2)
        await update.message.reply_text(
            "> Qu'est-ce que tu voudrais supprimer ?",
            reply_markup=ReplyKeyboardMarkup(keyboard)
        )
        return REMOVE_REPLY

    else:
        await update.message.reply_text(
            "???? Annulation de la suppresion ????",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END


async def remove_reply(update, context):
    reply = update.message.text.lower()
    
    if reply == "joueur":
        await update.message.reply_text(
            """
???? ATTENTION ????
Tu t'appr??tes ?? supprimer un JOUEUR de la base de donn??e. ??a aura pour effet de supprimer tous ses scores ?? toutes ses ANIMATIONS.

> Quel JOUEUR souhaites-tu supprimer ?
            """,
            reply_markup=ReplyKeyboardRemove()
        )
        return REMOVE_PLAYER
    elif reply == "inscription":
        await update.message.reply_text(
            """
???? ATTENTION ????
Tu t'appr??tes ?? d??sinscrire un JOUEUR d'une ANIMATION. ??a aura pour effet de supprimer ses points obtenus ?? l'ANIMATION.
            
> Quel JOUEUR souhaites-tu d??sinscrire ?
            """,
            reply_markup=ReplyKeyboardRemove()
        )
        return REMOVE_ANIM_1
    else:
        await update.message.reply_text("??? R??ponse invalide ???", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END


async def remove_anim_reply_player(update, context):
    player = sanitize_player(update.message.text)

    if player not in storage.players:
        await update.message.reply_text(
            f"??? {player} n'existe pas encore dans la base de donn??e. Rien n'a ??t?? fait ???"
        )
        return ConversationHandler.END

    context.user_data['remove'] = player

    keyboard = build_keyboard(list(storage.read(player=player).keys()))
    await update.message.reply_text(
        f"> De quelle ANIMATION faut-il d??sincrire {player} ?",
        reply_markup=ReplyKeyboardMarkup(keyboard)
    )

    return REMOVE_ANIM_2

async def remove_anim_reply_anim(update, context):
    player = context.user_data['remove']
    anim = sanitize_anim(update.message.text)

    if anim not in storage.anims:
        await update.message.reply_text(
            f"??? {player} n'est pas encore inscrit ?? l'ANIMATION {anim}. Rien a ??t?? fait ???",
            reply_markup=ReplyKeyboardRemove()
        )
    else:
        storage.remove(player, anim)
        await update.message.reply_text(
            f"???? {player} a ??t?? d??sinscrit de l'ANIMATION {anim} avec succ??s ????",
            reply_markup=ReplyKeyboardRemove()
        )

    return ConversationHandler.END


async def remove_player_reply(update, context):
    player = sanitize_player(update.message.text)

    if player not in storage.players:
        await update.message.reply_text(
            f"??? {player} n'existe pas encore dans la base de donn??e. Rien n'a ??t?? fait ???"
        )
    else:
        storage.remove(player)
        storage.save()
        await update.message.reply_text(
            f"???? {player} a ??t?? supprim?? de la base de donn??e avec succ??s ????"
        )

    return ConversationHandler.END


async def cancel(update, context):
    await update.message.reply_text(
        "???? Tu as entr?? une commande alors qu'une autre ??tait en cours. La commande pr??c??dente a donc ??t?? interrompue ????",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


async def debug(update, context):
    user = update.message.from_user
    user_id = user.id
    name = user.first_name or "" + " " + user.last_name or ""
    username = user.username
    logger.info(f"\nCHAT ID: {user_id}\nNAME: {name}\nUSERNAME: @{username}")
    await update.message.reply_text("success", reply_markup=ReplyKeyboardRemove())


def main() -> None:
    application = Application.builder().token(keys["token"]).build()

    application.add_handler(CommandHandler("help", help), 1)

    conv_filter = filters.TEXT & (~filters.COMMAND)

    points_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ANIM: [MessageHandler(filters=conv_filter, callback=pick_anim)],
            CREATE_ANIM: [MessageHandler(filters=conv_filter, callback=create_anim)],
            ADD_TO_ANIM: [MessageHandler(filters=conv_filter, callback=add_to_anim)],
            POINTS: [MessageHandler(filters=conv_filter, callback=enter_points)],
            SAVE: [MessageHandler(filters=conv_filter, callback=save)]
        },
        fallbacks=[MessageHandler(filters=filters.COMMAND, callback=cancel)]
    )
    application.add_handler(points_conv_handler, 0)

    register_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("register", register_player)],
        states={
            ADD_ANIM: [MessageHandler(filters=conv_filter, callback=add_anim)],
            ADD_ANIM_REPLY: [MessageHandler(filters=conv_filter, callback=add_anim_reply)],
            REGISTER_ANIM: [MessageHandler(filters=conv_filter, callback=register_anim)]
        },
        fallbacks=[MessageHandler(filters=filters.COMMAND, callback=cancel)]
    )
    application.add_handler(register_conv_handler, 1)

    remove_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("remove", remove)],
        states={
            REMOVE_PROCEED: [MessageHandler(filters=conv_filter, callback=remove_proceed)],
            REMOVE_REPLY: [MessageHandler(filters=conv_filter, callback=remove_reply)],
            REMOVE_PLAYER: [MessageHandler(filters=conv_filter, callback=remove_player_reply)],
            REMOVE_ANIM_1: [MessageHandler(filters=conv_filter, callback=remove_anim_reply_player)],
            REMOVE_ANIM_2: [MessageHandler(filters=conv_filter, callback=remove_anim_reply_anim)]
        },
        fallbacks=[MessageHandler(filters=filters.COMMAND, callback=cancel)]
    )
    application.add_handler(remove_conv_handler, 2)

    application.add_handler(CommandHandler("players", list_players), 3)
    application.add_handler(CommandHandler("anims", list_anims), 3)
    application.add_handler(CommandHandler("info", info), 3)
    application.add_handler(CommandHandler("status", status), 3)

    application.add_handler(CommandHandler("debug", debug), 3)

    application.run_polling()


if __name__ == '__main__':
    main()
