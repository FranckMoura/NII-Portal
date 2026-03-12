import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import warnings
import os
from datetime import datetime

# Suprime avisos desnecessários
warnings.filterwarnings("ignore")

# --- CONFIGURAÇÃO ---
NOME_ARQUIVO = "relatorio_faturamento.xlsx" 

def gerar_painel_monitoramento():
    print(">>> Iniciando Geração do Painel de Monitoramento...")
    
    # --- CORREÇÃO DE CAMINHO (O PULO DO GATO) ---
    # Descobre onde este script (painel_metas.py) está salvo
    pasta_do_script = os.path.dirname(os.path.abspath(__file__))
    # Monta o caminho completo para o Excel nesta mesma pasta
    caminho_completo = os.path.join(pasta_do_script, NOME_ARQUIVO)
    
    print(f"📂 Procurando arquivo em: {caminho_completo}")

    # 1. Carregar Dados
    df = None
    try:
        # Tenta ler como Excel
        df = pd.read_excel(caminho_completo)
    except:
        try:
            # Tenta ler como CSV (caso tenha salvo como csv)
            # Tenta separador ; primeiro, depois ,
            caminho_csv = caminho_completo.replace(".xlsx", ".csv")
            try:
                df = pd.read_csv(caminho_csv, encoding='latin1', sep=';')
            except:
                df = pd.read_csv(caminho_csv, encoding='latin1', sep=',')
        except Exception as e:
            print(f"\n❌ ERRO CRÍTICO: Não encontrei o arquivo '{NOME_ARQUIVO}'")
            print(f"   Certifique-se de que o arquivo de dados está na pasta: {pasta_do_script}")
            return

    # 2. Limpeza e Conversão de Datas
    date_cols = ['DT. INT.', 'DT. ALTA', 'DT. FCHMT.']
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], format='%d/%m/%Y', errors='coerce')

    # Filtro: Contas Fechadas ou com Alta
    if 'AIH FCHD.' in df.columns:
        df_realizado = df[df['AIH FCHD.'] == 'Sim'].copy()
    else:
        df_realizado = df[df['DT. ALTA'].notnull()].copy()
    
    if len(df_realizado) == 0:
        print("⚠️ Aviso: Usando todas as contas com Data de Alta (Filtro 'AIH Fechada' não retornou nada).")
        df_realizado = df[df['DT. ALTA'].notnull()].copy()

    print(f"✅ Registros processados: {len(df_realizado)}")

    # 3. Classificação (Lógica de Negócio)
    def classificar_clinica(row):
        proc = str(row['PROCED. SOLICITADO']).upper() if pd.notnull(row.get('PROCED. SOLICITADO')) else ""
        paciente = str(row['PACIENTE']).upper() if pd.notnull(row.get('PACIENTE')) else ""
        
        # PEDIATRIA
        if "RECEM-NASCIDO" in proc or "NEONATAL" in proc or "PERINATAL" in proc or paciente.startswith("RN "):
            return "Pediatria"
        # OBSTETRÍCIA
        obs_keywords = ["PARTO", "CESARIANA", "GRAVIDEZ", "PUERPERIO", "PLACENTA", "CURETAGEM", "CERCLAGEM", "OBSTETRICIA", "UTERINO"]
        if any(k in proc for k in obs_keywords):
            return "Obstetrícia"
        # CIRÚRGICA
        surg_keywords = ["PLASTIA", "ECTOMIA", "TOMIA", "AMPUTACAO", "RESSUTURA", "LAQUEADURA", "CIRURGIA", "EXCISÃO", "SUTURA", "DESARTICULACAO", "COLECISTECTOMIA", "HERNIOPLASTIA", "HISTERECTOMIA", "LAPAROTOMIA"]
        if any(k in proc for k in surg_keywords):
            return "Clínica Cirúrgica"
        # CLÍNICA MÉDICA
        return "Clínica Médica"

    df_realizado['Clinica'] = df_realizado.apply(classificar_clinica, axis=1)

    # 4. Indicadores
    qtd_por_clinica = df_realizado['Clinica'].value_counts()

    # TMP
    if 'DT. ALTA' in df_realizado.columns and 'DT. INT.' in df_realizado.columns:
        df_realizado['Permanencia'] = (df_realizado['DT. ALTA'] - df_realizado['DT. INT.']).dt.days
        df_realizado['Permanencia'] = df_realizado['Permanencia'].apply(lambda x: 1 if x == 0 else x)
        tmp_por_clinica = df_realizado.groupby('Clinica')['Permanencia'].mean()
    else:
        tmp_por_clinica = pd.Series()

    # Cesárea
    dados_obs = df_realizado[df_realizado['Clinica'] == 'Obstetrícia']
    total_partos = 0; qtd_cesareas = 0
    if not dados_obs.empty:
        total_partos = dados_obs[dados_obs['PROCED. SOLICITADO'].str.contains("PARTO|CESARIANA", case=False, na=False)].shape[0]
        qtd_cesareas = dados_obs[dados_obs['PROCED. SOLICITADO'].str.contains("CESARIANA", case=False, na=False)].shape[0]
    taxa_cesarea = (qtd_cesareas / total_partos * 100) if total_partos > 0 else 0

    # Metas
    metas_producao = {"Clínica Médica": 73, "Clínica Cirúrgica": 148, "Pediatria": 84, "Obstetrícia": 0}
    metas_tmp_limite = {"Clínica Médica": 8.0, "Clínica Cirúrgica": 4.8, "Obstetrícia": 2.8, "Pediatria": 5.0}

    # 5. Visualização
    plt.figure(figsize=(18, 12))
    plt.suptitle(f"PAINEL DE MONITORAMENTO SISREG - {datetime.now().strftime('%m/%Y')}", fontsize=22, weight='bold', color='#333')

    # Plot 1: Produção
    plt.subplot(2, 2, 1)
    clinicas = list(metas_producao.keys())
    v_real = [qtd_por_clinica.get(c, 0) for c in clinicas]
    v_meta = [metas_producao.get(c, 0) for c in clinicas]
    x = np.arange(len(clinicas)); width = 0.35
    plt.bar(x - width/2, v_real, width, label='Realizado', color='#2E7D32')
    plt.bar(x + width/2, v_meta, width, label='Meta', color='#FF9800', alpha=0.7)
    plt.ylabel('Qtd'); plt.title('Produção Física', fontsize=14, weight='bold')
    plt.xticks(x, clinicas); plt.legend(); plt.grid(axis='y', linestyle='--', alpha=0.3)
    for i, v in enumerate(v_real): plt.text(i - width/2, v + 2, str(v), ha='center', fontweight='bold')

    # Plot 2: Cesárea
    plt.subplot(2, 2, 2)
    if total_partos > 0:
        labels = ['Cesárea', 'Parto Normal']; sizes = [qtd_cesareas, total_partos - qtd_cesareas]
        colors = ['#D32F2F' if taxa_cesarea > 35 else '#388E3C', '#1976D2']
        plt.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90, explode=(0.05, 0))
        plt.title(f'Taxa de Cesárea (Teto: 35%)', fontsize=14, weight='bold')
        status = "DENTRO DA META" if taxa_cesarea <= 35 else "ALERTA"
        plt.text(0, -1.2, f"{status}: {taxa_cesarea:.1f}%", ha='center', fontsize=12, weight='bold', color=colors[0])
    else:
        plt.text(0.5, 0.5, "Sem dados de Parto", ha='center'); plt.axis('off')

    # Plot 3: TMP
    plt.subplot(2, 2, 3)
    c_tmp = [c for c in clinicas if c in metas_tmp_limite]
    v_tmp = [tmp_por_clinica.get(c, 0) for c in c_tmp]
    m_tmp = [metas_tmp_limite.get(c, 0) for c in c_tmp]
    y_pos = np.arange(len(c_tmp))
    colors = ['#388E3C' if v <= m else '#D32F2F' for v, m in zip(v_tmp, m_tmp)]
    plt.barh(y_pos, v_tmp, align='center', color=colors, alpha=0.8)
    plt.yticks(y_pos, c_tmp); plt.xlabel('Dias'); plt.title('Tempo Médio de Permanência', fontsize=14, weight='bold')
    for i, m in enumerate(m_tmp):
        plt.axvline(x=m, color='gray', linestyle='--'); plt.text(m, i, f' {m}d', va='bottom', fontsize=9)
        if not np.isnan(v_tmp[i]): plt.text(v_tmp[i] + 0.1, i, f'{v_tmp[i]:.1f}d', va='center', fontweight='bold')

    # Plot 4: Resumo
    plt.subplot(2, 2, 4); plt.axis('off')
    txt = f"RESUMO EXECUTIVO\n------------------\nTotal Faturado: {len(df_realizado)}\n\n"
    for c in clinicas:
        r = qtd_por_clinica.get(c, 0); m = metas_producao[c]
        p = (r/m)*100 if m > 0 else 0
        icon = "🟢" if 90 <= p <= 110 else "🔴" if p > 110 else "🟡"
        txt += f"• {c}: {r}/{m} ({p:.0f}%) {icon}\n"
    plt.text(0.05, 0.9, txt, fontsize=12, va='top', family='monospace')

    caminho_imagem = os.path.join(pasta_do_script, "painel_monitoramento.png")
    plt.tight_layout()
    plt.savefig(caminho_imagem, dpi=100)
    print(f"✅ Painel salvo em: {caminho_imagem}")
    plt.show()

if __name__ == "__main__":
    gerar_painel_monitoramento()