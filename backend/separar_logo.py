import cv2
import os

def dividir_colunas_finais():
    print("--- Iniciando Separação Final ---")
    
    # 1. Define onde procurar as imagens geradas anteriormente
    diretorio_atual = os.getcwd()
    pasta_origem = os.path.join(diretorio_atual, 'icones_portal_final')
    pasta_destino = os.path.join(diretorio_atual, 'icones_portal_prontos') # Nova pasta final

    if not os.path.exists(pasta_origem):
        print(f"ERRO: Não encontrei a pasta '{pasta_origem}'.")
        print("Verifique se o passo anterior criou essa pasta.")
        return

    if not os.path.exists(pasta_destino):
        os.makedirs(pasta_destino)

    # 2. Mapeamento: Arquivo Coluna -> [Nome do Card de Cima, Nome do Card de Baixo]
    # O script anterior usou os primeiros nomes da lista para salvar as colunas.
    tarefas = {
        "sisreg_painel_regulacao.png": ["sisreg_painel_regulacao.png", "metas_contrato_qualidade.png"],
        "ses_indicasus_leitos.png":    ["ses_indicasus_leitos.png",    "producao_cirurgica.png"],
        "sus_faturamento.png":         ["sus_faturamento.png",         "sigtap_consulta.png"]
    }

    arquivos_processados = 0

    for arquivo_coluna, (nome_topo, nome_base) in tarefas.items():
        caminho_completo = os.path.join(pasta_origem, arquivo_coluna)
        
        if os.path.exists(caminho_completo):
            # Carrega a imagem da coluna
            img = cv2.imread(caminho_completo)
            h, w, _ = img.shape
            
            # 3. O Corte Mágico: Divide exatamente na metade da altura
            meio = h // 2
            
            # Recorta
            img_topo = img[0:meio, 0:w]     # Do topo até o meio
            img_base = img[meio:h, 0:w]     # Do meio até o fim
            
            # Salva na pasta nova
            cv2.imwrite(os.path.join(pasta_destino, nome_topo), img_topo)
            cv2.imwrite(os.path.join(pasta_destino, nome_base), img_base)
            
            print(f"Separado '{arquivo_coluna}' em: \n  -> {nome_topo}\n  -> {nome_base}")
            arquivos_processados += 1
        else:
            print(f"AVISO: Arquivo '{arquivo_coluna}' não encontrado na pasta de origem.")

    if arquivos_processados > 0:
        print("-" * 40)
        print(f"SUCESSO! {arquivos_processados * 2} ícones gerados.")
        print(f"Verifique a pasta final: 'icones_portal_prontos'")
    else:
        print("Nenhum arquivo foi processado. Verifique os nomes na pasta 'icones_portal_final'.")

if __name__ == "__main__":
    dividir_colunas_finais()