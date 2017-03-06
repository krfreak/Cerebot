Cerebot
=======

| Cerebot is a Discord chat bot that can relay queries to the IRC
  knowledge bots
| for `DCSS <http://crawl.develz.org/wordpress/>`__. See the
| `command guide <docs/commands.md>`__ for details on using Cerebot from
| Discord. The remaining instructions on this page are only relevant if
  you want to
| run a custom instance of this bot.

Details
~~~~~~~

| Cerebot can listen to one or more channels on an discord server for
  which it is
| authorized, and can also respond to private channel queries. It
  supports
| rate-limiting responses to excessive messages on the IRC connection.
  It
| also supports basic vanity role modification commands.

| Cerebot is single-threaded and uses
| `asyncio <https://docs.python.org/3.4/library/asyncio.html>`__ to
  manage an
| event loop with concurrent tasks.

Installation
~~~~~~~~~~~~

The following are required:

-  Python 3.4 or later
-  asyncio module (3.4.3 tested)
-  irc module (13.1 tested)
-  pytoml module (0.1.5 tested)
-  discord module (0.16 tested)
-  `beem <https://github.com/gammafunk/beem>`__ module

| All packages above except *beem* are available in PyPI. You can
  install
| *beem* directly from its github repository using pip3. For example:

::

    pip3 install --user git+https://github.com/gammafunk/beem.git

Configuration
~~~~~~~~~~~~~

| Copy the `cerebot\_config.toml.sample <cerebot_config.toml.sample>`__
  file to
| ``cerebot_config.toml`` and edit the necessary fields based on how
  you'd like to run
| the bot. The config file format is
  `toml <https://github.com/toml-lang/toml>`__,
| and the various fields you can change are in this file are documented
  in
| comments.
