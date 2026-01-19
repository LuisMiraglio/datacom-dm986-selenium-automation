# main.py
import threading
import tkinter as tk
from tkinter import ttk, font

from tkinter import messagebox  # usado en safe_messagebox
from logic_414 import ConfiguradorModem414

try:
    from logic_416 import ConfiguradorModem416
except Exception:
    ConfiguradorModem416 = None


# =========================
# ScrollableFrame
# =========================
class ScrollableFrame(ttk.Frame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        self.canvas = tk.Canvas(self, highlightthickness=0)
        self.v_scroll = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.v_scroll.set)

        self.v_scroll.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.inner = ttk.Frame(self.canvas)
        self.inner_id = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")

        self.inner.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        self._bind_mousewheel(self.canvas)
        self._bind_mousewheel(self.inner)

    def _on_frame_configure(self, _event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.canvas.itemconfigure(self.inner_id, width=event.width)

    def _bind_mousewheel(self, widget):
        widget.bind("<Enter>", lambda _e: self._activate_mousewheel())
        widget.bind("<Leave>", lambda _e: self._deactivate_mousewheel())

    def _activate_mousewheel(self):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Button-4>", self._on_mousewheel_linux)
        self.canvas.bind_all("<Button-5>", self._on_mousewheel_linux)

    def _deactivate_mousewheel(self):
        self.canvas.unbind_all("<MouseWheel>")
        self.canvas.unbind_all("<Button-4>")
        self.canvas.unbind_all("<Button-5>")

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_mousewheel_linux(self, event):
        if event.num == 4:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.canvas.yview_scroll(1, "units")


# =========================
# UI Principal + Adapter
# =========================
class MainApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Configurador Automático Datacom DM986 (Unified)")

        # Ventana
        self.root.geometry("780x920")
        self.root.minsize(720, 820)
        self.root.resizable(True, True)
        self.root.configure(bg="#f5f5f5")

        # Icono (opcional)
        try:
            self.root.iconbitmap("assets/icons/icono.ico")
        except Exception:
            pass

        # Paleta
        self.primary_color = "#1976D2"
        self.bg_color = "#F5F5F5"
        self.text_color = "#212121"

        # Variables
        self.modelo = tk.StringVar(value="DM986-416 AX30")

        # ✅ CAMBIO: navegador ahora es texto (para Combobox)
        self.browser_choice = tk.StringVar(value="Google Chrome (recomendado)")

        self.username = tk.StringVar()
        self.password = tk.StringVar()
        self.ssid_name = tk.StringVar()
        self.wpa_password = tk.StringVar()
        self.new_password = tk.StringVar()

        # Extras WLAN
        self.use_custom_wlan = tk.BooleanVar(value=False)

        # Fuentes
        self.title_font = font.Font(family="Segoe UI", size=16, weight="bold")
        self.header_font = font.Font(family="Segoe UI", size=12, weight="bold")
        self.normal_font = font.Font(family="Segoe UI", size=10)
        self.small_font = font.Font(family="Segoe UI", size=9)

        # Estilos ttk
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.style.configure("TFrame", background=self.bg_color)
        self.style.configure("Header.TFrame", background=self.primary_color)
        self.style.configure("TLabel", background=self.bg_color, foreground=self.text_color, font=self.normal_font)
        self.style.configure("Header.TLabel", background=self.primary_color, foreground="white", font=self.header_font)
        self.style.configure("Status.TLabel", background=self.bg_color, foreground=self.primary_color, font=self.normal_font)
        self.style.configure("TProgressbar", troughcolor=self.bg_color, background="#2196F3", thickness=10)

        # Header fijo
        self.header_frame = ttk.Frame(self.root, style="Header.TFrame")
        self.header_frame.pack(fill=tk.X)

        ttk.Label(
            self.header_frame,
            text="Configurador Automático Datacom DM986 (Selector de Modelo)",
            style="Header.TLabel"
        ).pack(pady=10)

        # Área scrolleable
        self.scroll_area = ScrollableFrame(self.root)
        self.scroll_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.main_frame = ttk.Frame(self.scroll_area.inner, padding="20", style="TFrame")
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # ===== Selector de modelo =====
        model_frame = ttk.LabelFrame(self.main_frame, text="SELECCIONE MODELO", padding="15 10 15 15")
        model_frame.pack(fill=tk.X, pady=10)

        ttk.Label(model_frame, text="Modelo:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.cb_model = ttk.Combobox(
            model_frame,
            state="readonly",
            width=28,
            textvariable=self.modelo,
            values=["DM986-416 AX30", "DM986-414"]
        )
        self.cb_model.grid(row=0, column=1, sticky=tk.W, padx=10, pady=5)
        self.cb_model.bind("<<ComboboxSelected>>", self._on_model_change)

        # ===== Navegador (✅ CAMBIO A COMBOBOX) =====
        browser_frame = ttk.LabelFrame(self.main_frame, text="SELECCIONE NAVEGADOR", padding="15 10 15 15")
        browser_frame.pack(fill=tk.X, pady=10)

        ttk.Label(browser_frame, text="Navegador:").grid(row=0, column=0, sticky=tk.W, pady=5)

        self.cb_browser = ttk.Combobox(
            browser_frame,
            state="readonly",
            width=28,
            textvariable=self.browser_choice,
            values=[
                "Google Chrome (recomendado)",
                "Microsoft Edge",
                "Firefox",
                "Autodetectar (puede ser más lento)"
            ]
        )
        self.cb_browser.grid(row=0, column=1, sticky=tk.W, padx=10, pady=5)

        # ===== Config base =====
        config_frame = ttk.LabelFrame(self.main_frame, text="INFORMACIÓN DE CONFIGURACIÓN", padding="15 10 15 15")
        config_frame.pack(fill=tk.X, pady=10)

        labels = [
            "Nombre de usuario del modem:",
            "Contraseña actual del modem:",
            "Nombre de la red Wi-Fi (SSID):",
            "Contraseña WPA para WiFi:",
            "Nueva contraseña admin:"
        ]
        vars_ = [self.username, self.password, self.ssid_name, self.wpa_password, self.new_password]

        for i, (lbl, v) in enumerate(zip(labels, vars_)):
            ttk.Label(config_frame, text=lbl).grid(row=i, column=0, sticky=tk.W, pady=8)
            if i in [1, 3, 4]:
                e = ttk.Entry(config_frame, textvariable=v, width=30)
                e.grid(row=i, column=1, sticky=tk.W, padx=10)
                show_var = tk.BooleanVar(value=True)
                ttk.Checkbutton(
                    config_frame,
                    text="Ocultar",
                    variable=show_var,
                    command=lambda entry=e, sv=show_var: self._toggle_password(entry, sv)
                ).grid(row=i, column=2, sticky=tk.W)
            else:
                ttk.Entry(config_frame, textvariable=v, width=30).grid(row=i, column=1, sticky=tk.W, padx=10)

        # ===== Extras WLAN =====
        extra_frame = ttk.LabelFrame(self.main_frame, text="CONFIGURACIONES ADICIONALES (WLAN)", padding="15 10 15 15")
        extra_frame.pack(fill=tk.X, pady=10)

        ttk.Checkbutton(
            extra_frame,
            text="Aplicar configuraciones personalizadas (Channel Width / Channel Number)",
            variable=self.use_custom_wlan,
            command=self._toggle_extra_controls
        ).grid(row=0, column=0, columnspan=4, sticky=tk.W, pady=(0, 10))

        ttk.Label(extra_frame, text="WLAN 5GHz:", font=self.header_font) \
            .grid(row=1, column=0, sticky=tk.W, pady=(0, 6))

        ttk.Label(extra_frame, text="Channel Width:").grid(row=2, column=0, sticky=tk.W, pady=4)
        self.cb_5_width = ttk.Combobox(extra_frame, state="readonly", width=26)
        self.cb_5_width.grid(row=2, column=1, sticky=tk.W, padx=10)

        ttk.Label(extra_frame, text="Channel Number:").grid(row=3, column=0, sticky=tk.W, pady=4)
        self.cb_5_chan = ttk.Combobox(extra_frame, state="readonly", width=26)
        self.cb_5_chan.grid(row=3, column=1, sticky=tk.W, padx=10)

        ttk.Label(extra_frame, text="WLAN 2.4GHz:", font=self.header_font) \
            .grid(row=4, column=0, sticky=tk.W, pady=(12, 6))

        ttk.Label(extra_frame, text="Channel Width:").grid(row=5, column=0, sticky=tk.W, pady=4)
        self.cb_24_width = ttk.Combobox(extra_frame, state="readonly", width=26)
        self.cb_24_width.grid(row=5, column=1, sticky=tk.W, padx=10)

        ttk.Label(extra_frame, text="Channel Number:").grid(row=6, column=0, sticky=tk.W, pady=4)
        self.cb_24_chan = ttk.Combobox(extra_frame, state="readonly", width=26)
        self.cb_24_chan.grid(row=6, column=1, sticky=tk.W, padx=10)

        # Set opciones iniciales (modelo por defecto 416)
        self._apply_model_wifi_options(model="DM986-416 AX30")

        self._toggle_extra_controls()

        # ===== Botón =====
        button_section = tk.Frame(self.main_frame, bg="#E3F2FD")
        button_section.pack(fill=tk.X, pady=(10, 5))
        tk.Label(button_section, text="INICIAR PROCESO:", font=("Segoe UI", 11), bg="#E3F2FD").pack(pady=(2, 0))

        self.btn_run = tk.Button(
            button_section,
            text="Configurar Modem",
            command=self.on_run,
            bg="#1976D2",
            fg="white",
            font=("Segoe UI", 11),
            width=30,
            height=1,
            relief=tk.RAISED
        )
        self.btn_run.pack(pady=(5, 8))

        # ===== Progreso + estado =====
        progress_frame = ttk.Frame(self.main_frame)
        progress_frame.pack(fill=tk.X, pady=(5, 0))

        self.progress = ttk.Progressbar(
            progress_frame,
            orient="horizontal",
            length=600,
            mode="indeterminate",
            style="TProgressbar"
        )
        self.progress.pack(pady=5)

        self.status_var = tk.StringVar(value="Listo para iniciar configuración")
        self.status_label = ttk.Label(progress_frame, textvariable=self.status_var, style="Status.TLabel")
        self.status_label.pack(pady=5)

        # Footer
        footer = ttk.Frame(self.root, style="TFrame")
        footer.pack(fill=tk.X, side=tk.BOTTOM, pady=5)
        ttk.Label(footer, text="© Luis Miraglio | miraglioluis1@gmail.com", font=self.small_font) \
            .pack(side=tk.RIGHT, padx=10)

    # =========================
    # Cambios por modelo (opciones de combos)
    # =========================
    def _on_model_change(self, _event=None):
        self._apply_model_wifi_options(model=self.modelo.get())
        self._toggle_extra_controls()

    def _apply_model_wifi_options(self, model: str):
        """
        Ajusta las opciones de los combobox según el modelo.
        - 416: 5GHz width 20/40/80/160 + canales 36..128 (DFS)
        - 414: 5GHz width 20/40/80 + canales 36/40/44/48 + 149/153/157/161 (Auto DFS)
              2.4 width 20/40 (sin 20/40MHz) + canales Auto/5..11
        """
        if model == "DM986-414":
            # 414
            self.cb_5_width.configure(values=["20MHz", "40MHz", "80MHz"])
            self.cb_5_chan.configure(values=["Auto(DFS)", "36", "40", "44", "48", "149", "153", "157", "161"])

            self.cb_24_width.configure(values=["20MHz", "40MHz"])
            self.cb_24_chan.configure(values=["Auto", "5", "6", "7", "8", "9", "10", "11"])

            # Defaults visibles 414
            self.cb_5_width.set("80MHz")
            self.cb_5_chan.set("Auto(DFS)")
            self.cb_24_width.set("20MHz")
            self.cb_24_chan.set("Auto")

        else:
            # 416
            self.cb_5_width.configure(values=["20MHz", "40MHz", "80MHz", "160MHz"])
            self.cb_5_chan.configure(values=[
                "DFS", "36", "40", "44", "48", "52", "56", "60", "64",
                "100", "104", "108", "112", "116", "120", "124", "128"
            ])

            self.cb_24_width.configure(values=["20MHz", "40MHz", "20/40MHz"])
            self.cb_24_chan.configure(values=["Auto", "5", "6", "7", "8", "9", "10", "11"])

            # Defaults visibles 416
            self.cb_5_width.set("80MHz")
            self.cb_5_chan.set("DFS")
            self.cb_24_width.set("20MHz")
            self.cb_24_chan.set("Auto")

    # =========================
    # UI Adapter Methods (para logic_*.py)
    # =========================
    def actualizar_estado(self, msg: str):
        self.root.after(0, lambda: self.status_var.set(msg))

    def safe_messagebox(self, title: str, text: str, kind: str = "error"):
        def _show():
            if kind == "error":
                messagebox.showerror(title, text)
            elif kind == "warning":
                messagebox.showwarning(title, text)
            else:
                messagebox.showinfo(title, text)

        self.root.after(0, _show)

    # ✅ CAMBIO: ahora el browser_choice es texto (combo)
    def get_browser_choice(self) -> str:
        txt = self.browser_choice.get()
        mapping = {
            "Google Chrome (recomendado)": "chrome",
            "Microsoft Edge": "edge",
            "Firefox": "firefox",
            "Autodetectar (puede ser más lento)": "auto",
        }
        return mapping.get(txt, "chrome")

    def get_credentials(self) -> dict:
        return {
            "username": self.username.get().strip(),
            "password": self.password.get().strip(),
            "ssid": self.ssid_name.get().strip(),
            "wpa": self.wpa_password.get().strip(),
            "new_password": self.new_password.get().strip(),
        }

    def get_extra_wifi_config(self) -> dict:
        """
        IMPORTANTE: Este formato es el que esperan logic_416 y logic_414:
          enabled, chanwid_5, chan_5, chanwid_24, chan_24
        Los valores devueltos son los 'value' reales para Select().select_by_value(...)
        """
        enabled = self.use_custom_wlan.get()
        model = self.modelo.get()

        if not enabled:
            return {"enabled": False}

        if model == "DM986-414":
            # 414: width 20/40/80 (0/1/2), chan Auto(DFS)=0, 36/40/44/48/149/153/157/161
            map_5w = {"20MHz": "0", "40MHz": "1", "80MHz": "2"}
            map_5c = {
                "Auto(DFS)": "0",
                "36": "36", "40": "40", "44": "44", "48": "48",
                "149": "149", "153": "153", "157": "157", "161": "161"
            }

            # 414: 2.4 width 20/40 (0/1) ; chan Auto=0; 5..11
            map_24w = {"20MHz": "0", "40MHz": "1"}
            map_24c = {"Auto": "0", "5": "5", "6": "6", "7": "7", "8": "8", "9": "9", "10": "10", "11": "11"}

            return {
                "enabled": True,
                "chanwid_5": map_5w.get(self.cb_5_width.get(), "2"),
                "chan_5": map_5c.get(self.cb_5_chan.get(), "0"),
                "chanwid_24": map_24w.get(self.cb_24_width.get(), "0"),
                "chan_24": map_24c.get(self.cb_24_chan.get(), "0"),
            }

        # 416: width 20/40/80/160 (0/1/2/3), chan DFS=0, + 36..128
        map_5w = {"20MHz": "0", "40MHz": "1", "80MHz": "2", "160MHz": "3"}
        map_5c = {
            "DFS": "0",
            "36": "36", "40": "40", "44": "44", "48": "48",
            "52": "52", "56": "56", "60": "60", "64": "64",
            "100": "100", "104": "104", "108": "108", "112": "112",
            "116": "116", "120": "120", "124": "124", "128": "128"
        }

        map_24w = {"20MHz": "0", "40MHz": "1", "20/40MHz": "3"}
        map_24c = {"Auto": "0", "5": "5", "6": "6", "7": "7", "8": "8", "9": "9", "10": "10", "11": "11"}

        return {
            "enabled": True,
            "chanwid_5": map_5w.get(self.cb_5_width.get(), "2"),
            "chan_5": map_5c.get(self.cb_5_chan.get(), "0"),
            "chanwid_24": map_24w.get(self.cb_24_width.get(), "0"),
            "chan_24": map_24c.get(self.cb_24_chan.get(), "0"),
        }

    # =========================
    # UI Helpers
    # =========================
    def _toggle_password(self, entry, show_var):
        entry.configure(show="" if show_var.get() else "*")

    def _toggle_extra_controls(self):
        state = "readonly" if self.use_custom_wlan.get() else "disabled"
        for cb in (self.cb_5_width, self.cb_5_chan, self.cb_24_width, self.cb_24_chan):
            cb.configure(state=state)

    def _validate_required(self) -> bool:
        creds = self.get_credentials()
        return all([creds["username"], creds["password"], creds["ssid"], creds["wpa"], creds["new_password"]])

    def set_buttons_enabled(self, enabled: bool):
        def _set():
            self.btn_run.config(state="normal" if enabled else "disabled")
            self.btn_run.config(bg="#1976D2" if enabled else "#CCCCCC")

        self.root.after(0, _set)

    def start_progress(self):
        self.root.after(0, lambda: self.progress.start(10))

    def stop_progress(self):
        self.root.after(0, self.progress.stop)

    # =========================
    # Run
    # =========================
    def on_run(self):
        if not self._validate_required():
            self.safe_messagebox("Campos incompletos", "Por favor, complete todos los campos antes de continuar", kind="error")
            return

        model = self.modelo.get()

        self.set_buttons_enabled(False)
        self.start_progress()
        self.actualizar_estado(f"Iniciando configuración para {model}...")

        threading.Thread(target=self._run_worker, daemon=True).start()

    def _run_worker(self):
        try:
            model = self.modelo.get()

            if model == "DM986-416 AX30":
                if ConfiguradorModem416 is None:
                    raise Exception("No se pudo importar logic_416.py (ConfiguradorModem416).")
                logic = ConfiguradorModem416(self)
            else:
                logic = ConfiguradorModem414(self)

            logic.run()
            self.actualizar_estado("✅ Proceso finalizado")

        except Exception as e:
            self.actualizar_estado(f"❌ ERROR: {e}")
            self.safe_messagebox("Error", str(e), kind="error")

        finally:
            self.stop_progress()
            self.set_buttons_enabled(True)


# =========================
# Main
# =========================
if __name__ == "__main__":
    root = tk.Tk()
    app = MainApp(root)
    root.mainloop()
