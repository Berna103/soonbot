import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio
import json
import os
import datetime

# ============================================
#              KONFIGURACJA
# ============================================
TOKEN = 'token'

def wczytaj():
    try:
        if os.path.exists("ustawienia.json"):
            with open("ustawienia.json", "r", encoding="utf-8") as f:
                return json.load(f)
    except:
        pass
    return {}

def zapisz(dane):
    try:
        with open("ustawienia.json", "w", encoding="utf-8") as f:
            json.dump(dane, f, indent=4)
    except:
        try:
            os.remove("ustawienia.json")
            with open("ustawienia.json", "w", encoding="utf-8") as f:
                json.dump(dane, f, indent=4)
        except:
            print("Nie mozna zapisac ustawien!")

cfg = wczytaj()
warny_db = {}

# ============================================
#              PRZYCISKI I MENU
# ============================================

class WeryfikacjaView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Zweryfikuj Się", style=discord.ButtonStyle.green, emoji="✅", custom_id="verify_btn")
    async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        gid = str(interaction.guild.id)
        rid = cfg.get(gid, {}).get("rola_weryfikacja")
        if not rid:
            return await interaction.response.send_message("❌ Brak ustawionej roli!", ephemeral=True)
        rola = interaction.guild.get_role(rid)
        if not rola:
            return await interaction.response.send_message("❌ Rola usunięta!", ephemeral=True)
        if rola in interaction.user.roles:
            return await interaction.response.send_message("✅ Już jesteś zweryfikowany!", ephemeral=True)
        try:
            await interaction.user.add_roles(rola)
            embed = discord.Embed(
                title="✅ Weryfikacja Pomyślna",
                description=(
                    f"Witaj {interaction.user.mention}!\n\n"
                    f"── Pomyślnie zweryfikowano twoje konto.\n"
                    f"── Masz teraz pełny dostęp do serwera.\n"
                    f"── Miłego pobytu na **{interaction.guild.name}**!"
                ),
                color=discord.Color.green()
            )
            embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else interaction.user.default_avatar.url)
            embed.set_footer(text=f"{interaction.guild.name} × Weryfikacja")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except:
            await interaction.response.send_message("❌ Bot nie ma uprawnień! Rola bota musi być WYŻEJ!", ephemeral=True)


class TicketDropdown(discord.ui.Select):
    def __init__(self):
        opcje = [
            discord.SelectOption(label="Współpraca", emoji="🤝", description="Propozycja współpracy", value="wspolpraca"),
            discord.SelectOption(label="Zamówienie", emoji="🛒", description="Złóż zamówienie", value="zamowienie"),
            discord.SelectOption(label="Pomoc", emoji="❓", description="Potrzebuję pomocy", value="pomoc"),
            discord.SelectOption(label="Rekrutacja", emoji="📋", description="Chcę dołączyć do ekipy", value="rekrutacja"),
            discord.SelectOption(label="Inne", emoji="📝", description="Inny temat", value="inne"),
        ]
        super().__init__(
            placeholder="📂 Wybierz kategorię ticketu...",
            options=opcje,
            custom_id="ticket_dropdown"
        )

    async def callback(self, interaction: discord.Interaction):
        kategoria = self.values[0]
        guild = interaction.guild
        gid = str(guild.id)
        server_name = guild.name

        nazwy = {
            "wspolpraca": "🤝 Współpraca",
            "zamowienie": "🛒 Zamówienie",
            "pomoc": "❓ Pomoc",
            "rekrutacja": "📋 Rekrutacja",
            "inne": "📝 Inne"
        }
        kolory = {
            "wspolpraca": discord.Color.blue(),
            "zamowienie": discord.Color.green(),
            "pomoc": discord.Color.orange(),
            "rekrutacja": discord.Color.purple(),
            "inne": discord.Color.greyple()
        }

        for ch in guild.text_channels:
            if ch.name == f"ticket-{interaction.user.name.lower()}":
                return await interaction.response.send_message(f"❌ Masz już otwarty ticket: {ch.mention}", ephemeral=True)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        rid = cfg.get(gid, {}).get("rola_support")
        if rid:
            rola = guild.get_role(rid)
            if rola:
                overwrites[rola] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        kanal = await guild.create_text_channel(f"ticket-{interaction.user.name}", overwrites=overwrites)
        await interaction.response.send_message(f"✅ Ticket utworzony: {kanal.mention}", ephemeral=True)

        embed = discord.Embed(
            title=f"{server_name} × Ticket",
            description=(
                f"{'═' * 40}\n\n"
                f"📩 **Nowy Ticket**\n\n"
                f"**Kategoria:** {nazwy[kategoria]}\n"
                f"**Użytkownik:** {interaction.user.mention}\n"
                f"**Data:** {datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
                f"── Opisz dokładnie swój problem lub sprawę.\n"
                f"── Administracja odpowie najszybciej jak to możliwe.\n"
                f"── Aby zamknąć ticket kliknij przycisk poniżej.\n\n"
                f"{'═' * 40}"
            ),
            color=kolory[kategoria],
            timestamp=datetime.datetime.now()
        )
        embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else interaction.user.default_avatar.url)
        embed.set_footer(text=f"{server_name} × Support")
        await kanal.send(embed=embed, view=ZamknijTicketView())


class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketDropdown())


class ZamknijTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Zamknij Ticket", style=discord.ButtonStyle.red, custom_id="close_btn")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        server_name = interaction.guild.name
        embed = discord.Embed(
            title=f"{server_name} × Ticket Zamknięty",
            description=(
                f"── Ticket został zamknięty przez {interaction.user.mention}\n"
                f"── Kanał zostanie usunięty za **5 sekund**...\n\n"
                f"*Dziękujemy za kontakt!*"
            ),
            color=discord.Color.red(),
            timestamp=datetime.datetime.now()
        )
        embed.set_footer(text=f"{server_name} × Support")
        await interaction.response.send_message(embed=embed)
        await asyncio.sleep(5)
        await interaction.channel.delete()


class GiveawayView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.uczestnicy = set()

    @discord.ui.button(label="🎉 Dołącz!", style=discord.ButtonStyle.green, custom_id="gw_btn")
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user in self.uczestnicy:
            return await interaction.response.send_message("⚠️ Już bierzesz udział!", ephemeral=True)
        self.uczestnicy.add(interaction.user)
        await interaction.response.send_message(f"✅ Dołączyłeś! Uczestników: {len(self.uczestnicy)}", ephemeral=True)


# ============================================
#              KLASA BOTA
# ============================================

class AtlasBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        self.add_view(WeryfikacjaView())
        self.add_view(TicketView())
        self.add_view(ZamknijTicketView())
        await self.tree.sync()
        print("✅ Komendy zsynchronizowane!")

bot = AtlasBot()


# ============================================
#              EVENTY
# ============================================

@bot.event
async def on_ready():
    print(f"✅ Bot {bot.user} jest online!")
    print(f"📡 Serwery: {len(bot.guilds)}")
    print(f"📋 Komendy: {len(bot.tree.get_commands())}")
    print("=" * 40)
    await bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.watching, name="SOONCODE BEST SERWER")
    )

@bot.event
async def on_member_join(member):
    gid = str(member.guild.id)
    rid = cfg.get(gid, {}).get("autorola")
    if rid:
        rola = member.guild.get_role(rid)
        if rola:
            try:
                await member.add_roles(rola)
            except:
                pass
    cid = cfg.get(gid, {}).get("welcome_kanal")
    if cid:
        kanal = member.guild.get_channel(cid)
        if kanal:
            server_name = member.guild.name
            embed = discord.Embed(
                title=f"{server_name} × Witamy!",
                description=f"Cześć {member.mention}!\nWitamy na **{server_name}**!\nJesteś {member.guild.member_count}. członkiem!",
                color=discord.Color.gold()
            )
            if member.avatar:
                embed.set_thumbnail(url=member.avatar.url)
            embed.set_footer(text=f"{server_name}")
            await kanal.send(embed=embed)

@bot.event
async def on_member_remove(member):
    gid = str(member.guild.id)
    cid = cfg.get(gid, {}).get("welcome_kanal")
    if cid:
        kanal = member.guild.get_channel(cid)
        if kanal:
            await kanal.send(f"😢 **{member.name}** opuścił serwer...")


# ============================================
#           POMOC
# ============================================

@bot.tree.command(name="pomoc", description="Lista wszystkich komend")
async def pomoc(interaction: discord.Interaction):
    server_name = interaction.guild.name
    embed = discord.Embed(
        title=f"{server_name} × Lista Komend",
        description="Darmowy wielofunkcyjny bot!",
        color=discord.Color.blue()
    )
    embed.add_field(name="⚙️ Setup (Admin)", value=(
        "`/weryfikacja_panel` - Panel weryfikacji\n"
        "`/ticket_panel` - Panel ticketów\n"
        "`/ticket_supportrole` - Rola supportu\n"
        "`/autorole` - Auto rola\n"
        "`/welcomekanal` - Kanał powitalny"
    ), inline=False)
    embed.add_field(name="🛡️ Moderacja", value=(
        "`/ban` `/kick` `/warn` `/warny`\n"
        "`/czysc` `/mute` `/unmute`\n"
        "`/slowmode` `/lock` `/unlock`\n"
        "`/nick` `/oglos`"
    ), inline=False)
    embed.add_field(name="🎉 Giveaway", value="`/startgiveaway`", inline=False)
    embed.add_field(name="💰 Sklep", value="`/cennik`", inline=False)
    embed.add_field(name="📊 Info", value=(
        "`/ping` `/serwer` `/user`\n"
        "`/avatar` `/botinfo`"
    ), inline=False)
    embed.add_field(name="🎮 Zabawa", value=(
        "`/zabawa-iq` `/zabawa-8ball`\n"
        "`/zabawa-moneta` `/zabawa-kostka`\n"
        "`/zabawa-ship` `/zabawa-hack`\n"
        "`/zabawa-pp` `/zabawa-howgay`\n"
        "`/zabawa-fight` `/zabawa-slap`\n"
        "`/zabawa-rate` `/zabawa-rps`\n"
        "`/zabawa-przytul` `/zabawa-losuj`\n"
        "`/zabawa-komplement`"
    ), inline=False)
    embed.add_field(name="🔧 Narzędzia", value=(
        "`/say` `/embed` `/ankieta`"
    ), inline=False)
    embed.set_footer(text=f"{server_name} × Bot")
    await interaction.response.send_message(embed=embed)


# ============================================
#           SETUP
# ============================================

@bot.tree.command(name="weryfikacja_panel", description="Tworzy panel weryfikacji")
@app_commands.describe(rola="Rola po weryfikacji")
@app_commands.default_permissions(administrator=True)
async def weryfikacja_panel(interaction: discord.Interaction, rola: discord.Role):
    gid = str(interaction.guild.id)
    if gid not in cfg:
        cfg[gid] = {}
    cfg[gid]["rola_weryfikacja"] = rola.id
    zapisz(cfg)
    server_name = interaction.guild.name
    embed = discord.Embed(
        title=f"{server_name} × System Weryfikacji",
        description=(
            f"{'═' * 40}\n\n"
            f"👋 **Witaj na serwerze {server_name}!**\n\n"
            f"── Aby uzyskać dostęp do serwera, musisz się zweryfikować.\n"
            f"── Po pomyślnej weryfikacji otrzymasz dostęp do wszystkich kanałów.\n"
            f"── Weryfikując się akceptujesz regulamin serwera.\n\n"
            f"🔐 Kliknij przycisk poniżej aby kontynuować.\n\n"
            f"{'═' * 40}"
        ),
        color=discord.Color.dark_embed()
    )
    if interaction.guild.icon:
        embed.set_thumbnail(url=interaction.guild.icon.url)
    embed.set_footer(text=f"{server_name} × Weryfikacja")
    await interaction.channel.send(embed=embed, view=WeryfikacjaView())
    await interaction.response.send_message(f"✅ Panel gotowy! Rola: {rola.mention}", ephemeral=True)


@bot.tree.command(name="ticket_panel", description="Tworzy panel ticketów na tym kanale")
@app_commands.default_permissions(administrator=True)
async def ticket_panel(interaction: discord.Interaction):
    server_name = interaction.guild.name
    embed = discord.Embed(
        title=f"{server_name} × System Ticketów",
        description=(
            f"{'═' * 40}\n\n"
            f"📞 **Potrzebujesz pomocy?**\n\n"
            f"── Wybierz kategorię z menu poniżej.\n"
            f"── Zostanie utworzony prywatny kanał z administracją.\n"
            f"── Opisz dokładnie swoją sprawę.\n"
            f"── Administracja odpowie najszybciej jak to możliwe.\n\n"
            f"⚠️ *Tworzenie bezsensownych ticketów = ban*\n\n"
            f"{'═' * 40}"
        ),
        color=discord.Color.dark_embed()
    )
    if interaction.guild.icon:
        embed.set_thumbnail(url=interaction.guild.icon.url)
    embed.set_footer(text=f"{server_name} × Support")
    await interaction.channel.send(embed=embed, view=TicketView())
    await interaction.response.send_message("✅ Panel ticketów utworzony!", ephemeral=True)


@bot.tree.command(name="ticket_supportrole", description="Rola supportu")
@app_commands.describe(rola="Rola która widzi tickety")
@app_commands.default_permissions(administrator=True)
async def ticket_supportrole(interaction: discord.Interaction, rola: discord.Role):
    gid = str(interaction.guild.id)
    if gid not in cfg:
        cfg[gid] = {}
    cfg[gid]["rola_support"] = rola.id
    zapisz(cfg)
    await interaction.response.send_message(f"✅ Rola supportu: {rola.mention}", ephemeral=True)


@bot.tree.command(name="autorole", description="Auto rola dla nowych")
@app_commands.describe(rola="Rola do nadania")
@app_commands.default_permissions(administrator=True)
async def autorole(interaction: discord.Interaction, rola: discord.Role):
    gid = str(interaction.guild.id)
    if gid not in cfg:
        cfg[gid] = {}
    cfg[gid]["autorola"] = rola.id
    zapisz(cfg)
    await interaction.response.send_message(f"✅ Autorola: {rola.mention}", ephemeral=True)


@bot.tree.command(name="welcomekanal", description="Kanał powitalny")
@app_commands.describe(kanal="Kanał na powitania")
@app_commands.default_permissions(administrator=True)
async def welcomekanal(interaction: discord.Interaction, kanal: discord.TextChannel):
    gid = str(interaction.guild.id)
    if gid not in cfg:
        cfg[gid] = {}
    cfg[gid]["welcome_kanal"] = kanal.id
    zapisz(cfg)
    await interaction.response.send_message(f"✅ Kanał powitalny: {kanal.mention}", ephemeral=True)


# ============================================
#           MODERACJA
# ============================================

@bot.tree.command(name="ban", description="Banuje użytkownika")
@app_commands.describe(osoba="Kogo", powod="Powód")
@app_commands.default_permissions(ban_members=True)
async def ban(interaction: discord.Interaction, osoba: discord.Member, powod: str = "Brak powodu"):
    if osoba.top_role >= interaction.user.top_role:
        return await interaction.response.send_message("❌ Nie możesz zbanować kogoś z wyższą rolą!", ephemeral=True)
    embed = discord.Embed(title="🔨 BAN", color=discord.Color.red(), timestamp=datetime.datetime.now())
    embed.add_field(name="Osoba", value=osoba.mention)
    embed.add_field(name="Mod", value=interaction.user.mention)
    embed.add_field(name="Powód", value=powod, inline=False)
    await osoba.ban(reason=powod)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="kick", description="Wyrzuca użytkownika")
@app_commands.describe(osoba="Kogo", powod="Powód")
@app_commands.default_permissions(kick_members=True)
async def kick(interaction: discord.Interaction, osoba: discord.Member, powod: str = "Brak powodu"):
    if osoba.top_role >= interaction.user.top_role:
        return await interaction.response.send_message("❌ Nie możesz kicknąć kogoś z wyższą rolą!", ephemeral=True)
    embed = discord.Embed(title="👢 KICK", color=discord.Color.orange(), timestamp=datetime.datetime.now())
    embed.add_field(name="Osoba", value=osoba.mention)
    embed.add_field(name="Mod", value=interaction.user.mention)
    embed.add_field(name="Powód", value=powod, inline=False)
    await osoba.kick(reason=powod)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="warn", description="Ostrzeżenie")
@app_commands.describe(osoba="Kogo", powod="Powód")
@app_commands.default_permissions(kick_members=True)
async def warn(interaction: discord.Interaction, osoba: discord.Member, powod: str):
    if osoba.id not in warny_db:
        warny_db[osoba.id] = []
    warny_db[osoba.id].append({
        "powod": powod,
        "mod": interaction.user.name,
        "data": datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
    })
    embed = discord.Embed(title="⚠️ WARN", color=discord.Color.yellow(), timestamp=datetime.datetime.now())
    embed.add_field(name="Osoba", value=osoba.mention)
    embed.add_field(name="Mod", value=interaction.user.mention)
    embed.add_field(name="Powód", value=powod, inline=False)
    embed.set_footer(text=f"Warn #{len(warny_db[osoba.id])}")
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="warny", description="Lista warnów")
@app_commands.describe(osoba="Kogo sprawdzić")
@app_commands.default_permissions(kick_members=True)
async def warny(interaction: discord.Interaction, osoba: discord.Member):
    if osoba.id not in warny_db or not warny_db[osoba.id]:
        return await interaction.response.send_message(f"✅ **{osoba.name}** nie ma warnów!")
    embed = discord.Embed(title=f"⚠️ Warny: {osoba.name}", color=discord.Color.red())
    for i, w in enumerate(warny_db[osoba.id]):
        embed.add_field(name=f"#{i+1} | {w['data']}", value=f"Powód: {w['powod']}\nMod: {w['mod']}", inline=False)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="czysc", description="Usuwa wiadomości")
@app_commands.describe(ile="Ile (1-100)")
@app_commands.default_permissions(manage_messages=True)
async def czysc(interaction: discord.Interaction, ile: int):
    if ile < 1 or ile > 100:
        return await interaction.response.send_message("❌ Podaj 1-100!", ephemeral=True)
    await interaction.response.defer(ephemeral=True)
    usuniete = await interaction.channel.purge(limit=ile)
    await interaction.followup.send(f"🧹 Usunięto **{len(usuniete)}** wiadomości!", ephemeral=True)


@bot.tree.command(name="mute", description="Wycisza")
@app_commands.describe(osoba="Kogo", minuty="Na ile minut")
@app_commands.default_permissions(moderate_members=True)
async def mute(interaction: discord.Interaction, osoba: discord.Member, minuty: int = 10):
    await osoba.timeout(datetime.timedelta(minutes=minuty))
    embed = discord.Embed(title="🔇 MUTE", color=discord.Color.greyple())
    embed.add_field(name="Osoba", value=osoba.mention)
    embed.add_field(name="Czas", value=f"{minuty} min")
    embed.add_field(name="Mod", value=interaction.user.mention)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="unmute", description="Odmutowuje")
@app_commands.describe(osoba="Kogo")
@app_commands.default_permissions(moderate_members=True)
async def unmute(interaction: discord.Interaction, osoba: discord.Member):
    await osoba.timeout(None)
    await interaction.response.send_message(f"🔊 Odmutowano **{osoba.name}**!")


@bot.tree.command(name="slowmode", description="Slowmode")
@app_commands.describe(sekundy="Ile sekund (0=off)")
@app_commands.default_permissions(manage_channels=True)
async def slowmode(interaction: discord.Interaction, sekundy: int):
    await interaction.channel.edit(slowmode_delay=sekundy)
    if sekundy == 0:
        await interaction.response.send_message("✅ Slowmode wyłączony!")
    else:
        await interaction.response.send_message(f"🐌 Slowmode: **{sekundy}s**")


@bot.tree.command(name="lock", description="Blokuje kanał")
@app_commands.default_permissions(manage_channels=True)
async def lock(interaction: discord.Interaction):
    await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=False)
    await interaction.response.send_message("🔒 Kanał zablokowany!")


@bot.tree.command(name="unlock", description="Odblokowuje kanał")
@app_commands.default_permissions(manage_channels=True)
async def unlock(interaction: discord.Interaction):
    await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=True)
    await interaction.response.send_message("🔓 Kanał odblokowany!")


@bot.tree.command(name="nick", description="Zmienia nick")
@app_commands.describe(osoba="Komu", nick="Nowy nick")
@app_commands.default_permissions(manage_nicknames=True)
async def nick(interaction: discord.Interaction, osoba: discord.Member, nick: str):
    await osoba.edit(nick=nick)
    await interaction.response.send_message(f"✅ Nick zmieniony na **{nick}**!")


@bot.tree.command(name="oglos", description="Ogłoszenie")
@app_commands.describe(tekst="Treść")
@app_commands.default_permissions(administrator=True)
async def oglos(interaction: discord.Interaction, tekst: str):
    server_name = interaction.guild.name
    embed = discord.Embed(title=f"📢 {server_name} × Ogłoszenie", description=tekst, color=discord.Color.red(), timestamp=datetime.datetime.now())
    embed.set_footer(text=f"Nadawca: {interaction.user.name}")
    await interaction.channel.send(embed=embed)
    await interaction.response.send_message("✅ Wysłano!", ephemeral=True)


# ============================================
#           CENNIK
# ============================================

@bot.tree.command(name="cennik", description="Wyświetla cennik usług")
async def cennik(interaction: discord.Interaction):
    server_name = interaction.guild.name
    embed = discord.Embed(
        title=f"{server_name} × Cennik",
        color=discord.Color.dark_embed()
    )
    embed.add_field(
        name="📦 Zamówienia:",
        value=(
            f"{'─' * 35}\n"
            "─ Aby złożyć zamówienie udaj się na kanał ticket, a następnie\n"
            "─ utwórz ticketa i napisz co byś chciał zamówić.\n"
            f"{'─' * 35}"
        ),
        inline=False
    )
    embed.add_field(
        name="💰 Nasze Oferty:",
        value=(
            "```\n"
            "┌────────────────────────────────────┐\n"
            "│ Skrypty na zamówienie  │ 5zł/20 PSC│\n"
            "│ Pluginy na zamówienie  │ 5zł PSC   │\n"
            "│ Serwery Discord        │ 10zł/20PSC│\n"
            "│ Plugin BetterEssent.   │ 15zł/20PSC│\n"
            "│ Plugin anty cheat      │ 10zł/15PSC│\n"
            "│ Strefa Premium         │ 10zł/20PSC│\n"
            "│ Serwery MC             │ 20 PSC    │\n"
            "│ Bot Discord (Python)   │ 20 PSC    │\n"
            "└────────────────────────────────────┘\n"
            "```"
        ),
        inline=False
    )
    embed.add_field(
        name="⚠️ Ważne:",
        value=(
            "── Tworzenie bezsensownych ticketów = **ban**\n"
            "── Administracja odpowie najszybciej jak to możliwe\n"
            "── **Akceptujemy wyłącznie kody PSC!**"
        ),
        inline=False
    )
    if interaction.guild.icon:
        embed.set_thumbnail(url=interaction.guild.icon.url)
    embed.set_footer(text=f"{server_name} × Cennik")
    await interaction.response.send_message(embed=embed)


# ============================================
#           GIVEAWAY
# ============================================

@bot.tree.command(name="startgiveaway", description="Rozpoczyna giveaway")
@app_commands.describe(nagroda="Nagroda", czas="Czas w sekundach")
@app_commands.default_permissions(administrator=True)
async def startgiveaway(interaction: discord.Interaction, nagroda: str, czas: int):
    server_name = interaction.guild.name
    widok = GiveawayView()
    koniec = datetime.datetime.now() + datetime.timedelta(seconds=czas)
    embed = discord.Embed(
        title=f"🎉 {server_name} × Giveaway!",
        description=f"**Nagroda:** {nagroda}\n**Kończy się:** za {czas}s\n**Organizator:** {interaction.user.mention}\n\nKliknij 🎉 aby dołączyć!",
        color=discord.Color.gold(),
        timestamp=koniec
    )
    embed.set_footer(text=f"{server_name} × Giveaway")
    await interaction.response.send_message("✅ Giveaway rozpoczęty!", ephemeral=True)
    msg = await interaction.channel.send(embed=embed, view=widok)
    await asyncio.sleep(czas)
    if not widok.uczestnicy:
        embed.description = f"**Nagroda:** {nagroda}\n\n❌ Nikt nie dołączył!"
        embed.color = discord.Color.red()
    else:
        wygrany = random.choice(list(widok.uczestnicy))
        embed.description = f"**Nagroda:** {nagroda}\n\n🏆 Wygrał: {wygrany.mention}!"
        embed.color = discord.Color.green()
        await interaction.channel.send(f"🎊 Gratulacje {wygrany.mention}! Wygrywasz **{nagroda}**! 🎊")
    embed.title = f"🎉 {server_name} × Giveaway Zakończony"
    try:
        await msg.edit(embed=embed, view=None)
    except:
        pass


# ============================================
#           INFO
# ============================================

@bot.tree.command(name="ping", description="Ping bota")
async def ping(interaction: discord.Interaction):
    embed = discord.Embed(title="🏓 Pong!", color=discord.Color.green())
    embed.add_field(name="Opóźnienie", value=f"**{round(bot.latency * 1000)}ms**")
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="serwer", description="Info o serwerze")
async def serwer(interaction: discord.Interaction):
    g = interaction.guild
    embed = discord.Embed(title=f"📊 {g.name}", color=discord.Color.blue())
    embed.add_field(name="👑 Właściciel", value=g.owner.mention if g.owner else "?")
    embed.add_field(name="👥 Członkowie", value=g.member_count)
    embed.add_field(name="💬 Kanały", value=len(g.channels))
    embed.add_field(name="😀 Emotki", value=len(g.emojis))
    embed.add_field(name="🎭 Role", value=len(g.roles))
    embed.add_field(name="📅 Utworzono", value=g.created_at.strftime("%d.%m.%Y"))
    if g.icon:
        embed.set_thumbnail(url=g.icon.url)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="user", description="Info o użytkowniku")
@app_commands.describe(osoba="Kogo sprawdzić")
async def user(interaction: discord.Interaction, osoba: discord.Member = None):
    osoba = osoba or interaction.user
    embed = discord.Embed(title=f"👤 {osoba.name}", color=osoba.color)
    embed.add_field(name="📛 Nick", value=osoba.display_name)
    embed.add_field(name="🆔 ID", value=osoba.id)
    embed.add_field(name="📅 Konto", value=osoba.created_at.strftime("%d.%m.%Y"))
    embed.add_field(name="📥 Dołączył", value=osoba.joined_at.strftime("%d.%m.%Y"))
    embed.add_field(name="🎭 Rola", value=osoba.top_role.mention)
    embed.set_thumbnail(url=osoba.avatar.url if osoba.avatar else osoba.default_avatar.url)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="avatar", description="Avatar użytkownika")
@app_commands.describe(osoba="Czyj")
async def avatar(interaction: discord.Interaction, osoba: discord.Member = None):
    osoba = osoba or interaction.user
    url = osoba.avatar.url if osoba.avatar else osoba.default_avatar.url
    embed = discord.Embed(title=f"🖼️ {osoba.name}", color=osoba.color)
    embed.set_image(url=url)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="botinfo", description="Info o bocie")
async def botinfo(interaction: discord.Interaction):
    embed = discord.Embed(title="🤖 Atlas Bot", description="Darmowy wielofunkcyjny bot!", color=discord.Color.blue())
    embed.add_field(name="📡 Serwery", value=len(bot.guilds))
    embed.add_field(name="👥 Użytkownicy", value=len(bot.users))
    embed.add_field(name="📋 Komendy", value=len(bot.tree.get_commands()))
    embed.add_field(name="🏓 Ping", value=f"{round(bot.latency * 1000)}ms")
    embed.add_field(name="📦 discord.py", value=discord.__version__)
    await interaction.response.send_message(embed=embed)


# ============================================
#           ZABAWA
# ============================================

@bot.tree.command(name="zabawa-iq", description="Sprawdź IQ!")
@app_commands.describe(osoba="Czyje IQ")
async def zabawa_iq(interaction: discord.Interaction, osoba: discord.Member = None):
    osoba = osoba or interaction.user
    iq = random.randint(10, 175)
    if iq < 40: tekst = "💀 O nie..."
    elif iq < 70: tekst = "😬 Słabo"
    elif iq < 90: tekst = "😅 Mogło być lepiej"
    elif iq < 110: tekst = "😊 Przeciętne"
    elif iq < 130: tekst = "🧠 Mądre!"
    elif iq < 150: tekst = "🧠✨ Geniusz!"
    else: tekst = "🧠👑 MEGA MÓZG!"
    pasek = "█" * (iq // 10) + "░" * (17 - iq // 10)
    embed = discord.Embed(title="🧠 Test IQ", color=discord.Color.magenta())
    embed.add_field(name="Osoba", value=osoba.mention, inline=False)
    embed.add_field(name=f"IQ: {iq}", value=f"`{pasek}` {tekst}", inline=False)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="zabawa-8ball", description="Magiczna kula")
@app_commands.describe(pytanie="Pytanie")
async def zabawa_8ball(interaction: discord.Interaction, pytanie: str):
    odpowiedzi = [
        "✅ Tak!", "✅ Zdecydowanie!", "✅ Na pewno!",
        "🤔 Raczej tak", "🤔 Możliwe...",
        "😐 Nie wiem", "😐 Zapytaj później",
        "❌ Nie", "❌ Na pewno nie!", "💀 Nawet nie pytaj"
    ]
    embed = discord.Embed(title="🔮 Magiczna Kula", color=discord.Color.purple())
    embed.add_field(name="❓ Pytanie", value=pytanie, inline=False)
    embed.add_field(name="🎱 Odpowiedź", value=random.choice(odpowiedzi), inline=False)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="zabawa-moneta", description="Rzuć monetą")
async def zabawa_moneta(interaction: discord.Interaction):
    await interaction.response.send_message(f"🪙 {random.choice(['🟡 **Orzeł!**', '⚪ **Reszka!**'])}")


@bot.tree.command(name="zabawa-kostka", description="Rzuć kostką")
async def zabawa_kostka(interaction: discord.Interaction):
    emotki = {1: "⚀", 2: "⚁", 3: "⚂", 4: "⚃", 5: "⚄", 6: "⚅"}
    wynik = random.randint(1, 6)
    await interaction.response.send_message(f"🎲 {emotki[wynik]} Wypadło: **{wynik}**!")


@bot.tree.command(name="zabawa-losuj", description="Losuj liczbę")
@app_commands.describe(min="Min", max="Max")
async def zabawa_losuj(interaction: discord.Interaction, min: int = 1, max: int = 100):
    await interaction.response.send_message(f"🎯 Wylosowano: **{random.randint(min, max)}** ({min}-{max})")


@bot.tree.command(name="zabawa-przytul", description="Przytul kogoś")
@app_commands.describe(kogo="Kogo")
async def zabawa_przytul(interaction: discord.Interaction, kogo: discord.Member):
    if kogo == interaction.user:
        return await interaction.response.send_message(f"🥺 {interaction.user.mention} przytula samego siebie...")
    await interaction.response.send_message(f"🤗 {interaction.user.mention} przytula {kogo.mention}! ❤️")


@bot.tree.command(name="zabawa-slap", description="Daj komuś liścia")
@app_commands.describe(kogo="Kogo")
async def zabawa_slap(interaction: discord.Interaction, kogo: discord.Member):
    teksty = [
        f"👋 {interaction.user.mention} daje z liścia {kogo.mention}!",
        f"🐟 {interaction.user.mention} wali {kogo.mention} rybą po twarzy!",
        f"💥 {interaction.user.mention} nokautuje {kogo.mention}!",
        f"🥊 {interaction.user.mention} daje sierpowego {kogo.mention}!",
        f"🍳 {interaction.user.mention} wali {kogo.mention} patelnią!",
    ]
    await interaction.response.send_message(random.choice(teksty))


@bot.tree.command(name="zabawa-ship", description="Sprawdź miłość")
@app_commands.describe(osoba1="Osoba 1", osoba2="Osoba 2")
async def zabawa_ship(interaction: discord.Interaction, osoba1: discord.Member, osoba2: discord.Member):
    procent = random.randint(0, 100)
    if procent < 20: tekst = "💔 Nie ma szans"
    elif procent < 40: tekst = "😕 Mało prawdopodobne"
    elif procent < 60: tekst = "😊 Jest potencjał!"
    elif procent < 80: tekst = "😍 Świetna para!"
    else: tekst = "💘 IDEALNA PARA!"
    pasek = "❤️" * (procent // 10) + "🖤" * (10 - procent // 10)
    embed = discord.Embed(title="💕 Ship", color=discord.Color.pink())
    embed.add_field(name="Para", value=f"{osoba1.mention} x {osoba2.mention}", inline=False)
    embed.add_field(name=f"{procent}%", value=f"{pasek}\n{tekst}", inline=False)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="zabawa-hack", description="Zhakuj kogoś (żart)")
@app_commands.describe(kogo="Kogo")
async def zabawa_hack(interaction: discord.Interaction, kogo: discord.Member):
    await interaction.response.send_message(f"💻 Hakowanie **{kogo.name}**... `[▓░░░░░░░░░] 5%`")
    msg = await interaction.original_response()
    etapy = [
        "`[▓▓▓░░░░░░░] 25%` Szukam IP...",
        "`[▓▓▓▓▓░░░░░] 50%` Kradnę hasła...",
        "`[▓▓▓▓▓▓▓░░░] 75%` Wchodzę do systemu...",
        "`[▓▓▓▓▓▓▓▓▓▓] 100%` ✅ ZHAKOWANO!",
    ]
    for tekst in etapy:
        await asyncio.sleep(1)
        await msg.edit(content=f"💻 Hakowanie **{kogo.name}**... {tekst}")
    hasla = ["zaq1@WSX", "kochamMame123", "password", "admin123", "qwerty"]
    embed = discord.Embed(title=f"💻 Zhakowano {kogo.name}", color=discord.Color.dark_green())
    embed.add_field(name="📧 Email", value=f"`{kogo.name.lower()}@gmail.com`")
    embed.add_field(name="🔑 Hasło", value=f"`{random.choice(hasla)}`")
    embed.add_field(name="📍 IP", value=f"`{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}`")
    embed.set_footer(text="To tylko żart!")
    await msg.edit(content=None, embed=embed)


@bot.tree.command(name="zabawa-pp", description="Sprawdź rozmiar pp")
@app_commands.describe(osoba="Kogo")
async def zabawa_pp(interaction: discord.Interaction, osoba: discord.Member = None):
    osoba = osoba or interaction.user
    d = random.randint(1, 30)
    pasek = "8" + "=" * d + "D"
    embed = discord.Embed(title="📏 PP Size", color=discord.Color.blue())
    embed.add_field(name=osoba.name, value=f"`{pasek}`\n**{d} cm**")
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="zabawa-howgay", description="Ile % gay")
@app_commands.describe(osoba="Kogo")
async def zabawa_howgay(interaction: discord.Interaction, osoba: discord.Member = None):
    osoba = osoba or interaction.user
    p = random.randint(0, 100)
    pasek = "🏳️‍🌈" * (p // 10) + "⬜" * (10 - p // 10)
    embed = discord.Embed(title="🏳️‍🌈 How Gay", color=discord.Color.magenta())
    embed.add_field(name=osoba.name, value=f"**{p}%** gay\n{pasek}")
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="zabawa-fight", description="Walka!")
@app_commands.describe(przeciwnik="Z kim")
async def zabawa_fight(interaction: discord.Interaction, przeciwnik: discord.Member):
    hp1 = 100
    hp2 = 100
    log = ""
    while hp1 > 0 and hp2 > 0:
        d1 = random.randint(10, 35)
        d2 = random.randint(10, 35)
        hp2 -= d1
        hp1 -= d2
        log += f"⚔️ {interaction.user.name} → **{d1}** dmg | {przeciwnik.name} [{max(0,hp2)} HP]\n"
        log += f"🗡️ {przeciwnik.name} → **{d2}** dmg | {interaction.user.name} [{max(0,hp1)} HP]\n\n"
    if hp1 > hp2:
        wynik = f"🏆 {interaction.user.mention} wygrywa!"
    elif hp2 > hp1:
        wynik = f"🏆 {przeciwnik.mention} wygrywa!"
    else:
        wynik = "🤝 Remis!"
    embed = discord.Embed(title=f"⚔️ {interaction.user.name} vs {przeciwnik.name}", description=log + wynik, color=discord.Color.red())
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="zabawa-rate", description="Oceń coś")
@app_commands.describe(co="Co ocenić")
async def zabawa_rate(interaction: discord.Interaction, co: str):
    ocena = random.randint(0, 10)
    gwiazdki = "⭐" * ocena + "☆" * (10 - ocena)
    await interaction.response.send_message(f"📊 **{co}**: {gwiazdki} **{ocena}/10**")


@bot.tree.command(name="zabawa-rps", description="Kamień papier nożyce")
@app_commands.describe(wybor="Twój wybór")
@app_commands.choices(wybor=[
    app_commands.Choice(name="🪨 Kamień", value="kamien"),
    app_commands.Choice(name="📄 Papier", value="papier"),
    app_commands.Choice(name="✂️ Nożyce", value="nozyce"),
])
async def zabawa_rps(interaction: discord.Interaction, wybor: str):
    bot_wybor = random.choice(["kamien", "papier", "nozyce"])
    emotki = {"kamien": "🪨", "papier": "📄", "nozyce": "✂️"}
    if wybor == bot_wybor:
        wynik = "🤝 Remis!"
    elif (wybor == "kamien" and bot_wybor == "nozyce") or \
         (wybor == "papier" and bot_wybor == "kamien") or \
         (wybor == "nozyce" and bot_wybor == "papier"):
        wynik = "🎉 Wygrałeś!"
    else:
        wynik = "😢 Przegrałeś!"
    await interaction.response.send_message(f"Ty: {emotki[wybor]} vs Bot: {emotki[bot_wybor]}\n\n**{wynik}**")


@bot.tree.command(name="zabawa-komplement", description="Daj komuś komplement!")
@app_commands.describe(osoba="Komu")
async def zabawa_komplement(interaction: discord.Interaction, osoba: discord.Member = None):
    osoba = osoba or interaction.user
    komplementy = [
        f"✨ {osoba.mention} jest niesamowitą osobą!",
        f"🌟 {osoba.mention} rozświetla każde pomieszczenie!",
        f"💎 {osoba.mention} jest jak diament - rzadki i cenny!",
        f"🔥 {osoba.mention} jest po prostu legendarny/a!",
        f"🌈 {osoba.mention} sprawia że świat jest lepszy!",
        f"👑 {osoba.mention} ma charakter króla/królowej!",
        f"🎯 {osoba.mention} jest perfekcyjny/a!",
        f"🦁 {osoba.mention} ma odwagę lwa i serce ze złota!",
        f"🧠 {osoba.mention} jest mądrzejszy/a niż myśli!",
        f"💪 {osoba.mention} jest silniejszy/a niż kiedykolwiek!",
        f"🌸 {osoba.mention} ma najpiękniejszy uśmiech!",
        f"🚀 {osoba.mention} osiągnie wszystko!",
        f"🤩 {osoba.mention} to ikona!",
        f"💫 {osoba.mention} jest gwiazdą serwera!",
        f"🎵 {osoba.mention} ma głos anioła!",
    ]
    embed = discord.Embed(title="💝 Komplement", description=random.choice(komplementy), color=discord.Color.pink())
    if osoba != interaction.user:
        embed.set_footer(text=f"Komplement od {interaction.user.name}")
    await interaction.response.send_message(embed=embed)


# ============================================
#           NARZĘDZIA
# ============================================

@bot.tree.command(name="say", description="Bot mówi")
@app_commands.describe(tekst="Co powiedzieć")
@app_commands.default_permissions(manage_messages=True)
async def say(interaction: discord.Interaction, tekst: str):
    await interaction.response.send_message("✅", ephemeral=True)
    await interaction.channel.send(tekst)


@bot.tree.command(name="embed", description="Tworzy embed")
@app_commands.describe(tytul="Tytuł", opis="Treść", kolor="red/blue/green/gold/purple")
@app_commands.default_permissions(manage_messages=True)
async def embed_cmd(interaction: discord.Interaction, tytul: str, opis: str, kolor: str = "blue"):
    kolory = {"red": discord.Color.red(), "blue": discord.Color.blue(), "green": discord.Color.green(), "gold": discord.Color.gold(), "purple": discord.Color.purple()}
    embed = discord.Embed(title=tytul, description=opis, color=kolory.get(kolor.lower(), discord.Color.blue()))
    embed.set_footer(text=f"Autor: {interaction.user.name}")
    await interaction.response.send_message("✅", ephemeral=True)
    await interaction.channel.send(embed=embed)


@bot.tree.command(name="ankieta", description="Tworzy ankietę")
@app_commands.describe(pytanie="Treść ankiety")
@app_commands.default_permissions(manage_messages=True)
async def ankieta(interaction: discord.Interaction, pytanie: str):
    server_name = interaction.guild.name
    embed = discord.Embed(title=f"📊 {server_name} × Ankieta", description=pytanie, color=discord.Color.blue())
    embed.set_footer(text=f"Od: {interaction.user.name}")
    await interaction.response.send_message("✅", ephemeral=True)
    msg = await interaction.channel.send(embed=embed)
    await msg.add_reaction("👍")
    await msg.add_reaction("👎")


# ============================================
#           OBSŁUGA BŁĘDÓW
# ============================================

@bot.tree.error
async def on_error(interaction: discord.Interaction, error):
    try:
        if isinstance(error, app_commands.errors.MissingPermissions):
            await interaction.response.send_message("❌ Brak uprawnień!", ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ Błąd: {str(error)[:200]}", ephemeral=True)
            print(f"BLAD: {error}")
    except:
        print(f"BLAD: {error}")


# ============================================
#              START
# ============================================
try:
    bot.run(TOKEN)
except Exception as e:
    print("\n" + "="*50)
    print("KRYTYCZNY BLAD BOTA!")
    print(e)
    print("="*50 + "\n")
    input("Wcisnij ENTER aby zamknac...")
