import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GUILD_ID = int(os.getenv("GUILD_ID", "0"))

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

intents = discord.Intents.default()
bot = commands.Bot(intents=intents)

# Изумрудный цвет для эмбов
EMERALD = discord.Color.from_rgb(16, 185, 129)

STATS = ["speed", "magic", "reaction", "endurance", "durability", "strength"]

STAT_NAMES_RU = {
    "speed": "⚡ Скорость",
    "magic": "✨ Магия",
    "reaction": "🌀 Реакция",
    "endurance": "🫁 Выносливость",
    "durability": "🛡️ Прочность",
    "strength": "💪 Сила",
}


@bot.event
async def on_ready():
    print(f"Emerynth Bot готов: {bot.user}")
    try:
        synced = await bot.tree.sync(guild=discord.Object(id=GUILD_ID) if GUILD_ID else None)
        print(f"Синхронизировано {len(synced)} slash-команд")
    except Exception as e:
        print(f"Ошибка синхронизации: {e}")


# ---------- /create_character ----------
@bot.tree.command(
    name="create_character",
    description="Создать персонажа в мультиверсе Emerynth",
    guild=discord.Object(id=GUILD_ID) if GUILD_ID else None,
)
@discord.option("name", str, description="Имя персонажа", required=True)
@discord.option("speed", int, description="Скорость (0-100)", min_value=0, max_value=100, required=True)
@discord.option("magic", int, description="Магия (0-100)", min_value=0, max_value=100, required=True)
@discord.option("reaction", int, description="Реакция (0-100)", min_value=0, max_value=100, required=True)
@discord.option("endurance", int, description="Выносливость (0-100)", min_value=0, max_value=100, required=True)
@discord.option("durability", int, description="Прочность (0-100)", min_value=0, max_value=100, required=True)
@discord.option("strength", int, description="Сила (0-100)", min_value=0, max_value=100, required=True)
async def create_character(
    ctx: discord.ApplicationContext,
    name: str,
    speed: int,
    magic: int,
    reaction: int,
    endurance: int,
    durability: int,
    strength: int,
):
    discord_id = str(ctx.author.id)

    # Проверка: у пользователя уже есть персонаж с таким именем
    existing = (
        supabase.table("characters")
        .select("id")
        .eq("discord_id", discord_id)
        .eq("character_name", name)
        .execute()
    )
    if existing.data:
        await ctx.respond(
            f"❌ У вас уже есть персонаж с именем **{name}**. Выберите другое имя.",
            ephemeral=True,
        )
        return

    # Сумма статов (можно ограничить, например, 300)
    total = speed + magic + reaction + endurance + durability + strength
    if total > 300:
        await ctx.respond(
            f"❌ Сумма статов не должна превышать **300** (у вас: {total}).",
            ephemeral=True,
        )
        return

    data = {
        "discord_id": discord_id,
        "character_name": name,
        "speed": speed,
        "magic": magic,
        "reaction": reaction,
        "endurance": endurance,
        "durability": durability,
        "strength": strength,
    }

    try:
        supabase.table("characters").insert(data).execute()
    except Exception as e:
        await ctx.respond(f"⚠️ Ошибка БД: `{e}`", ephemeral=True)
        return

    embed = discord.Embed(
        title=f"🌿 Персонаж создан: {name}",
        description=f"Владелец: {ctx.author.mention}\nМир: **Emerynth**",
        color=EMERALD,
    )
    for stat in STATS:
        embed.add_field(
            name=STAT_NAMES_RU[stat],
            value=f"`{data[stat]}`",
            inline=True,
        )
    embed.set_footer(text=f"Сумма статов: {total}/300 • Изумрудный мультиверс")
    await ctx.respond(embed=embed)


# ---------- /my_characters ----------
@bot.tree.command(
    name="my_characters",
    description="Показать всех ваших персонажей в Emerynth",
    guild=discord.Object(id=GUILD_ID) if GUILD_ID else None,
)
async def my_characters(ctx: discord.ApplicationContext):
    discord_id = str(ctx.author.id)
    result = (
        supabase.table("characters")
        .select("*")
        .eq("discord_id", discord_id)
        .order("created_at")
        .execute()
    )

    if not result.data:
        await ctx.respond(
            "У вас пока нет персонажей. Создайте первого командой `/create_character`.",
            ephemeral=True,
        )
        return

    embeds = []
    for char in result.data:
        total = sum(char[s] for s in STATS)
        embed = discord.Embed(
            title=f"🌿 {char['character_name']}",
            color=EMERALD,
        )
        for stat in STATS:
            embed.add_field(
                name=STAT_NAMES_RU[stat],
                value=f"`{char[stat]}`",
                inline=True,
            )
        embed.set_footer(text=f"Сумма: {total}/300 • Emerynth")
        embeds.append(embed)

    # Discord лимит: 10 эмбов за сообщение
    if len(embeds) <= 10:
        await ctx.respond(embeds=embeds)
    else:
        for i in range(0, len(embeds), 10):
            chunk = embeds[i:i+10]
            if i == 0:
                await ctx.respond(embeds=chunk)
            else:
                await ctx.followup.send(embeds=chunk)


# ---------- /character_info ----------
@bot.tree.command(
    name="character_info",
    description="Показать информацию о конкретном персонаже (своём или чужом)",
    guild=discord.Object(id=GUILD_ID) if GUILD_ID else None,
)
@discord.option("name", str, description="Имя персонажа", required=True)
async def character_info(ctx: discord.ApplicationContext, name: str):
    result = (
        supabase.table("characters")
        .select("*")
        .eq("character_name", name)
        .execute()
    )

    if not result.data:
        await ctx.respond(f"Персонаж с именем **{name}** не найден.", ephemeral=True)
        return

    char = result.data[0]
    owner_id = char["discord_id"]
    try:
        owner = await bot.fetch_user(int(owner_id))
        owner_display = owner.mention
    except Exception:
        owner_display = f"<@{owner_id}>"

    total = sum(char[s] for s in STATS)
    embed = discord.Embed(
        title=f"🌿 {char['character_name']}",
        description=f"Владелец: {owner_display}\nМир: **Emerynth**",
        color=EMERALD,
    )
    for stat in STATS:
        embed.add_field(name=STAT_NAMES_RU[stat], value=f"`{char[stat]}`", inline=True)
    embed.set_footer(text=f"Сумма статов: {total}/300 • Изумрудный мультиверс")
    await ctx.respond(embed=embed)


# ---------- /leaderboard ----------
@bot.tree.command(
    name="leaderboard",
    description="Топ персонажей Emerynth по сумме статов",
    guild=discord.Object(id=GUILD_ID) if GUILD_ID else None,
)
async def leaderboard(ctx: discord.ApplicationContext):
    result = supabase.table("characters").select("*").execute()
    if not result.data:
        await ctx.respond("Пока нет ни одного персонажа.", ephemeral=True)
        return

    ranked = sorted(
        result.data,
        key=lambda c: sum(c[s] for s in STATS),
        reverse=True,
    )[:10]

    embed = discord.Embed(
        title="🏆 Сильнейшие персонажи Emerynth",
        color=EMERALD,
    )
    for i, char in enumerate(ranked, start=1):
        total = sum(char[s] for s in STATS)
        embed.add_field(
            name=f"{i}. {char['character_name']}",
            value=f"Сумма: **{total}** • Владелец: <@{char['discord_id']}>",
            inline=False,
        )
    embed.set_footer(text="Топ-10 по сумме статов • Изумрудный мультиверс")
    await ctx.respond(embed=embed)


if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)