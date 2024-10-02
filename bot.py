import discord
from discord.ext import commands
import random
import json
import re

bot_version = '1.1'
bot_prefix = '%'

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix=bot_prefix, intents=intents)


# Load the profanity word list from a text file
def load_profanity_list():
    try:
        with open('profanity.txt', 'r') as f:
            return [line.strip().lower() for line in f]
    except FileNotFoundError:
        return []


profanity_list = load_profanity_list()


def load_config():
    try:
        with open('config.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_config(config):
    with open('config.json', 'w') as f:
        json.dump(config, f)


config = load_config()


# Scramble the word while preserving leading and trailing punctuation
def scramble_word(word):
    match = re.match(r"([^\w]*)(\w+)([^\w]*)", word)
    if match:
        leading_punct = match.group(1)
        core_word = match.group(2)
        trailing_punct = match.group(3)
        if len(core_word) > 3:
            middle = list(core_word[1:-1])
            random.shuffle(middle)
            scrambled = core_word[0] + ''.join(middle) + core_word[-1]
        else:
            scrambled = core_word
        return leading_punct + scrambled + trailing_punct
    return word


# Clean the word by removing spaces and non-alphabet characters for better profanity detection
def clean_word(word):
    return re.sub(r'\W+', '', word).lower()


# Check if any word in the scrambled message (with spaces and punctuation removed) matches the profanity list
def contains_profanity(scrambled_message):
    for word in scrambled_message.split():
        cleaned_word = clean_word(word)  # Clean the word by removing spaces and special chars
        if cleaned_word in profanity_list:
            return True
    return False


@bot.command()
async def info(ctx):
    bot_user = bot.user
    embed = discord.Embed(description="This bot scrambles the words of every message you send.",
                          color=discord.Color.lighter_gray())
    embed.set_author(name='Raed Tihs Help', icon_url=bot_user.avatar.url)
    embed.add_field(name="Commands",
                    value=f"`{bot_prefix}setchannel [#channel]`: Set the channel for the bot to listen in.")
    embed.set_footer(text=f"Version {bot_version} | The bot will only work in the configured channel.")
    await ctx.send(embed=embed)


@bot.command()
@commands.has_permissions(manage_guild=True)
async def setchannel(ctx, channel: discord.TextChannel):
    config['scramble_channel'] = channel.id
    save_config(config)
    bot_user = bot.user
    embed = discord.Embed(description=f"Raed Tihs is now active in {channel.mention}.",
                          color=discord.Color.lighter_gray())
    embed.set_author(name='Raed Tihs Channel Updated', icon_url=bot_user.avatar.url)
    await ctx.send(embed=embed)


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    await bot.process_commands(message)

    scramble_channel_id = config.get('scramble_channel')
    if scramble_channel_id is None or message.channel.id != scramble_channel_id:
        return

    if not message.content.strip():
        return

    webhook = None

    webhooks = await message.channel.webhooks()
    for wh in webhooks:
        if wh.name == "Raed Tihs":
            webhook = wh
            break

    if not webhook:
        webhook = await message.channel.create_webhook(name="Raed Tihs")

    scrambled_message = ' '.join([scramble_word(word) for word in message.content.split()])

    # Check if the scrambled message contains profanity, even with spaces or punctuation removed
    if contains_profanity(scrambled_message):
        bot_user = bot.user
        embed = discord.Embed(description="Inappropriate content detected.",
                              color=discord.Color.red())
        embed.set_author(name="⚠️ Warning", icon_url=bot_user.avatar.url)

        # Send the warning embed and delete it after 5 seconds
        warning_message = await message.channel.send(embed=embed)
        await message.delete()
        await warning_message.delete(delay=5)
        return  # Stop further processing if profanity is detected

    # Send the scrambled message using the webhook without attachments
    await webhook.send(
        content=scrambled_message,
        username=message.author.display_name,
        avatar_url=message.author.avatar.url,
        files=[await attachment.to_file() for attachment in message.attachments]
    )

    await message.delete()


@bot.event
async def on_ready():
    print(f'Bot is ready. Logged in as {bot.user.name}')
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching,
                                                        name="your every move"))

bot.run('BOT_TOKEN_HERE')
