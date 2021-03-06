from discord.ext import commands
from .utils.chat_formatting import *
from .utils.dataIO import dataIO
from .utils import checks
from __main__ import user_allowed, send_cmd_help
from copy import deepcopy
import os
import discord


class Alias:
    def __init__(self, bot):
        self.bot = bot
        self.file_path = "data/alias/aliases.json"
        self.aliases = dataIO.load_json(self.file_path)
        self.remove_old()

    @commands.group(pass_context=True, no_pm=True)
    async def alias(self, ctx):
        """Gestion des alias"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @alias.command(name="add", pass_context=True, no_pm=True)
    @checks.mod_or_permissions(manage_server=True)
    async def _add_alias(self, ctx, command, *, to_execute):
        """Ajoute une commande alias

           Exemple: !alias add test flip @Acrown"""
        server = ctx.message.server
        command = command.lower()
        if len(command.split(" ")) != 1:
            await self.bot.say("Il est impossible de faire des commandes avec plusieurs mots.")
            return
        if self.part_of_existing_command(command, server.id):
            await self.bot.say('Une commande existe déjà avec ce nom !')
            return
        prefix = self.get_prefix(server, to_execute)
        if prefix is not None:
            to_execute = to_execute[len(prefix):]
        if server.id not in self.aliases:
            self.aliases[server.id] = {}
        if command not in self.bot.commands:
            self.aliases[server.id][command] = to_execute
            dataIO.save_json(self.file_path, self.aliases)
            await self.bot.say("Alias '{}' ajouté.".format(command))
        else:
            await self.bot.say("Impossible d'ajouter '{}' car c'est une commande Bot.".format(command))

    @alias.command(name="help", pass_context=True, no_pm=True)
    async def _help_alias(self, ctx, command):
        """Essaye d'executer les commandes d'aide aux alias"""
        server = ctx.message.server
        if server.id in self.aliases:
            server_aliases = self.aliases[server.id]
            if command in server_aliases:
                help_cmd = server_aliases[command].split(" ")[0]
                new_content = self.bot.settings.get_prefixes(server)[0]
                new_content += "help "
                new_content += help_cmd[len(self.get_prefix(server,
                                        help_cmd)):]
                message = ctx.message
                message.content = new_content
                await self.bot.process_commands(message)
            else:
                await self.bot.say("Cet alias n'existe pas.")

    @alias.command(name="show", pass_context=True, no_pm=True)
    async def _show_alias(self, ctx, command):
        """Montre quelle commande un alias exécute."""
        server = ctx.message.server
        if server.id in self.aliases:
            server_aliases = self.aliases[server.id]
            if command in server_aliases:
                await self.bot.say(box(server_aliases[command]))
            else:
                await self.bot.say("Cet alias n'existe pas.")

    @alias.command(name="del", pass_context=True, no_pm=True)
    @checks.mod_or_permissions(manage_server=True)
    async def _del_alias(self, ctx, command):
        """Supprime un alias"""
        command = command.lower()
        server = ctx.message.server
        if server.id in self.aliases:
            self.aliases[server.id].pop(command, None)
            dataIO.save_json(self.file_path, self.aliases)
        await self.bot.say("Alias '{}' supprimé.".format(command))

    @alias.command(name="list", pass_context=True, no_pm=True)
    async def _alias_list(self, ctx):
        """Affiche une liste des alias disponibles

        En MP"""
        server = ctx.message.server
        if server.id in self.aliases:
            message = "```Alias - liste:\n"
            for alias in sorted(self.aliases[server.id]):
                if len(message) + len(alias) + 3 > 2000:
                    await self.bot.whisper(message)
                    message = "```\n"
                message += "\t{}\n".format(alias)
            if message != "```Alias - liste:\n":
                message += "```"
                await self.bot.whisper(message)
            else:
                await self.bot.say("Aucun alias sur ce serveur.")

    async def on_message(self, message):
        if len(message.content) < 2 or message.channel.is_private:
            return

        msg = message.content
        server = message.server
        prefix = self.get_prefix(server, msg)

        if not prefix:
            return

        if server.id in self.aliases and user_allowed(message):
            alias = self.first_word(msg[len(prefix):]).lower()
            if alias in self.aliases[server.id]:
                new_command = self.aliases[server.id][alias]
                args = message.content[len(prefix + alias):]
                new_message = deepcopy(message)
                new_message.content = prefix + new_command + args
                await self.bot.process_commands(new_message)

    def part_of_existing_command(self, alias, server):
        '''Command or alias'''
        for command in self.bot.commands:
            if alias.lower() == command.lower():
                return True
        return False

    def remove_old(self):
        for sid in self.aliases:
            to_delete = []
            to_add = []
            for aliasname, alias in self.aliases[sid].items():
                lower = aliasname.lower()
                if aliasname != lower:
                    to_delete.append(aliasname)
                    to_add.append((lower, alias))
                if aliasname != self.first_word(aliasname):
                    to_delete.append(aliasname)
                    continue
                server = discord.Object(id=sid)
                prefix = self.get_prefix(server, alias)
                if prefix is not None:
                    self.aliases[sid][aliasname] = alias[len(prefix):]
            for alias in to_delete:  # Fixes caps and bad prefixes
                del self.aliases[sid][alias]
            for alias, command in to_add:  # For fixing caps
                self.aliases[sid][alias] = command
        dataIO.save_json(self.file_path, self.aliases)

    def first_word(self, msg):
        return msg.split(" ")[0]

    def get_prefix(self, server, msg):
        prefixes = self.bot.settings.get_prefixes(server)
        for p in prefixes:
            if msg.startswith(p):
                return p
        return None


def check_folder():
    if not os.path.exists("data/alias"):
        print("Creating data/alias folder...")
        os.makedirs("data/alias")


def check_file():
    aliases = {}

    f = "data/alias/aliases.json"
    if not dataIO.is_valid_json(f):
        print("Creating default alias's aliases.json...")
        dataIO.save_json(f, aliases)


def setup(bot):
    check_folder()
    check_file()
    bot.add_cog(Alias(bot))
