import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from dotenv import load_dotenv
from threading import Thread
from flask import Flask

load_dotenv()

with open('config.json', encoding='utf-8') as f:
    config = json.load(f)

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
raid_temp_data = {}

class RoleSelect(discord.ui.View):
    def __init__(self, user_id, tipo):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.tipo = tipo
        self.selected_roles = set()

        all_groups = config["roles"][tipo]

        for group_name, group_roles in all_groups.items():
            options = []
            for key, role in group_roles.items():
                try:
                    emoji = discord.PartialEmoji.from_str(role["emoji"])
                    options.append(discord.SelectOption(label=role["nome"], value=key, emoji=emoji))
                except Exception as e:
                    print(f"[ERRO] Emoji inválido para '{role['nome']}': {role['emoji']} - {e}")

            select = discord.ui.Select(
                placeholder=f"Selecione funções - {group_name}",
                min_values=0,
                max_values=min(25, len(options)),
                options=options,
                custom_id=group_name
            )
            select.callback = self.select_callback
            self.add_item(select)


        confirm_button = discord.ui.Button(label="Confirmar Seleção", style=discord.ButtonStyle.green)
        confirm_button.callback = self.confirm_callback
        self.add_item(confirm_button)

    async def select_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Você não pode interagir com essa seleção.", ephemeral=True)
            return

        values = interaction.data["values"]
        for v in values:
            self.selected_roles.add(v)

        await interaction.response.send_message(f"Funções selecionadas até agora: {', '.join(self.selected_roles)}", ephemeral=True)

    async def confirm_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Você não pode confirmar a seleção de outro usuário.", ephemeral=True)
            return

        if not self.selected_roles:
            await interaction.response.send_message("Selecione ao menos uma função antes de confirmar.", ephemeral=True)
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

        for role_id in self.selected_roles:
            for group in config["roles"][self.tipo].values():
                if role_id in group:
                    role = group[role_id]
                    embed.add_field(
                        name=f"{role['emoji']} {role['nome']} (0)",
                        value="(vazio)",
                        inline=True
                    )

        msg = await interaction.channel.send(embed=embed)

        for role_id in self.selected_roles:
            for group in config["roles"][self.tipo].values():
                if role_id in group:
                    await msg.add_reaction(group[role_id]["emoji"])

        await interaction.response.edit_message(content="Raid criada com sucesso!", view=None)

@bot.event
async def on_ready():
    try:
        await bot.tree.sync()
        print(f"✅ Comandos slash sincronizados globalmente como {bot.user}")

        atividade = discord.Activity(type=discord.ActivityType.watching, name="as formações da próxima raid ⚔️")
        await bot.change_presence(status=discord.Status.online, activity=atividade)

    except Exception as e:
        print(f"❌ Erro ao sincronizar comandos globais: {e}")

@bot.tree.command(name="criar_raid", description="Cria uma raid PvP ou PvE")
@app_commands.describe(
    tipo="Tipo de conteúdo: pvp ou pve",
    titulo="Título da raid",
    descricao="Descrição da raid",
    data="Data",
    horario="Horário"
)
async def criar_raid(interaction: discord.Interaction, tipo: str, titulo: str, descricao: str, data: str, horario: str):
    tipo = tipo.lower()
    if tipo not in ["pvp", "pve"]:
        await interaction.response.send_message("❌ Tipo inválido. Escolha entre `pvp` ou `pve`.", ephemeral=True)
        return

    cargo_permitido = discord.utils.get(interaction.guild.roles, name=config.get("permissao_criar_raid", "Raid Maker"))
    if not cargo_permitido or cargo_permitido not in interaction.user.roles:
        await interaction.response.send_message(
            "❌ Você não tem permissão para criar raids. Apenas membros com o cargo **Raid Maker** podem usar este comando.",
            ephemeral=True
        )
        return

    if not interaction.response.is_done():
        await interaction.response.defer(ephemeral=True)

    raid_temp_data[interaction.user.id] = {
        "titulo": titulo,
        "descricao": descricao,
        "data": data,
        "horario": horario,
        "tipo": tipo
    }

    view = RoleSelect(user_id=interaction.user.id, tipo=tipo)
    await interaction.followup.send("Selecione as funções desejadas:", view=view, ephemeral=True)

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
        for role_group in config["roles"].values():
            for subgroup in role_group.values():
                for role_id, role in subgroup.items():
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
        for role_group in config["roles"].values():
            for subgroup in role_group.values():
                for role_id, role in subgroup.items():
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
                    
app = Flask('')

@app.route('/')
def home():
    return "Bot está online!"

def run_web():
    app.run(host='0.0.0.0', port=8080)

# Inicia a thread do Flask
Thread(target=run_web).start()
bot.run(os.getenv("DISCORD_BOT_TOKEN"))
