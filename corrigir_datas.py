import json
import re

# Nome do arquivo gerado anteriormente
arquivo_entrada = 'BACKUP_COMPLETO_HISTORICO.json'
arquivo_saida = 'BACKUP_CORRIGIDO.json'

print("--- INICIANDO CORREÇÃO DE DATAS ---")

try:
    with open(arquivo_entrada, 'r', encoding='utf-8') as f:
        pacientes = json.load(f)

    corrigidos = 0

    for p in pacientes:
        # Função interna para corrigir ano
        def ajustar_ano(data_str):
            if not data_str or len(data_str) < 10: return data_str
            ano = int(data_str.split('-')[0])
            
            # Se o ano for maior que 2025 (futuro impossível para histórico)
            if ano > 2025:
                nova_data = data_str.replace(str(ano), '2025')
                print(f" Corrigindo: {p['nome']} | {data_str} -> {nova_data}")
                return nova_data
            
            # Se o ano for muito antigo (erro de digitação, ex: 202)
            if ano < 2020:
                nova_data = data_str.replace(str(ano), '2025')
                print(f" Corrigindo: {p['nome']} | {data_str} -> {nova_data}")
                return nova_data
                
            return data_str

        # Aplica correção na admissão e saída
        data_adm_antiga = p['admissao']
        p['admissao'] = ajustar_ano(p['admissao'])
        
        data_saida_antiga = p['saida']
        p['saida'] = ajustar_ano(p['saida'])

        if data_adm_antiga != p['admissao'] or data_saida_antiga != p['saida']:
            corrigidos += 1

    # Salva o novo arquivo
    with open(arquivo_saida, 'w', encoding='utf-8') as f:
        json.dump(pacientes, f, ensure_ascii=False, indent=4)

    print("-" * 30)
    print(f"Processo finalizado. {corrigidos} registros corrigidos.")
    print(f"Use o arquivo '{arquivo_saida}' para importar no portal agora.")

except Exception as e:
    print(f"Erro: {e}")