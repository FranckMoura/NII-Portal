import os

print("--- 🔍 ANALISADOR DE DADOS SOULMV ---")

pasta_alvo = r"C:\Users\DELL\OneDrive\NII-Portal-Cloud\backend\bd_soulmv"
arquivo_saida = os.path.join(pasta_alvo, "resumo_para_o_gemini.txt")

with open(arquivo_saida, 'w', encoding='utf-8') as out:
    out.write("=== RESUMO DOS ARQUIVOS EXTRAÍDOS DO SOULMV ===\n\n")
    
    if not os.path.exists(pasta_alvo):
        print(f"❌ Pasta não encontrada: {pasta_alvo}")
        out.write(f"Erro: Pasta {pasta_alvo} não encontrada.\n")
    else:
        arquivos = os.listdir(pasta_alvo)
        
        for arq in arquivos:
            caminho_completo = os.path.join(pasta_alvo, arq)
            
            # --- SE FOR CSV ---
            if arq.lower().endswith('.csv'):
                print(f"Lendo CSV: {arq}...")
                out.write(f"=========================================\n")
                out.write(f"📁 ARQUIVO CSV: {arq}\n")
                out.write(f"=========================================\n")
                try:
                    # Usando latin1 pois o Oracle costuma exportar assim no Windows
                    with open(caminho_completo, 'r', encoding='latin1') as f:
                        linhas = f.readlines()
                        
                        total_linhas = len(linhas)
                        out.write(f"Total de linhas brutas: {total_linhas}\n\n")
                        
                        out.write(">>> PRIMEIRAS 5 LINHAS:\n")
                        for linha in linhas[:5]:
                            out.write(linha.strip() + "\n")
                            
                        out.write("\n>>> ÚLTIMAS 5 LINHAS:\n")
                        # Garante que não repete linhas se o arquivo for muito pequeno
                        inicio_ultimas = max(5, total_linhas - 5)
                        for linha in linhas[inicio_ultimas:]:
                            out.write(linha.strip() + "\n")
                            
                except Exception as e:
                    out.write(f"Erro ao ler {arq}: {e}\n")
                out.write("\n\n")
                
            # --- SE FOR TXT (SUAS QUERYs) ---
            elif arq.lower().endswith('.txt') and arq != "resumo_para_o_gemini.txt":
                print(f"Lendo Query (TXT): {arq}...")
                out.write(f"=========================================\n")
                out.write(f"📜 ARQUIVO DE QUERY: {arq}\n")
                out.write(f"=========================================\n")
                try:
                    with open(caminho_completo, 'r', encoding='utf-8') as f:
                        out.write(f.read() + "\n")
                except Exception as e:
                    try: # Tenta outra codificação se falhar
                        with open(caminho_completo, 'r', encoding='latin1') as f:
                            out.write(f.read() + "\n")
                    except Exception as e2:
                        out.write(f"Erro ao ler {arq}: {e2}\n")
                out.write("\n\n")

print(f"\n✅ Concluído! Abra a pasta bd_soulmv e copie o conteúdo do arquivo:")
print(f"-> resumo_para_o_gemini.txt")