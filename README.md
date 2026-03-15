# 🏥 Portal NII - Núcleo Interno de Informação
**Hospital Beneficente Santa Helena**

Este repositório contém o código-fonte e a documentação do **Ecossistema NII**, uma plataforma de inteligência de dados desenvolvida para centralizar, automatizar e monitorar as operações críticas do hospital: Regulação (SISREG), Faturamento SUS (SIH), Repasses Médicos, Tabela SIGTAP, Prévia de Simuladas, Auditoria de Fichas e Auditoria de Leitos (IndicaSUS).

---

## 🏗️ Arquitetura do Sistema

O sistema opera sob uma arquitetura **Serverless Híbrida**:
1.  **Frontend (UI):** Interfaces web leves (HTML5 + TailwindCSS + DataTables + Chart.js + Mermaid.js) que se conectam diretamente ao banco de dados via JavaScript (Client-Side).
2.  **Backend (Robôs):** Scripts em Python executados localmente (ou em servidor) para extração de dados (ETL), leitura de PDFs/CSVs complexos e automação de navegador (Selenium).
3.  **Database:** Supabase (PostgreSQL + Storage) na nuvem, atuando como o "Coração" que sincroniza e armazena tudo em tempo real.

---

## 🧩 Módulos e Scripts

### 1. 🚨 Módulo de Regulação (SISREG)
*Monitoramento em tempo real de solicitações, autorizações e filas.*
* **`monitor_silencioso.py` (Maestro):** Robô principal que roda em loop. Navega no SISREG de forma invisível ("headless"), detecta mudanças de status, faz o download dos PDFs das Fichas de Internação e envia notificações.
* **`extracao_sisreg_v18.py` / `processar_regulacao_v21.py`:** Baixam e higienizam relatórios CSV completos para o banco histórico.
* **Frontend:** `painel_regulacao.html` com sistema de notificações em tempo real e paginação infinita (Loop de 1000 registros).
* **Tabelas:** `regulacao`, `notificacoes`

### 2. 💰 Módulo Financeiro e Repasses
*Cálculo automatizado de produção médica e terceirizados (SADT).*
* **`robo_repasses.py` (Médico):** Lê PDFs de produção individual. Usa *Fuzzy Matching* para corrigir nomes, cruza com tabela de pesos e calcula rateios líquidos.
* **`robo_financeiro_geral.py` (Terceiros):** Classifica produção SADT (UTI, Tomografia, etc.) usando regras de negócio por grupos SIGTAP.
* **Tabelas:** `financeiro_repasses`, `financeiro_geral`

### 3. 📊 Módulo de Faturamento SUS (TABNET)
*Análise histórica de produção aprovada pelo governo.*
* **`processar_tabnet.py`:** Lê exportações estruturadas do TABNET, identifica competências automaticamente e injeta série histórica na nuvem.
* **Tabela:** `faturamento`

### 4. 📚 Módulo SIGTAP (Catálogo e Auditoria)
*Consulta rápida de preços, compatibilidades de OPME e rateios de honorários.*
* **`robo_sigtap.py`:** Lê arquivos `.CSV` brutos da MV (SoulMV). Mapeia hierarquia Cirurgia x Prótese, quantidades máximas e regras clínicas (Idade, CID, Porte, Anestesia).
* **Frontend:** Cálculo automático de honorários com anestesia (Divisão 70/30) direto no painel.
* **Tabela:** `sigtap_unificada`

### 5. 🖨️ Módulo de Índice de Simuladas (Prévia Faturamento)
*Painel de busca rápida, paginação e fila de impressão para espelhos de AIH gerados pelo SISAIH01.*
* **`script_simuladas.py`:** Lê o PDF gigantesco das "Simuladas" (frequentemente > 1.000 páginas). Utiliza o algoritmo "Squash" (compressão de texto) para driblar quebras de linha invisíveis, extraindo com precisão: Nome, AIH, Prontuário, Especialidade, CNS, Procedimento e Datas (Internação/Saída).
* **Cloud Storage:** Faz o upload automático do PDF e do Painel HTML gerado para o bucket `arquivos-faturamento` no Supabase e cadastra os links no banco.
* **Frontend (`indice_pacientes.html`):** Carrinho "Fila de Impressão", botões de exportação (CSV/Excel), filtros individuais por coluna e Layout Oficial de Impressão HSH blindado.
* **Tabela:** `controle_simuladas`

### 6. 🔎 Módulo de Auditoria de Fichas (SoulMV x SISREG)
*Cruzamento automático de contas pendentes no faturamento com as AIHs aprovadas no SISREG.*
* **`cruzador_mv_sisreg.py`:** Vasculha a pasta em busca do arquivo `conferencia_autorizacao` (exportado do MV). Limpa os nomes e cruza os dados locais com a tabela `regulacao` da nuvem, filtrando rigorosamente apenas AIHs definitivas (>= 12 dígitos) e status "Aprovado/Autorizado".
* **Frontend (`Painel_Fichas_Liberadas.html`):** Painel web gerado dinamicamente na pasta `frontend`, que lista apenas os pacientes prontos para faturamento, trazendo um botão de atalho para abrir e imprimir diretamente a Ficha de Internação (PDF) arquivada na nuvem.
* **Output Secundário:** Gera backup em Excel (`FICHAS_PARA_IMPRIMIR.xlsx`).

### 7. 🛏️ Módulo de Auditoria IndicaSUS (Cofinanciamento de Leitos)
*Extração profunda, auditoria e cruzamento de diárias hospitalares no sistema estadual.*
* **`robo_auditor_retroativo.py` (Robô "Trator"):** Algoritmo de RPA avançado que navega no IndicaSUS. Lida automaticamente com paginação oculta, ignora bloqueios de HTML (`disabled inputs`), e extrai com "força bruta": CPF, CNS, Mãe, AIH, SISREG, Evolução Clínica e Status SUS. Possui "Inteligência de Competência" que fatia automaticamente as diárias em meses corretos e conta com um Raio-X em tempo real no terminal.
* **Frontend (`painel_indicasus_v2.html`):** Dashboard analítico de alta performance com cálculos efetuados em memória (Client-Side). Apresenta KPIs dinâmicos (UTI, UTIN, UCINCo, Enfermaria), filtragem por Tipo de Paciente (SUS / Não SUS), gráficos interativos via `Chart.js` e um Dossiê completo do paciente via popup.
* **Base de Conhecimento (`painel_rotinas.html`):** Documentação viva do setor, contendo um mapeamento do Pipeline de Faturamento gerado inteiramente por código vetorial através da biblioteca `Mermaid.js`, com suporte a tela cheia e download em alta resolução (`html2canvas`).
* **Tabela:** `indicasus_leitos`

---

## ⚙️ Instalação e Configuração

**1. Dependências do Python:**
```bash
pip install selenium webdriver-manager pandas pdfplumber supabase python-dotenv unidecode openpyxl graphviz