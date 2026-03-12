import json
import time
from selenium import webdriver
from selenium.webdriver.common.by import By

# Configuração para capturar logs do navegador (onde o JS vai jogar os dados)
options = webdriver.ChromeOptions()
options.set_capability('goog:loggingPrefs', {'browser': 'ALL'})

driver = webdriver.Chrome(options=options)
driver.get("https://www.google.com")  # Troque pela página inicial desejada

# Script JS para gerar um seletor CSS único quando clicar
js_injector = """
document.addEventListener('click', function(e) {
    e.preventDefault(); // Impede o clique real para não navegar (opcional)
    
    // Função simples para gerar caminho CSS
    function getCssPath(el) {
        if (!(el instanceof Element)) return;
        var path = [];
        while (el.nodeType === Node.ELEMENT_NODE) {
            var selector = el.nodeName.toLowerCase();
            if (el.id) {
                selector += '#' + el.id;
                path.unshift(selector);
                break;
            } else {
                var sib = el, nth = 1;
                while (sib = sib.previousElementSibling) {
                    if (sib.nodeName.toLowerCase() == selector)
                       nth++;
                }
                if (nth != 1)
                    selector += ":nth-of-type("+nth+")";
            }
            path.unshift(selector);
            el = el.parentNode;
        }
        return path.join(" > ");
    }
    
    var fullPath = getCssPath(e.target);
    console.log("ELEMENTO_CAPTURADO|" + fullPath);
    alert("Elemento Capturado: " + fullPath); // Feedback visual
}, true);
"""

# Injeta o JS na página
driver.execute_script(js_injector)

print("--- MODO DE GRAVAÇÃO ---")
print("Clique nos elementos que deseja automatizar.")
print("Pressione CTRL+C no terminal para parar e salvar.")

passos = []

try:
    while True:
        # Lê os logs do console do navegador
        logs = driver.get_log('browser')
        for entry in logs:
            mensagem = entry['message']
            if "ELEMENTO_CAPTURADO|" in mensagem:
                # Limpa a string para pegar só o seletor
                seletor = mensagem.split("ELEMENTO_CAPTURADO|")[1].replace('"', '').replace("'", "")
                # Remove lixo extra do log se houver
                if " " in seletor and seletor.endswith("source"): 
                    seletor = seletor.split(" ")[0]
                
                print(f"Capturado: {seletor}")
                passos.append({"acao": "click", "seletor": seletor})
        time.sleep(1)

except KeyboardInterrupt:
    print("\nGravacão finalizada. Salvando passos...")
    with open('automacao.json', 'w') as f:
        json.dump(passos, f, indent=4)
    print("Arquivo 'automacao.json' salvo com sucesso!")
    driver.quit()