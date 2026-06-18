import os

# 1. Template Base HTML (O padrão visual para todas as calculadoras)
html_template = """<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{titulo} - Portal NII</title>
    
    <script src="https://code.jquery.com/jquery-3.7.0.min.js"></script>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">

    <style>
        :root {{
            --bg-body: #0f172a;
            --bg-card: #1e293b;
            --border-color: #334155;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --color-primary: #38bdf8;
            --color-success: #34d399;
            --color-warning: #fbbf24;
            --color-danger:  #f87171;
            --color-purple:  #c084fc;
        }}
        
        body {{ font-family: 'Inter', sans-serif; background-color: var(--bg-body); color: var(--text-main); display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; padding: 20px; }}
        .calc-container {{ background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 12px; width: 100%; max-width: 600px; padding: 24px; box-shadow: 0 10px 40px rgba(0,0,0,0.5); }}
        .input-form {{ width: 100%; padding: 12px; border-radius: 8px; font-size: 0.9rem; background: var(--bg-body); border: 1px solid var(--border-color); color: var(--text-main); outline: none; margin-top: 6px; transition: 0.2s; }}
        .input-form:focus {{ border-color: var(--color-primary); box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.15); }}
        .btn-submit {{ width: 100%; background: var(--color-primary); color: white; font-weight: 700; padding: 12px; border-radius: 8px; border: none; cursor: pointer; transition: 0.2s; margin-top: 15px; box-shadow: 0 4px 6px -1px rgba(56, 189, 248, 0.3); }}
        .btn-submit:hover {{ filter: brightness(1.1); transform: translateY(-1px); }}
        
        /* Classes extras para a Prevent e layouts duplos */
        .label-title {{ font-size: 0.75rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; }}
        .alert-box {{ background: rgba(251, 191, 36, 0.1); border: 1px solid rgba(251, 191, 36, 0.3); color: #fbbf24; padding: 12px; border-radius: 8px; font-size: 0.8rem; margin-bottom: 20px; text-align: justify; }}
    </style>
</head>
<body>

    <div class="calc-container">
        <h2 class="font-bold text-xl mb-6 border-b border-slate-700 pb-3 flex items-center gap-2">
            <i class="fas {icone} text-{cor_icone}"></i> {titulo}
        </h2>
        
        {formulario}
        
        <div id="calcResult" class="mt-6 text-center font-bold text-xl py-4 bg-black/20 rounded hidden border border-gray-600/30"></div>
        
        <div class="mt-8 text-center text-xs font-semibold text-slate-500 border-t border-slate-700/50 pt-4">
            Desenvolvido por Franck Moura
        </div>
    </div>

    <script>
        {script_js}
    </script>
</body>
</html>
"""

# 2. Dicionário com os dados individuais de cada calculadora
calculadoras = {
    "calc_imc.html": {
        "titulo": "Calculadora de IMC",
        "icone": "fa-weight",
        "cor_icone": "yellow-400",
        "formulario": """
            <div class="mb-4">
                <label class="text-xs font-bold text-gray-400 uppercase">Peso (kg)</label>
                <input type="number" id="calcPeso" class="input-form" placeholder="Ex: 85.5">
            </div>
            <div class="mb-4">
                <label class="text-xs font-bold text-gray-400 uppercase">Altura (m)</label>
                <input type="number" id="calcAltura" class="input-form" placeholder="Ex: 1.75">
            </div>
            <button onclick="calcularIMC()" class="btn-submit">Calcular IMC</button>
        """,
        "script_js": """
            function calcularIMC() {
                let p = parseFloat($('#calcPeso').val()); let a = parseFloat($('#calcAltura').val());
                if(!p || !a) return;
                let imc = p / (a * a); let diag = "Normal"; let color = "text-green-500";
                if(imc >= 40) { diag = "Obesidade Grau III"; color = "text-red-500"; }
                else if(imc >= 35) { diag = "Obesidade Grau II"; color = "text-orange-500"; }
                else if(imc >= 30) { diag = "Obesidade Grau I"; color = "text-yellow-500"; }
                else if(imc >= 25) { diag = "Sobrepeso"; color = "text-yellow-500"; }
                $('#calcResult').html(`IMC: <span class="${color}">${imc.toFixed(1)}</span><br><span class="text-sm font-normal text-gray-500 mt-1 block">${diag}</span>`).removeClass('hidden');
            }
        """
    },
    "calc_renal.html": {
        "titulo": "Clearance de Creatinina",
        "icone": "fa-vial",
        "cor_icone": "red-400",
        "formulario": """
            <div class="grid grid-cols-2 gap-4 mb-4">
                <div><label class="text-xs font-bold text-gray-400 uppercase">Idade</label><input type="number" id="calcIdade" class="input-form" placeholder="Anos"></div>
                <div><label class="text-xs font-bold text-gray-400 uppercase">Peso (kg)</label><input type="number" id="calcPesoCr" class="input-form" placeholder="kg"></div>
            </div>
            <div class="grid grid-cols-2 gap-4 mb-4">
                <div><label class="text-xs font-bold text-gray-400 uppercase">Creatinina Sérica</label><input type="number" step="0.1" id="calcCr" class="input-form" placeholder="mg/dL"></div>
                <div><label class="text-xs font-bold text-gray-400 uppercase">Sexo</label>
                    <select id="calcSexoCr" class="input-form"><option value="M">Masculino</option><option value="F">Feminino</option></select>
                </div>
            </div>
            <button onclick="calcularClCr()" class="btn-submit bg-red-500 hover:bg-red-600 shadow-red-500/30">Calcular Função Renal</button>
        """,
        "script_js": """
            function calcularClCr() {
                let id = parseFloat($('#calcIdade').val()); let p = parseFloat($('#calcPesoCr').val());
                let cr = parseFloat($('#calcCr').val()); let sx = $('#calcSexoCr').val();
                if(!id || !p || !cr) return;
                let clcr = ((140 - id) * p) / (72 * cr); if (sx === 'F') clcr = clcr * 0.85;
                let f = "", d = "", c = "";
                if (clcr >= 90) { f="Fase 1"; d="TFG normal ou aumentada"; c="text-green-500"; }
                else if (clcr >= 60) { f="Fase 2"; d="Leve diminuição"; c="text-yellow-500"; }
                else if (clcr >= 45) { f="Fase 3A"; d="Leve a moderada"; c="text-orange-500"; }
                else if (clcr >= 30) { f="Fase 3B"; d="Moderada a grave"; c="text-orange-600"; }
                else if (clcr >= 15) { f="Fase 4"; d="Grave"; c="text-red-500"; }
                else { f="Fase 5"; d="Falência renal"; c="text-red-600"; }
                $('#calcResult').html(`ClCr: <span class="text-blue-500">${clcr.toFixed(1)} ml/min</span><br><div class="mt-2 text-sm"><span class="font-bold ${c}">${f}</span><br><span class="font-normal text-gray-500">${d}</span></div>`).removeClass('hidden');
            }
        """
    },
    "calc_glasgow.html": {
        "titulo": "Escala de Glasgow",
        "icone": "fa-brain",
        "cor_icone": "purple-400",
        "formulario": """
            <div class="mb-3">
                <label class="text-xs font-bold text-gray-400 uppercase">Abertura Ocular</label>
                <select id="gOcular" class="input-form">
                    <option value="4">4 - Espontânea</option>
                    <option value="3">3 - À voz (comando verbal)</option>
                    <option value="2">2 - À dor (estímulo doloroso)</option>
                    <option value="1">1 - Nenhuma</option>
                </select>
            </div>
            <div class="mb-3">
                <label class="text-xs font-bold text-gray-400 uppercase">Resposta Verbal</label>
                <select id="gVerbal" class="input-form">
                    <option value="5">5 - Orientada e conversando</option>
                    <option value="4">4 - Confusa (desorientada)</option>
                    <option value="3">3 - Palavras inapropriadas</option>
                    <option value="2">2 - Sons incompreensíveis</option>
                    <option value="1">1 - Nenhuma</option>
                </select>
            </div>
            <div class="mb-4">
                <label class="text-xs font-bold text-gray-400 uppercase">Resposta Motora</label>
                <select id="gMotora" class="input-form">
                    <option value="6">6 - Obedece a comandos</option>
                    <option value="5">5 - Localiza dor</option>
                    <option value="4">4 - Retirada (flexão normal)</option>
                    <option value="3">3 - Flexão anormal (Decorticação)</option>
                    <option value="2">2 - Extensão anormal (Descerebração)</option>
                    <option value="1">1 - Nenhuma</option>
                </select>
            </div>
            <button onclick="calcularGlasgow()" class="btn-submit bg-purple-500 hover:bg-purple-600 shadow-purple-500/30">Calcular Glasgow</button>
        """,
        "script_js": """
            function calcularGlasgow() {
                let oc = parseInt($('#gOcular').val()); let vb = parseInt($('#gVerbal').val()); let mt = parseInt($('#gMotora').val());
                let total = oc + vb + mt;
                let diag = ""; let color = "";
                if(total >= 13) { diag = "Trauma Leve"; color = "text-green-500"; }
                else if(total >= 9) { diag = "Trauma Moderado"; color = "text-yellow-500"; }
                else { diag = "Trauma Grave (Intubação indicada)"; color = "text-red-500"; }
                $('#calcResult').html(`ECG Total: <span class="${color} text-2xl">${total}</span> / 15<br><span class="text-sm font-normal text-gray-500 mt-1 block">${diag}</span>`).removeClass('hidden');
            }
        """
    },
    "calc_sirs.html": {
        "titulo": "Critérios de SIRS",
        "icone": "fa-virus",
        "cor_icone": "red-400",
        "formulario": """
            <div class="mb-4 text-sm text-gray-400">Selecione os critérios presentes no paciente:</div>
            
            <div class="mb-3 flex items-start gap-3">
                <input type="checkbox" id="sirsTemp" class="w-5 h-5 mt-1 cursor-pointer accent-red-500">
                <label for="sirsTemp" class="text-sm font-semibold cursor-pointer">Temperatura<br><span class="font-normal text-gray-500">> 38°C ou < 36°C</span></label>
            </div>
            <div class="mb-3 flex items-start gap-3">
                <input type="checkbox" id="sirsFC" class="w-5 h-5 mt-1 cursor-pointer accent-red-500">
                <label for="sirsFC" class="text-sm font-semibold cursor-pointer">Frequência Cardíaca<br><span class="font-normal text-gray-500">> 90 bpm</span></label>
            </div>
            <div class="mb-3 flex items-start gap-3">
                <input type="checkbox" id="sirsFR" class="w-5 h-5 mt-1 cursor-pointer accent-red-500">
                <label for="sirsFR" class="text-sm font-semibold cursor-pointer">Frequência Respiratória<br><span class="font-normal text-gray-500">> 20 irpm ou PaCO2 < 32 mmHg</span></label>
            </div>
            <div class="mb-5 flex items-start gap-3">
                <input type="checkbox" id="sirsLeuco" class="w-5 h-5 mt-1 cursor-pointer accent-red-500">
                <label for="sirsLeuco" class="text-sm font-semibold cursor-pointer">Leucócitos<br><span class="font-normal text-gray-500">> 12.000 ou < 4.000 ou > 10% bastões</span></label>
            </div>
            <button onclick="calcularSIRS()" class="btn-submit bg-red-500 hover:bg-red-600 shadow-red-500/30">Avaliar SIRS</button>
        """,
        "script_js": """
            function calcularSIRS() {
                let pontos = 0;
                if($('#sirsTemp').is(':checked')) pontos++;
                if($('#sirsFC').is(':checked')) pontos++;
                if($('#sirsFR').is(':checked')) pontos++;
                if($('#sirsLeuco').is(':checked')) pontos++;
                let diag = ""; let color = "";
                if(pontos >= 2) { diag = "Critérios de SIRS Preenchidos!<br>Atenção ao risco de Sepse."; color = "text-red-500"; } 
                else { diag = "Sem critérios para SIRS."; color = "text-green-500"; }
                $('#calcResult').html(`Pontuação: <span class="${color} text-2xl">${pontos}</span><br><span class="text-sm font-normal text-gray-500 mt-2 block">${diag}</span>`).removeClass('hidden');
            }
        """
    },
    "calc_news2.html": {
        "titulo": "Escore NEWS 2",
        "icone": "fa-notes-medical",
        "cor_icone": "blue-400",
        "formulario": """
            <div style="max-height: 50vh; overflow-y: auto; padding-right: 10px;" class="mb-4">
                <div class="mb-3">
                    <label class="text-xs font-bold text-gray-400 uppercase">Frequência Respiratória (irpm)</label>
                    <select id="nFR" class="input-form"><option value="3">≤ 8</option><option value="1">9 a 11</option><option value="0" selected>12 a 20</option><option value="2">21 a 24</option><option value="3">≥ 25</option></select>
                </div>
                <div class="mb-3">
                    <label class="text-xs font-bold text-gray-400 uppercase">Saturação de O2 (%)</label>
                    <select id="nSat" class="input-form"><option value="3">≤ 91</option><option value="2">92 a 93</option><option value="1">94 a 95</option><option value="0" selected>≥ 96</option></select>
                </div>
                <div class="mb-3">
                    <label class="text-xs font-bold text-gray-400 uppercase">Uso de O2 Suplementar</label>
                    <select id="nO2" class="input-form"><option value="0" selected>Não</option><option value="2">Sim</option></select>
                </div>
                <div class="mb-3">
                    <label class="text-xs font-bold text-gray-400 uppercase">Pressão Sistólica (mmHg)</label>
                    <select id="nPAS" class="input-form"><option value="3">≤ 90</option><option value="2">91 a 100</option><option value="1">101 a 110</option><option value="0" selected>111 a 219</option><option value="3">≥ 220</option></select>
                </div>
                <div class="mb-3">
                    <label class="text-xs font-bold text-gray-400 uppercase">Frequência Cardíaca (bpm)</label>
                    <select id="nFC" class="input-form"><option value="3">≤ 40</option><option value="1">41 a 50</option><option value="0" selected>51 a 90</option><option value="1">91 a 110</option><option value="2">111 a 130</option><option value="3">≥ 131</option></select>
                </div>
                <div class="mb-3">
                    <label class="text-xs font-bold text-gray-400 uppercase">Nível de Consciência</label>
                    <select id="nCons" class="input-form"><option value="0" selected>Alerta / Normal</option><option value="3">CVDU (Confusão, Voz, Dor, Irresponsivo)</option></select>
                </div>
                <div class="mb-3">
                    <label class="text-xs font-bold text-gray-400 uppercase">Temperatura (°C)</label>
                    <select id="nTemp" class="input-form"><option value="3">≤ 35.0</option><option value="1">35.1 a 36.0</option><option value="0" selected>36.1 a 38.0</option><option value="1">38.1 a 39.0</option><option value="2">≥ 39.1</option></select>
                </div>
            </div>
            <button onclick="calcularNEWS2()" class="btn-submit bg-blue-500 hover:bg-blue-600 shadow-blue-500/30">Calcular Risco (NEWS 2)</button>
        """,
        "script_js": """
            function calcularNEWS2() {
                let param1 = parseInt($('#nFR').val()); let param2 = parseInt($('#nSat').val());
                let param3 = parseInt($('#nO2').val()); let param4 = parseInt($('#nPAS').val());
                let param5 = parseInt($('#nFC').val()); let param6 = parseInt($('#nCons').val());
                let param7 = parseInt($('#nTemp').val());

                let score = param1 + param2 + param3 + param4 + param5 + param6 + param7;
                let parametroIsoladoCritico = (param1===3 || param2===3 || param3===3 || param4===3 || param5===3 || param6===3 || param7===3);

                let risco = ""; let conduta = ""; let color = "";
                if(score >= 7) { risco = "ALTO RISCO"; conduta = "Resposta clínica de emergência (Time de Resposta Rápida/UTI)."; color = "text-red-500"; }
                else if(score >= 5 || parametroIsoladoCritico) { risco = "MÉDIO RISCO"; conduta = "Revisão médica urgente. Aumento da frequência de monitorização."; color = "text-orange-500"; }
                else if(score >= 1) { risco = "BAIXO RISCO"; conduta = "Aumentar monitorização (a cada 4-6h). Avaliação médica se necessário."; color = "text-yellow-500"; }
                else { risco = "RISCO CLÍNICO MÍNIMO"; conduta = "Manter rotina de monitorização (a cada 12h)."; color = "text-green-500"; }

                $('#calcResult').html(`Escore Total: <span class="${color} text-2xl">${score}</span><br>
                    <div class="mt-3 text-sm border border-slate-600/50 p-3 rounded bg-black/30">
                        <span class="font-bold block mb-1 ${color}">${risco}</span>
                        <span class="font-normal text-gray-300">${conduta}</span>
                    </div>
                `).removeClass('hidden');
            }
        """
    },
    "calc_risco_cardio.html": {
        "titulo": "Risco Cardiovascular (Framingham)",
        "icone": "fa-heart",
        "cor_icone": "red-500",
        "formulario": """
            <div class="grid grid-cols-2 gap-4 mb-3">
                <div><label class="text-xs font-bold text-gray-400 uppercase">Idade (anos)</label><input type="number" id="fIdade" class="input-form" placeholder="30 a 74"></div>
                <div><label class="text-xs font-bold text-gray-400 uppercase">Sexo</label>
                    <select id="fSexo" class="input-form"><option value="M">Masculino</option><option value="F">Feminino</option></select>
                </div>
            </div>
            <div class="grid grid-cols-2 gap-4 mb-3">
                <div><label class="text-xs font-bold text-gray-400 uppercase">Colesterol Total</label><input type="number" id="fCT" class="input-form" placeholder="mg/dL"></div>
                <div><label class="text-xs font-bold text-gray-400 uppercase">Colesterol HDL</label><input type="number" id="fHDL" class="input-form" placeholder="mg/dL"></div>
            </div>
            <div class="grid grid-cols-2 gap-4 mb-3">
                <div><label class="text-xs font-bold text-gray-400 uppercase">Pressão Sistólica</label><input type="number" id="fPAS" class="input-form" placeholder="mmHg"></div>
                <div><label class="text-xs font-bold text-gray-400 uppercase">Trata Hipertensão?</label>
                    <select id="fTrataPAS" class="input-form"><option value="N">Não</option><option value="S">Sim</option></select>
                </div>
            </div>
            <div class="mb-4">
                <label class="text-xs font-bold text-gray-400 uppercase">Fatores Adicionais</label>
                <div class="flex gap-4 mt-2">
                    <label class="flex items-center gap-2 text-sm cursor-pointer"><input type="checkbox" id="fFumante" class="w-4 h-4 accent-red-500"> Fumante</label>
                    <label class="flex items-center gap-2 text-sm cursor-pointer"><input type="checkbox" id="fDiabetes" class="w-4 h-4 accent-red-500"> Diabetes</label>
                </div>
            </div>
            <button onclick="calcularFramingham()" class="btn-submit bg-red-500 hover:bg-red-600 shadow-red-500/30">Calcular Risco (10 Anos)</button>
        """,
        "script_js": """
            function calcularFramingham() {
                let idade = parseFloat($('#fIdade').val()); let ct = parseFloat($('#fCT').val());
                let hdl = parseFloat($('#fHDL').val()); let pas = parseFloat($('#fPAS').val());
                let sexo = $('#fSexo').val(); let trata = $('#fTrataPAS').val() === 'S';
                let fumante = $('#fFumante').is(':checked'); let diabetes = $('#fDiabetes').is(':checked');
                
                if(!idade || !ct || !hdl || !pas) { alert("Preencha todos os valores numéricos!"); return; }
                if(idade < 30 || idade > 74) { alert("Atenção: A calculadora de Framingham é mais precisa para idades entre 30 e 74 anos."); }
                
                let lnIdade = Math.log(idade); let lnCT = Math.log(ct); let lnHDL = Math.log(hdl); let lnPAS = Math.log(pas);
                let riskFactors = 0; let risk = 0;
                
                if(sexo === 'F') {
                    riskFactors = (2.32888 * lnIdade) + (1.20904 * lnCT) - (0.70833 * lnHDL) + 
                                  (trata ? 2.82263 * lnPAS : 2.76157 * lnPAS) + 
                                  (fumante ? 0.52873 : 0) + (diabetes ? 0.69154 : 0);
                    risk = 100 * (1 - Math.pow(0.9533, Math.exp(riskFactors - 26.1931)));
                } else {
                    riskFactors = (3.06117 * lnIdade) + (1.12370 * lnCT) - (0.93263 * lnHDL) + 
                                  (trata ? 1.99881 * lnPAS : 1.93303 * lnPAS) + 
                                  (fumante ? 0.65451 : 0) + (diabetes ? 0.57367 : 0);
                    risk = 100 * (1 - Math.pow(0.88936, Math.exp(riskFactors - 23.9802)));
                }
                
                let classificacao = ""; let cor = "";
                if(risk < 10) { classificacao = "Risco Baixo"; cor = "text-green-500"; }
                else if(risk <= 20) { classificacao = "Risco Intermediário"; cor = "text-yellow-500"; }
                else { classificacao = "Risco Alto"; cor = "text-red-500"; }
                
                $('#calcResult').html(`Risco em 10 anos: <span class="${cor} text-2xl">${risk.toFixed(1)}%</span><br>
                    <div class="mt-3 text-sm border border-slate-600/50 p-3 rounded bg-black/30">
                        <span class="font-bold block mb-1 ${cor}">${classificacao}</span>
                        <span class="font-normal text-gray-300">Probabilidade de sofrer um evento cardiovascular maior na próxima década.</span>
                    </div>
                `).removeClass('hidden');
            }
        """
    },
    "calc_prevent.html": {
        "titulo": "Calculadora PREVENT (AHA) - Teste",
        "icone": "fa-heartbeat",
        "cor_icone": "red-500",
        "formulario": """
            <div class="alert-box">
                <strong><i class="fas fa-exclamation-triangle"></i> Versão de Protótipo e UI/UX</strong><br>
                Esta interface foi desenhada para estudos de usabilidade contendo os novos parâmetros do escore PREVENT (2023). O cálculo atual emite um valor aproximado para testes de fluxo. Para uso clínico, a matriz completa de coeficientes da AHA deve ser integrada ao backend.
            </div>
            <div class="grid grid-cols-2 gap-4 mb-4">
                <div>
                    <label class="label-title">Idade (anos)</label>
                    <input type="number" id="pIdade" class="input-form" placeholder="30 a 79">
                </div>
                <div>
                    <label class="label-title">Sexo Biológico</label>
                    <select id="pSexo" class="input-form">
                        <option value="F">Feminino</option>
                        <option value="M">Masculino</option>
                    </select>
                </div>
            </div>
            <div class="grid grid-cols-2 gap-4 mb-4">
                <div>
                    <label class="label-title">Colesterol Total (mg/dL)</label>
                    <input type="number" id="pCT" class="input-form" placeholder="130 a 320">
                </div>
                <div>
                    <label class="label-title">Colesterol HDL (mg/dL)</label>
                    <input type="number" id="pHDL" class="input-form" placeholder="20 a 100">
                </div>
            </div>
            <div class="grid grid-cols-2 gap-4 mb-4">
                <div>
                    <label class="label-title">Pressão Sistólica (mmHg)</label>
                    <input type="number" id="pPAS" class="input-form" placeholder="90 a 200">
                </div>
                <div>
                    <label class="label-title">Trata Hipertensão?</label>
                    <select id="pTrataPAS" class="input-form">
                        <option value="N">Não</option>
                        <option value="S">Sim</option>
                    </select>
                </div>
            </div>
            <div class="grid grid-cols-2 gap-4 mb-4">
                <div>
                    <label class="label-title">eGFR (Função Renal)</label>
                    <input type="number" id="pGFR" class="input-form" placeholder="mL/min/1.73m² (Ex: 90)">
                </div>
                <div>
                    <label class="label-title">IMC (Índice de Massa)</label>
                    <input type="number" step="0.1" id="pIMC" class="input-form" placeholder="kg/m² (Ex: 25.5)">
                </div>
            </div>
            <div class="mb-2">
                <label class="label-title">Histórico e Medicações</label>
                <div class="flex flex-wrap gap-4 mt-3">
                    <label class="flex items-center gap-2 text-sm cursor-pointer hover:text-red-400 transition">
                        <input type="checkbox" id="pFumante" class="w-4 h-4 accent-red-500"> Tabagismo
                    </label>
                    <label class="flex items-center gap-2 text-sm cursor-pointer hover:text-red-400 transition">
                        <input type="checkbox" id="pDiabetes" class="w-4 h-4 accent-red-500"> Diabetes
                    </label>
                    <label class="flex items-center gap-2 text-sm cursor-pointer hover:text-red-400 transition">
                        <input type="checkbox" id="pStatina" class="w-4 h-4 accent-red-500"> Uso de Estatina
                    </label>
                </div>
            </div>
            <button onclick="calcularPreventMock()" class="btn-submit bg-red-500 hover:bg-red-600 shadow-red-500/30">Estimar Risco (10 Anos)</button>
        """,
        "script_js": """
            function calcularPreventMock() {
                let idade = parseFloat($('#pIdade').val());
                let sexo = $('#pSexo').val();
                let ct = parseFloat($('#pCT').val());
                let hdl = parseFloat($('#pHDL').val());
                let pas = parseFloat($('#pPAS').val());
                let egfr = parseFloat($('#pGFR').val());
                let imc = parseFloat($('#pIMC').val());
                
                if(!idade || !ct || !hdl || !pas || !egfr || !imc) { 
                    alert("Por favor, preencha todos os campos numéricos para realizar a simulação."); 
                    return; 
                }
                
                let baseRisco = (idade - 30) * 0.15; 
                if (sexo === 'M') baseRisco += 1.5;
                if (ct > 200) baseRisco += (ct - 200) * 0.02;
                if (hdl < 40) baseRisco += (40 - hdl) * 0.05;
                if (pas > 120) baseRisco += (pas - 120) * 0.04;
                if ($('#pTrataPAS').val() === 'S') baseRisco += 0.5;
                
                if (egfr < 60) baseRisco += (60 - egfr) * 0.1;
                if (imc > 30) baseRisco += (imc - 30) * 0.1;   
                
                if ($('#pFumante').is(':checked')) baseRisco *= 1.5;
                if ($('#pDiabetes').is(':checked')) baseRisco *= 1.4;
                if ($('#pStatina').is(':checked')) baseRisco *= 0.8;

                let riscoFinal = Math.max(1.0, Math.min(baseRisco, 40.0));

                let classificacao = ""; let cor = ""; let recomendacao = "";
                if(riscoFinal < 5) { 
                    classificacao = "Risco Baixo"; cor = "text-green-500"; recomendacao = "Ênfase em estilo de vida saudável.";
                }
                else if(riscoFinal < 7.5) { 
                    classificacao = "Risco Limítrofe (Borderline)"; cor = "text-yellow-400"; recomendacao = "Considerar discussão sobre riscos.";
                }
                else if(riscoFinal < 20) { 
                    classificacao = "Risco Intermediário"; cor = "text-orange-500"; recomendacao = "Recomendado iniciar/intensificar estatinas.";
                }
                else { 
                    classificacao = "Risco Alto"; cor = "text-red-500"; recomendacao = "Forte recomendação para terapia intensiva com estatinas.";
                }
                
                $('#calcResult').html(`
                    Risco de Doença Cardiovascular (10 Anos): <br>
                    <span class="${cor} text-4xl">${riscoFinal.toFixed(1)}%</span><br>
                    <div class="mt-4 text-sm border border-slate-600/50 p-4 rounded bg-black/40 text-left">
                        <span class="font-bold block mb-2 ${cor} uppercase text-center">${classificacao}</span>
                        <span class="font-normal text-gray-300"><i class="fas fa-info-circle mr-1"></i> ${recomendacao}</span>
                    </div>
                `).removeClass('hidden');
            }
        """
    }
}

# 3. Gerador: Laço de repetição para criar os 7 arquivos
for nome_arquivo, dados in calculadoras.items():
    conteudo_final = html_template.format(
        titulo=dados["titulo"],
        icone=dados["icone"],
        cor_icone=dados["cor_icone"],
        formulario=dados["formulario"],
        script_js=dados["script_js"]
    )
    
    with open(nome_arquivo, "w", encoding="utf-8") as arquivo:
        arquivo.write(conteudo_final)
        
    print(f"Sucesso: {nome_arquivo} criado!")

print("Todas as 7 calculadoras foram geradas com sucesso. Prontas para o GitHub!")