# c2c
<div align="center">
<img src="testing/99d48ed4682a0c26cb135ed5e5a788f9 (1).png" width="100" height="100"/>
</div>
A highly integrated and powerful discord bot.
I have been actively working on this project for the past 3 years, it is rare to encounter any bugs on the bot. 

## Features
- Advanced economy system (no json, using databases)
  - Running these databases using connection pools via [@Rapptz](https://www.github.com/Rapptz)'s `asqlite` repo.
  - The connection pool makes it fast and reliable, data loss is rare.
  - Rob, Bankrob, Slots, Bets, Highlow, Building robberies
  - More is being added every month..
- Miscellaneous Features
  -  Get the time now in Discord's timestamp formatting using any style
  -  Get a list of every emoji the client can access
  -  Search for songs on spotify (dupes show up)
  -  Generate a random fact or even ideas of what to do if you're bored..
  -  And so much more..
-  Some owner-only features I am proud of
  - Playing local files in a voice-channel (yes)
  - Having **a lot** of control over the economy system
    -  Kick users off the economy system, generate assets without paying etc.
    -  Ability to modify any attribute of the economy system with ease of any user (credits to [DB Browser for SQlite](https://sqlitebrowser.org/) for this.)

## My Personal Favourite Feature
The help command. It is an interactive menu sorting all the commands within cogs by category and assumes each cog fits into one category. A dropdown is displayed to list the available categories and clicking any given one provides an embed edited from the original response containing every single command that corresponds to the category. My thought process at the time of making it was robust and there has been no situation yet encountered in which it faltered.

In the course of making this bot, I learnt a lot of things. I was just a beginner at first and had no idea how to read or even understand the discord.py documentation. i did not on many tutorials but I think it was my initiative one day to just completley absolve the docs of all of its contents one day that led me to where this project has come now. It is a passion project and I am not considering disbanding the project any time soon.

## Credits
- **The [discord.py](https://discord.gg/r3sSKJJ) server**: almost every question/bug ive encountered has been solved on their discord server, so many situations to fix burning problems were fixed because of them. It is also a great place to learn code optimizations that lower speed and time complexity for the bot.
- **[API Ninjas](https://api-ninjas.com/)**: their are a diverse range of APIs available for free (10,000 requests per month)
- **[Stack Overflow](https://stackoverflow.com/)**: a pretty good place for to find answers to your general python bugs and errors
- **[DrenJaha's Blackjack Discord Bot](https://github.com/DrenJaha/discord-blackjack-bot): his bot and functions for the blackjack system were used as the foundation for building up the blackjack command for what it is today.
- **[Danny's Eval Command](https://github.com/Rapptz/RoboDanny/blob/rewrite/cogs/admin.py#L214-L259)**: still use it and made minor tweaks to it.
- **[skrphenix's Economy System in `aiosqlite`](https://github.com/Modern-Realm/economy-bot-discord.py/tree/master/economy%20with%20aiosqlite)**: this was a big one, the project structure and design was straightforward making it easy to change, though i had eventually migrated to [Danny's `asqlite` lib](https://github.com/Rapptz/asqlite) afterward as i was frustrated with the way it was code. Instead of creating connections every time the command is called, multiple connections are made in a 'connection pool' and on each query a connection is 'acquired' from the pool and then later on 'released' back into the pool. This did make asynchronous transactions even more faster and reliable.
