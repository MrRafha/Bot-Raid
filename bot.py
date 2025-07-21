import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from dotenv import load_dotenv
import Flask
from threading import Thread
from flask import Flask

load_dotenv()

with open('config.json') as f:
    config = json.load(f)

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
raid_temp_data = {}

# View personalizada com select
class RoleSelect(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=60)
        self.user_id = user_id

        options = [
            discord.SelectOption(label=role["nome"], value=key, emoji=role["emoji"])
            for key, role in config["roles"].items()
        ]

        self.select = discord.ui.Select(
            placeholder="Selecione as funções da raid",
            min_values=1,
            max_values=len(options),
            options=options,
        )
        self.select.callback = self.select_callback
        self.add_item(self.select)

    async def select_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Você não pode interagir com essa seleção.", ephemeral=True)
            return

        raid = raid_temp_data.pop(interaction.user.id, None)
        if not raid:
            await interaction.response.send_message("Erro: dados da raid não encontrados.", ephemeral=True)
            return

        embed = discord.Embed(
            title=raid["titulo"],
            color=discord.Color.blue()
        )
        embed.description = f"{raid['descricao']}\n\n📅 **Data:** {raid['data']}     ⏰ **Horário:** {raid['horario']}\n\n"

        selected_roles = self.select.values
        for role_id in selected_roles:
            role = config["roles"][role_id]
            embed.add_field(
                name=f"{role['emoji']} {role['nome']} (0)",
                value="(vazio)",
                inline=True
            )

        msg = await interaction.channel.send(embed=embed)

        for role_id in selected_roles:
            await msg.add_reaction(config["roles"][role_id]["emoji"])

        try:
            if not interaction.response.is_done():
                await interaction.response.edit_message(content="Raid criada com sucesso!", view=None)
            else:
                await interaction.followup.send("Raid criada com sucesso!", ephemeral=True)
        except discord.NotFound:
            print("[Erro] Interação já expirou.")
        except discord.HTTPException as e:
            print(f"[Erro HTTP] ao tentar enviar/editar mensagem: {e}")

@bot.event
async def on_ready():
    try:
        await bot.tree.sync()
        print(f"✅ Comandos slash sincronizados globalmente como {bot.user}")
    except Exception as e:
        print(f"❌ Erro ao sincronizar comandos globais: {e}")

@bot.tree.command(name="criar_raid", description="Cria uma raid no Albion")
@app_commands.describe(titulo="Título da raid", descricao="Descrição da raid", data="Data", horario="Horário")
async def criar_raid(interaction: discord.Interaction, titulo: str, descricao: str, data: str, horario: str):
    cargo_permitido = discord.utils.get(interaction.guild.roles, name=config["permissao_criar_raid"])
    if not cargo_permitido or cargo_permitido not in interaction.user.roles:
        await interaction.response.send_message(
            "❌ Você não tem permissão para criar raids. Apenas membros com o cargo **Raid Maker** podem usar este comando.",
            ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=True)  # ✅ só defer se ainda não respondeu

    raid_temp_data[interaction.user.id] = {
        "titulo": titulo,
        "descricao": descricao,
        "data": data,
        "horario": horario
    }

    view = RoleSelect(user_id=interaction.user.id)
    await interaction.followup.send("Selecione as funções desejadas:", view=view, ephemeral=True)

# Reagir adiciona nome
@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    if payload.user_id == bot.user.id:
        return

    channel = bot.get_channel(payload.channel_id)
    if not channel:
        return

    try:
        message = await channel.fetch_message(payload.message_id)
        user = payload.member
        if not user:
            guild = bot.get_guild(payload.guild_id)
            user = await guild.fetch_member(payload.user_id)
    except Exception as e:
        print(f"[Erro ao buscar mensagem ou membro] {e}")
        return

    embed = message.embeds[0] if message.embeds else None
    if not embed or len(embed.fields) == 0:
        return

    emoji = str(payload.emoji)
    for i, field in enumerate(embed.fields):
        for role_id, role in config["roles"].items():
            if role["emoji"] in field.name and role["emoji"] == emoji:
                nome = f"{user.display_name}"
                linhas = [line.strip() for line in field.value.splitlines() if line.strip() and line.strip() != "(vazio)"]
                if nome in linhas:
                    return
                linhas.append(nome)
                linhas_ordenadas = [f"{idx+1} {n}" for idx, n in enumerate(linhas)]
                new_value = "\n".join(linhas_ordenadas)
                new_name = f"{role['emoji']} {role['nome']} ({len(linhas)})"
                embed.set_field_at(i, name=new_name, value=new_value)
                await message.edit(embed=embed)
                return

# Remover reação tira nome
@bot.event
async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent):
    if payload.user_id == bot.user.id:
        return

    channel = bot.get_channel(payload.channel_id)
    if not channel:
        return

    try:
        message = await channel.fetch_message(payload.message_id)
        guild = bot.get_guild(payload.guild_id)
        user = await guild.fetch_member(payload.user_id)
    except Exception as e:
        print(f"[Erro ao buscar mensagem ou membro] {e}")
        return

    embed = message.embeds[0] if message.embeds else None
    if not embed or len(embed.fields) == 0:
        return

    emoji = str(payload.emoji)
    for i, field in enumerate(embed.fields):
        for role_id, role in config["roles"].items():
            if role["emoji"] in field.name and role["emoji"] == emoji:
                nome = f"{user.display_name}"
                linhas = [line.strip() for line in field.value.splitlines() if line.strip() and line.strip() != "(vazio)"]
                novas_linhas = [l for l in linhas if nome not in l]
                if not novas_linhas:
                    new_value = "(vazio)"
                else:
                    new_value = "\n".join([f"{idx+1} {n.split(' ', 1)[1]}" for idx, n in enumerate(novas_linhas)])
                new_name = f"{role['emoji']} {role['nome']} ({len(novas_linhas)})"
                embed.set_field_at(i, name=new_name, value=new_value)
                await message.edit(embed=embed)
                return

bot.run(os.getenv("DISCORD_BOT_TOKEN"))
app = Flask('')

@app.route('/')
def home():
    return "Bot está online!"

def run_web():
    app.run(host='0.0.0.0', port=8080)

# Inicia a thread do Flask
Thread(target=run_web).start()
