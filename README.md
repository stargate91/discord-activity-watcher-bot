# Iris Bot - Server Activity Tracker

Hello! This is the README file for our project called Iris. It is a very cool Discord bot that we built to help people keep track of what is happening on their servers. It watches who is talking, who is playing games, and who is hanging out in voice channels, and then it gives them points for being active.

## What this bot does

We wanted to make a bot that makes servers more fun. Here are the main things it can do:

### Tracking and Points
The bot is like a very organized secretary. It watches when people send messages or add reactions to things. If you share a cool picture or a video link from YouTube or TikTok, the bot notices and gives you extra points for being helpful and sharing media. It even knows if you are just talking or if you are sharing your screen or camera in a voice room, and it calculates your points based on that.

### Games and Roles
Iris loves games! It can automatically give you a role on Discord based on the game you are playing right now. We also have a system called Franchises where we group similar games together.

### Weekly Elites
Every Monday, the bot looks at its notebook (the database) and finds out who was the most active during the week. It gives out special awards (Elites) for things like:
- Playing the most games
- Playing many different types of games
- Listening to the most music on Spotify
- Streaming for the community
- Sharing the most memes and pictures
There is also a Hall of Fame for people who win a lot of times!

### Profiles and Leaderboards
Users can type /me to see a very pretty card that shows all their stats. It even has a little chart that shows how active they were during the week. You can also use /top to see who the top 10 people on the whole server are.

### Linked Accounts
Sometimes people have a second account or a "mini" account. Our bot is smart enough to link them together so all your points from both accounts go into one big pile. It also makes sure your roles are the same on all your accounts.

### Emoji and Sticker Manager
We added a special tool that lets server admins easily add new emojis or stickers from a website called emoji.gg or from any direct link. It can also rename them or show them in a very large size if you want to see the details.

### Reaction Roles
This part of the bot helps you set up those cool messages where people can click an emoji to get a role. The bot can even send the message for you and add all the emojis automatically!

### Localization
We made sure the bot can speak different languages! Right now it knows English and Hungarian. Everything the bot says is saved in simple JSON files, so it is very easy to add more languages later.

For the people running the server, the bot keeps a very detailed log of everything that happens, like when someone joins, leaves, deletes a message, or changes their nickname. It also provides maintenance tools like `/reset-games`, `/reset-elites`, and `/reset-reaction-roles` for data management.

## How to set it up

If you want to run this bot yourself, here is what you need to do:

1. Make sure you have Python 3.10 or newer installed on your computer.
2. Install the requirements by typing "pip install -r requirements.txt" in your terminal.
3. Put your secret Discord Token into a file named .env.
4. Open the config.json file and fill in the ID numbers for your server roles and channels.
5. You can change what the bot says by looking at the files in the locales folder.
6. Start the bot by running "python bot.py".

## How it works inside

We tried to keep the code very neat and organized:
- The bot.py is the main brain that starts everything.
- The cogs folder has different files for each feature, like stats or events.
- The core folder has all the heavy-lifting logic, like the database manager and the image generator.
- We use SQLite to save all the data because it is simple and fast.

We are very happy with how it turned out and we hope it makes your server a much better place to hang out!
