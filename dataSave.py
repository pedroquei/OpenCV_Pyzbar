import csv
from datetime import datetime
import os

def adicionarLog(objeto, endereco, arquivo='log_leituras.csv'):
    colunas = ['Timestamp', 'Objeto', 'Endereço']
    
    # Verifica se o arquivo precisa de um cabeçalho
    escrever_cabecalho = not os.path.exists(arquivo)

    try:
        with open(arquivo, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Escreve o cabeçalho apenas se o arquivo for novo
            if escrever_cabecalho:
                writer.writerow(colunas)
            
            # Escreve a nova linha de dados
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            writer.writerow([timestamp, objeto, endereco])
            print(f"[INFO] Dados salvos com sucesso!")
        return
    
    except Exception as e:
        print(f"[ERRO] Falha ao salvar no log: {e}")
        return