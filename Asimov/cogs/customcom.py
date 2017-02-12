from discord.ext import commands
from .utils.dataIO import dataIO
from .utils import checks
from __main__ import user_allowed
import os
import re


class CustomCommands:
    """Custom commands."""

    def __init__(self, bot):
        self.bot = bot
        self.file_path = "data/customcom/commands.json"
        self.c_commands = dataIO.load_json(self.file_path)

    @commands.command(pass_context=True, no_pm=True)
    @checks.mod_or_permissions(administrator=True)
    async def addcom(self, ctx, command : str, *, text):
        """Ajoute une commande custom

        Exemple:
        !addcom votrecommande Texte voulu
        """
        server = ctx.message.server
        command = command.lower()
        if command in self.bot.commands.keys():
            await self.bot.say("Cette commande existe déjà.")
            return
        if not server.id in self.c_commands:
            self.c_commands[server.id] = {}
        cmdlist = self.c_commands[server.id]
        if command not in cmdlist:
            cmdlist[command] = text
            self.c_commands[server.id] = cmdlist
            dataIO.save_json(self.file_path, self.c_commands)
            await self.bot.say("Commande créée.")
        else:
            await self.bot.say("Cette commande existe déjà.")

    @commands.command(pass_context=True, no_pm=True)
    @checks.mod_or_permissions(administrator=True)
    async def editcom(self, ctx, command : str, *, text):
        """Edite une commande existante
        """
        server = ctx.message.server
        command = command.lower()
        if server.id in self.c_commands:
            cmdlist = self.c_commands[server.id]
            if command in cmdlist:
                cmdlist[command] = text
                self.c_commands[server.id] = cmdlist
                dataIO.save_json(self.file_path, self.c_commands)
                await self.bot.say("Commande éditée.")
            else:
                await self.bot.say("Cette commande n'existe pas")
        else:
             await self.bot.say("Ce serveur ne possède pas de commandes personnalisées.")

    @commands.command(pass_context=True, no_pm=True)
    @checks.mod_or_permissions(administrator=True)
    async def delcom(self, ctx, command : str):
        """Supprime une commande personnalisée"""
        server = ctx.message.server
        command = command.lower()
        if server.id in self.c_commands:
            cmdlist = self.c_commands[server.id]
            if command in cmdlist:
                cmdlist.pop(command, None)
                self.c_commands[server.id] = cmdlist
                dataIO.save_json(self.file_path, self.c_commands)
                await self.bot.say("Supprimée avec succès.")
            else:
                await self.bot.say("Cette commande n'existe pas.")
        else:
            await self.bot.say("Aucune commande custom sur ce serveur.")

    @commands.command(pass_context=True, no_pm=True)
    async def customcommands(self, ctx):
        """Montre une liste des commandes custom"""
        server = ctx.message.server
        if server.id in self.c_commands:
            cmdlist = self.c_commands[server.id]
            if cmdlist:
                i = 0
                msg = ["```Commandes custom:\n"]
                for cmd in sorted([cmd for cmd in cmdlist.keys()]):
                    if len(msg[i]) + len(ctx.prefix) + len(cmd) + 5 > 2000:
                        msg[i] += "```"
                        i += 1
                        msg.append("``` {}{}\n".format(ctx.prefix, cmd))
                    else:
                        msg[i] += " {}{}\n".format(ctx.prefix, cmd)
                msg[i] += "```"
                for cmds in msg:
                    await self.bot.whisper(cmds)
            else:
                await self.bot.say("Il n'y a pas de commandes custom sur ce serveur")
        else:
            await self.bot.say("Il n'y a pas de commandes custom sur ce serveur")

    async def checkCC(self, message):
        if len(message.content) < 2 or message.channel.is_private:
            return

        server = message.server
        prefix = self.get_prefix(message)

        if not prefix:
            return

        if server.id in self.c_commands and user_allowed(message):
            cmdlist = self.c_commands[server.id]
            cmd = message.content[len(prefix):]
            if cmd in cmdlist.keys():
                cmd = cmdlist[cmd]
                cmd = self.format_cc(cmd, message)
                await self.bot.send_message(message.channel, cmd)
            elif cmd.lower() in cmdlist.keys():
                cmd = cmdlist[cmd.lower()]
                cmd = self.format_cc(cmd, message)
                await self.bot.send_message(message.channel, cmd)

    def get_prefix(self, message):
        for p in self.bot.settings.get_prefixes(message.server):
            if message.content.startswith(p):
                return p
        return False

    def format_cc(self, command, message):
        results = re.findall("\{([^}]+)\}", command)
        for result in results:
            param = self.transform_parameter(result, message)
            command = command.replace("{" + result + "}", param)
        return command

    def transform_parameter(self, result, message):
        """
        For security reasons only specific objects are allowed
        Internals are ignored
        """
        raw_result = "{" + result + "}"
        objects = {
            "message" : message,
            "author"  : message.author,
            "channel" : message.channel,
            "server"  : message.server
        }
        if result in objects:
            return str(objects[result])
        try:
            first, second = result.split(".")
        except ValueError:
            return raw_result
        if first in objects and not second.startswith("_"):
            first = objects[first]
        else:
            return raw_result
        return str(getattr(first, second, raw_result))


def check_folders():
    if not os.path.exists("data/customcom"):
        print("Creating data/customcom folder...")
        os.makedirs("data/customcom")

def check_files():
    f = "data/customcom/commands.json"
    if not dataIO.is_valid_json(f):
        print("Creating empty commands.json...")
        dataIO.save_json(f, {})

def setup(bot):
    check_folders()
    check_files()
    n = CustomCommands(bot)
    bot.add_listener(n.checkCC, "on_message")
    bot.add_cog(n)
