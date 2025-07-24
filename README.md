# transcripter

Transcripter é um sistema de terminal para transcrição e análise de áudios de reuniões, vídeos do YouTube, microfone e áudio do sistema. Ele permite transcrever, consultar, analisar com IA e gerenciar um histórico de transcrições de forma simples e interativa.

---

![Demonstração do sistema](coloque_seu_gif_aqui.gif)

---

## Instalação

### 1. Clone o projeto e entre na pasta
```bash
git clone https://github.com/seuusuario/transcripter.git
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

### 5. Outras dependências
- Python 3.8+
- API Key do Groq (adicione no seu .env como `GROQ_API_KEY=...`)

---

## Como rodar

Ative o ambiente virtual e execute:
```bash
transcripter
```

Siga o menu interativo para gravar, transcrever, analisar e gerenciar suas transcrições.

---

## Observações
- Para transcrever áudio do sistema (reuniões, vídeos, etc.), é necessário configurar corretamente o dispositivo virtual (BlackHole no macOS, VB-Cable/VoiceMeeter no Windows).
- O sistema salva o histórico em `transcricoes.json` na raiz do projeto.
- Para usar a análise com IA, configure corretamente o agente no código e sua chave de API.
