import cv2
import pytesseract
from pyzbar import pyzbar
import re
import dataSave
import time

pytesseract.pytesseract.tesseract_cmd = r'C:/Program Files/Tesseract-OCR/tesseract.exe'

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

def extrair_dados_da_etiqueta_live(frame):
    resultados = {
        'barcode_info': None,
        'ocr_info_objeto': None,
        'ocr_info_endereco': None
    }
    
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Barcode
    barcodes = pyzbar.decode(gray)
    if barcodes:
        b_info = barcodes[0]
        b_data = b_info.data.decode('utf-8')
        b_rect = b_info.rect
        resultados['barcode_info'] = {'data': b_data, 'rect': b_rect}

    # OCR
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    config = '-l por --psm 6'
    texto_ocr_completo = pytesseract.image_to_string(thresh, config=config)
    
    # Regex para Objeto
    padrao_objeto = r"Objeto:\s*(\d+)"
    match_objeto = re.search(padrao_objeto, texto_ocr_completo, re.IGNORECASE)
    if match_objeto:
        resultados['ocr_info_objeto'] = {'objeto': match_objeto.group(1)}

    # Regex para Endereço
    padrao_endereco = r"(\d{3})\s+(\d{3})\s+(\d{3})\s+(\d{3})\s+(\d{3})\s+(\d{3})"
    match_endereco = re.search(padrao_endereco, texto_ocr_completo)
    if match_endereco:
        resultados['ocr_info_endereco'] = {
            'cidade': match_endereco.group(1), 'bairro': match_endereco.group(2),
            'rua': match_endereco.group(3), 'predio': match_endereco.group(4),
            'nivel': match_endereco.group(5), 'apartamento': match_endereco.group(6)
        }
    
    return resultados

# --- FUNÇÃO PRINCIPAL ---
def main():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Erro: Não foi possível abrir a câmera.")
        return 

    set_best_resolution(cap)

    print("Iniciando scanner... Pressione 'q' para sair.")
    print("Aproxime o código do OBJETO ou ENDEREÇO.")
    print("-" * 40)

    codigo_obj = None
    codigo_endereco = None

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        dados = extrair_dados_da_etiqueta_live(frame)
        display_frame = frame.copy()

        # --- LÓGICA DE PAREAMENTO E SALVAMENTO ---
        if dados['barcode_info']:
            barcode_data = dados['barcode_info']['data']
            
            if barcode_data.upper().startswith('OBJ;'):
                if codigo_obj != barcode_data:
                    codigo_obj = barcode_data
                    print(f"[ESTADO] Objeto atualizado: {codigo_obj}")
            elif barcode_data.upper().startswith('APT;'):
                if codigo_endereco != barcode_data:
                    codigo_endereco = barcode_data
                    print(f"[ESTADO] Endereço atualizado: {codigo_endereco}")

        if codigo_obj and codigo_endereco:
            print("\n--- PAR COMPLETO DETECTADO ---")
            dataSave.adicionarLog(codigo_obj, codigo_endereco)
            
            codigo_obj = None
            codigo_endereco = None
            
            print("RESETADO. Aguardando próximo par...")
            print("-" * 40)
            
            time.sleep(2)
            continue

        # Desenha o retângulo se um barcode foi detectado NESTE frame
        if dados['barcode_info']:
            info = dados['barcode_info']
            x, y, w, h = info['rect']
            cv2.rectangle(display_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(display_frame, info['data'], (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

        # Exibe os resultados do OCR para debug
        if dados['ocr_info_objeto']:
            info = dados['ocr_info_objeto']
            ocr_text = f"OCR Objeto: {info['objeto']}"
            cv2.putText(display_frame, ocr_text, (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        if dados['ocr_info_endereco']:
            info = dados['ocr_info_endereco']
            addr_text = f"C:{info['cidade']} B:{info['bairro']} R:{info['rua']}"
            cv2.putText(display_frame, addr_text, (10, display_frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        
        cv2.imshow("Scanner Híbrido", display_frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    print("Encerrando...")
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()