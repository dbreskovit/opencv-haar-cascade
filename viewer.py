import cv2
import os
import tkinter as tk

from PIL import Image, ImageTk

PASTA_DETECTADOS = os.path.join("resultados", "detectados")

SUFIXO_LABEL = {
    "_face_default": "Face — padrão",
    "_face_sf105":   "Face — scaleFactor=1.05",
    "_face_sf130":   "Face — scaleFactor=1.30",
    "_face_mn3":     "Face — minNeighbors=3",
    "_face_mn8":     "Face — minNeighbors=8",
    "_eye":          "Olhos",
    "_smile":        "Sorriso",
}

ORDEM_SUFIXOS = list(SUFIXO_LABEL.keys())

BG_DARK  = "#1e1e2e"
BG_PANEL = "#181825"
BG_SEL   = "#313244"
FG_MAIN  = "#cdd6f4"
FG_SUB   = "#a6adc8"
FG_GROUP = "#89b4fa"
ACCENT   = "#89dceb"


def listar_resultados_ordenados():
    if not os.path.isdir(PASTA_DETECTADOS):
        return []

    entradas = []
    for nome in os.listdir(PASTA_DETECTADOS):
        if not nome.lower().endswith((".jpg", ".jpeg", ".png")):
            continue
        stem = os.path.splitext(nome)[0]
        sufixo_encontrado = None
        for suf in ORDEM_SUFIXOS:
            if stem.endswith(suf):
                sufixo_encontrado = suf
                break
        base = stem[: -len(sufixo_encontrado)] if sufixo_encontrado else stem
        entradas.append((
            os.path.join(PASTA_DETECTADOS, nome),
            base,
            sufixo_encontrado or "",
        ))

    entradas.sort(key=lambda e: (e[1], ORDEM_SUFIXOS.index(e[2]) if e[2] in ORDEM_SUFIXOS else 99))
    return entradas


class Visualizador:
    LARGURA_IMG = 820
    ALTURA_IMG  = 600

    def __init__(self, root, entradas):
        self.root     = root
        self.entradas = entradas
        self.sel      = 0

        root.title("Visualizador — Haar Cascade")
        root.configure(bg=BG_DARK)
        root.resizable(True, True)
        root.bind("<Up>",     lambda _: self.navegar(-1))
        root.bind("<Down>",   lambda _: self.navegar(+1))
        root.bind("<Escape>", lambda _: root.destroy())

        self._construir_layout()
        self._preencher_lista()
        self.selecionar(0)

    def _construir_layout(self):
        painel_esq = tk.Frame(self.root, bg=BG_PANEL, width=260)
        painel_esq.pack(side="left", fill="y")
        painel_esq.pack_propagate(False)

        tk.Label(
            painel_esq, text="Resultados", bg=BG_PANEL, fg=FG_GROUP,
            font=("Segoe UI", 10, "bold"), anchor="w", padx=10, pady=8,
        ).pack(fill="x")

        frame_lista = tk.Frame(painel_esq, bg=BG_PANEL)
        frame_lista.pack(fill="both", expand=True)

        scroll = tk.Scrollbar(frame_lista, orient="vertical", bg=BG_PANEL, troughcolor=BG_DARK)
        scroll.pack(side="right", fill="y")

        self.listbox = tk.Listbox(
            frame_lista,
            yscrollcommand=scroll.set,
            bg=BG_PANEL, fg=FG_MAIN,
            selectbackground=BG_SEL, selectforeground=ACCENT,
            activestyle="none",
            font=("Segoe UI", 9),
            borderwidth=0, highlightthickness=0,
            relief="flat",
        )
        self.listbox.pack(side="left", fill="both", expand=True)
        scroll.config(command=self.listbox.yview)
        self.listbox.bind("<<ListboxSelect>>", self._on_lista_clique)

        painel_dir = tk.Frame(self.root, bg=BG_DARK)
        painel_dir.pack(side="left", fill="both", expand=True)

        self.label_titulo = tk.Label(
            painel_dir, text="", bg=BG_DARK, fg=FG_MAIN,
            font=("Segoe UI", 11), anchor="w", padx=12, pady=6,
        )
        self.label_titulo.pack(fill="x")

        self.label_sub = tk.Label(
            painel_dir, text="", bg=BG_DARK, fg=FG_SUB,
            font=("Segoe UI", 9), anchor="w", padx=12, pady=0,
        )
        self.label_sub.pack(fill="x")

        self.canvas = tk.Canvas(
            painel_dir, bg=BG_PANEL, highlightthickness=0,
            width=self.LARGURA_IMG, height=self.ALTURA_IMG,
        )
        self.canvas.pack(padx=10, pady=8, expand=True)

        rodape = tk.Frame(painel_dir, bg=BG_DARK)
        rodape.pack(fill="x", padx=10, pady=(0, 8))

        self.label_contador = tk.Label(
            rodape, text="", bg=BG_DARK, fg=FG_SUB, font=("Segoe UI", 9),
        )
        self.label_contador.pack(side="left")

        tk.Label(
            rodape, text="↑↓ navegar  ·  Esc fechar",
            bg=BG_DARK, fg=BG_SEL, font=("Segoe UI", 9),
        ).pack(side="right")

    def _preencher_lista(self):
        grupo_anterior = None
        self.mapa_lista = []

        for i, (caminho, base, sufixo) in enumerate(self.entradas):
            if base != grupo_anterior:
                self.listbox.insert("end", f"  {base}")
                self.listbox.itemconfig("end", fg=FG_GROUP, selectbackground=BG_PANEL,
                                        selectforeground=FG_GROUP)
                self.mapa_lista.append(None)
                grupo_anterior = base

            label = SUFIXO_LABEL.get(sufixo, sufixo)
            self.listbox.insert("end", f"    {label}")
            self.mapa_lista.append(i)

    def _on_lista_clique(self, _evento):
        sel = self.listbox.curselection()
        if not sel:
            return
        idx_lista   = sel[0]
        idx_entrada = self.mapa_lista[idx_lista]
        if idx_entrada is None:
            for j in range(idx_lista + 1, len(self.mapa_lista)):
                if self.mapa_lista[j] is not None:
                    self.selecionar(self.mapa_lista[j])
                    self.listbox.selection_clear(0, "end")
                    self.listbox.selection_set(j)
                    return
        else:
            self.selecionar(idx_entrada)

    def navegar(self, delta):
        novo = (self.sel + delta) % len(self.entradas)
        self.selecionar(novo)
        for idx_lista, idx_entrada in enumerate(self.mapa_lista):
            if idx_entrada == novo:
                self.listbox.selection_clear(0, "end")
                self.listbox.selection_set(idx_lista)
                self.listbox.see(idx_lista)
                break

    def selecionar(self, idx_entrada):
        self.sel = idx_entrada
        caminho, base, sufixo = self.entradas[idx_entrada]

        label = SUFIXO_LABEL.get(sufixo, sufixo)
        self.label_titulo.config(text=f"{base}  ·  {label}")
        self.label_sub.config(text=os.path.basename(caminho))
        self.label_contador.config(text=f"{idx_entrada + 1} / {len(self.entradas)}")

        self._exibir_imagem(caminho)

    def _exibir_imagem(self, caminho):
        img_cv = cv2.imread(caminho)
        if img_cv is None:
            return
        img_rgb = cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB)
        h, w    = img_rgb.shape[:2]

        escala = min(self.LARGURA_IMG / w, self.ALTURA_IMG / h)
        novo_w = int(w * escala)
        novo_h = int(h * escala)

        pil_img    = Image.fromarray(img_rgb).resize((novo_w, novo_h), Image.LANCZOS)
        self._foto = ImageTk.PhotoImage(pil_img)

        self.canvas.delete("all")
        self.canvas.create_image(
            self.LARGURA_IMG // 2, self.ALTURA_IMG // 2,
            anchor="center", image=self._foto,
        )


def iniciar_viewer():
    entradas = listar_resultados_ordenados()
    if not entradas:
        print("[AVISO] Nenhum resultado encontrado em resultados/detectados/.")
        return

    root = tk.Tk()
    Visualizador(root, entradas)
    root.mainloop()
