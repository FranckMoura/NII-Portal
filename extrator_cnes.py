import requests
import pandas as pd
import os
import urllib3
import time
import json

# --- CONFIGURAÇÕES INICIAIS ---
CNES_CURTO = "2311682"
CNES_LONGO = "5103402311682" 
NOME_HOSPITAL = "Hospital Beneficente Santa Helena"
BASE_URL = "https://cnes.datasus.gov.br/services/estabelecimentos"
PASTA_DESTINO = "arquivos"

# Desabilita avisos de SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Garante que a pasta existe
if not os.path.exists(PASTA_DESTINO):
    os.makedirs(PASTA_DESTINO)

print(f"🏥 --- EXTRATOR CNES NII (V4 - DIAGNÓSTICO) ---")
print(f"Alvo: {NOME_HOSPITAL}")

# Sessão Global
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Connection': 'keep-alive'
})

def salvar_csv(dataframe, nome_arquivo):
    if dataframe is not None and not dataframe.empty:
        caminho = os.path.join(PASTA_DESTINO, nome_arquivo)
        dataframe.to_csv(caminho, index=False, sep=';', encoding='utf-8-sig')
        print(f"      ✅ Salvo: {nome_arquivo} ({len(dataframe)} linhas)")
    else:
        print(f"      ⚠️ Arquivo {nome_arquivo} estaria vazio. Pulei.")

def descobrir_id_correto():
    """Tenta descobrir se a API responde pelo ID Longo ou Curto"""
    print("\n[1/5] Calibrando conexão com o DATASUS...")
    
    # Tenta autenticar na página principal (obter cookies)
    try:
        url_auth = f"https://cnes.datasus.gov.br/pages/estabelecimentos/ficha/index.jsp?coUnidade={CNES_LONGO}"
        session.get(url_auth, verify=False, timeout=10)
    except:
        pass

    # Teste 1: ID Longo
    print(f"   -> Testando ID Longo ({CNES_LONGO})...", end="")
    resp_longo = session.get(f"{BASE_URL}/{CNES_LONGO}", verify=False)
    if resp_longo.status_code == 200:
        print(" SUCESSO!")
        return CNES_LONGO
    else:
        print(f" Falhou ({resp_longo.status_code})")

    # Teste 2: ID Curto
    print(f"   -> Testando ID Curto ({CNES_CURTO})...", end="")
    resp_curto = session.get(f"{BASE_URL}/{CNES_CURTO}", verify=False)
    if resp_curto.status_code == 200:
        print(" SUCESSO!")
        return CNES_CURTO
    else:
        print(f" Falhou ({resp_curto.status_code})")
    
    return None

def baixar_modulo(id_validado, endpoint_suffix, nome_csv, json_key=None):
    """Função genérica para baixar qualquer módulo"""
    time.sleep(1) # Pausa para não bloquear
    url = f"{BASE_URL}/{id_validado}/{endpoint_suffix}" if endpoint_suffix else f"{BASE_URL}/{id_validado}"
    
    print(f"   -> Baixando {nome_csv}...", end="")
    try:
        resp = session.get(url, verify=False, timeout=15)
        if resp.status_code == 200:
            dados = resp.json()
            
            # Se precisar entrar numa chave especifica (ex: 'habilitacoes')
            if json_key:
                if json_key in dados:
                    dados = dados[json_key]
                else:
                    print(" Chave não encontrada.")
                    return None
            
            # Normaliza JSON para Tabela
            if isinstance(dados, list):
                df = pd.DataFrame(dados)
                print(" OK.")
                return df
            else:
                print(" Formato inesperado.")
                return None
        else:
            print(f" Erro {resp.status_code}.")
            return None
    except Exception as e:
        print(f" Erro: {e}")
        return None

# --- FLUXO PRINCIPAL ---

ID_FINAL = descobrir_id_correto()

if not ID_FINAL:
    print("\n❌ ERRO CRÍTICO: Não foi possível conectar com nenhum ID.")
    print("O site do CNES pode estar fora do ar ou mudou completamente.")
else:
    print(f"\n✅ Conexão estabelecida usando ID: {ID_FINAL}")
    
    # 2. HABILITAÇÕES (Geralmente está dentro do payload principal)
    print("\n[2/5] Processando Habilitações...")
    df_hab = baixar_modulo(ID_FINAL, "", "CNES_Habilitacoes.csv", json_key="habilitacoes")
    if df_hab is not None:
        # Seleciona colunas úteis se existirem
        cols = ['codHabilitacao', 'dsHabilitacao', 'dtCompetenciaInicial', 'dtCompetenciaFinal']
        cols_existentes = [c for c in cols if c in df_hab.columns]
        salvar_csv(df_hab[cols_existentes], "CNES_Habilitacoes.csv")

    # 3. PROFISSIONAIS
    print("\n[3/5] Processando Profissionais...")
    df_prof = baixar_modulo(ID_FINAL, "profissionais", "CNES_Profissionais.csv")
    if df_prof is not None:
        cols = ['nome', 'cns', 'cbo', 'dsCbo', 'dsVinculo', 'chHosp', 'chAmb']
        cols_existentes = [c for c in cols if c in df_prof.columns]
        salvar_csv(df_prof[cols_existentes], "CNES_Profissionais.csv")

    # 4. LEITOS
    print("\n[4/5] Processando Leitos...")
    df_leitos = baixar_modulo(ID_FINAL, "leitos", "CNES_Leitos.csv")
    if df_leitos is not None:
        cols = ['codLeito', 'dsLeito', 'dsTipoLeito', 'qtExistente', 'qtSus']
        cols_existentes = [c for c in cols if c in df_leitos.columns]
        salvar_csv(df_leitos[cols_existentes], "CNES_Leitos.csv")

    # 5. EQUIPAMENTOS
    print("\n[5/5] Processando Equipamentos...")
    df_equip = baixar_modulo(ID_FINAL, "equipamentos", "CNES_Equipamentos.csv")
    if df_equip is not None:
        cols = ['dsEquipamento', 'dsTipoEquipamento', 'qtExistente', 'qtSus', 'qtUso']
        cols_existentes = [c for c in cols if c in df_equip.columns]
        salvar_csv(df_equip[cols_existentes], "CNES_Equipamentos.csv")

print("\n🚀 Fim do Processo. Verifique a pasta 'arquivos'.")