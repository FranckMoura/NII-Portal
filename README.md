🏥 Portal NII - Núcleo Interno de Informação
Hospital Beneficente Santa Helena

Este repositório contém o código-fonte e a documentação do Ecossistema NII, uma plataforma de inteligência de dados desenvolvida para centralizar, automatizar e monitorar as operações críticas do hospital: Regulação (SISREG), Faturamento SUS (SIH), Repasses Médicos, Tabela SIGTAP, Prévia de Simuladas, Auditoria de Fichas, Auditoria de Leitos (IndicaSUS) e Apuração de Filantropia (CEBAS).

🏗️ Arquitetura do Sistema
O sistema opera sob uma arquitetura Serverless Híbrida:

- Frontend (UI): Interfaces web leves (HTML5 + TailwindCSS + DataTables + Chart.js) que se conectam diretamente ao banco de dados via JavaScript (Client-Side) com suporte a Temas Híbridos (Dark Neon e Clássico Portal).
- Backend (Robôs): Scripts em Python executados localmente para extração de dados (ETL), leitura de PDFs/CSVs complexos, comunicação via FTP e integração via API Supabase.
- Database: Supabase (PostgreSQL + Storage) na nuvem, atuando como o "Coração" que sincroniza e processa o cruzamento de dados em tempo real.

🧩 Módulos e Scripts

... [Módulos 1 a 8 mantidos] ...

9. 🛡️ Módulo de Auditoria Estratégica (SIH x SP)
Motor de conformidade avançada que cruza os dados da Capa da AIH (RD) com os itens detalhados de honorários e exames (SP).

- 🤖 6_atualizacao_mensal.py (Robô ETL): Automação completa de fechamento de competência. Conecta-se ao FTP do DATASUS, baixa arquivos .DBC (RD/SP) do Mato Grosso, descompacta, filtra o CNES 2311682 e realiza o upload para a nuvem com "Escudo de Idempotência" (limpeza automática de lotes para evitar duplicatas e timeouts).
- Algoritmo "Redutor Matemático": Lógica implementada no Frontend para unificar as fatias de Serviço Hospitalar (SH) e Serviço Profissional (SP) em linhas únicas, somando valores e corrigindo a inflação de dados do banco, espelhando fielmente o SISAIH01.
- Inteligência de Terceirizados: Regra de negócio automatizada que identifica o prestador correto via prefixo SIGTAP. Direciona exames para Laboratório Santa Helena, Santa Helena Imagem, Lapat, Diag X, Cinecor, Hemosan e Clinemat, mesmo quando o arquivo SP oculta o CNES do terceiro.
- Frontend (painel_cruzamento_sih_sp.html): Dashboard executivo com:
    - KPIs em tempo real (Faturamento, AIHs, Ticket Médio e Diárias de UTI).
    - Gráficos de Composição: Distribuição por Especialidade (Cirúrgica, Obstétrica, etc.) e Epidemiologia (Top 5 Capítulos CID-10).
    - Auditoria AIH: Layout oficial de espelho de auditoria com resumo da internação (Caráter de Atendimento, Motivo de Saída, Permanência e Dados de UTI).

Tabelas: sih_sus_hsh, sp_sus_hsh | View: vw_cruzamento_sih_sp

⚙️ Instalação e Configuração
1. Dependências do Python:

Bash:
pip install selenium webdriver-manager pandas pdfplumber supabase python-dotenv unidecode openpyxl dbfread datasus-dbc