import os, tempfile, uuid, platform, subprocess, time
from datetime import datetime
from tinydb import TinyDB
from groq import Groq
import sounddevice as sd
import soundfile as sf
from pytubefix import YouTube
import numpy as np

import questionary
from rich.console import Console
from rich.table import Table

from agno.agent import Agent
from agno.models.openai import OpenAIChat

from dotenv import load_dotenv
load_dotenv()

db = TinyDB("transcricoes.json")
client = Groq()
console = Console()



def baixar_youtube(url):
    yt = YouTube(url)
    f = f"{uuid.uuid4()}.wav"
    yt.streams.filter(only_audio=True).first().download(filename=f)
    return f, yt.title

def gravar_audio(msg):
    print(msg)
    grava = []
    try:
        with sd.InputStream(samplerate=48000, channels=1) as s:
            while True: 
                grava.append(s.read(1024)[0])
    except KeyboardInterrupt:
        print("\nGravação interrompida.")

    f = tempfile.mktemp(suffix=".wav")
    if grava: 
        sf.write(f, np.vstack(grava), 48000)
    return f

def gravar_tela():
    """
    Grava o áudio do sistema.
    Esta função agora detecta o sistema operacional e usa o método apropriado
    para capturar o áudio de saída do sistema (desktop).
    """
    system = platform.system()
    audio_temp_file = tempfile.mktemp(suffix=".wav")
    cmd = []

    if system == "Darwin":
        print("Gravando áudio do sistema (macOS / BlackHole)... Pressione Ctrl+C para pausar.")
        # Comando para macOS usando AVFoundation, assumindo que BlackHole é o dispositivo de entrada :1
        cmd = [
            'ffmpeg', '-f', 'avfoundation', '-i', ':1', '-ac', '1', 
            '-ar', '48000', '-y', audio_temp_file
        ]
    elif system == "Linux":
        print("Gravando áudio do sistema (Linux / PulseAudio)... Pressione Ctrl+C para pausar.")
        monitor_source = None
        try:
            # Tenta encontrar a fonte de monitor da saída de áudio padrão dinamicamente
            default_sink = subprocess.check_output(["pactl", "get-default-sink"], text=True).strip()
            monitor_source = f"{default_sink}.monitor"
            console.print(f"[green]Dispositivo de áudio detectado:[/green] {monitor_source}")
        except (FileNotFoundError, subprocess.CalledProcessError) as e:
            console.print("[yellow]Aviso: Não foi possível detectar o dispositivo de áudio padrão com 'pactl'.[/yellow]")
            console.print("[yellow]Certifique-se de que 'pulseaudio-utils' está instalado (`sudo apt install pulseaudio-utils`).[/yellow]")
            console.print("[yellow]Tentando usar 'default.monitor' como fallback...[/yellow]")
            # Se `pactl` falhar, podemos tentar um nome genérico, embora menos confiável.
            monitor_source = "default.monitor" 

        cmd = [
            'ffmpeg', '-f', 'pulse', '-i', monitor_source, '-ac', '1', 
            '-ar', '48000', '-y', audio_temp_file
        ]
    else:
        console.print(f"[bold red]ERRO: A gravação de tela não é suportada neste sistema operacional ({system}).[/bold red]")
        return None

    # O processo de execução do ffmpeg é o mesmo para ambos os sistemas
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        # Espera o processo do ffmpeg terminar. O usuário interrompe com Ctrl+C.
        proc.wait()
    except KeyboardInterrupt:
        print("\nGravação interrompida pelo usuário.")
        proc.terminate() # Envia o sinal de término para o ffmpeg
        
        # Espera um pouco para garantir que o processo realmente terminou e liberou o arquivo
        try:
            proc.wait(timeout=1)
        except subprocess.TimeoutExpired:
            proc.kill() # Força o encerramento se não terminar a tempo

    # Pequena pausa para garantir que o arquivo foi completamente escrito no disco
    time.sleep(0.5) 
    
    # Verifica se o arquivo foi criado e não está vazio
    if os.path.exists(audio_temp_file) and os.path.getsize(audio_temp_file) > 0:
        return audio_temp_file
    else:
        console.print("[bold red]Falha na gravação. O arquivo de áudio não foi criado ou está vazio.[/bold red]")
        return None

def transcrever(audio_path):
    print("Enviando áudio para transcrição, aguarde...")
    try:
        with open(audio_path, "rb") as file:
            transcription = client.audio.transcriptions.create(
                file=(audio_path, file.read()),
                model="whisper-large-v3-turbo",
                response_format="verbose_json",
                timestamp_granularities=["word"],
            )
            texto = transcription.text
            print("\n[Transcrição]")
            console.rule("Transcrição")
            console.print(texto)
            input("\nPressione ENTER para continuar...")
            return texto
    except KeyboardInterrupt:
        print("\nTranscrição interrompida pelo usuário.")
        return ""
    except Exception as e:
        console.print(f"[bold red]Ocorreu um erro durante a transcrição: {e}[/bold red]")
        return ""

def salvar_transcricao(origem, titulo, texto):
    if not texto:
        console.print("[yellow]Nenhum texto para salvar.[/yellow]")
        return
    db.insert({
        "origem": origem,
        "titulo": titulo,
        "texto": texto,
        "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    console.print("[green]Transcrição salva com sucesso![/green]")

def ver_historico():
    table = Table(title="Histórico de Transcrições")
    table.add_column("Nº", style="bold yellow")
    table.add_column("Data", style="cyan")
    table.add_column("Origem", style="magenta")
    table.add_column("Título/Nome", style="green")
    table.add_column("Trecho", style="white")
    transcricoes = db.all()
    
    for i, item in enumerate(transcricoes):
        trecho = (item["texto"][:40] + "...") if len(item["texto"]) > 40 else item["texto"]
        table.add_row(str(i+1), item.get("data", ""), item.get("origem", ""), item.get("titulo", ""), trecho)
    console.print(table)

    if transcricoes:
        idx = questionary.text("Digite o número da transcrição para ver completa (ou ENTER para sair):").ask()
        if idx and idx.isdigit() and 1 <= int(idx) <= len(transcricoes):
            item = transcricoes[int(idx)-1]
            console.rule(item.get("titulo", ""))
            console.print(item["texto"])

def chat_ia(transcricao):
    console.clear()
    console.print("""[bold green]Iniciando análise com IA. 
                  Digite sua pergunta sobre a transcrição. 
                  Digite 'sair' para encerrar a conversa.[/bold green]""")
    console.rule("Transcrição Selecionada")
    console.print(transcricao)

    memory_agent = Agent(
        model=OpenAIChat(id="gpt-4.1"),
        add_history_to_messages=True,
        num_history_runs=3,
        markdown=True,
        instructions=f"""
        Você é um assistente de análise de transcrições de vídeos.
        O usuário lhe fornecerá uma transcrição de um vídeo/áudio e você deve analisá-la e
        responder as perguntas do usuário.

        Transcrição: 
        {transcricao}
        """
    )

    while True:
        pergunta = questionary.text("Você:").ask()
        
        if not pergunta:
            continue
        
        if pergunta.strip().lower() == "sair":
            console.print("\n[bold red]Conversa encerrada.[/bold red]")
            input("Pressione ENTER para voltar.")
            break
        
        response = memory_agent.run(pergunta, stream=True)
        for msg in response:
            print(msg.content, end="", flush=True)
        print("\n")

def analise_transcricoes():
    while True:
        console.clear()
        transcricoes = db.all()
        if not transcricoes:
            console.print("[yellow]Nenhuma transcrição encontrada.[/yellow]")
            input("Pressione ENTER para voltar.")
            return
        # Mostra tabela
        table = Table(title="Histórico de Transcrições")
        table.add_column("Nº", style="bold yellow")
        table.add_column("Data", style="cyan")
        table.add_column("Origem", style="magenta")
        table.add_column("Título/Nome", style="green")
        table.add_column("Trecho", style="white")
        for i, item in enumerate(transcricoes):
            trecho = (item["texto"][:40] + "...") if len(item["texto"]) > 40 else item["texto"]
            table.add_row(str(i+1), item.get("data", ""), item.get("origem", ""), item.get("titulo", ""), trecho)
        console.print(table)
        acao = questionary.select(
            "O que deseja fazer?",
            choices=[
                "1. Análise com IA",
                "2. Acessar transcrição",
                "3. Deletar transcrição",
                "4. Voltar"
            ]).ask()
        if acao.startswith("4."):
            break
        idx = questionary.text("Digite o número da transcrição:").ask()
        if not idx or not idx.isdigit() or not (1 <= int(idx) <= len(transcricoes)):
            console.print("[red]Número inválido![/red]")
            continue
        item = transcricoes[int(idx)-1]
        if acao.startswith("1."):
            chat_ia(item["texto"])
        elif acao.startswith("2."):
            console.clear()
            console.rule(item.get("titulo", ""))
            console.print(item["texto"])
            input("Pressione ENTER para voltar.")
        elif acao.startswith("3."):
            db.remove(doc_ids=[item.doc_id])
            console.print("[red]Transcrição deletada![/red]")
            input("Pressione ENTER para voltar.")


def main():
    
    while True:
        console.clear()
        escolha = questionary.select(
            "O que deseja fazer?",
            choices=[
                "1. Nova gravação",
                "2. Análise de transcrições",
                "3. Sair"
            ]).ask()
        
        audio, texto, titulo, nome, origem = (None, "", "", "", "")

        if escolha.startswith("1."):
            console.clear()
            fonte = questionary.select(
                "Escolha a fonte do áudio:",
                choices=["1. YouTube", "2. Microfone", "3. Tela", "4. Voltar"]).ask()
            
            if fonte.startswith("1."):
                url = questionary.text("URL do vídeo:").ask()
                audio, titulo = baixar_youtube(url)
                origem = "youtube"

            elif fonte.startswith("2."):
                audio = gravar_audio("Gravando do microfone... Pressione Ctrl+C para pausar.")
                origem = "microfone"

            elif fonte.startswith("3."):
                audio = gravar_tela()
                origem = "tela"

            else:
                continue

            # Processamento unificado após a captura do áudio
            if audio:
                texto = transcrever(audio)
                if texto:
                    if origem in ["microfone", "tela"]:
                        nome = texto[:50] + "..." if len(texto) > 50 else texto
                        salvar_transcricao(origem, nome, texto)
                    elif origem == "youtube":
                        salvar_transcricao(origem, titulo, texto)
                
                # Limpa o arquivo de áudio temporário
                os.remove(audio)
            else:
                console.print("[yellow]Nenhum áudio foi gravado para processar.[/yellow]")
                input("Pressione ENTER para continuar...")


        elif escolha.startswith("2."):
            analise_transcricoes()
        else:
            break


if __name__ == "__main__":
    main()