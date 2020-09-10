# Testing

Discord bots are a pain in the ass to test in a reproducible environment so to get around this, I have created an **Oghma Testing** bot that will allow contributors to test their changes in a sandbox environment. To access this testing bot, follow these steps:

1. Create a new issue creating access to the bot [using this template](https://github.com/shadowedlucario/oghma/issues/new?assignees=&labels=Access+Request&template=request-to-access-the-testing-bot.md&title=). Wait for an admin to approve of your application (to speed it up, make sure you join the [discord server](https://discord.gg/8YZ2NZ5) and post in #contributing). If your application is taking a while (a few days), ping [@shadowedlucario](https://github.com/shadowedlucario) or post on the discord.

2. Once you have been approved, you'll then be in the discord team of the testing bot with access to run it. To do so, clone your forked repository and branch. Then, `pip install` the dependencies in [requirements.txt](./requirements.txt):

```bash
pip3 install -r requirements.txt
```
or do it manually...
```bash
pip3 install requests discord python-dotenv
```

3. Store the bot key that the Admin DM's you in an environment variable called `BOT_KEY` and run the main python file:

```bash
export BOT_KEY=<the-bot-key>
python3 bot.py
```

4. Head over to `#oghma-testing` on the discord and try to ping the bot (`?ping`). If you get a response back from `Oghma Testing`, congrats! You have control of the test bot.

Any queries or questions, raise an issue or ping `@Admin` on the discord.
