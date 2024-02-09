
<div align="center">
<img src=".github/99d48ed4682a0c26cb135ed5e5a788f9 (1).png" width="100" height="100"/>
</div>

<h2 align="center">c2c</h2>

<p align="center">
  <em>
    About
    · Made using discord.py
    · Created on 30/11/2022
  </em>
  <br />
  <em>
    Key Features
    · Error Handler
    · Components
    · See more below
  </em>
  <br />
</p>
<p align="center">
  <a href="https://github.com/astral-sh/ruff">
    <img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json" alt="Ruff" style="max-width:100%;"></a>
  <a href="https://img.shields.io/badge/os-windows-yellow">
    <img alt="Windows" src="https://img.shields.io/badge/os-windows-yellow"></a>
  <a href="https://www.python.org/downloads/release">
    <img alt="Python Compatible Versions" src="https://img.shields.io/badge/Python-3.12%20%7C%203.13-blue"></a>
  <br/>
</p>
<div align="center">
  
[![python badge](http://ForTheBadge.com/images/badges/made-with-python.svg)](https://www.python.org/ "Python")
</div>


## Developer Team
We are 2 teenagers in the UK studying A-Levels, and chose to make this Discord bot as a side hussle.
- [Splint](https://discordapp.com/users/992152414566232139/): The primary developer for most commands in the bot.
- [inter_geo](https://discordapp.com/users/546086191414509599): The secondary developer, making some commands in the bot.

## Installation
> [!CAUTION]
> We do not support running an instance of the bot. Setup details will not be given, if you can figure it out, go nuts.
> 
> We are not responsible for any errors that may occur when running this bot. It is also **not** production-ready.

## Features
- Advanced economy system (no json, only using a database):
  - Running these databases using connection pools via [@Rapptz](https://www.github.com/Rapptz)'s `asqlite` repo.
  - The connection pool makes it fast and reliable, data loss is near impossible.
  - Rob, Bankrob, Slots, Bets, Highlow, Blackjack and Building robberies.
  - Advanced profile customization:
    - Set a custom profile title, profile avatar, profile bio and profile showcase.
  - More is being added regularly.
- Miscellaneous Features
  -  Get the time now in Discord's timestamp formatting using any style.
  -  Get a list of every emoji the client can access.
  -  Search for songs on spotify (dupes show up).
  -  Make GET requests to multiple APIs like konachan and API Ninjas. 
  -  Generate a random fact or even ideas of what to do if you're bored.
  -  And so much more..
-  Some owner-only features We are proud of:
    - Having **a lot** of control over the economy system:
      -  Kick users off the economy system.
      -  Ability to modify any attribute of the economy system with ease of any user (credits to [DB Browser for SQlite](https://sqlitebrowser.org/) for this.)

## Developer's Favourite Feature
The help command. 
It is an interactive menu sorting all the commands within cogs by category and assumes each cog fits into one category. 
A dropdown is displayed to list the available categories and clicking any given one provides an embed edited from the original response containing every single command that corresponds to the category. My thought process at the time of making it was robust. It can also list subcommands of a grouped slash command.  All of the embed images are now hosted on Imgur. 

In the course of making this bot, I learnt a lot of things. I was just a beginner at first and had no idea how to read or even understand the discord.py documentation. I think it was my initiative one day to just completley absolve the documentation and of all of its contents one day that led me to where this project has come now. And also the programming tips I've gotten over the years. It is a passion project and We are not considering disbanding the project any time soon.

> [!NOTE]
> The future of this project is uncertain. Given my limited free time, I may not be able to update the code after breaking changes to the library/API take place. This will only dwindle in the future. See https://github.com/SGA-A/c2c/discussions/9 [and the Version Guarantees for discord.py.](https://discordpy.readthedocs.io/en/stable/version_guarantees.html)

## Credits
Of course, we didn't make it work all by ourselves. We have to acknowledge these author's for making certain features possible:
- **The [discord.py](https://discord.gg/r3sSKJJ) server**: almost every question/bug we have encountered has been solved on their discord server, so many situations to fix burning problems were fixed because of them. It is also a great place to learn code optimizations that lower speed and time complexity for the bot.
- **[API Ninjas](https://api-ninjas.com/)**: their are a diverse range of APIs available for free (10,000 requests per month)
- **[Jake Lee's Formula](https://blog.jakelee.co.uk/converting-levels-into-xp-vice-versa/)**: helped made converting levels into experience a breeze.
- **[Stack Overflow](https://stackoverflow.com/)**: a pretty good place for to find answers to your general python bugs and error.
- **[DrenJaha's Blackjack Discord Bot](https://github.com/DrenJaha/discord-blackjack-bot)**: his bot and functions for the blackjack system were used as the foundation for building up the blackjack command for what it is today. We made large changes to the design, but the method of storing data remains largely the same.
- **[Danny's Eval Command](https://github.com/Rapptz/RoboDanny/blob/rewrite/cogs/admin.py#L214-L259)**: still use it and made minor tweaks to it.
- **[skrphenix's Economy System in aiosqlite](https://github.com/Modern-Realm/economy-bot-discord.py/tree/master/economy%20with%20aiosqlite)**: The project structure and design was straightforward making it easy to change, though i had eventually migrated to [Danny's asqlite lib](https://github.com/Rapptz/asqlite) afterward as we were frustrated with the way it was coded. Instead of creating connections every time the command is called, multiple connections are made in a 'connection pool' and on each query a connection is 'acquired' from the pool and then later on 'released' back into the pool. Asynchronous transactions have now become even more faster and reliable. It has `WAL` enabled. See below for a description as for what that is:
> There are advantages and disadvantages to using WAL instead of a rollback journal. Read more about it [here.](https://www.sqlite.org/wal.html)
