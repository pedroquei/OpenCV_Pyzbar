import cv2
import pytesseract
from pyzbar import pyzbar
import re
import threading
import time
import dataSave # Seu módulo para salvar em CSV

# --- CONFIGURAÇÕES E VARIÁVEIS GLOBAIS ---
pytesseract.pytesseract.tesseract_cmd = r'C:/Program Files/Tesseract-OCR/tesseract.exe'

frame_global = None
dados_display = {
    'barcode_rects': [],
    'status_obj': 'AGUARDANDO...',
    'status_end': 'AGUARDANDO...'
}
lock = threading.Lock()
executando = True

# --- FUNÇÕES AUXILIARES (sem grandes alterações) ---

def set_best_resolution(cap):
    resolutions = [(1920, 1080), (1280, 720)]
    for w, h in resolutions:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
        real_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        real_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        if real_w == w and real_h == h:
            print(f"Resolução configurada para: {real_w}x{real_h}")
            return
    print(f"Usando resolução padrão: {int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x{int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))}")

# --- THREADS DE CAPTURA E PROCESSAMENTO (LÓGICA PRINCIPAL AQUI) ---

def captura_continua(cap):
    """Thread que lê continuamente os frames da câmera."""
    global frame_global, executando
    while executando:
        ret, frame = cap.read()
        if ret:
            with lock:
                frame_global = frame.copy()
        time.sleep(0.01) # Pequena pausa para não sobrecarregar a CPU

def processamento_continuo():
    """Thread que processa os frames, pareia os códigos e salva no log."""
    global frame_global, dados_display, executando
    
    # Variáveis de estado locais para esta thread
    codigo_obj = None
    codigo_endereco = None

    while executando:
        frame_para_processar = None
        with lock:
            if frame_global is not None:
                frame_para_processar = frame_global.copy()
        
        if frame_para_processar is not None:
            gray = cv2.cvtColor(frame_para_processar, cv2.COLOR_BGR2GRAY)
            barcodes = pyzbar.decode(gray)
            
            barcode_rects_neste_frame = []

            for barcode in barcodes:
                barcode_data = barcode.data.decode('utf-8')
                barcode_rects_neste_frame.append(barcode.rect)

                # Lógica de atualização de estado
                if barcode_data.upper().startswith('OBJ;'):
                    if codigo_obj != barcode_data:
                        codigo_obj = barcode_data
                        print(f"[PROCESSAMENTO] Objeto atualizado: {codigo_obj}")
                elif barcode_data.upper().startswith('APT;'):
                    if codigo_endereco != barcode_data:
                        codigo_endereco = barcode_data
                        print(f"[PROCESSAMENTO] Endereço atualizado: {codigo_endereco}")

            # Lógica de salvamento
            if codigo_obj and codigo_endereco:
                print("\n--- [PROCESSAMENTO] PAR COMPLETO DETECTADO ---")
                dataSave.adicionarLog(codigo_obj, codigo_endereco)
                
                # Reseta o estado para a próxima leitura
                codigo_obj = None
                codigo_endereco = None
                
                print("[PROCESSAMENTO] RESETADO. Aguardando próximo par...")
                time.sleep(2) # Pausa para evitar rescanear imediatamente

            # Atualiza os dados para a thread de exibição
            with lock:
                dados_display['barcode_rects'] = barcode_rects_neste_frame
                dados_display['status_obj'] = f"Objeto: {codigo_obj if codigo_obj else '...'}"
                dados_display['status_end'] = f"Endereco: {codigo_endereco if codigo_endereco else '...'}"
        
        time.sleep(0.1) # Processa ~10 frames por segundo

# --- BLOCO PRINCIPAL (INICIALIZAÇÃO E LOOP DE EXIBIÇÃO) ---

def main():
    global executando

    cap = cv2.VideoCapture(0) # Use o índice correto
    if not cap.isOpened():
        print("Erro: Não foi possível abrir a câmera.")
        return

    set_best_resolution(cap)

    # Inicia as threads
    thread_captura = threading.Thread(target=captura_continua, args=(cap,), daemon=True)
    thread_processamento = threading.Thread(target=processamento_continuo, daemon=True)
    
    thread_captura.start()
    thread_processamento.start()

    print("Iniciando scanner... Pressione 'q' para sair.")
    print("-" * 40)

    # Loop principal (apenas para exibição)
    while True:
        frame_para_exibir = None
        dados_para_exibir = None

        with lock:
            if frame_global is not None:
                frame_para_exibir = frame_global.copy()
            dados_para_exibir = dados_display.copy()

        if frame_para_exibir is None:
            time.sleep(0.01)
            continue
        
        # Desenha os retângulos dos barcodes detectados no frame atual
        if dados_para_exibir and dados_para_exibir['barcode_rects']:
            for rect in dados_para_exibir['barcode_rects']:
                x, y, w, h = rect
                cv2.rectangle(frame_para_exibir, (x, y), (x + w, y + h), (0, 255, 0), 2)
        
        # Desenha o painel de status
        cv2.rectangle(frame_para_exibir, (0,0), (650, 80), (0,0,0), -1)
        cv2.putText(frame_para_exibir, dados_para_exibir['status_obj'], (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 0), 1)
        cv2.putText(frame_para_exibir, dados_para_exibir['status_end'], (10, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 0), 1)

        cv2.imshow("Scanner Assíncrono - Pareamento de Barcodes", frame_para_exibir)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            executando = False
            break

    # Encerramento
    print("Encerrando...")
    time.sleep(0.5) # Dá um tempo para as threads terminarem
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()