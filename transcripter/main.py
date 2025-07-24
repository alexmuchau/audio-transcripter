import os, tempfile, uuid
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
    print("Gravando áudio do sistema (BlackHole)... pressione Ctrl+C para pausar.")
    import subprocess, time
    audio = tempfile.mktemp(suffix=".wav")
    cmd = [
        'ffmpeg', '-f', 'avfoundation', '-i', ':1', '-ac', '1', '-ar', '48000', '-y', audio
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        proc.wait()
    except KeyboardInterrupt:
        print("\nGravação interrompida pelo usuário.")
        proc.terminate()
        proc.wait()
    try:
        time.sleep(0.2)
    except KeyboardInterrupt:
        pass
    return audio

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

def salvar_transcricao(origem, titulo, texto):
    db.insert({
        "origem": origem,
        "titulo": titulo,
        "texto": texto,
        "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

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
        
        # prompt = f"""\n\nContexto da transcrição:\n" + transcricao + "\n\n" + {pergunta}"""
        # memory_agent.print_response(pergunta, stream=True)
        response = memory_agent.run(pergunta, stream=True)
        for msg in response:
            print(msg.content, end="", flush=True)
        print("\n")
        # console.print(f"[bold blue]IA:[/bold blue] {resposta.content if hasattr(resposta, 'content') else resposta}")

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
        
        if escolha.startswith("1."):
            console.clear()
            fonte = questionary.select(
                "Escolha a fonte do áudio:",
                choices=["1. YouTube", "2. Microfone", "3. Tela", "4. Voltar"]).ask()
            
            if fonte.startswith("1."):
                url = questionary.text("URL do vídeo:").ask()
                audio, titulo = baixar_youtube(url)
                texto = transcrever(audio)
                salvar_transcricao("youtube", titulo, texto)
                os.remove(audio)

            elif fonte.startswith("2."):
                audio = gravar_audio("Gravando... Ctrl+C para pausar.")
                texto = transcrever(audio)
                nome = texto[:50] + "..." if len(texto) > 50 else texto
                salvar_transcricao("microfone", nome, texto)
                os.remove(audio)

            elif fonte.startswith("3."):
                audio = gravar_tela()
                texto = transcrever(audio)
                nome = texto[:50] + "..." if len(texto) > 50 else texto
                salvar_transcricao("tela", nome, texto)
                os.remove(audio)

            else:
                continue

        elif escolha.startswith("2."):
            analise_transcricoes()
        else:
            break


if __name__ == "__main__":
    main()