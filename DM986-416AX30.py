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
        self.root.geometry("650x680")
        self.root.resizable(False, False)
        self.root.configure(bg="#f5f5f5")

        try:
            self.root.iconbitmap("datacom_config.ico")
        except:
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

        # Variables
        self.browser_choice = tk.StringVar(value="1")  # Chrome por defecto
        self.username = tk.StringVar()
        self.password = tk.StringVar()
        self.ssid_name = tk.StringVar()
        self.wpa_password = tk.StringVar()
        self.new_password = tk.StringVar()

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

        # Header
        self.header_frame = ttk.Frame(self.root, style="Header.TFrame")
        self.header_frame.pack(fill=tk.X)
        header_title = ttk.Label(self.header_frame, text="DATACOM DM986 - Configurador Automático", style="Header.TLabel")
        header_title.pack(pady=10)

        # Main
        self.main_frame = ttk.Frame(self.root, padding="20", style="TFrame")
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

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
                ttk.Checkbutton(config_frame, text="Ocultar", variable=show_var,
                                command=lambda e=entry, v=show_var: self.toggle_password(e, v))\
                    .grid(row=i, column=2, sticky=tk.W)
            else:
                ttk.Entry(config_frame, textvariable=var, width=30).grid(row=i, column=1, sticky=tk.W, padx=10)

        # Botón principal
        button_section = tk.Frame(self.main_frame, bg="#E3F2FD")
        button_section.pack(fill=tk.X, pady=(10, 5))
        tk.Label(button_section, text="INICIAR PROCESO:", font=("Segoe UI", 11), bg="#E3F2FD").pack(pady=(2, 0))
        self.big_configure_button = tk.Button(button_section, text="Configurar Modem",
                                              command=self.iniciar_configuracion, bg="#1976D2",
                                              fg="white", font=("Segoe UI", 11), width=30, height=1, relief=tk.RAISED)
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

        # Footer
        info_frame = ttk.Frame(self.root, style="TFrame")
        info_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=5)
        ttk.Label(info_frame, text="© Luis Miraglio | miraglioluis1@gmail.com", font=self.small_font)\
           .pack(side=tk.RIGHT, padx=10)

    # ===== Helpers UI thread-safe =====
    def actualizar_estado(self, mensaje: str):
        """Actualiza el estado en el hilo principal"""
        logger.info(mensaje)
        self.root.after(0, lambda: self.status_var.set(mensaje))

    def safe_messagebox(self, title: str, text: str, kind: str = "error"):
        """Messagebox seguro desde hilo de trabajo"""
        def _show():
            if kind == "error":
                messagebox.showerror(title, text)
            elif kind == "warning":
                messagebox.showwarning(title, text)
            else:
                messagebox.showinfo(title, text)
        self.root.after(0, _show)

    def set_buttons_enabled(self, enabled: bool):
        """Habilita/deshabilita botones en el hilo principal"""
        def _set():
            if hasattr(self, 'configure_button'):
                self.configure_button.config(state="normal" if enabled else "disabled")
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
            # Datos
            browser_choice = self.browser_choice.get()
            username = self.username.get()
            password = self.password.get()
            ssid_name = self.ssid_name.get()
            wpa_password = self.wpa_password.get()
            new_password = self.new_password.get()

            logger.info(f"Configurando modem con usuario '{username}' y SSID '{ssid_name}'")

            # Driver
            def setup_driver():
                # Determinar el navegador según la elección del usuario
                if browser_choice == "1":  # Chrome
                    self.actualizar_estado("Inicializando Google Chrome...")
                    options = ChromeOptions()
                    options.add_argument("--ignore-certificate-errors")
                    options.add_argument("--ignore-ssl-errors")
                    options.add_argument("--disable-web-security")
                    options.add_argument("--allow-running-insecure-content")
                    # === Mantener ventana abierta tras driver.quit() ===
                    options.add_experimental_option("detach", True)
                    try:
                        return webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
                    except Exception as e:
                        self.actualizar_estado(f"Error al inicializar Chrome: {e}")
                        logger.error(f"Error al inicializar Chrome: {e}")

                elif browser_choice == "2":  # Edge (Chromium)
                    self.actualizar_estado("Inicializando Microsoft Edge...")
                    options = EdgeOptions()
                    options.add_argument("--ignore-certificate-errors")
                    options.add_argument("--ignore-ssl-errors")
                    options.add_argument("--disable-web-security")
                    options.add_argument("--allow-running-insecure-content")
                    # === Mantener ventana abierta tras driver.quit() ===
                    options.add_experimental_option("detach", True)
                    try:
                        return webdriver.Edge(service=EdgeService(EdgeChromiumDriverManager().install()), options=options)
                    except Exception as e:
                        self.actualizar_estado(f"Error al inicializar Edge: {e}")
                        logger.error(f"Error al inicializar Edge: {e}")

                elif browser_choice == "3":  # Firefox
                    self.actualizar_estado("Inicializando Firefox...")
                    options = FirefoxOptions()
                    options.accept_insecure_certs = True
                    try:
                        return webdriver.Firefox(service=FirefoxService(GeckoDriverManager().install()), options=options)
                    except Exception as e:
                        self.actualizar_estado(f"Error al inicializar Firefox: {e}")
                        logger.error(f"Error al inicializar Firefox: {e}")

                else:  # Autodetectar (Chrome -> Edge -> Firefox)
                    for browser in ['chrome', 'edge', 'firefox']:
                        try:
                            if browser == 'chrome':
                                self.actualizar_estado("Intentando con Chrome...")
                                options = ChromeOptions()
                                options.add_argument("--ignore-certificate-errors")
                                options.add_argument("--ignore-ssl-errors")
                                options.add_argument("--disable-web-security")
                                options.add_argument("--allow-running-insecure-content")
                                # === Mantener ventana abierta tras driver.quit() ===
                                options.add_experimental_option("detach", True)
                                return webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)

                            elif browser == 'edge':
                                self.actualizar_estado("Intentando con Edge...")
                                options = EdgeOptions()
                                options.add_argument("--ignore-certificate-errors")
                                options.add_argument("--ignore-ssl-errors")
                                options.add_argument("--disable-web-security")
                                options.add_argument("--allow-running-insecure-content")
                                # === Mantener ventana abierta tras driver.quit() ===
                                options.add_experimental_option("detach", True)
                                return webdriver.Edge(service=EdgeService(EdgeChromiumDriverManager().install()), options=options)

                            elif browser == 'firefox':
                                self.actualizar_estado("Intentando con Firefox...")
                                options = FirefoxOptions()
                                options.accept_insecure_certs = True
                                return webdriver.Firefox(service=FirefoxService(GeckoDriverManager().install()), options=options)

                        except Exception as e:
                            self.actualizar_estado(f"No se pudo inicializar {browser}: {e}")
                            logger.warning(f"No se pudo inicializar {browser}: {e}")
                            continue

                # Si llegamos aquí, ningún navegador funcionó
                raise Exception("No se encontró ningún navegador compatible instalado.")

            try:
                driver = setup_driver()
                logger.info("Navegador inicializado correctamente")
                self.actualizar_estado("Navegador inicializado correctamente.")
            except Exception as e:
                logger.error(f"Error al inicializar el navegador: {str(e)}")
                raise

            try:
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
                logger.info("Formulario de login enviado")

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

                # WAN nuevo enlace TR069 VLAN 600
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

                chanwid_dropdown = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "chanwid")))
                for option in chanwid_dropdown.find_elements(By.TAG_NAME, "option"):
                    if option.get_attribute("value") == "3":
                        option.click()
                        break
                time.sleep(1)

                chan_select_dropdown = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "chan_select")))
                for option in chan_select_dropdown.find_elements(By.TAG_NAME, "option"):
                    if option.get_attribute("value") == "0":
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

                chanwid_dropdown_wlan1 = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "chanwid")))
                for option in chanwid_dropdown_wlan1.find_elements(By.TAG_NAME, "option"):
                    if option.get_attribute("value") == "3":
                        option.click()
                        break
                time.sleep(1)

                chan_select_dropdown_wlan1 = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "chan_select")))
                for option in chan_select_dropdown_wlan1.find_elements(By.TAG_NAME, "option"):
                    if option.get_attribute("value") == "0":
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

                show_old_password_checkbox = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//input[@type='checkbox' and @onclick='show_password(3)']")))
                show_old_password_checkbox.click()

                new_password_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "newpass")))
                new_password_input.clear()
                new_password_input.send_keys(new_password)
                time.sleep(1)

                show_new_password_checkbox = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//input[@type='checkbox' and @onclick='show_password(1)']")))
                show_new_password_checkbox.click()

                confirmed_password_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "confpass")))
                confirmed_password_input.clear()
                confirmed_password_input.send_keys(new_password)
                time.sleep(1)

                show_confirmed_password_checkbox = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//input[@type='checkbox' and @onclick='show_password(2)']")))
                show_confirmed_password_checkbox.click()

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
                try:
                    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", advance_tab)
                    advance_tab.click()
                except Exception:
                    driver.execute_script("arguments[0].click();", advance_tab)

                side_menu = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "side")))
                remote_access_link = WebDriverWait(side_menu, 15).until(
                    EC.element_to_be_clickable((By.XPATH, ".//a[@target='contentIframe' and @href='rmtacc.asp' and normalize-space()='Remote Access']")))
                try:
                    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", remote_access_link)
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

                # Guardar archivo con credenciales reales
                archivo_guardado = self.guardar_resumen_configuracion(ssid_name, wpa_password, new_password)
                if archivo_guardado:
                    self.actualizar_estado(f"Configuración completada. Guardado en: {archivo_guardado}")
                else:
                    self.actualizar_estado("Configuración completada. No se pudo guardar el archivo de resumen.")

            except Exception as e:
                error_msg = f"Error durante la configuración: {str(e)}"
                logger.error(error_msg)

                # Capturas de diagnóstico
                try:
                    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    documentos = os.path.join(os.path.expanduser("~"), "Documents")
                    if not os.path.isdir(documentos):
                        documentos = os.path.expanduser("~")
                    base_dir = os.path.join(documentos, "Datacom Configuradas")
                    os.makedirs(base_dir, exist_ok=True)
                    if driver:
                        screenshot_path = os.path.join(base_dir, f"error_{ts}.png")
                        html_path = os.path.join(base_dir, f"error_{ts}.html")
                        driver.save_screenshot(screenshot_path)
                        with open(html_path, "w", encoding="utf-8") as f:
                            f.write(driver.page_source)
                        logger.info(f"Capturas de error guardadas: {screenshot_path} / {html_path}")
                except Exception as cap_err:
                    logger.warning(f"No se pudieron guardar capturas de error: {cap_err}")

                self.safe_messagebox("Error durante la configuración", error_msg, kind="error")
                self.actualizar_estado(f"ERROR: {str(e)}")

        except Exception as e:
            error_msg = f"No se pudo iniciar el navegador o proceso: {str(e)}"
            logger.error(error_msg)
            self.safe_messagebox("Error de inicialización", error_msg, kind="error")
            self.actualizar_estado(f"ERROR: {str(e)}")
        finally:
            # NO cerrar el navegador para poder revisarlo manualmente
            try:
                if 'driver' in locals() and driver:
                    # Para Chrome/Edge, con detach=True el navegador queda abierto.
                    # Para Firefox, no llamamos quit() (queda abierto mientras la app siga viva).
                    pass
            except Exception as e:
                logger.warning(f"No se pudo gestionar el navegador al finalizar: {e}")

            # Restaurar UI
            self.set_buttons_enabled(True)
            self.stop_progress()
            logger.info("Proceso de configuración finalizado. El navegador queda abierto; cerralo con la ❌ cuando termines.")


    # ===== Guardado en carpeta única "Datacom Configuradas" =====
    def guardar_resumen_configuracion(self, ssid: str, wpa: str, admin_pass: str) -> str:
        """
        Guarda el resumen en ~/Documents/Datacom Configuradas
        Crea un archivo por configuración con fecha/hora + SSID en el nombre.
        """
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

# Visor de logs (sin unificar rutas; queda igual)
def mostrar_logs():
    logger.info("Abriendo visor de logs")
    log_window = tk.Toplevel()
    log_window.title("Visor de Logs - Configurador Datacom")
    log_window.geometry("800x600")
    log_window.configure(bg="#f5f5f5")

    try:
        log_window.iconbitmap("datacom_config.ico")
    except:
        pass

    primary_color = "#1976D2"
    bg_color = "#F5F5F5"

    header_frame = tk.Frame(log_window, bg=primary_color)
    header_frame.pack(fill=tk.X)
    tk.Label(header_frame, text="Registros del Configurador", font=("Segoe UI", 14, "bold"),
             bg=primary_color, fg="white").pack(pady=10)

    main_frame = tk.Frame(log_window, bg=bg_color)
    main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)

    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
    log_files = []
    if os.path.exists(log_dir):
        log_files = [f for f in os.listdir(log_dir) if f.startswith('datacom_config_') and f.endswith('.log')]
        log_files.sort(reverse=True)

    select_frame = tk.Frame(main_frame, bg=bg_color)
    select_frame.pack(fill=tk.X, pady=10)
    tk.Label(select_frame, text="Seleccionar archivo de registro:", font=("Segoe UI", 10), bg=bg_color)\
      .pack(side=tk.LEFT, padx=5)

    selected_log = tk.StringVar()
    if log_files:
        selected_log.set(log_files[0])

    log_dropdown = ttk.Combobox(select_frame, textvariable=selected_log, values=log_files, state="readonly", width=40)
    log_dropdown.pack(side=tk.LEFT, padx=10)

    def cargar_log():
        log_text.config(state=tk.NORMAL)
        log_text.delete(1.0, tk.END)
        selected_file = selected_log.get()
        if selected_file:
            log_path = os.path.join(log_dir, selected_file)
            try:
                with open(log_path, 'r', encoding='utf-8') as f:
                    contenido = f.read()
                    log_text.insert(tk.END, contenido)
            except Exception as e:
                log_text.insert(tk.END, f"Error al leer el archivo: {str(e)}")
        log_text.config(state=tk.DISABLED)

    ttk.Button(select_frame, text="Cargar", command=cargar_log).pack(side=tk.LEFT, padx=5)

    log_frame = tk.Frame(main_frame, bg=bg_color)
    log_frame.pack(fill=tk.BOTH, expand=True, pady=10)

    log_text = tk.Text(log_frame, wrap=tk.WORD, font=("Consolas", 9), bg="white", fg="#212121", bd=1, relief=tk.SOLID)
    log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    scrollbar = ttk.Scrollbar(log_frame, command=log_text.yview)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    log_text.config(yscrollcommand=scrollbar.set)

    button_frame = tk.Frame(main_frame, bg=bg_color)
    button_frame.pack(fill=tk.X, pady=15)

    def actualizar_lista():
        if os.path.exists(log_dir):
            new_log_files = [f for f in os.listdir(log_dir) if f.startswith('datacom_config_') and f.endswith('.log')]
            new_log_files.sort(reverse=True)
            log_dropdown['values'] = new_log_files
            if new_log_files:
                selected_log.set(new_log_files[0])
                cargar_log()

    ttk.Button(button_frame, text="Actualizar", command=actualizar_lista).pack(side=tk.LEFT, padx=5)
    ttk.Button(button_frame, text="Cerrar", command=log_window.destroy).pack(side=tk.RIGHT, padx=5)

    if log_files:
        cargar_log()

if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = ConfiguradorModem(root)

        menubar = tk.Menu(root)
        root.config(menu=menubar)
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Herramientas", menu=tools_menu)
        tools_menu.add_command(label="Ver registros", command=mostrar_logs)

        logger.info("Interfaz gráfica inicializada correctamente")
        root.mainloop()

    except Exception as e:
        logger.critical(f"Error no controlado en la aplicación: {str(e)}")
        messagebox.showerror("Error crítico",
                             f"Ha ocurrido un error inesperado en la aplicación:\n{str(e)}\n\n"
                             f"Consulte los logs para más detalles.")

# Para compilar (ejemplo):
# pyinstaller --onefile --noconsole --icon=datacom_config.ico --add-data "datacom_config.ico;." --hidden-import=webdriver_manager.chrome --hidden-import=webdriver_manager.microsoft --hidden-import=webdriver_manager.firefox --hidden-import=tkinter --name "Configurador Datacom DM986" "DM986-416AX30.py"

