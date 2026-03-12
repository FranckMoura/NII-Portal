import pdfplumber
import re
import os
import glob
from datetime import datetime, timezone
from supabase import create_client, Client

# --- CONFIGURAÇÕES ---
SUPABASE_URL = "https://voweywtzoldwfhgkniup.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZvd2V5d3R6b2xkd2ZoZ2tuaXVwIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2ODEwMTU5NSwiZXhwIjoyMDgzNjc3NTk1fQ.deftZEa4j3SFFsNNjVhU4cE67CGi1rVQSBAltz-AmPk"

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    print(f"❌ Erro ao conectar no Supabase: {e}")
    exit()

def converter_valor(texto):
    """Converte '10.500,00' ou '"10.500,00"' para float 10500.00"""
    if not texto: return 0.0
    limpo = re.sub(r'[^\d,\.]', '', texto)
    limpo = limpo.replace('.', '').replace(',', '.')
    try:
        return float(limpo)
    except:
        return 0.0

def extrair_dados_previsao(caminho_arquivo):
    nome_arq = os.path.basename(caminho_arquivo)
    
    # Filtro de segurança: processa apenas relatórios financeiros globais
    if "R_PREV_REC_GLO" not in nome_arq:
        return []

    print(f"\n📄 Lendo: {nome_arq}")
    
    dados_arquivo = []
    
    try:
        with pdfplumber.open(caminho_arquivo) as pdf:
            competencia = None
            especialidade_atual = "GERAL"
            
            for page in pdf.pages:
                text = page.extract_text()
                if not text: continue
                
                lines = text.split('\n')
                
                for line in lines:
                    # 1. Competência
                    if "Competência:" in line and not competencia:
                        match_comp = re.search(r'(\d{2}/\d{4})', line)
                        if match_comp:
                            raw_comp = match_comp.group(1)
                            mes, ano = raw_comp.split('/')
                            competencia = f"{ano}-{mes}" 
                            print(f"   🗓️  Ref: {competencia}")

                    # 2. Especialidade (Setor)
                    if "Especialidade:" in line:
                        match_esp = re.search(r'Especialidade:\s*\d+\s+(.+)', line)
                        if match_esp:
                            especialidade_atual = match_esp.group(1).strip()
                            if "CLINICO" in especialidade_atual: especialidade_atual = "Clínica Médica"
                            elif "CIRURGICO" in especialidade_atual: especialidade_atual = "Clínica Cirúrgica"
                            elif "OBSTETRICOS" in especialidade_atual: especialidade_atual = "Obstetrícia"
                            elif "PEDIATRIA" in especialidade_atual: especialidade_atual = "Pediatria"

                    # 3. Extração de Indicadores
                    if not competencia: continue # Só extrai se já achou a data

                    # UTI
                    if "UTI Especializada" in line and "Profissionais" not in line:
                        match = re.search(r'UTI Especializada.*?(\d+).*?([\d\.]+,\d{2})', line)
                        if match:
                            dados_arquivo.append({
                                "competencia": competencia,
                                "clinica": especialidade_atual,
                                "indicador": "Diárias UTI",
                                "quantidade": int(match.group(1)),
                                "valor": converter_valor(match.group(2)),
                                "tipo": "SADT"
                            })

                    # Enfermaria
                    elif "Enfermaria" in line:
                        match = re.search(r'Enfermaria.*?(\d+).*?([\d\.]+,\d{2})', line)
                        if match:
                            dados_arquivo.append({
                                "competencia": competencia,
                                "clinica": especialidade_atual,
                                "indicador": "Diárias Enfermaria",
                                "quantidade": int(match.group(1)),
                                "valor": converter_valor(match.group(2)),
                                "tipo": "HOSP"
                            })

                    # Total Hospitalar
                    elif "TOTAL SERVIÇOS HOSPITALARES" in line:
                        match = re.search(r'HOSPITALARES.*?(\d+).*?([\d\.]+,\d{2})', line)
                        if match:
                            dados_arquivo.append({
                                "competencia": competencia,
                                "clinica": especialidade_atual,
                                "indicador": "Total Hospitalar",
                                "quantidade": int(match.group(1)),
                                "valor": converter_valor(match.group(2)),
                                "tipo": "TOTAL_HOSP"
                            })

                    # Total Profissional
                    elif "TOTAL PROFISSIONAIS" in line:
                        match = re.search(r'PROFISSIONAIS.*?([\d\.]+,\d{2})', line)
                        if match:
                            dados_arquivo.append({
                                "competencia": competencia,
                                "clinica": especialidade_atual,
                                "indicador": "Total Profissional",
                                "quantidade": 0,
                                "valor": converter_valor(match.group(1)),
                                "tipo": "TOTAL_PROF"
                            })
    except Exception as e:
        print(f"⚠️ Erro ao ler {nome_arq}: {e}")

    return dados_arquivo

def processar():
    pasta_script = os.path.dirname(os.path.abspath(__file__))
    
    # Busca em todas as subpastas para garantir
    arquivos = glob.glob(os.path.join(pasta_script, "**", "R_PREV_REC_GLO*.pdf"), recursive=True)
    
    # Remove duplicatas de caminho (caso existam)
    arquivos = list(set(arquivos))

    if not arquivos:
        print("❌ Nenhum arquivo 'R_PREV_REC_GLO...' encontrado.")
        return

    print(f"✅ Encontrados {len(arquivos)} arquivos.")

    todos_dados_brutos = []
    for arq in arquivos:
        dados = extrair_dados_previsao(arq)
        todos_dados_brutos.extend(dados)

    # --- DEDUPLICAÇÃO E CONSOLIDAÇÃO ---
    # Se houver duas linhas para a mesma (competencia, clinica, indicador), a última vence.
    dados_map = {}
    
    for d in todos_dados_brutos:
        # Chave única composta
        chave = (d['competencia'], d['clinica'], d['indicador'])
        
        if chave in dados_map:
            # Opcional: Avisar sobre conflito
            # print(f"   ⚠️ Conflito resolvido (Sobrescrevendo): {chave} -> R$ {d['valor']}")
            pass
            
        dados_map[chave] = d

    lista_final = list(dados_map.values())
    
    print(f"\n📊 Processamento Final: {len(lista_final)} indicadores únicos (após dedup).")
    
    # Debug UTI
    utis = [d for d in lista_final if d['indicador'] == 'Diárias UTI']
    if utis:
        print("\n--- ✅ DADOS DE UTI (Consolidados) ---")
        for u in utis:
            print(f"   {u['competencia']} | {u['clinica']}: {u['quantidade']} diárias -> R$ {u['valor']:,.2f}")

    if len(lista_final) > 0:
        print("\n☁️ Enviando para Supabase...")
        try:
            data_envio = [
                {
                    "competencia": d["competencia"],
                    "clinica": d["clinica"],
                    "indicador": d["indicador"],
                    "quantidade": d["quantidade"],
                    "valor": d["valor"],
                    "tipo": d["tipo"],
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
                for d in lista_final if d["competencia"]
            ]
            
            # Upsert seguro (agora sem duplicatas no lote)
            supabase.table("indicadores_metas").upsert(data_envio, on_conflict="competencia, clinica, indicador").execute()
            print("✅ Sucesso! Banco atualizado.")
        except Exception as e:
            print(f"⚠️ Erro ao enviar: {e}")
            print("   Dica: Verifique se a tabela 'indicadores_metas' existe no Supabase.")

if __name__ == "__main__":
    processar()