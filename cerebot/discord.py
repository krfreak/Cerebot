"""Creating and managing the Discord connection."""

import asyncio
if hasattr(asyncio, "async"):
    ensure_future = asyncio.async
else:
    ensure_future = asyncio.ensure_future

from beem.chat import ChatWatcher, bot_help_command
import discord
import logging
import os
import re
import signal
import time

from .version import version as Version

_log = logging.getLogger()

class DiscordChannel(ChatWatcher):
    def __init__(self, manager, channel, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.manager = manager
        self.channel = channel
        self.login_username = None
        self.bot_chat_link = "Private Message"
        if self.manager.user:
            self.login_username = self.manager.user.name
        if not channel.name or channel.is_private:
            self.name = channel.id
        else:
            self.name = '#' + channel.name
        self.admins_can_target = False

    def describe_source(self):
        return "{}:{}".format(self.channel.server.name, self.name)

    def get_username(self, user):
        return user.name

    def lookup_nick(self, username):
        return None

    def get_vanity_roles(self):
        if self.channel.is_private:
            return

        server = self.channel.server
        bot_role = None
        for r in server.roles:
            if r.name == "Bot" and r in server.me.roles:
                bot_role = r
                break
        if not bot_role:
            return

        roles = []
        for r in server.roles:
            # Only give roles with default permissions.
            if (r.position < bot_role.position
                and not r.is_everyone
                and r.permissions == server.default_role.permissions):
                roles.append(r)

        return roles

    def bot_command_allowed(self, user, command):
        entry = self.manager.bot_commands[command]
        if (entry["source_restriction"] == "channel"
            and self.channel.is_private):
            return (False, "This command must be run in a channel.")

        return super().bot_command_allowed(user, command)

    def handle_timeout(self):
        if self.manager.handle_timeout():
            _log.info("%s: Command ignored due to command limit (channel: %s, "
                      "requester: %s): %s",
                      self.manager.service, self.name, sender, message)
            return True

        return False

    def get_source_ident(self):
        """Get a unique identifier hash of the discord channel."""

        return {"service" : self.manager.service, "name" : self.channel.id}

    @asyncio.coroutine
    def send_chat(self, message, message_type="normal"):
        if message_type == "action":
            message = '_' + message + '_'
        elif message_type == "monster":
            message = '```' + message + '```'
        elif self.message_needs_escape(message):
            message = "]" + message

        yield from self.manager.send_message(self.channel, message)


class DiscordManager(discord.Client):
    def __init__(self, conf, dcss_manager, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.service = "Discord"
        self.conf = conf
        self.single_user = False
        self.dcss_manager = dcss_manager
        dcss_manager.managers["Discord"] = self
        self.bot_commands = bot_commands
        self.message_times = []

    @asyncio.coroutine
    def on_message(self, message):
        if not self.is_logged_in:
            return

        source = DiscordChannel(self, message.channel)
        yield from source.read_chat(message.author, message.content)

    @asyncio.coroutine
    def on_ready(self):
        self.login_username = self.user.name

    def get_source_by_ident(self, source_ident):
        channel = self.get_channel(source_ident["name"])
        return DiscordChannel(self, channel)

    @asyncio.coroutine
    def start(self):
        _log.info("Discord: Starting manager")

    def user_is_admin(self, user):
        """Return True if the user is a admin."""

        admins = self.conf.get("admins")
        if not admins:
            return False

        for u in admins:
            if u == str(user):
                return True
        return False

    @asyncio.coroutine
    def start(self):
        yield from self.login(self.conf['token'])
        yield from self.connect()

    def disconnect(self):
        """Disconnect from Discord. This will log any disconnection error, but
        never raise.

        """

        if self.conf.get("fake_connect") or self.is_closed:
            return

        try:
            yield from self.close()
        except Exception as e:
            err_reason = type(e).__name__
            if e.args:
                err_reason = e.args[0]
            _log.error("Discord: Error when disconnecting: %s", err_reason)

    def handle_timeout(self):
        current_time = time.time()
        for timestamp in list(self.message_times):
            if current_time - timestamp >= self.conf["command_period"]:
                self.message_times.remove(timestamp)
        if len(self.message_times) >= self.conf["command_limit"]:
            return True

        self.message_times.append(current_time)
        return False


@asyncio.coroutine
def bot_version_command(source, user):
    """!version chat command"""

    report = "Version {}".format(Version)
    manager = source.manager
    yield from source.send_chat(report)


@asyncio.coroutine
def bot_listroles_command(source, user):
    """!listroles chat command"""


    roles = source.get_vanity_roles()
    if not roles:
        yield from source.send_chat("No available roles found.")
        return

    yield from source.send_chat(', '.join(r.name for r in roles))

@asyncio.coroutine
def bot_addrole_command(source, user, rolename):
    """!addrole chat command"""

    roles = source.get_vanity_roles()
    for r in roles:
        if rolename != r.name:
            continue

        yield from source.manager.add_roles(user, r)
        yield from source.send_chat(
                "Member {} has been given role {}".format(user.name, rolename))
        return

    yield from source.send_chat("Unknown role: {}".format(rolename))

@asyncio.coroutine
def bot_removerole_command(source, user, rolename):
    """!removerole chat command"""

    roles = source.get_vanity_roles()
    for r in roles:
        if rolename != r.name:
            continue

        if r not in user.roles:
            yield from source.send_chat(
                    "Member {} does not have role {}".format(user.name,
                        rolename))
            return

        yield from source.manager.remove_roles(user, r)
        yield from source.send_chat(
                "Member {} has lost role {}".format(user.name, rolename))
        return

    yield from source.send_chat("Unknown role: {}".format(rolename))

@asyncio.coroutine
def bot_glasses_command(source, user):
    """!glasses chat command"""

    message = yield from source.manager.send_message(source.channel, '( •_•)')
    yield from asyncio.sleep(0.5)
    yield from source.manager.edit_message(message, '( •_•)>⌐■-■')
    yield from asyncio.sleep(0.5)
    yield from source.manager.edit_message(message, '(⌐■_■)')

@asyncio.coroutine
def bot_deal_command(source, user):
    """!deal chat command"""

    glasses = '    ⌐■-■    '
    glasson = '   (⌐■_■)   '
    dealwith = 'deal with it'
    lines = ['            ',
             '            ',
             '            ',
             '    (•_•)   ']
    mgr = source.manager
    message = yield from mgr.send_message(source.channel,
            '```{}```'.format('\n'.join(lines)))
    yield from asyncio.sleep(0.5)
    for i in range(3):
        yield from mgr.edit_message(message, '```{}```'.format(
            '\n'.join(lines[:i] + [glasses]+lines[i + 1:])))
        yield from asyncio.sleep(0.5)
    yield from mgr.edit_message(message, '```{}```'.format(
        '\n'.join(lines[:1] + [dealwith] + lines[2:3] + [glasson])))

@asyncio.coroutine
def bot_dance_command(source, user):
    """!dance chat command"""

    mgr = source.manager
    figures = [':D|-<', ':D/-<', ':D|-<', r':D\\-<']
    message = yield from mgr.send_message(source.channel, figures[0])
    yield from asyncio.sleep(0.25)
    for n in range(2):
        for f in figures[0 if n else 1:]:
            yield from mgr.edit_message(message, f)
            yield from asyncio.sleep(0.25)
    yield from mgr.edit_message(message, figures[0])

@asyncio.coroutine
def bot_zxcdance_command(source, user):
    """!zxcdance chat command"""

    mgr = source.manager
    figures = ['└[^_^]┐', '┌[^_^]┘']
    message = yield from mgr.send_message(source.channel, figures[0])
    yield from asyncio.sleep(0.25)
    for n in range(2):
        for f in figures[0 if n else 1:]:
            yield from mgr.edit_message(message, f)
            yield from asyncio.sleep(0.25)
    yield from mgr.edit_message(message, figures[0])

# Discord bot commands
bot_commands = {
    "version" : {
        "arg_pattern" : None,
        "arg_description" : None,
        "single_user_allowed" : True,
        "source_restriction" : "admin",
        "function" : bot_version_command,
    },
    "bothelp" : {
        "arg_pattern" : None,
        "arg_description" : None,
        "single_user_allowed" : True,
        "source_restriction" : None,
        "function" : bot_help_command,
    },
    "listroles" : {
        "arg_pattern" : None,
        "arg_description" : None,
        "single_user_allowed" : True,
        "source_restriction" : "channel",
        "function" : bot_listroles_command,
    },
    "addrole" : {
        "arg_pattern" : r".+$",
        "arg_description" : "ROLE",
        "arg_required" : True,
        "single_user_allowed" : True,
        "source_restriction" : "channel",
        "function" : bot_addrole_command,
    },
    "removerole" : {
        "arg_pattern" : r".+$",
        "arg_description" : "ROLE",
        "arg_required" : True,
        "single_user_allowed" : True,
        "source_restriction" : "channel",
        "function" : bot_removerole_command,
    },
    "glasses" : {
        "arg_pattern" : None,
        "arg_description" : None,
        "single_user_allowed" : True,
        "source_restriction" : None,
        "function" : bot_glasses_command,
    },
    "deal" : {
        "arg_pattern" : None,
        "arg_description" : None,
        "single_user_allowed" : True,
        "source_restriction" : None,
        "function" : bot_deal_command,
    },
    "dance" : {
        "arg_pattern" : None,
        "arg_description" : None,
        "single_user_allowed" : True,
        "source_restriction" : None,
        "function" : bot_dance_command,
    },
    "zxcdance" : {
        "arg_pattern" : None,
        "arg_description" : None,
        "single_user_allowed" : True,
        "source_restriction" : None,
        "function" : bot_zxcdance_command,
    },
}
