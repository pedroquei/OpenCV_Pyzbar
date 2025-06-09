import cv2
from pyzbar import pyzbar

# Inicializa a câmera
cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Decodifica códigos de barras no frame
    barcodes = pyzbar.decode(frame)

    for barcode in barcodes:
        # Extraia as coordenadas do retângulo ao redor do código
        (x, y, w, h) = barcode.rect
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

        # Decodifica o valor (dados) e tipo do código de barras
        barcode_data = barcode.data.decode("utf-8")
        barcode_type = barcode.type

        # Exibe o tipo e os dados decodificados na imagem
        text = f"{barcode_type}: {barcode_data}"
        cv2.putText(frame, text, (x, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        print(f"Tipo: {barcode_type}, Dados: {barcode_data}")

    # Exibe o resultado
    cv2.imshow("Leitor de Código de Barras", frame)

    # Sai do loop com 'q'
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()