import os
import math
import pandas as pd
from supabase import create_client, Client

print("--- 🚀 UPLOAD CNES: TABELA NACIONAL DE ESTABELECIMENTOS ---")

# =========================================================
# CONFIGURAÇÕES
# =========================================================
SB_URL = "https://voweywtzoldwfhgkniup.supabase.co"
SB_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZvd2V5d3R6b2xkd2ZoZ2tuaXVwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjgxMDE1OTUsImV4cCI6MjA4MzY3NzU5NX0.aLtDv7A7_k41ag2CCQDb-PYcOE6UxJqhyl_g_PVtKl0"

try:
    supabase: Client = create_client(SB_URL, SB_KEY)
except Exception as e:
    print(f"❌ Erro ao conectar no Supabase: {e}"); exit()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Procure o arquivo com o nome exato que baixou
ARQUIVO_CSV = os.path.join(BASE_DIR, "bases_cnes_csv", "tbEstabelecimento.csv")

def subir_estabelecimentos():
    if not os.path.exists(ARQUIVO_CSV):
        print(f"❌ Arquivo '{ARQUIVO_CSV}' não encontrado.")
        print("💡 Baixe o arquivo 'tbEstabelecimento' do portal CNES e coloque na pasta 'bases_cnes_csv' com este nome exato.")
        return

    print(f"📂 Lendo o arquivo nacional {ARQUIVO_CSV}...")
    try:
        # A base nacional costuma vir separada por ponto e vírgula
        df = pd.read_csv(ARQUIVO_CSV, sep=';', encoding='latin-1', dtype=str, on_bad_lines='skip')
        
        # Filtra apenas o estado de Mato Grosso (Código IBGE = 51 ou UF = MT)
        # Primeiro, listamos as colunas para descobrir os nomes exatos
        colunas = [c.upper().replace('"', '').strip() for c in df.columns]
        df.columns = colunas
        df = df.fillna("")

        col_cnes = next((c for c in colunas if 'CO_CNES' in c or c == 'CNES'), None)
        col_fantasia = next((c for c in colunas if 'NO_FANTASIA' in c or 'FANTASIA' in c), None)
        col_razao = next((c for c in colunas if 'NO_RAZAO_SOCIAL' in c or 'RAZAO' in c or 'NOME' in c), None)
        col_estado = next((c for c in colunas if 'CO_ESTADO_GESTOR' in c or 'UF' in c), None)

        if not col_cnes:
            print("❌ Coluna CNES não encontrada no CSV Nacional.")
            return

        # Filtra o estado do MT (Código IBGE de MT é 51)
        if col_estado:
            df = df[(df[col_estado] == '51') | (df[col_estado].str.upper() == 'MT')]
            print(f"🔍 Filtrados {len(df)} estabelecimentos do estado do MT.")
        else:
            print("⚠️ Coluna de Estado não encontrada. Subindo hospitais do Brasil inteiro (vai demorar mais).")

        df = df[df[col_cnes].str.strip() != ""]
        df = df.drop_duplicates(subset=[col_cnes], keep='first')

        payload = []
        for _, row in df.iterrows():
            payload.append({
                "cnes": str(row[col_cnes]).replace('"', '').strip(),
                "nome_fantasia": str(row[col_fantasia]).replace('"', '').strip().upper() if col_fantasia else "",
                "razao_social": str(row[col_razao]).replace('"', '').strip().upper() if col_razao else "",
                "gestao": "" # Ignorado na base nacional para poupar tempo
            })
        
        tamanho_lote = 500
        total = len(payload)
        tabela_destino = "cnes_estabelecimentos"

        print(f"☁️ PREPARANDO PACOTES DE 500 PARA A TABELA '{tabela_destino}'...")

        for i in range(0, total, tamanho_lote):
            lote = payload[i : i + tamanho_lote]
            try:
                supabase.table(tabela_destino).upsert(lote).execute()
                print(f"   ⬆️ Lote enviado: {min(i + tamanho_lote, total)} de {total}...")
            except Exception as err:
                print(f"   ❌ Erro ao enviar lote: {err}")

        print("\n✅ TABELA DE ESTABELECIMENTOS SINCRONIZADA!")

    except Exception as e:
        print(f"❌ Erro grave ao ler o CSV Nacional: {e}")

if __name__ == "__main__":
    subir_estabelecimentos()