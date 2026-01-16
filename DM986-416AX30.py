from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from webdriver_manager.firefox import GeckoDriverManager
import os
import time
import base64
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox, font
import datetime
import logging
from logging.handlers import RotatingFileHandler

# Verificar si las bibliotecas necesarias están instaladas
try:
    import webdriver_manager  # noqa: F401
except ImportError:
    print("Instalando las bibliotecas necesarias...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "webdriver-manager"])
    print("Bibliotecas instaladas correctamente. Reiniciando script...")
    os.execv(sys.executable, ['python'] + sys.argv)


# =========================
# ScrollableFrame (NUEVO)
# =========================
class ScrollableFrame(ttk.Frame):
    """
    Frame scrolleable vertical (header fijo + contenido con scroll).
    Soporta rueda del mouse.
    """
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

        # Scroll con rueda del mouse
        self._bind_mousewheel(self.canvas)
        self._bind_mousewheel(self.inner)

    def _on_frame_configure(self, event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.canvas.itemconfigure(self.inner_id, width=event.width)

    def _bind_mousewheel(self, widget):
        widget.bind("<Enter>", lambda e: self._activate_mousewheel())
        widget.bind("<Leave>", lambda e: self._deactivate_mousewheel())

    def _activate_mousewheel(self):
        # Windows / Mac (en Windows delta suele ser +-120)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        # Linux
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


# Configuración del sistema de logs
def setup_logger():
    """Configura el sistema de logs de la aplicación"""
    if getattr(sys, 'frozen', False):
        app_dir = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'ConfiguradorDatacom')
    else:
        app_dir = os.path.dirname(os.path.abspath(__file__))
    log_dir = os.path.join(app_dir, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f'datacom_config_{datetime.datetime.now().strftime("%Y%m%d")}.log')

    logger = logging.getLogger('DatacomConfig')
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:
        file_handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=5, encoding='utf-8')
        file_formatter = logging.Formatter('%(asctime)s [%(levelname)s] - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(console_formatter)
        console_handler.setLevel(logging.INFO)
        logger.addHandler(console_handler)

    return logger


logger = setup_logger()
logger.info("=== Iniciando Configurador Automático de Modem Datacom DM986 ===")


class ConfiguradorModem:
    def __init__(self, root):
        logger.info("Inicializando interfaz gráfica")
        self.root = root
        self.root.title("Configurador Automático de Modem Datacom DM986")

        # ✅ Ventana más grande + redimensionable (NUEVO)
        self.root.geometry("760x900")
        self.root.minsize(720, 800)
        self.root.resizable(True, True)
        self.root.configure(bg="#f5f5f5")

        try:
            self.root.iconbitmap("datacom_config.ico")
        except Exception:
            pass

        # Paleta
        self.primary_color = "#1976D2"
        self.secondary_color = "#2196F3"
        self.accent_color = "#03A9F4"
        self.warning_color = "#FFC107"
        self.success_color = "#4CAF50"
        self.error_color = "#F44336"
        self.bg_color = "#F5F5F5"
        self.text_color = "#212121"

        # Variables base
        self.browser_choice = tk.StringVar(value="1")  # Chrome por defecto
        self.username = tk.StringVar()
        self.password = tk.StringVar()
        self.ssid_name = tk.StringVar()
        self.wpa_password = tk.StringVar()
        self.new_password = tk.StringVar()

        # ============================
        # NUEVAS VARIABLES (WLAN extra)
        # ============================
        self.use_custom_wlan = tk.BooleanVar(value=False)

        # 5GHz
        self.wlan5_chan_width = tk.StringVar(value="2")   # default: 80MHz (value 2)
        self.wlan5_chan_number = tk.StringVar(value="0")  # default: DFS (value 0)

        # 2.4GHz
        self.wlan24_chan_width = tk.StringVar(value="0")  # default: 20MHz (value 0)
        self.wlan24_chan_number = tk.StringVar(value="0") # default: Auto (value 0)

        # Fuentes
        self.title_font = font.Font(family="Segoe UI", size=16, weight="bold")
        self.header_font = font.Font(family="Segoe UI", size=12, weight="bold")
        self.normal_font = font.Font(family="Segoe UI", size=10)
        self.small_font = font.Font(family="Segoe UI", size=9)
        self.button_font = font.Font(family="Segoe UI", size=10, weight="bold")

        # Estilos
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure("TFrame", background=self.bg_color)
        self.style.configure("Header.TFrame", background=self.primary_color)
        self.style.configure("TLabel", background=self.bg_color, foreground=self.text_color, font=self.normal_font)
        self.style.configure("Header.TLabel", background=self.primary_color, foreground="white", font=self.header_font)
        self.style.configure("Title.TLabel", background=self.bg_color, foreground=self.primary_color, font=self.title_font)
        self.style.configure("Status.TLabel", background=self.bg_color, foreground=self.primary_color, font=self.normal_font)
        self.style.configure("TRadiobutton", background=self.bg_color, foreground=self.text_color, font=self.normal_font)
        self.style.configure("TProgressbar", troughcolor=self.bg_color, background=self.secondary_color, thickness=10)

        # Header fijo
        self.header_frame = ttk.Frame(self.root, style="Header.TFrame")
        self.header_frame.pack(fill=tk.X)
        header_title = ttk.Label(
            self.header_frame,
            text="DATACOM DM986-416AX30 - Configurador Automático",
            style="Header.TLabel"
        )
        header_title.pack(pady=10)

        # ✅ Área principal scrolleable (NUEVO)
        self.scroll_area = ScrollableFrame(self.root)
        self.scroll_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.main_frame = ttk.Frame(self.scroll_area.inner, padding="20", style="TFrame")
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Navegador
        browser_frame = ttk.LabelFrame(self.main_frame, text="SELECCIONE NAVEGADOR", padding="15 10 15 15")
        browser_frame.pack(fill=tk.X, pady=10)
        for i, (browser_text, browser_val) in enumerate([
            ("Google Chrome (recomendado)", "1"),
            ("Microsoft Edge", "2"),
            ("Firefox", "3"),
            ("Autodetectar (puede ser más lento)", "4")
        ]):
            ttk.Radiobutton(browser_frame, text=browser_text, variable=self.browser_choice, value=browser_val)\
               .grid(row=i, column=0, sticky=tk.W, pady=3)

        # Config
        config_frame = ttk.LabelFrame(self.main_frame, text="INFORMACIÓN DE CONFIGURACIÓN", padding="15 10 15 15")
        config_frame.pack(fill=tk.X, pady=10)

        field_labels = [
            "Nombre de usuario del modem:",
            "Contraseña actual del modem:",
            "Nombre de la red Wi-Fi (SSID):",
            "Contraseña WPA para WiFi:",
            "Nueva contraseña admin:"
        ]
        field_vars = [self.username, self.password, self.ssid_name, self.wpa_password, self.new_password]
        self.entry_fields = []

        for i, (label_text, var) in enumerate(zip(field_labels, field_vars)):
            ttk.Label(config_frame, text=label_text).grid(row=i, column=0, sticky=tk.W, pady=8)
            if i in [1, 3, 4]:  # contraseñas visibles + check "Ocultar"
                entry = ttk.Entry(config_frame, textvariable=var, width=30)
                entry.grid(row=i, column=1, sticky=tk.W, padx=10)
                self.entry_fields.append(entry)
                show_var = tk.BooleanVar(value=True)
                ttk.Checkbutton(
                    config_frame,
                    text="Ocultar",
                    variable=show_var,
                    command=lambda e=entry, v=show_var: self.toggle_password(e, v)
                ).grid(row=i, column=2, sticky=tk.W)
            else:
                ttk.Entry(config_frame, textvariable=var, width=30).grid(row=i, column=1, sticky=tk.W, padx=10)

        # ==========================================
        # NUEVA SECCIÓN: CONFIGURACIONES ADICIONALES
        # ==========================================
        extra_frame = ttk.LabelFrame(self.main_frame, text="CONFIGURACIONES ADICIONALES (WLAN)", padding="15 10 15 15")
        extra_frame.pack(fill=tk.X, pady=10)

        ttk.Checkbutton(
            extra_frame,
            text="Aplicar configuraciones personalizadas (Channel Width / Channel Number)",
            variable=self.use_custom_wlan,
            command=self._toggle_extra_controls
        ).grid(row=0, column=0, columnspan=4, sticky=tk.W, pady=(0, 10))

        # --- WLAN 5GHz ---
        ttk.Label(extra_frame, text="WLAN 5GHz:", font=self.header_font).grid(row=1, column=0, sticky=tk.W, pady=(0, 6))

        ttk.Label(extra_frame, text="Channel Width:").grid(row=2, column=0, sticky=tk.W, pady=4)
        self.cb_5_width = ttk.Combobox(
            extra_frame,
            state="readonly",
            width=26,
            values=["20MHz", "40MHz", "80MHz", "160MHz"]
        )
        self.cb_5_width.grid(row=2, column=1, sticky=tk.W, padx=10)

        self._set_combobox_by_value(self.cb_5_width, self.wlan5_chan_width.get(), mapping={
            "0": "20MHz", "1": "40MHz", "2": "80MHz", "3": "160MHz"
        })

        ttk.Label(extra_frame, text="Channel Number:").grid(row=3, column=0, sticky=tk.W, pady=4)
        self.cb_5_chan = ttk.Combobox(
            extra_frame,
            state="readonly",
            width=26,
            values=[
                "DFS", "36", "40", "44", "48", "52", "56", "60", "64",
                "100", "104", "108", "112", "116", "120", "124", "128"
            ]
        )
        self.cb_5_chan.grid(row=3, column=1, sticky=tk.W, padx=10)

        self._set_combobox_by_value(self.cb_5_chan, self.wlan5_chan_number.get(), mapping={
            "0": "DFS", "36": "36", "40": "40", "44": "44", "48": "48",
            "52": "52", "56": "56", "60": "60", "64": "64",
            "100": "100", "104": "104", "108": "108", "112": "112",
            "116": "116", "120": "120", "124": "124", "128": "128"
        })

        # --- WLAN 2.4GHz ---
        ttk.Label(extra_frame, text="WLAN 2.4GHz:", font=self.header_font).grid(row=4, column=0, sticky=tk.W, pady=(12, 6))

        ttk.Label(extra_frame, text="Channel Width:").grid(row=5, column=0, sticky=tk.W, pady=4)
        self.cb_24_width = ttk.Combobox(
            extra_frame,
            state="readonly",
            width=26,
            values=["20MHz", "40MHz", "20/40MHz"]
        )
        self.cb_24_width.grid(row=5, column=1, sticky=tk.W, padx=10)

        self._set_combobox_by_value(self.cb_24_width, self.wlan24_chan_width.get(), mapping={
            "0": "20MHz", "1": "40MHz", "3": "20/40MHz"
        })

        ttk.Label(extra_frame, text="Channel Number:").grid(row=6, column=0, sticky=tk.W, pady=4)
        self.cb_24_chan = ttk.Combobox(
            extra_frame,
            state="readonly",
            width=26,
            values=["Auto", "5", "6", "7", "8", "9", "10", "11"]
        )
        self.cb_24_chan.grid(row=6, column=1, sticky=tk.W, padx=10)

        self._set_combobox_by_value(self.cb_24_chan, self.wlan24_chan_number.get(), mapping={
            "0": "Auto", "5": "5", "6": "6", "7": "7", "8": "8", "9": "9", "10": "10", "11": "11"
        })

        # Deshabilitar al inicio
        self._toggle_extra_controls()

        # Botón principal
        button_section = tk.Frame(self.main_frame, bg="#E3F2FD")
        button_section.pack(fill=tk.X, pady=(10, 5))
        tk.Label(button_section, text="INICIAR PROCESO:", font=("Segoe UI", 11), bg="#E3F2FD").pack(pady=(2, 0))
        self.big_configure_button = tk.Button(
            button_section,
            text="Configurar Modem",
            command=self.iniciar_configuracion,
            bg="#1976D2",
            fg="white",
            font=("Segoe UI", 11),
            width=30,
            height=1,
            relief=tk.RAISED
        )
        self.big_configure_button.pack(pady=(5, 8))

        # Progreso + estado
        progress_frame = ttk.Frame(self.main_frame)
        progress_frame.pack(fill=tk.X, pady=(5, 0))
        self.progress = ttk.Progressbar(progress_frame, orient="horizontal", length=600,
                                        mode="indeterminate", style="TProgressbar")
        self.progress.pack(pady=5)
        self.status_var = tk.StringVar(value="Listo para iniciar configuración")
        self.status_label = ttk.Label(progress_frame, textvariable=self.status_var, style="Status.TLabel")
        self.status_label.pack(pady=5)

        # Footer fijo (NO scrollea)
        info_frame = ttk.Frame(self.root, style="TFrame")
        info_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=5)
        ttk.Label(info_frame, text="© Luis Miraglio | miraglioluis1@gmail.com", font=self.small_font)\
           .pack(side=tk.RIGHT, padx=10)

    # ===== Helpers UI thread-safe =====
    def actualizar_estado(self, mensaje: str):
        logger.info(mensaje)
        self.root.after(0, lambda: self.status_var.set(mensaje))

    def safe_messagebox(self, title: str, text: str, kind: str = "error"):
        def _show():
            if kind == "error":
                messagebox.showerror(title, text)
            elif kind == "warning":
                messagebox.showwarning(title, text)
            else:
                messagebox.showinfo(title, text)
        self.root.after(0, _show)

    def set_buttons_enabled(self, enabled: bool):
        def _set():
            self.big_configure_button.config(state="normal" if enabled else "disabled")
            self.big_configure_button.config(bg="#1976D2" if enabled else "#CCCCCC")
        self.root.after(0, _set)

    def start_progress(self):
        self.root.after(0, lambda: self.progress.start(10))

    def stop_progress(self):
        self.root.after(0, self.progress.stop)

    # =================================
    def toggle_password(self, entry, var):
        if var.get():
            entry.config(show="")
        else:
            entry.config(show="*")

    # ===== NUEVO: habilitar/deshabilitar combos =====
    def _toggle_extra_controls(self):
        enabled = self.use_custom_wlan.get()
        state = "readonly" if enabled else "disabled"
        try:
            self.cb_5_width.configure(state=state)
            self.cb_5_chan.configure(state=state)
            self.cb_24_width.configure(state=state)
            self.cb_24_chan.configure(state=state)
        except Exception:
            pass

    def _set_combobox_by_value(self, cb: ttk.Combobox, value: str, mapping: dict):
        text = mapping.get(value)
        if text and text in cb["values"]:
            cb.set(text)
        else:
            if cb["values"]:
                cb.set(cb["values"][0])

    def _read_extra_wlan_config(self):
        """
        Devuelve dict con values reales para Selenium:
        - chanwid_5, chan_5, chanwid_24, chan_24 (strings)
        Si no está activado, devuelve defaults.
        """
        if not self.use_custom_wlan.get():
            # Defaults (ajustado a lo que tenías en tu código)
            return {
                "chanwid_5": "3",   # ojo: si en tu firmware 80MHz es "2", cambiá esto.
                "chan_5": "0",      # DFS
                "chanwid_24": "0",  # 20MHz
                "chan_24": "0",     # Auto
            }

        map_5_width = {"20MHz": "0", "40MHz": "1", "80MHz": "2", "160MHz": "3"}
        map_5_chan = {
            "DFS": "0", "36": "36", "40": "40", "44": "44", "48": "48",
            "52": "52", "56": "56", "60": "60", "64": "64",
            "100": "100", "104": "104", "108": "108", "112": "112",
            "116": "116", "120": "120", "124": "124", "128": "128"
        }
        map_24_width = {"20MHz": "0", "40MHz": "1", "20/40MHz": "3"}
        map_24_chan = {"Auto": "0", "5": "5", "6": "6", "7": "7", "8": "8", "9": "9", "10": "10", "11": "11"}

        return {
            "chanwid_5": map_5_width.get(self.cb_5_width.get(), "2"),
            "chan_5": map_5_chan.get(self.cb_5_chan.get(), "0"),
            "chanwid_24": map_24_width.get(self.cb_24_width.get(), "0"),
            "chan_24": map_24_chan.get(self.cb_24_chan.get(), "0"),
        }

    def iniciar_configuracion(self):
        if not all([self.username.get(), self.password.get(), self.ssid_name.get(),
                    self.wpa_password.get(), self.new_password.get()]):
            messagebox.showerror("Campos incompletos", "Por favor, complete todos los campos antes de continuar")
            logger.warning("Intento de iniciar configuración con campos incompletos")
            return

        logger.info("Iniciando proceso de configuración")
        logger.info(f"Navegador seleccionado: {self.get_browser_name(self.browser_choice.get())}")

        self.set_buttons_enabled(False)
        self.actualizar_estado("Iniciando configuración...")
        self.start_progress()

        threading.Thread(target=self.proceso_configuracion, daemon=True).start()

    def get_browser_name(self, choice):
        return {"1": "Google Chrome", "2": "Microsoft Edge", "3": "Firefox", "4": "Autodetectar"}.get(choice, "Desconocido")

    def proceso_configuracion(self):
        driver = None
        try:
            browser_choice = self.browser_choice.get()
            username = self.username.get()
            password = self.password.get()
            ssid_name = self.ssid_name.get()
            wpa_password = self.wpa_password.get()
            new_password = self.new_password.get()

            extra = self._read_extra_wlan_config()
            logger.info(f"Extra WLAN: {extra}")

            def setup_driver():
                if browser_choice == "1":
                    self.actualizar_estado("Inicializando Google Chrome...")
                    options = ChromeOptions()
                    options.add_argument("--ignore-certificate-errors")
                    options.add_argument("--ignore-ssl-errors")
                    options.add_argument("--disable-web-security")
                    options.add_argument("--allow-running-insecure-content")
                    options.add_experimental_option("detach", True)
                    return webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)

                elif browser_choice == "2":
                    self.actualizar_estado("Inicializando Microsoft Edge...")
                    options = EdgeOptions()
                    options.add_argument("--ignore-certificate-errors")
                    options.add_argument("--ignore-ssl-errors")
                    options.add_argument("--disable-web-security")
                    options.add_argument("--allow-running-insecure-content")
                    options.add_experimental_option("detach", True)
                    return webdriver.Edge(service=EdgeService(EdgeChromiumDriverManager().install()), options=options)

                elif browser_choice == "3":
                    self.actualizar_estado("Inicializando Firefox...")
                    options = FirefoxOptions()
                    options.accept_insecure_certs = True
                    return webdriver.Firefox(service=FirefoxService(GeckoDriverManager().install()), options=options)

                else:
                    for browser in ['chrome', 'edge', 'firefox']:
                        try:
                            if browser == 'chrome':
                                self.actualizar_estado("Intentando con Chrome...")
                                options = ChromeOptions()
                                options.add_argument("--ignore-certificate-errors")
                                options.add_argument("--ignore-ssl-errors")
                                options.add_argument("--disable-web-security")
                                options.add_argument("--allow-running-insecure-content")
                                options.add_experimental_option("detach", True)
                                return webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
                            elif browser == 'edge':
                                self.actualizar_estado("Intentando con Edge...")
                                options = EdgeOptions()
                                options.add_argument("--ignore-certificate-errors")
                                options.add_argument("--ignore-ssl-errors")
                                options.add_argument("--disable-web-security")
                                options.add_argument("--allow-running-insecure-content")
                                options.add_experimental_option("detach", True)
                                return webdriver.Edge(service=EdgeService(EdgeChromiumDriverManager().install()), options=options)
                            else:
                                self.actualizar_estado("Intentando con Firefox...")
                                options = FirefoxOptions()
                                options.accept_insecure_certs = True
                                return webdriver.Firefox(service=FirefoxService(GeckoDriverManager().install()), options=options)
                        except Exception as e:
                            logger.warning(f"No se pudo inicializar {browser}: {e}")
                            continue
                    raise Exception("No se encontró ningún navegador compatible instalado.")

            driver = setup_driver()
            self.actualizar_estado("Navegador inicializado correctamente.")

            # Login
            logger.info("Accediendo a la página de login del modem (192.168.0.1)")
            driver.get("https://192.168.0.1/admin/login.asp")
            time.sleep(2)

            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            if iframes:
                driver.switch_to.frame(iframes[0])

            self.actualizar_estado("Completando credenciales de acceso...")
            username_field = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "username")))
            username_field.send_keys(username)
            password_field = driver.find_element(By.NAME, "password")
            password_field.send_keys(password)

            encoded_password = base64.b64encode(password.encode('utf-8')).decode('utf-8')
            driver.execute_script("""
                document.getElementsByName('encodePassword')[0].value = arguments[0];
                document.getElementsByName('password')[0].disabled = true;
            """, encoded_password)

            login_button = driver.find_element(By.XPATH, "//input[@type='submit' and @value='Login']")
            login_button.click()

            self.actualizar_estado("Accediendo al modem...")
            nav_menu = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "nav")))
            logger.info("Login exitoso, interfaz del modem cargada")

            # WAN
            self.actualizar_estado("Configurando sección WAN...")
            wan_link = nav_menu.find_element(By.XPATH, ".//a[@rel='4' and text()='WAN']")
            wan_link.click()

            content_iframe = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "contentIframe")))
            driver.switch_to.frame(content_iframe)

            vlan_checkbox = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//input[@type='checkbox' and @name='vlan' and @value='ON']")))
            vlan_checkbox.click()
            time.sleep(1)

            vid_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "vid")))
            vid_input.clear()
            vid_input.send_keys("500")
            time.sleep(1)

            channel_mode_dropdown = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.NAME, "adslConnectionMode")))
            for option in channel_mode_dropdown.find_elements(By.TAG_NAME, "option"):
                if option.get_attribute("value") == "1":
                    option.click()
                    break
            time.sleep(1)

            chkpt_all_checkbox = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//input[@name='chkpt_all']")))
            chkpt_all_checkbox.click()
            time.sleep(1)

            apply_changes_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//input[@type='submit' and @value='Apply Changes' and @name='apply']")))
            apply_changes_button.click()
            time.sleep(2)

            driver.switch_to.default_content()

            # WAN new link VLAN 600 TR069
            self.actualizar_estado("Volviendo a la sección WAN...")
            nav_menu = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "nav")))
            wan_link = nav_menu.find_element(By.XPATH, ".//a[@rel='4' and text()='WAN']")
            wan_link.click()
            time.sleep(1)

            content_iframe = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "contentIframe")))
            driver.switch_to.frame(content_iframe)

            self.actualizar_estado("Seleccionando enlace 'new link' en WAN...")
            lkname_select = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "lkname")))
            for option in lkname_select.find_elements(By.TAG_NAME, "option"):
                if option.get_attribute("value") == "new":
                    option.click()
                    break
            time.sleep(1)

            vlan_checkbox_new = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//input[@type='checkbox' and @name='vlan' and @value='ON']")))
            vlan_checkbox_new.click()
            time.sleep(1)

            vid_input_new = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "vid")))
            vid_input_new.clear()
            vid_input_new.send_keys("600")
            time.sleep(1)

            channel_mode_dropdown_new = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.NAME, "adslConnectionMode")))
            for option in channel_mode_dropdown_new.find_elements(By.TAG_NAME, "option"):
                if option.get_attribute("value") == "1":
                    option.click()
                    break
            time.sleep(1)

            self.actualizar_estado("Seleccionando tipo de conexión TR069...")
            ctype_dropdown_new = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "ctype")))
            for option in ctype_dropdown_new.find_elements(By.TAG_NAME, "option"):
                if option.get_attribute("value") == "1":
                    option.click()
                    break
            time.sleep(1)

            dhcp_radio = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//input[@type='radio' and @name='ipMode' and @value='1']")))
            dhcp_radio.click()
            time.sleep(1)

            checkbox_all = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//input[@type='checkbox' and @name='chkpt_all']")))
            checkbox_all.click()
            WebDriverWait(driver, 5).until(lambda d: not checkbox_all.is_selected())
            checkbox_all.click()
            time.sleep(1)

            apply_changes_button_new = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//input[@type='submit' and @name='apply' and @value='Apply Changes']")))
            apply_changes_button_new.click()
            time.sleep(2)

            # WLAN 5 GHz
            driver.switch_to.default_content()
            self.actualizar_estado("Configurando red WiFi 5GHz...")
            wlan_link = nav_menu.find_element(By.XPATH, ".//a[@rel='3' and text()='WLAN']")
            wlan_link.click()

            content_iframe = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "contentIframe")))
            driver.switch_to.frame(content_iframe)

            ssid_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "ssid")))
            ssid_input.clear()
            ssid_input.send_keys(ssid_name)
            time.sleep(1)

            # Aplicar extras 5GHz
            self.actualizar_estado("Aplicando Channel Width / Channel Number (5GHz)...")
            chanwid_dropdown = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "chanwid")))
            desired_width_5 = extra["chanwid_5"]
            for option in chanwid_dropdown.find_elements(By.TAG_NAME, "option"):
                if option.get_attribute("value") == desired_width_5:
                    option.click()
                    break
            time.sleep(1)

            chan_select_dropdown = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "chan_select")))
            desired_chan_5 = extra["chan_5"]
            for option in chan_select_dropdown.find_elements(By.TAG_NAME, "option"):
                if option.get_attribute("value") == desired_chan_5:
                    option.click()
                    break
            time.sleep(1)

            txpower_dropdown = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "txpower")))
            for option in txpower_dropdown.find_elements(By.TAG_NAME, "option"):
                if option.get_attribute("value") == "0":
                    option.click()
                    break
            time.sleep(1)

            apply_changes_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//input[@type='submit' and @value='Apply Changes' and @name='save']")))
            apply_changes_button.click()
            time.sleep(10)

            driver.switch_to.default_content()

            side_menu = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "side")))
            self.actualizar_estado("Configurando seguridad WiFi 5GHz...")
            security_link = WebDriverWait(side_menu, 10).until(
                EC.element_to_be_clickable((By.XPATH, ".//a[contains(@href, '/wlwpa.asp') and contains(@href, 'wlan_idx=0')]")))
            security_link.click()
            time.sleep(1)

            content_iframe = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "contentIframe")))
            driver.switch_to.frame(content_iframe)

            wpa_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "wpapsk")))
            wpa_input.clear()
            wpa_input.send_keys(wpa_password)
            time.sleep(1)

            show_password_checkbox = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//input[@type='checkbox' and @onclick='show_password(1)']")))
            show_password_checkbox.click()

            apply_changes_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//input[@type='submit' and @name='save' and @value='Apply Changes']")))
            apply_changes_button.click()
            time.sleep(10)

            # WLAN 2.4 GHz
            driver.switch_to.default_content()
            side_menu = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "side")))
            self.actualizar_estado("Configurando red WiFi 2.4GHz...")
            wlan1_header = WebDriverWait(side_menu, 10).until(
                EC.element_to_be_clickable((By.XPATH, ".//h3/a[text()='wlan1 (2.4GHz)']")))
            wlan1_header.click()
            time.sleep(1)

            content_iframe = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "contentIframe")))
            driver.switch_to.frame(content_iframe)

            ssid_input_wlan1 = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "ssid")))
            ssid_input_wlan1.clear()
            ssid_input_wlan1.send_keys(ssid_name)
            time.sleep(1)

            # Aplicar extras 2.4GHz
            self.actualizar_estado("Aplicando Channel Width / Channel Number (2.4GHz)...")
            chanwid_dropdown_wlan1 = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "chanwid")))
            desired_width_24 = extra["chanwid_24"]
            for option in chanwid_dropdown_wlan1.find_elements(By.TAG_NAME, "option"):
                if option.get_attribute("value") == desired_width_24:
                    option.click()
                    break
            time.sleep(1)

            chan_select_dropdown_wlan1 = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "chan_select")))
            desired_chan_24 = extra["chan_24"]
            for option in chan_select_dropdown_wlan1.find_elements(By.TAG_NAME, "option"):
                if option.get_attribute("value") == desired_chan_24:
                    option.click()
                    break
            time.sleep(1)

            txpower_dropdown_wlan1 = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "txpower")))
            for option in txpower_dropdown_wlan1.find_elements(By.TAG_NAME, "option"):
                if option.get_attribute("value") == "0":
                    option.click()
                    break
            time.sleep(1)

            apply_changes_button_wlan1 = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//input[@type='submit' and @name='save' and @value='Apply Changes']")))
            apply_changes_button_wlan1.click()
            time.sleep(10)

            driver.switch_to.default_content()

            side_menu = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "side")))
            self.actualizar_estado("Configurando seguridad WiFi 2.4GHz...")
            security_link_wlan1 = WebDriverWait(side_menu, 10).until(
                EC.element_to_be_clickable((By.XPATH, ".//a[contains(@href, '/wlwpa.asp') and contains(@href, 'wlan_idx=1')]")))
            security_link_wlan1.click()

            content_iframe = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "contentIframe")))
            driver.switch_to.frame(content_iframe)

            wpa_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "wpapsk")))
            wpa_input.clear()
            wpa_input.send_keys(wpa_password)
            time.sleep(1)

            show_password_checkbox = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//input[@type='checkbox' and @onclick='show_password(1)']")))
            show_password_checkbox.click()

            apply_changes_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//input[@type='submit' and @name='save' and @value='Apply Changes']")))
            apply_changes_button.click()
            time.sleep(10)

            # Admin -> Password
            driver.switch_to.default_content()
            nav_menu = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "nav")))
            self.actualizar_estado("Cambiando contraseña de administrador...")
            admin_link = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//a[@href='javascript:void(0)' and @rel='9']")))
            admin_link.click()

            side_menu = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "side")))
            password_link = WebDriverWait(side_menu, 10).until(
                EC.element_to_be_clickable((By.XPATH, ".//a[@target='contentIframe' and @href='password.asp' and text()='Password']")))
            password_link.click()

            content_iframe = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "contentIframe")))
            driver.switch_to.frame(content_iframe)

            old_password_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "oldpass")))
            old_password_input.clear()
            old_password_input.send_keys(password)
            time.sleep(1)

            new_password_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "newpass")))
            new_password_input.clear()
            new_password_input.send_keys(new_password)
            time.sleep(1)

            confirmed_password_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "confpass")))
            confirmed_password_input.clear()
            confirmed_password_input.send_keys(new_password)
            time.sleep(1)

            apply_changes_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//input[@type='submit' and @name='save' and @value='Apply Changes']")))
            apply_changes_button.click()
            time.sleep(5)

            # Admin -> TR-069
            driver.switch_to.default_content()
            admin_tab = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.XPATH, "//ul[@id='nav']//a[@href='javascript:void(0)' and @rel='9' and normalize-space()='Admin']")))
            admin_tab.click()

            side_menu = WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.ID, "side")))
            tr069_link = WebDriverWait(side_menu, 15).until(
                EC.element_to_be_clickable((By.XPATH, ".//a[@target='contentIframe' and contains(@href,'tr069config.asp') and normalize-space()='TR-069']")))
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", tr069_link)
            try:
                tr069_link.click()
            except Exception:
                driver.execute_script("arguments[0].click();", tr069_link)

            WebDriverWait(driver, 15).until(EC.frame_to_be_available_and_switch_to_it((By.ID, "contentIframe")))

            url_input = WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.NAME, "url")))
            url_input.clear()
            url_input.send_keys("http://172.22.16.109:7995/")
            time.sleep(1)

            username_input = driver.find_element(By.NAME, "username")
            username_input.clear()
            username_input.send_keys("admin")

            password_input = driver.find_element(By.NAME, "password")
            password_input.clear()
            password_input.send_keys("admin")
            time.sleep(1)

            conreq_user = driver.find_element(By.NAME, "conreqname")
            conreq_user.clear()
            conreq_user.send_keys("admin")

            conreq_pw = driver.find_element(By.NAME, "conreqpw")
            conreq_pw.clear()
            conreq_pw.send_keys("admin")
            time.sleep(1)

            apply_button = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.XPATH, "//input[@type='submit' and @name='save' and @value='Apply']")))
            apply_button.click()
            time.sleep(5)

            try:
                WebDriverWait(driver, 3).until(EC.alert_is_present())
                driver.switch_to.alert.accept()
            except Exception:
                pass

            # Advance -> Remote Access
            driver.switch_to.default_content()
            nav_menu = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "nav")))
            advance_tab = WebDriverWait(nav_menu, 15).until(
                EC.element_to_be_clickable((By.XPATH, ".//a[@href='javascript:void(0)' and @rel='7' and normalize-space()='Advance']")))
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", advance_tab)
            try:
                advance_tab.click()
            except Exception:
                driver.execute_script("arguments[0].click();", advance_tab)

            side_menu = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "side")))
            remote_access_link = WebDriverWait(side_menu, 15).until(
                EC.element_to_be_clickable((By.XPATH, ".//a[@target='contentIframe' and @href='rmtacc.asp' and normalize-space()='Remote Access']")))
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", remote_access_link)
            try:
                remote_access_link.click()
            except Exception:
                driver.execute_script("arguments[0].click();", remote_access_link)

            WebDriverWait(driver, 15).until(EC.frame_to_be_available_and_switch_to_it((By.ID, "contentIframe")))
            https_wan_checkbox = WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.NAME, "w_https")))
            if not https_wan_checkbox.is_selected():
                https_wan_checkbox.click()

            apply_changes_button = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.XPATH, "//input[@type='submit' and @name='set' and @value='Apply Changes']")))
            apply_changes_button.click()

            archivo_guardado = self.guardar_resumen_configuracion(ssid_name, wpa_password, new_password)
            if archivo_guardado:
                self.actualizar_estado(f"Configuración completada. Guardado en: {archivo_guardado}")
            else:
                self.actualizar_estado("Configuración completada. No se pudo guardar el archivo de resumen.")

        except Exception as e:
            error_msg = f"Error durante la configuración: {str(e)}"
            logger.error(error_msg)
            self.safe_messagebox("Error durante la configuración", error_msg, kind="error")
            self.actualizar_estado(f"ERROR: {str(e)}")

        finally:
            try:
                if driver:
                    driver.quit()
            except Exception as e:
                logger.warning(f"No se pudo cerrar el navegador: {e}")

            self.set_buttons_enabled(True)
            self.stop_progress()
            logger.info("Proceso de configuración finalizado")

    # ===== Guardado en carpeta única "Datacom Configuradas" =====
    def guardar_resumen_configuracion(self, ssid: str, wpa: str, admin_pass: str) -> str:
        try:
            ahora = datetime.datetime.now()
            fecha = ahora.strftime("%d-%m-%Y")
            hora = ahora.strftime("%H-%M-%S")

            documentos = os.path.join(os.path.expanduser("~"), "Documents")
            if not os.path.isdir(documentos):
                documentos = os.path.expanduser("~")

            base_dir = os.path.join(documentos, "Datacom Configuradas")
            os.makedirs(base_dir, exist_ok=True)

            safe_ssid = "".join(c for c in (ssid or "") if c.isalnum() or c in ("-", "_")).strip()
            file_name = f"{fecha} {hora} - {safe_ssid}.txt" if safe_ssid else f"{fecha} {hora}.txt"
            file_path = os.path.join(base_dir, file_name)

            contenido = (
                "Configuración completada de ONU\n"
                f"Fecha: {fecha}\n"
                f"Hora: {hora}\n"
                f"SSID: {ssid}\n"
                f"Contraseña: {wpa}\n"
                f"Contraseña administrador: {admin_pass}\n"
            )
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(contenido)

            logger.info(f"Resumen de configuración guardado en: {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"No se pudo guardar el resumen de configuración: {e}")
            return ""


def mostrar_logs():
    logger.info("Abriendo visor de logs")
    log_window = tk.Toplevel()
    log_window.title("Visor de Logs - Configurador Datacom")
    log_window.geometry("800x600")
    log_window.configure(bg="#f5f5f5")


if __name__ == "__main__":
    root = tk.Tk()
    app = ConfiguradorModem(root)
    root.mainloop()
