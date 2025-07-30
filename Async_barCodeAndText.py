import cv2
import pytesseract
from pyzbar import pyzbar
import re
import threading
import time

# Caminho do Tesseract
pytesseract.pytesseract.tesseract_cmd = r'C:/Program Files/Tesseract-OCR/tesseract.exe'

# Variáveis globais
frame_global = None
dados_global = None
lock = threading.Lock()
executando = True

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

    # 1. Barcode
    barcodes = pyzbar.decode(gray)
    if barcodes:
        b_info = barcodes[0]
        b_data = b_info.data.decode('utf-8')
        b_rect = b_info.rect
        resultados['barcode_info'] = {'data': b_data, 'rect': b_rect}

    # 2. OCR
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    config = '-l por --psm 6'
    texto_ocr_completo = pytesseract.image_to_string(thresh, config=config)

    # 3. Regex
    padrao_objeto = r"Objeto:\s*(\d{8})"
    match_objeto = re.search(padrao_objeto, texto_ocr_completo, re.IGNORECASE)
    if match_objeto:
        resultados['ocr_info_objeto'] = {'objeto': match_objeto.group(1)}

    padrao_endereco = r"(\d{3})\s+(\d{3})\s+(\d{3})\s+(\d{3})\s+(\d{3})\s+(\d{3})"
    match_endereco = re.search(padrao_endereco, texto_ocr_completo)
    if match_endereco:
        resultados['ocr_info_endereco'] = {
            'cidade': match_endereco.group(1),
            'bairro': match_endereco.group(2),
            'rua': match_endereco.group(3),
            'predio': match_endereco.group(4),
            'nivel': match_endereco.group(5),
            'apartamento': match_endereco.group(6)
        }

    return resultados

# Thread: Captura contínua de frames
def captura_continua(cap):
    global frame_global, executando
    while executando:
        ret, frame = cap.read()
        if not ret:
            continue
        with lock:
            frame_global = frame.copy()

# Thread: Processamento do OCR/barcode
def processamento_continuo():
    global frame_global, dados_global, executando
    while executando:
        try:
            time.sleep(0.05)
            frame_copia = None
            with lock:
                if frame_global is not None:
                    frame_copia = frame_global.copy()
            if frame_copia is not None:
                dados = extrair_dados_da_etiqueta_live(frame_copia)
                with lock:
                    dados_global = dados
        except Exception as e:
            print(f"[Erro na thread de processamento] {e}")

# Inicialização da câmera
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Erro: Não foi possível abrir a câmera.")
    exit()

set_best_resolution(cap)

# Início das threads
threading.Thread(target=captura_continua, args=(cap,), daemon=True).start()
threading.Thread(target=processamento_continuo, daemon=True).start()

print("Iniciando scanner... Pressione 'q' para sair.")
print("-" * 40)

# Loop principal de exibição
while True:
    with lock:
        frame = frame_global.copy() if frame_global is not None else None
        dados = dados_global.copy() if dados_global is not None else None

    if frame is None:
        continue

    if dados:
        if dados['barcode_info']:
            info = dados['barcode_info']
            x, y, w, h = info['rect']
            barcode_text = f"{info['data']}"
            print(f"BARCODE LIDO -> {barcode_text}")
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(frame, barcode_text, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

        if dados['ocr_info_objeto']:
            info = dados['ocr_info_objeto']
            ocr_text = f"OCR Objeto: {info['objeto']}"
            print(f"OCR LIDO (Objeto) -> {ocr_text}")
            cv2.putText(frame, ocr_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        if dados['ocr_info_endereco']:
            info = dados['ocr_info_endereco']
            addr_text = f"C:{info['cidade']} B:{info['bairro']} R:{info['rua']} P:{info['predio']} N:{info['nivel']} A:{info['apartamento']}"
            print(f"OCR LIDO (Endereco) -> {addr_text}")
            cv2.putText(frame, addr_text, (10, frame.shape[0] - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)

    cv2.imshow("Scanner Híbrido - Barcode e OCR (Assíncrono)", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Encerramento
executando = False
time.sleep(0.5)
cap.release()
cv2.destroyAllWindows()
