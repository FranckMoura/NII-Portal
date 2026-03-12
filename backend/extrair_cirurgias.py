import pdfplumber
import pandas as pd
import re

# Configuração dos arquivos
arquivo_pdf = 'CIRURGIAS_MULTIPLAS_0126.pdf'
arquivo_saida = 'Relatorio_Cirurgias_Multiplas_Processado.xlsx'

# Lista para armazenar os dados extraídos
dados_pacientes = []

print("Iniciando processamento do PDF...")

with pdfplumber.open(arquivo_pdf) as pdf:
    # O PDF parece ter uma página por AIH (ou o início de uma nova AIH reseta o contexto)
    # Vamos percorrer página por página, mas mantendo um buffer caso a AIH ocupe mais de uma página
    
    texto_completo = ""
    for page in pdf.pages:
        texto_completo += page.extract_text() + "\n---QUEBRA_PAGINA---\n"

# Dividir o texto por "MS-DATASUS" ou "Num AIH", pois isso indica um novo espelho
# Vamos usar Regex para capturar blocos de cada paciente
# A estratégia aqui é dividir o texto bruto em blocos de AIH

blocos_aih = re.split(r'(?=Num AIH:)', texto_completo)

for bloco in blocos_aih:
    if "Num AIH:" not in bloco:
        continue
        
    try:
        # 1. Extração de Dados do Cabeçalho
        aih_match = re.search(r'Num AIH:\s*(\d{13}-?\d?)', bloco)
        paciente_match = re.search(r'Paciente:\s*(.+)', bloco)
        prontuario_match = re.search(r'Prontuário:\s*(\d+)', bloco)
        cns_match = re.search(r'CNS/CPF:\s*([\d.-]+)', bloco)
        dt_internacao_match = re.search(r'Data internação:\s*(\d{2}/\d{2}/\d{4})', bloco)
        dt_saida_match = re.search(r'Data saída:\s*(\d{2}/\d{2}/\d{4})', bloco)
        competencia_match = re.search(r'Apresentação:\s*(\d{2}/\d{4})', bloco)

        # Se não tiver AIH ou Paciente, pula (pode ser sujeira de cabeçalho)
        if not aih_match or not paciente_match:
            continue

        aih = aih_match.group(1).replace("-", "").strip()
        nome = paciente_match.group(1).strip()
        prontuario = prontuario_match.group(1).strip() if prontuario_match else ""
        cns = cns_match.group(1).replace(".", "").replace("-", "").strip() if cns_match else ""
        data_intern = dt_internacao_match.group(1) if dt_internacao_match else ""
        data_alta = dt_saida_match.group(1) if dt_saida_match else ""
        competencia = competencia_match.group(1) if competencia_match else ""

        # 2. Extração dos Procedimentos Realizados (Cirurgias Múltiplas)
        # Procuramos por linhas que contenham códigos de procedimento (formato 04.xx.xx.xxx)
        # O PDF lista procedimentos em uma tabela. Vamos capturar linhas que começam com '04' (Grupo Cirúrgico)
        # Ignoramos '02' (Exames), '03' (Clínicos), '07' (OPM), '08' (Diárias) para focar nas cirurgias
        
        procedimentos_encontrados = set() # Usar set para evitar duplicatas se a página quebrar
        
        # Regex para pegar o código do procedimento na tabela "PROCEDIMENTOS REALIZADOS"
        # Padrão visual no texto extraído: "1 0409060100 ... Descrição"
        linhas = bloco.split('\n')
        capturando_procedimentos = False
        
        for linha in linhas:
            if "PROCEDIMENTOS REALIZADOS" in linha:
                capturando_procedimentos = True
                continue
            if "VALORES DA PRÉVIA" in linha or "DADOS DE OPM" in linha:
                capturando_procedimentos = False
                continue
            
            if capturando_procedimentos:
                # Procura por sequencia numérica que parece um procedimento (10 dígitos) começando com 04
                # Exemplo de linha: "1 0407040102 702909532904479..."
                proc_match = re.search(r'\b(04\d{8})\b', linha)
                if proc_match:
                    codigo_proc = proc_match.group(1)
                    procedimentos_encontrados.add(codigo_proc)

        # Concatena os procedimentos com espaço
        procs_concatenados = " ".join(sorted(list(procedimentos_encontrados)))

        # Se não achou cirurgias (04...), o campo fica vazio
        
        # Adicionar à lista
        dados_pacientes.append({
            'HOSPITAL': 'HOSPITAL BENEFICENTE SANTA HELENA',
            'CNES': '2311682',
            'COMPETENCIA': competencia,
            'NOME': nome,
            'N º. CNS-SUS': cns,
            'AIH': aih,
            'ATEND/Nº PRONT': prontuario,
            'COD. PROC REALIZADO': procs_concatenados,
            'DATA INTERN.': data_intern,
            'DATA ALTA': data_alta,
            'COMP. FATURADA': f"01/{competencia}" if competencia else "" 
        })

    except Exception as e:
        print(f"Erro ao processar bloco: {e}")

# Criar DataFrame
df = pd.DataFrame(dados_pacientes)

# Formatação final para garantir que CNES/CNS/AIH sejam texto e não números científicos no Excel
df['N º. CNS-SUS'] = df['N º. CNS-SUS'].astype(str)
df['AIH'] = df['AIH'].astype(str)

# Salvar
df.to_excel(arquivo_saida, index=False)
print(f"Arquivo gerado com sucesso: {arquivo_saida}")
print(f"Total de AIHs processadas: {len(df)}")