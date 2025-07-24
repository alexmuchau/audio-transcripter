# transcripter

Transcripter é um sistema de terminal completo para transcrição e análise de áudios e vídeos. Com ele, você pode:
- Gravar e transcrever áudio do microfone
- Gravar e transcrever o áudio do sistema (reuniões, vídeos, etc.)
- Baixar e transcrever o áudio de vídeos do YouTube
- Consultar e gerenciar um histórico de transcrições
- Analisar qualquer transcrição com IA conversacional (chat com contexto)
- Deletar transcrições específicas
Tudo isso em uma interface interativa e amigável no terminal.

---

![Demonstração do sistema](media/transcripter.gif)

---

## Instalação

### 1. Clone o projeto e entre na pasta
```bash
git clone https://github.com/rtadewald/transcripter.git
cd transcripter
```

### 2. Instale as dependências com [uv](https://github.com/astral-sh/uv)
```bash
uv venv
source .venv/bin/activate  # ou .venv\Scripts\activate no Windows
uv pip install -e .
```

### 3. Instale o ffmpeg
- **macOS:**
  ```bash
  brew install ffmpeg
  ```
- **Windows:**
  Baixe em https://ffmpeg.org/download.html e adicione o binário ao PATH.

### 4. Instale o BlackHole (para capturar áudio do sistema)
- **macOS:**
  1. Baixe em https://existential.audio/blackhole/
  2. Instale e crie um Multi-Output Device no Utilitário de Áudio MIDI, incluindo BlackHole e seus alto-falantes/fones.
  3. Defina o Multi-Output Device como saída padrão do sistema.
- **Windows:**
  Use [VB-Cable](https://vb-audio.com/Cable/) ou [VoiceMeeter](https://vb-audio.com/Voicemeeter/) para criar um dispositivo de áudio virtual e roteie o áudio do sistema para ele.

### 5. Crie o arquivo `.env` com suas chaves de API
Crie um arquivo chamado `.env` na raiz do projeto com o seguinte conteúdo:
```
GROQ_API_KEY=coloque_sua_chave_groq_aqui
OPENAI_API_KEY=coloque_sua_chave_openai_aqui
```
- `GROQ_API_KEY`: Necessária para transcrição com Whisper (Groq)
- `OPENAI_API_KEY`: Necessária para análise com IA (agente conversacional)

### 6. Outras dependências
- Python 3.8+

---

## Como rodar

Ative o ambiente virtual e execute:
```bash
uv run transcripter/main.py
```

Siga o menu interativo para gravar, transcrever, analisar e gerenciar suas transcrições.

---

## Observações
- Para transcrever áudio do sistema (reuniões, vídeos, etc.), é necessário configurar corretamente o dispositivo virtual (BlackHole no macOS, VB-Cable/VoiceMeeter no Windows).
- O sistema salva o histórico em `transcricoes.json` na raiz do projeto.
- Para usar a análise com IA, configure corretamente o agente no código e sua chave de API.
