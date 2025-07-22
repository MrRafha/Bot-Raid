
## 📜 Bot de Raids para Discord – Albion Online

Um bot personalizado para organizar raids com **funções, emojis e participações dinâmicas via reações**, ideal para guildas de Albion Online.

---

### 🚀 Funcionalidades

* Comando `/criar_raid` com modal de título, descrição, data e horário
* Escolha de funções com emojis via menu interativo
* Mensagem embed com cada função separada, numerada com os participantes
* Participação via reações automáticas
* Nome do participante aparece ao reagir e é removido ao tirar a reação
* Apenas membros com o cargo `Raid Maker` podem criar raids

---

### 📦 Requisitos

* Python 3.10+
* `discord.py` v2.3+
* `python-dotenv` (opcional para testes locais)

---

### 🛠️ Instalação Local

```bash
git clone https://github.com/MrRafha/Bot-Raid
cd seu-repositorio
pip install -r requirements.txt
```

---

### 🔐 Configuração

#### 1. `.env`

Crie um arquivo `.env` com:

```
DISCORD_BOT_TOKEN=seu_token_aqui
```

Ou configure diretamente no Render como variável de ambiente.

#### 2. `config.json`

Crie um arquivo `config.json` com:

```json
{
  "guild_id": 1234567890,
  "permissao_criar_raid": "Raid Maker",
  "roles": {
    "MainTank": { "emoji": "<:MainTank:ID>", "nome": "Main Tank" },
    "MainHeal": { "emoji": "<:MainHeal:ID>", "nome": "Main Heal" }
    // etc.
  }
}
```

⚠️ **Importante:** o bot precisa estar no servidor que contém os emojis usados, e ter permissão para usar emojis externos (`Use External Emojis`).

---

### 🧪 Rodando localmente

```bash
python bot.py
```

---

### ☁️ Hospedagem com Render

1. Suba este projeto no GitHub
2. Crie um Web Service em [https://render.com](https://render.com)
3. Configure as seguintes variáveis no painel:

   * `DISCORD_BOT_TOKEN = seu_token_real`
4. Comando de inicialização:

   ```
   python bot.py
   ```

---

### ✅ Permissões recomendadas

Ao adicionar o bot, use esta URL:

```
https://discord.com/oauth2/authorize?client_id=1395897383229067285&permissions=139855226960&integration_type=0&scope=bot+applications.commands
```

Essa URL permite:

* Usar comandos (`/criar_raid`)
* Usar emojis externos
* Enviar mensagens, reações e embeds

---

### 📄 Licença

Este projeto é de uso pessoal para servidores do Discord. Caso queira utiliza-lo em seu servidor entre em contato comigo! discord: mrrafha.

---
