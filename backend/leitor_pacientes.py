import os
import pdfplumber
import pandas as pd
import json
import re

PASTA_ALVO = r"C:\Users\DELL\OneDrive\NII-Portal-Cloud\backend\pacientes"

def normalizar_especialidade(texto):
    texto = texto.upper().strip()
    if "CIRURG" in texto: return "CIRURGICO"
    if "CLINIC" in texto: return "CLINICO"
    if "OBST" in texto: return "OBSTETRICO"
    if "PEDIAT" in texto: return "PEDIATRICO"
    return None # Ignora cabeçalhos que não sejam esses 4

def extrair_dados_relatorio(caminho_pdf):
    dados_extraidos = []
    
    # Inicializa como None para garantir que só pegue dados após ler um cabeçalho válido
    especialidade_atual = None 
    
    with pdfplumber.open(caminho_pdf) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text: continue
                
            lines = text.split('\n')
            
            for line in lines:
                # 1. Identificar Cabeçalho de Especialidade (ex: "01 CIRURGICO")
                # Procura por 2 dígitos seguidos de letras maiúsculas
                match_header = re.match(r'^\s*\d{2}\s+([A-ZÇÃÕ]+)', line)
                if match_header:
                    possivel_espec = match_header.group(1)
                    espec_normalizada = normalizar_especialidade(possivel_espec)
                    if espec_normalizada:
                        especialidade_atual = espec_normalizada
                    continue

                # 2. Identificar linha de paciente (Sequência numérica longa no início)
                # Só processa se já tivermos identificado uma especialidade válida
                if especialidade_atual:
                    match_paciente = re.search(r'^(\d{10,})\s+\d+\s+(.+)', line)
                    if match_paciente:
                        guia = match_paciente.group(1)
                        resto = match_paciente.group(2)
                        
                        # Limpeza do nome (remove prontuário no final se houver)
                        nome_match = re.split(r'\s\d+', resto)
                        nome_paciente = nome_match[0].strip() if nome_match else resto.strip()
                        
                        paciente = {
                            "guia": guia,
                            "paciente": nome_paciente,
                            "especialidade": especialidade_atual,
                            "origem_arquivo": os.path.basename(caminho_pdf)
                        }
                        dados_extraidos.append(paciente)

    return dados_extraidos

def main():
    todos_pacientes = []
    print(f"--- INICIANDO EXTRAÇÃO DE PACIENTES ---")
    print(f"Pasta: {PASTA_ALVO}")

    if not os.path.exists(PASTA_ALVO):
        print(f"ERRO: Pasta não encontrada.")
        return

    for arquivo in os.listdir(PASTA_ALVO):
        if arquivo.lower().endswith(".pdf"):
            caminho = os.path.join(PASTA_ALVO, arquivo)
            print(f"Lendo: {arquivo}...")
            try:
                dados = extrair_dados_relatorio(caminho)
                todos_pacientes.extend(dados)
            except Exception as e:
                print(f"  [ERRO] {arquivo}: {e}")

    # Salva JSON
    caminho_json = os.path.join(PASTA_ALVO, "pacientes_processados.json")
    with open(caminho_json, 'w', encoding='utf-8') as f:
        json.dump(todos_pacientes, f, ensure_ascii=False, indent=4)
        
    print(f"\nCONCLUÍDO! {len(todos_pacientes)} pacientes extraídos.")
    print(f"Arquivo gerado: {caminho_json}")
    print("Agora rode o script 'enviar_supabase.py' para atualizar o banco.")

if __name__ == "__main__":
    main()