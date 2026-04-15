🏥 Portal NII - Núcleo Interno de Informação
Hospital Beneficente Santa Helena

Este repositório contém o código-fonte e a documentação do Ecossistema NII, uma plataforma de inteligência de dados desenvolvida para centralizar, automatizar e monitorar as operações críticas do hospital: Regulação (SISREG), Faturamento SUS (SIH), Repasses Médicos, Tabela SIGTAP, Prévia de Simuladas, Auditoria de Fichas, Auditoria de Leitos (IndicaSUS) e Apuração de Filantropia (CEBAS).

🏗️ Arquitetura do Sistema
O sistema opera sob uma arquitetura Serverless Híbrida:

Frontend (UI): Interfaces web leves (HTML5 + TailwindCSS + DataTables + Chart.js + Mermaid.js) que se conectam diretamente ao banco de dados via JavaScript (Client-Side).

Backend (Robôs): Scripts em Python executados localmente (ou em servidor) para extração de dados (ETL), leitura de PDFs/CSVs complexos, automação de navegador (Selenium) e geração de planilhas oficiais (OpenPyXL/Pandas).

Database: Supabase (PostgreSQL + Storage) na nuvem, atuando como o "Coração" que sincroniza, processa e armazena tudo em tempo real.

🧩 Módulos e Scripts
1. 🚨 Módulo de Regulação (SISREG)
Monitoramento em tempo real de solicitações, autorizações e filas.

monitor_silencioso.py (Maestro): Robô principal que roda em loop. Navega no SISREG de forma invisível ("headless"), detecta mudanças de status, faz o download dos PDFs das Fichas de Internação e envia notificações.

extracao_sisreg_v18.py / processar_regulacao_v21.py: Baixam e higienizam relatórios CSV completos para o banco histórico.

Frontend: painel_regulacao.html com sistema de notificações em tempo real e paginação infinita (Loop de 1000 registros).

Tabelas: regulacao, notificacoes

2. 💰 Módulo Financeiro e Repasses
Cálculo automatizado de produção médica e terceirizados (SADT).

robo_repasses.py (Médico): Lê PDFs de produção individual. Usa Fuzzy Matching para corrigir nomes, cruza com tabela de pesos e calcula rateios líquidos.

robo_financeiro_geral.py (Terceiros): Classifica produção SADT (UTI, Tomografia, etc.) usando regras de negócio por grupos SIGTAP.

Tabelas: financeiro_repasses, financeiro_geral

3. 📊 Módulo de Faturamento SUS (TABNET)
Análise histórica de produção aprovada pelo governo.

processar_tabnet.py: Lê exportações estruturadas do TABNET, identifica competências automaticamente e injeta série histórica na nuvem.

Tabela: faturamento

4. 📚 Módulo SIGTAP (Catálogo e Auditoria)
Consulta rápida de preços, compatibilidades de OPME e rateios de honorários.

robo_sigtap.py: Lê arquivos .CSV brutos da MV (SoulMV). Mapeia hierarquia Cirurgia x Prótese, quantidades máximas e regras clínicas (Idade, CID, Porte, Anestesia).

Frontend: Cálculo automático de honorários com anestesia (Divisão 70/30) direto no painel.

Tabela: sigtap_unificada

5. 🖨️ Módulo de Índice de Simuladas (Prévia Faturamento)
Painel de busca rápida, paginação e fila de impressão para espelhos de AIH gerados pelo SISAIH01.

script_simuladas.py: Lê o PDF gigantesco das "Simuladas" (frequentemente > 1.000 páginas). Utiliza o algoritmo "Squash" (compressão de texto) para extrair com precisão: Nome, AIH, Prontuário, Especialidade, CNS, Procedimento e Datas.

Cloud Storage: Faz o upload automático do PDF e do Painel HTML gerado para o bucket arquivos-faturamento no Supabase e cadastra os links no banco.

Frontend (indice_pacientes.html): Carrinho "Fila de Impressão", botões de exportação e Layout Oficial de Impressão HSH blindado.

Tabela: controle_simuladas

6. 🔎 Módulo de Auditoria de Fichas (SoulMV x SISREG)
Cruzamento automático de contas pendentes no faturamento com as AIHs aprovadas no SISREG.

cruzador_mv_sisreg.py: Vasculha a pasta em busca do arquivo conferencia_autorizacao. Limpa os nomes e cruza os dados locais com a tabela regulacao da nuvem, filtrando rigorosamente apenas AIHs definitivas e status "Aprovado/Autorizado".

Frontend (Painel_Fichas_Liberadas.html): Painel web gerado dinamicamente que lista os pacientes prontos para faturamento, com atalho para imprimir a Ficha de Internação (PDF).

7. 🛏️ Módulo de Auditoria IndicaSUS (Cofinanciamento de Leitos)
Extração profunda, auditoria e cruzamento de diárias hospitalares no sistema estadual com proteção antiqueda.

robo_indicasus_v2.py (Robô Auditor): Algoritmo de RPA com processamento em lotes e "Anti-Crash Filter". Blinda os dados extraídos em memória cache local. Possui "Espera Explícita Rigorosa" para driblar lentidões do portal e fallback offline para o WebDriver. Extrai toda a linha do tempo de leitos do paciente.

Frontend (painel_indicasus_v2.html): Dashboard analítico de alta performance com cálculos Client-Side avançados:

Regra da Alta: Desconta matematicamente a diária de saída, exceto em casos de Óbito/Transferência, simulando o faturamento real do MS.

Escudo Antiduplicação: Mescla registros "RN DE..." com os nomes registrados posteriormente usando chave composta (CPF/CNS/Mãe + Data).

Cálculo de Capacidade: Monitoramento rigoroso da capacidade CNES (Ex: UTIN 18 leitos, UTI Adulto 11 leitos).

Tabela: indicasus_leitos

8. ⚖️ Módulo de Apuração SIH e Filantropia (CEBAS)
Engenharia de dados das remessas do Ministério da Saúde e automação de planilhas oficiais de prestação de contas.

Engenharia SQL: Processo de "Flattening" via SQL que converte estruturas JSON brutas das exportações do DATASUS em mais de 80 colunas relacionais, otimizando a velocidade de consulta e filtragem.

gerador_resumo_sus_v3.py: Cruza dados do SIH para gerar o "Resumo Estatístico Anual". Separa automaticamente as especialidades (Cirúrgica, Obstétrica, Clínica, Pediatria), rastreia a origem do paciente (Cuiabá vs Outros) e vasculha as tags VMATO para contabilizar óbitos neonatais com precisão.

consolidador_cebas_final.py: O motor de apuração dos 60% SUS. Funde relatórios de Internação (Frequência e Paciente-Dia) e Ambulatório (BPA/SIA), calculando as médias ponderadas mensais e desenhando o layout oficial (Plan1 e Plan2) diretamente em um arquivo Excel limpo e formatado.

Frontend (painel_sih.html): Dashboard gerencial de faturamento com botão de exportação brutal (DataTables) que baixa as 80+ colunas do banco estruturadas em CSV num clique.

Tabelas: sih_sus_hsh, sia_sus_hsh

⚙️ Instalação e Configuração
1. Dependências do Python:

Bash
pip install selenium webdriver-manager pandas pdfplumber supabase python-dotenv unidecode openpyxl graphviz