import cv2
import os
import shutil
import sys
from datetime import datetime

from viewer import iniciar_viewer

PASTA_IMAGENS    = "images"
PASTA_ORIGINAIS  = os.path.join("resultados", "originais")
PASTA_DETECTADOS = os.path.join("resultados", "detectados")
RELATORIO        = "relatorio_dados.txt"

EXPERIMENTOS_FACES = [
    ("_face_default", {"scaleFactor": 1.10, "minNeighbors": 5, "minSize": (30, 30)}, (  0, 255,   0)),
    ("_face_sf105",   {"scaleFactor": 1.05, "minNeighbors": 5, "minSize": (30, 30)}, (255,   0,   0)),
    ("_face_sf130",   {"scaleFactor": 1.30, "minNeighbors": 5, "minSize": (30, 30)}, (  0,   0, 255)),
    ("_face_mn3",     {"scaleFactor": 1.10, "minNeighbors": 3, "minSize": (30, 30)}, (  0, 255, 255)),
    ("_face_mn8",     {"scaleFactor": 1.10, "minNeighbors": 8, "minSize": (30, 30)}, (255,   0, 255)),
]


def carregar_imagens():
    if not os.path.isdir(PASTA_IMAGENS):
        print(f"[ERRO] Pasta '{PASTA_IMAGENS}' não encontrada.")
        sys.exit(1)
    arquivos = [
        os.path.join(PASTA_IMAGENS, f)
        for f in sorted(os.listdir(PASTA_IMAGENS))
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
    ]
    if not arquivos:
        print(f"[ERRO] Nenhuma imagem encontrada em '{PASTA_IMAGENS}'.")
        sys.exit(1)
    return arquivos


def carregar_classificador(xml):
    path = cv2.data.haarcascades + xml
    clf  = cv2.CascadeClassifier(path)
    if clf.empty():
        raise RuntimeError(f"Classificador não encontrado: {xml}")
    return clf


def ler_imagem(caminho):
    img = cv2.imread(caminho)
    if img is None:
        raise RuntimeError(f"Não foi possível ler: {caminho}")
    return img, cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


def salvar_resultado(img, caminho_origem, sufixo):
    os.makedirs(PASTA_DETECTADOS, exist_ok=True)
    stem    = os.path.splitext(os.path.basename(caminho_origem))[0]
    destino = os.path.join(PASTA_DETECTADOS, f"{stem}{sufixo}.jpg")
    cv2.imwrite(destino, img)
    return destino


def processar_imagem(caminho, clf_face, clf_eye, clf_smile):
    img_base, gray = ler_imagem(caminho)

    os.makedirs(PASTA_ORIGINAIS, exist_ok=True)
    shutil.copy2(caminho, os.path.join(PASTA_ORIGINAIS, os.path.basename(caminho)))

    dados = {"arquivo": os.path.basename(caminho)}

    for sufixo, params, cor in EXPERIMENTOS_FACES:
        img   = img_base.copy()
        faces = clf_face.detectMultiScale(gray, **params)
        for (x, y, w, h) in faces:
            cv2.rectangle(img, (x, y), (x + w, y + h), cor, 2)
        salvar_resultado(img, caminho, sufixo)
        dados[sufixo] = len(faces)

    img         = img_base.copy()
    faces       = clf_face.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
    total_olhos = 0
    for (x, y, w, h) in faces:
        cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)
        roi_gray     = gray[y:y + h, x:x + w]
        roi_bgr      = img[y:y + h, x:x + w]
        olhos        = clf_eye.detectMultiScale(roi_gray, scaleFactor=1.02, minNeighbors=4)
        total_olhos += len(olhos)
        for (ex, ey, ew, eh) in olhos:
            cv2.rectangle(roi_bgr, (ex, ey), (ex + ew, ey + eh), (255, 0, 0), 2)
    salvar_resultado(img, caminho, "_eye")
    dados["_eye"] = {"faces": len(faces), "olhos": total_olhos}

    img             = img_base.copy()
    faces           = clf_face.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
    total_sorrisos  = 0
    for (x, y, w, h) in faces:
        cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)
        roi_gray        = gray[y:y + h, x:x + w]
        roi_bgr         = img[y:y + h, x:x + w]
        sorrisos        = clf_smile.detectMultiScale(roi_gray, scaleFactor=1.7, minNeighbors=22, minSize=(25, 25))
        total_sorrisos += len(sorrisos)
        for (sx, sy, sw, sh) in sorrisos:
            cv2.rectangle(roi_bgr, (sx, sy), (sx + sw, sy + sh), (0, 0, 255), 2)
    salvar_resultado(img, caminho, "_smile")
    dados["_smile"] = {"faces": len(faces), "sorrisos": total_sorrisos}

    return dados


def processar_todas(caminhos):
    print("\n=== PROCESSANDO IMAGENS ===")
    clf_face  = carregar_classificador("haarcascade_frontalface_default.xml")
    clf_eye   = carregar_classificador("haarcascade_eye.xml")
    clf_smile = carregar_classificador("haarcascade_smile.xml")

    todos_dados = []
    for caminho in caminhos:
        print(f"\n  Processando: {os.path.basename(caminho)}")
        try:
            todos_dados.append(processar_imagem(caminho, clf_face, clf_eye, clf_smile))
        except RuntimeError as e:
            print(f"  [AVISO] {e}")

    gerar_relatorio(todos_dados)
    return todos_dados


def gerar_relatorio(todos_dados):
    agora  = datetime.now().strftime("%Y-%m-%d %H:%M")
    linhas = [f"=== RELATÓRIO DE EXPERIMENTOS HAAR CASCADE ===", f"Data: {agora}", ""]
    for d in todos_dados:
        linhas += [
            f"--- Imagem: {d['arquivo']} ---",
            f"  Parte 1  face padrão:    {d.get('_face_default', '-')} faces",
            f"  Parte 2A sf=1.05:        {d.get('_face_sf105',   '-')} faces",
            f"  Parte 2B sf=1.30:        {d.get('_face_sf130',   '-')} faces",
            f"  Parte 2C mn=3:           {d.get('_face_mn3',     '-')} faces",
            f"  Parte 2D mn=8:           {d.get('_face_mn8',     '-')} faces",
        ]
        if "_eye" in d:
            linhas.append(f"  Parte 3  olhos:          {d['_eye']['faces']} faces, {d['_eye']['olhos']} olhos")
        if "_smile" in d:
            linhas.append(f"  Parte 3  sorriso:        {d['_smile']['faces']} faces, {d['_smile']['sorrisos']} sorrisos")
        linhas.append("")

    with open(RELATORIO, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas))
    print(f"\n  Relatório salvo: {RELATORIO}")


def main():
    caminhos = carregar_imagens()
    processar_todas(caminhos)
    print("\n=== ABRINDO VISUALIZADOR ===\n  (↑↓ para navegar, Esc para fechar)")
    iniciar_viewer()


if __name__ == "__main__":
    main()
