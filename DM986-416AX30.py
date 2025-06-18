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
import platform
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
    import webdriver_manager
except ImportError:
    print("Instalando las bibliotecas necesarias...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "webdriver-manager"])
    print("Bibliotecas instaladas correctamente. Reiniciando script...")
    os.execv(sys.executable, ['python'] + sys.argv)

# Configuración del sistema de logs
def setup_logger():
    """Configura el sistema de logs de la aplicación"""
    # Determinar la ubicación adecuada según si es una aplicación compilada o no
    if getattr(sys, 'frozen', False):
        # Estamos en una aplicación compilada
        # Usar la carpeta de datos de la aplicación del usuario
        app_dir = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 
                              'ConfiguradorDatacom')
    else:
        # Estamos en desarrollo
        app_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Crear directorio de logs
    log_dir = os.path.join(app_dir, 'logs')
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Nombre del archivo de log con fecha
    log_file = os.path.join(log_dir, f'datacom_config_{datetime.datetime.now().strftime("%Y%m%d")}.log')
    
    # Configurar el logger principal
    logger = logging.getLogger('DatacomConfig')
    logger.setLevel(logging.DEBUG)
    
    # Evitar duplicación de handlers si el logger ya está configurado
    if not logger.handlers:
        # Handler para archivo con rotación (máximo 5 archivos de 5MB cada uno)
        file_handler = RotatingFileHandler(
            log_file, maxBytes=5*1024*1024, backupCount=5, encoding='utf-8'
        )
        file_formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] - %(message)s', 
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        
        # Handler para consola (útil durante desarrollo)
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(console_formatter)
        console_handler.setLevel(logging.INFO)
        logger.addHandler(console_handler)
        
    return logger

# Inicializar el logger global
logger = setup_logger()
logger.info("=== Iniciando Configurador Automático de Modem Datacom DM986 ===")

# Definición de la clase para la interfaz gráfica
class ConfiguradorModem:
    def __init__(self, root):
        logger.info("Inicializando interfaz gráfica")
        self.root = root
        self.root.title("Configurador Automático de Modem Datacom DM986")
        self.root.geometry("650x680")  # Ventana más alta para acomodar todos los elementos
        self.root.resizable(False, False)
        self.root.configure(bg="#f5f5f5")
        
        # Intentar establecer icono si existe
        try:
            self.root.iconbitmap("datacom_config.ico")
        except:
            pass
        
        # Definir colores principales
        self.primary_color = "#1976D2"  # Azul principal
        self.secondary_color = "#2196F3"  # Azul secundario
        self.accent_color = "#03A9F4"  # Azul acento
        self.warning_color = "#FFC107"  # Amarillo
        self.success_color = "#4CAF50"  # Verde
        self.error_color = "#F44336"  # Rojo
        self.bg_color = "#F5F5F5"  # Gris muy claro/casi blanco
        self.text_color = "#212121"  # Gris muy oscuro/casi negro
        
        # Crear variables para almacenar la configuración
        self.browser_choice = tk.StringVar(value="1")  # Default: Chrome
        self.username = tk.StringVar()
        self.password = tk.StringVar()
        self.ssid_name = tk.StringVar()
        self.wpa_password = tk.StringVar()
        self.new_password = tk.StringVar()
        
        # Crear fuentes personalizadas
        self.title_font = font.Font(family="Segoe UI", size=16, weight="bold")
        self.header_font = font.Font(family="Segoe UI", size=12, weight="bold")
        self.normal_font = font.Font(family="Segoe UI", size=10)
        self.small_font = font.Font(family="Segoe UI", size=9)
        self.button_font = font.Font(family="Segoe UI", size=10, weight="bold")
        
        # Crear el estilo
        self.style = ttk.Style()
        self.style.theme_use('clam')  # Usar un tema base limpio
        
        # Configurar estilos personalizados
        self.style.configure("TFrame", background=self.bg_color)
        self.style.configure("Header.TFrame", background=self.primary_color)
        
        self.style.configure("TLabel", 
                            background=self.bg_color, 
                            foreground=self.text_color, 
                            font=self.normal_font)
        
        self.style.configure("Header.TLabel", 
                            background=self.primary_color, 
                            foreground="white", 
                            font=self.header_font)
        
        self.style.configure("Title.TLabel", 
                            background=self.bg_color, 
                            foreground=self.primary_color, 
                            font=self.title_font)
        
        self.style.configure("Status.TLabel", 
                            background=self.bg_color, 
                            foreground=self.primary_color, 
                            font=self.normal_font)
                            
        self.style.configure("TRadiobutton", 
                            background=self.bg_color, 
                            foreground=self.text_color, 
                            font=self.normal_font)
        
        # Configurar estilo del botón principal (haciéndolo más llamativo)
        self.style.configure(
            "Accent.TButton", 
            background=self.accent_color, 
            foreground="white", 
            font=("Segoe UI", 11, "bold")
        )
        
        self.style.map(
            "Accent.TButton",
            background=[
                ('pressed', self.primary_color), 
                ('active', self.primary_color)
            ],
            foreground=[('pressed', 'white'), ('active', 'white')]
        )
        
        # Añadir este estilo más llamativo para el botón principal
        self.style.configure(
            "BigButton.TButton", 
            background="#FF5722", 
            foreground="white", 
            font=("Segoe UI", 14, "bold"),
            padding=10
        )
        
        self.style.map(
            "BigButton.TButton",
            background=[('pressed', "#E64A19"), ('active', "#FF7043")],
            foreground=[('pressed', 'white'), ('active', 'white')]
        )
        
        # Configurar LabelFrame                
        self.style.configure("TLabelframe", 
                            background=self.bg_color,
                            foreground=self.primary_color,
                            font=self.header_font)
        
        self.style.configure("TLabelframe.Label", 
                            background=self.bg_color,
                            foreground=self.primary_color,
                            font=self.header_font)
        
        # Configurar Checkbutton
        self.style.configure("TCheckbutton",
                            background=self.bg_color,
                            foreground=self.text_color,
                            font=self.normal_font)
        
        # Configurar barra de progreso
        self.style.configure("TProgressbar", 
                            troughcolor=self.bg_color, 
                            background=self.secondary_color,
                            thickness=10)
        
        # Header frame - Barra superior
        self.header_frame = ttk.Frame(self.root, style="Header.TFrame")
        self.header_frame.pack(fill=tk.X)
        
        # Título en la barra superior
        header_title = ttk.Label(self.header_frame, 
                                text="DATACOM DM986 - Configurador Automático",
                                style="Header.TLabel")
        header_title.pack(pady=10)
        
        # Marco principal
        self.main_frame = ttk.Frame(self.root, padding="20", style="TFrame")
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Sección del navegador
        browser_frame = ttk.LabelFrame(self.main_frame, 
                                      text="SELECCIONE NAVEGADOR", 
                                      padding="15 10 15 15")
        browser_frame.pack(fill=tk.X, pady=10)
        
        # Grid para organizar los radio buttons
        for i, (browser_text, browser_val) in enumerate([
            ("Google Chrome (recomendado)", "1"),
            ("Microsoft Edge", "2"),
            ("Firefox", "3"),
            ("Autodetectar (puede ser más lento)", "4")
        ]):
            ttk.Radiobutton(browser_frame, 
                          text=browser_text, 
                          variable=self.browser_choice, 
                          value=browser_val).grid(row=i, column=0, sticky=tk.W, pady=3)
        
        # Sección de credenciales y configuración
        config_frame = ttk.LabelFrame(self.main_frame, 
                                     text="INFORMACIÓN DE CONFIGURACIÓN", 
                                     padding="15 10 15 15")
        config_frame.pack(fill=tk.X, pady=10)
        
        # Crear y organizar los campos de entrada
        field_labels = [
            "Nombre de usuario del modem:",
            "Contraseña actual del modem:",
            "Nombre de la red Wi-Fi (SSID):",
            "Contraseña WPA para WiFi:",
            "Nueva contraseña admin:"
        ]
        
        field_vars = [
            self.username,
            self.password,
            self.ssid_name,
            self.wpa_password,
            self.new_password
        ]
        
        self.entry_fields = []  # Para guardar referencias a los campos de contraseña
        
        # Modificar la parte donde se crean los campos de entrada para que las contraseñas se muestren por defecto
        for i, (label_text, var) in enumerate(zip(field_labels, field_vars)):
            ttk.Label(config_frame, text=label_text).grid(row=i, column=0, sticky=tk.W, pady=8)
            
            # Si es un campo de contraseña
            if i in [1, 3, 4]:  # Campos de contraseña
                entry = ttk.Entry(config_frame, textvariable=var, width=30)  # Ya no usamos show="*" para que se vean los caracteres
                entry.grid(row=i, column=1, sticky=tk.W, padx=10)
                self.entry_fields.append(entry)
                
                # Variables para mostrar/ocultar contraseña (ahora por defecto es mostrar)
                show_var = tk.BooleanVar(value=True)  # Cambiado a True para mostrar por defecto
                check = ttk.Checkbutton(config_frame, text="Ocultar",  # Cambiado a "Ocultar" ya que ahora el comportamiento es inverso
                                        variable=show_var, 
                                        command=lambda e=entry, v=show_var: self.toggle_password(e, v))
                check.grid(row=i, column=2, sticky=tk.W)
            else:
                ttk.Entry(config_frame, textvariable=var, width=30).grid(row=i, column=1, sticky=tk.W, padx=10)
        
        # Sección del botón para iniciar configuración - SIMPLIFICADA
        button_section = tk.Frame(self.main_frame, bg="#E3F2FD")
        button_section.pack(fill=tk.X, pady=(10, 5))

        # Título simple
        tk.Label(button_section, 
                text="INICIAR PROCESO:", 
                font=("Segoe UI", 11),
                bg="#E3F2FD").pack(pady=(2, 0))

        # Botón simple y directo como en la imagen de referencia
        self.big_configure_button = tk.Button(
            button_section,
            text="Configurar Modem",
            command=self.iniciar_configuracion,
            bg="#1976D2",  # Azul principal
            fg="white",
            font=("Segoe UI", 11),
            width=30,      # Ancho fijo
            height=1,      # Altura fija
            relief=tk.RAISED
        )
        self.big_configure_button.pack(pady=(5, 8))

        # Barra de progreso
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

        # Etiqueta de estado
        self.status_var = tk.StringVar(value="Listo para iniciar configuración")
        self.status_label = ttk.Label(
            progress_frame, 
            textvariable=self.status_var, 
            style="Status.TLabel"
        )
        self.status_label.pack(pady=5)
        
        # Footer con información
        info_frame = ttk.Frame(self.root, style="TFrame")
        info_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=5)
        
        ttk.Label(info_frame, 
                 text="© Luis Miraglio | miraglioluis1@gmail.com", 
                 font=self.small_font).pack(side=tk.RIGHT, padx=10)
        
    def toggle_password(self, entry, var):
        """Alterna la visibilidad de la contraseña en el campo de entrada"""
        if var.get():
            entry.config(show="")  # Mostrar el texto
        else:
            entry.config(show="*")  # Ocultar con asteriscos
            
    def iniciar_configuracion(self):
        """Inicia el proceso de configuración en un hilo separado"""
        # Validar que todos los campos estén completos
        if not all([self.username.get(), self.password.get(), self.ssid_name.get(),
                    self.wpa_password.get(), self.new_password.get()]):
            messagebox.showerror("Campos incompletos", "Por favor, complete todos los campos antes de continuar")
            logger.warning("Intento de iniciar configuración con campos incompletos")
            return
        
        logger.info("Iniciando proceso de configuración")
        logger.info(f"Navegador seleccionado: {self.get_browser_name(self.browser_choice.get())}")
        
        # Deshabilitar AMBOS botones durante la configuración
        if hasattr(self, 'configure_button'):
            self.configure_button.config(state="disabled")
        self.big_configure_button.config(state="disabled", bg="#CCCCCC")
        
        self.status_var.set("Iniciando configuración...")
        self.progress.start(10)
        
        # Iniciar el proceso en un hilo separado para no bloquear la GUI
        threading.Thread(target=self.proceso_configuracion, daemon=True).start()
    
    def get_browser_name(self, choice):
        """Devuelve el nombre del navegador según la elección"""
        browsers = {
            "1": "Google Chrome",
            "2": "Microsoft Edge",
            "3": "Firefox",
            "4": "Autodetectar"
        }
        return browsers.get(choice, "Desconocido")
    
    def actualizar_estado(self, mensaje):
        """Actualiza el mensaje de estado en la interfaz y lo registra en el log"""
        self.status_var.set(mensaje)
        logger.info(mensaje)
        self.root.update_idletasks()
    
    def proceso_configuracion(self):
        """Realiza todo el proceso de configuración del modem"""
        try:
            # Recopilar datos del formulario
            browser_choice = self.browser_choice.get()
            username = self.username.get()
            password = self.password.get()
            ssid_name = self.ssid_name.get()
            wpa_password = self.wpa_password.get()
            new_password = self.new_password.get()
            
            logger.info(f"Configurando modem con usuario '{username}' y SSID '{ssid_name}'")
            
            # Función para inicializar el driver según la elección del usuario
            def setup_driver():
                browser = None
                
                # Determinar el navegador según la elección del usuario
                if browser_choice == "1":  # Chrome
                    self.actualizar_estado("Inicializando Google Chrome...")
                    options = ChromeOptions()
                    options.add_argument("--ignore-certificate-errors")
                    options.add_argument("--ignore-ssl-errors")
                    options.add_argument("--disable-web-security")
                    options.add_argument("--allow-running-insecure-content")
                    try:
                        return webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
                    except Exception as e:
                        self.actualizar_estado(f"Error al inicializar Chrome: {e}")
                        logger.error(f"Error al inicializar Chrome: {e}")
                        
                elif browser_choice == "2":  # Edge
                    self.actualizar_estado("Inicializando Microsoft Edge...")
                    options = EdgeOptions()
                    options.add_argument("--ignore-certificate-errors")
                    options.add_argument("--ignore-ssl-errors")
                    options.add_argument("--disable-web-security")
                    options.add_argument("--allow-running-insecure-content")
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
                
                else:  # Autodetectar (opción 4 o cualquier otra entrada)
                    # Lista de navegadores a probar en orden de preferencia
                    browsers = ['chrome', 'edge', 'firefox']
                    
                    for browser in browsers:
                        try:
                            if browser == 'chrome':
                                self.actualizar_estado("Intentando con Chrome...")
                                options = ChromeOptions()
                                options.add_argument("--ignore-certificate-errors")
                                options.add_argument("--ignore-ssl-errors")
                                options.add_argument("--disable-web-security")
                                options.add_argument("--allow-running-insecure-content")
                                return webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
                            
                            elif browser == 'edge':
                                self.actualizar_estado("Intentando con Edge...")
                                options = EdgeOptions()
                                options.add_argument("--ignore-certificate-errors")
                                options.add_argument("--ignore-ssl-errors")
                                options.add_argument("--disable-web-security")
                                options.add_argument("--allow-running-insecure-content")
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
            
            # Inicializar el driver
            self.actualizar_estado("Inicializando el navegador...")
            try:
                driver = setup_driver()
                logger.info("Navegador inicializado correctamente")
                self.actualizar_estado("Navegador inicializado correctamente.")
            except Exception as e:
                logger.error(f"Error al inicializar el navegador: {str(e)}")
                raise
            
            try:
                # Ir al login
                logger.info("Accediendo a la página de login del modem (192.168.0.1)")
                driver.get("https://192.168.0.1/admin/login.asp")
                time.sleep(2)  # espera corta inicial
                
                # Ver si hay iframe
                iframes = driver.find_elements(By.TAG_NAME, "iframe")
                if iframes:
                    logger.debug("Iframe detectado, cambiando al iframe")
                    driver.switch_to.frame(iframes[0])  # entrar al primer iframe
                
                # Esperar campo usuario
                self.actualizar_estado("Completando credenciales de acceso...")
                username_field = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.NAME, "username"))
                )
                username_field.send_keys(username)
                logger.debug("Campo de usuario completado")
                
                # Contraseña
                password_field = driver.find_element(By.NAME, "password")
                password_field.send_keys(password)
                logger.debug("Campo de contraseña completado")
                
                # Codificar
                encoded_password = base64.b64encode(password.encode('utf-8')).decode('utf-8')
                driver.execute_script("""
                    document.getElementsByName('encodePassword')[0].value = arguments[0];
                    document.getElementsByName('password')[0].disabled = true;
                """, encoded_password)
                logger.debug("Contraseña codificada")
                
                # Enviar
                login_button = driver.find_element(By.XPATH, "//input[@type='submit' and @value='Login']")
                login_button.click()
                logger.info("Formulario de login enviado")
                
                # Esperar a que el menú de navegación <ul id="nav"> esté presente
                self.actualizar_estado("Accediendo al modem...")
                nav_menu = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "nav"))
                )
                logger.info("Login exitoso, interfaz del modem cargada")
                
                # Hacer clic en el enlace "WAN"
                self.actualizar_estado("Configurando sección WAN...")
                wan_link = nav_menu.find_element(By.XPATH, ".//a[@rel='4' and text()='WAN']")
                wan_link.click()
                logger.info("Navegando a la sección WAN")
                
                # Esperar a que el iframe con id "contentIframe" esté presente
                content_iframe = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "contentIframe"))
                )
                
                # Cambiar al iframe
                driver.switch_to.frame(content_iframe)
                
                # Buscar y hacer clic en el checkbox "vlan"
                vlan_checkbox = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//input[@type='checkbox' and @name='vlan' and @value='ON']"))
                )
                vlan_checkbox.click()
                logger.info("VLAN activada")
                
                # Ingresar el número 500 en el campo VLAN ID
                vid_input = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//input[@name='vid']"))
                )
                vid_input.clear()  # Limpiar el campo antes de ingresar el valor
                vid_input.send_keys("500")
                logger.info("VLAN ID configurado a 500")
                
                # Seleccionar la opción "IPoE" en el menú desplegable "Channel Mode"
                channel_mode_dropdown = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.NAME, "adslConnectionMode"))
                )
                for option in channel_mode_dropdown.find_elements(By.TAG_NAME, "option"):
                    if option.get_attribute("value") == "1":
                        option.click()
                        logger.info("Modo de canal configurado a IPoE")
                        break
                
                # Marcar el checkbox "chkpt_all" Port Mapping
                chkpt_all_checkbox = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//input[@name='chkpt_all']"))
                )
                chkpt_all_checkbox.click()
                logger.info("Port Mapping activado para todos los puertos")
                
                # Hacer clic en el botón "Apply Changes" después de marcar el checkbox
                apply_changes_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//input[@type='submit' and @value='Apply Changes' and @name='apply']"))
                )
                apply_changes_button.click()
                logger.info("Cambios aplicados en la sección WAN")
                time.sleep(2)
                
                # Volver al contexto principal (por si estamos en un iframe aún)
                driver.switch_to.default_content()
                
                # Esperar a que el menú nav vuelva a estar presente
                nav_menu = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "nav"))
                )
                
                # Hacer clic en el enlace "WLAN"
                self.actualizar_estado("Configurando red WiFi 5GHz...")
                wlan_link = nav_menu.find_element(By.XPATH, ".//a[@rel='3' and text()='WLAN']")
                wlan_link.click()
                logger.info("Navegando a la sección WLAN para 5GHz")
                
                # Entrar al iframe WLAN
                content_iframe = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "contentIframe"))
                )
                driver.switch_to.frame(content_iframe)
                
                # Cambiar SSID
                ssid_input = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.NAME, "ssid"))
                )
                ssid_input.clear()
                ssid_input.send_keys(ssid_name)
                logger.info(f"SSID de 5GHz cambiado a: {ssid_name}")
                
                # Asegurarse de que la opción "160MHz" esté seleccionada en el menú desplegable
                chanwid_dropdown = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.NAME, "chanwid"))
                )
                for option in chanwid_dropdown.find_elements(By.TAG_NAME, "option"):
                    if option.get_attribute("value") == "3":
                        option.click()
                        logger.info("Ancho de canal de 5GHz configurado a 160MHz")
                        break
                
                # Asegurarse de que la opción "DFS" esté seleccionada en el menú desplegable "chan_select"
                chan_select_dropdown = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "chan_select"))
                )
                for option in chan_select_dropdown.find_elements(By.TAG_NAME, "option"):
                    if option.get_attribute("value") == "0":
                        option.click()
                        logger.info("Selección de canal de 5GHz configurada a DFS (automático)")
                        break
                
                # Asegurarse de que la opción "100%" esté seleccionada en el menú desplegable "txpower"
                txpower_dropdown = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.NAME, "txpower"))
                )
                for option in txpower_dropdown.find_elements(By.TAG_NAME, "option"):
                    if option.get_attribute("value") == "0":
                        option.click()
                        logger.info("Potencia de transmisión de 5GHz configurada al 100%")
                        break
                
                # Hacer clic en el botón "Apply Changes"
                apply_changes_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//input[@type='submit' and @value='Apply Changes' and @name='save']"))
                )
                apply_changes_button.click()
                logger.info("Cambios aplicados en la sección WLAN de 5GHz")
                time.sleep(5)
                
                # Volver al contexto principal (por si estamos en un iframe aún)
                driver.switch_to.default_content()
                
                # Esperar que aparezca el menú lateral
                side_menu = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "side"))
                )
                
                # Esperar y hacer clic en el enlace 'Security'
                self.actualizar_estado("Configurando seguridad WiFi 5GHz...")
                security_link = WebDriverWait(side_menu, 10).until(
                    EC.element_to_be_clickable((By.XPATH, ".//a[contains(@href, '/wlwpa.asp') and contains(@href, 'wlan_idx=0')]"))
                )
                security_link.click()
                logger.info("Navegando a la sección de seguridad para 5GHz")
                time.sleep(2)
                
                # Cambiar al iframe 'contentIframe'
                content_iframe = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "contentIframe"))
                )
                driver.switch_to.frame(content_iframe)
                
                # Ingresar la contraseña WPA en el campo correspondiente
                wpa_input = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "wpapsk"))
                )
                wpa_input.clear()
                wpa_input.send_keys(wpa_password)
                logger.info("Contraseña WPA de 5GHz configurada")
                
                # Hacer clic en el checkbox para mostrar la contraseña ingresada
                show_password_checkbox = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//input[@type='checkbox' and @onclick='show_password(1)']"))
                )
                show_password_checkbox.click()
                
                # Hacer clic en el botón "Apply Changes"
                apply_changes_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//input[@type='submit' and @name='save' and @value='Apply Changes']"))
                )
                apply_changes_button.click()
                logger.info("Cambios aplicados en la sección de seguridad para 5GHz")
                time.sleep(10)
                
                # Volver al contexto principal por si estamos en un iframe
                driver.switch_to.default_content()
                
                # Esperar que el menú lateral se recargue después del último Apply Changes
                side_menu = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "side"))
                )
                
                # Buscar el título <h3> que contiene el enlace wlan1 (2.4GHz)
                self.actualizar_estado("Configurando red WiFi 2.4GHz...")
                wlan1_header = WebDriverWait(side_menu, 10).until(
                    EC.element_to_be_clickable((By.XPATH, ".//h3/a[text()='wlan1 (2.4GHz)']"))
                )
                wlan1_header.click()
                logger.info("Navegando a la sección WLAN para 2.4GHz")
                time.sleep(2)
                
                # Cambiar al iframe nuevamente (puede haberse recargado)
                content_iframe = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "contentIframe"))
                )
                driver.switch_to.frame(content_iframe)
                
                # Cambiar SSID de wlan1
                ssid_input_wlan1 = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.NAME, "ssid"))
                )
                ssid_input_wlan1.clear()
                ssid_input_wlan1.send_keys(ssid_name)
                logger.info(f"SSID de 2.4GHz cambiado a: {ssid_name}")
                
                # Seleccionar la opción "40MHz" en el campo desplegable "chanwid"
                chanwid_dropdown_wlan1 = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.NAME, "chanwid"))
                )
                for option in chanwid_dropdown_wlan1.find_elements(By.TAG_NAME, "option"):
                    if option.get_attribute("value") == "1":
                        option.click()
                        logger.info("Ancho de canal de 2.4GHz configurado a 40MHz")
                        break
                
                # Seleccionar la opción "Auto" en el campo desplegable "chan_select"
                chan_select_dropdown_wlan1 = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "chan_select"))
                )
                for option in chan_select_dropdown_wlan1.find_elements(By.TAG_NAME, "option"):
                    if option.get_attribute("value") == "0":
                        option.click()
                        logger.info("Selección de canal de 2.4GHz configurada a Auto")
                        break
                
                # Seleccionar la opción "100%" en el campo desplegable "txpower"
                txpower_dropdown_wlan1 = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.NAME, "txpower"))
                )
                for option in txpower_dropdown_wlan1.find_elements(By.TAG_NAME, "option"):
                    if option.get_attribute("value") == "0":
                        option.click()
                        logger.info("Potencia de transmisión de 2.4GHz configurada al 100%")
                        break
                
                # Hacer clic en el botón "Apply Changes"
                apply_changes_button_wlan1 = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//input[@type='submit' and @name='save' and @value='Apply Changes']"))
                )
                apply_changes_button_wlan1.click()
                logger.info("Cambios aplicados en la sección WLAN de 2.4GHz")
                time.sleep(5)
                
                 # Volver al contexto principal por si estamos en un iframe
                driver.switch_to.default_content()
                
                # Esperar que el menú lateral se recargue después del último Apply Changes
                side_menu = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "side"))
                )
                
                # Hacer clic en el enlace 'Security' para wlan1
                self.actualizar_estado("Configurando seguridad WiFi 2.4GHz...")
                security_link_wlan1 = WebDriverWait(side_menu, 10).until(
                    EC.element_to_be_clickable((By.XPATH, ".//a[contains(@href, '/wlwpa.asp') and contains(@href, 'wlan_idx=1')]"))
                )
                security_link_wlan1.click()
                logger.info("Navegando a la sección de seguridad para 2.4GHz")
                
                # Cambiar al iframe 'contentIframe'
                content_iframe = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "contentIframe"))
                )
                driver.switch_to.frame(content_iframe)
                
                # Ingresar la contraseña WPA en el campo correspondiente
                wpa_input = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "wpapsk"))
                )
                wpa_input.clear()
                wpa_input.send_keys(wpa_password)
                logger.info("Contraseña WPA de 2.4GHz configurada")
                
                # Hacer clic en el checkbox para mostrar la contraseña ingresada
                show_password_checkbox = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//input[@type='checkbox' and @onclick='show_password(1)']"))
                )
                show_password_checkbox.click()
                
                # Hacer clic en el botón "Apply Changes"
                apply_changes_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//input[@type='submit' and @name='save' and @value='Apply Changes']"))
                )
                apply_changes_button.click()
                logger.info("Cambios aplicados en la sección de seguridad para 2.4GHz")
                time.sleep(10)
                
                 # Volver al contexto principal (por si estamos en un iframe aún)
                driver.switch_to.default_content()
                
                # Esperar a que el menú nav vuelva a estar presente
                nav_menu = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "nav"))
                )
                
                # Hacer clic en el enlace 'Admin'
                self.actualizar_estado("Cambiando contraseña de administrador...")
                admin_link = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//a[@href='javascript:void(0)' and @rel='9']"))
                )
                admin_link.click()
                logger.info("Navegando a la sección de administración")
                
                # Esperar que el menú lateral se cargue
                side_menu = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "side"))
                )
                
                # Hacer clic en el enlace 'Password'
                password_link = WebDriverWait(side_menu, 10).until(
                    EC.element_to_be_clickable((By.XPATH, ".//a[@target='contentIframe' and @href='password.asp' and text()='Password']"))
                )
                password_link.click()
                logger.info("Navegando a la sección de cambio de contraseña")
                
                # Cambiar al iframe 'contentIframe'
                content_iframe = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "contentIframe"))
                )
                driver.switch_to.frame(content_iframe)
                
                # Ingresar la contraseña antigua en el campo 'Old Password'
                old_password_input = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.NAME, "oldpass"))
                )
                old_password_input.clear()
                old_password_input.send_keys(password)
                logger.info("Contraseña antigua ingresada para cambio")
                
                # Hacer clic en el checkbox para mostrar la contraseña antigua
                show_old_password_checkbox = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//input[@type='checkbox' and @onclick='show_password(3)']"))
                )
                show_old_password_checkbox.click()
                
                # Ingresar la nueva contraseña en el campo 'New Password'
                new_password_input = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.NAME, "newpass"))
                )
                new_password_input.clear()
                new_password_input.send_keys(new_password)
                logger.info("Nueva contraseña ingresada")
                
                # Hacer clic en el checkbox para mostrar la nueva contraseña
                show_new_password_checkbox = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//input[@type='checkbox' and @onclick='show_password(1)']"))
                )
                show_new_password_checkbox.click()
                
                # Ingresar la misma contraseña en el campo 'Confirmed Password'
                confirmed_password_input = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.NAME, "confpass"))
                )
                confirmed_password_input.clear()
                confirmed_password_input.send_keys(new_password)
                logger.info("Contraseña confirmada ingresada")
                
                # Hacer clic en el checkbox para mostrar la contraseña confirmada
                show_confirmed_password_checkbox = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//input[@type='checkbox' and @onclick='show_password(2)']"))
                )
                show_confirmed_password_checkbox.click()
                
                # Hacer clic en el botón "Apply Changes"
                apply_changes_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//input[@type='submit' and @name='save' and @value='Apply Changes']"))
                )
                apply_changes_button.click()
                logger.info("Cambios aplicados en la sección de administración (contraseña)")
                time.sleep(5)
                
                # Volver al contexto principal (por si estamos en un iframe aún)
                driver.switch_to.default_content()
                
                # Esperar a que el menú nav vuelva a estar presente
                nav_menu = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "nav"))
                )
                
                # Hacer clic en el enlace 'Advance'
                self.actualizar_estado("Configurando acceso remoto...")
                advance_link = WebDriverWait(nav_menu, 10).until(
                    EC.element_to_be_clickable((By.XPATH, ".//a[@href='javascript:void(0)' and @rel='7' and text()='Advance']"))
                )
                advance_link.click()
                logger.info("Navegando a la sección de configuración avanzada")
                
                # Esperar que el menú lateral se cargue
                side_menu = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "side"))
                )
                
                # Hacer clic en el enlace 'Remote Access'
                remote_access_link = WebDriverWait(side_menu, 10).until(
                    EC.element_to_be_clickable((By.XPATH, ".//a[@target='contentIframe' and @href='rmtacc.asp' and text()='Remote Access']"))
                )
                remote_access_link.click()
                logger.info("Navegando a la sección de acceso remoto")
                
                # Cambiar al iframe 'contentIframe'
                content_iframe = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "contentIframe"))
                )
                driver.switch_to.frame(content_iframe)
                
                # Hacer clic en el checkbox 'w_https'
                https_wan_checkbox = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.NAME, "w_https"))
                )
                https_wan_checkbox.click()
                logger.info("Acceso remoto por HTTPS activado")
                
                # Hacer clic en el botón "Apply Changes"
                apply_changes_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//input[@type='submit' and @name='set' and @value='Apply Changes']"))
                )
                apply_changes_button.click()
                logger.info("Cambios aplicados en la sección de acceso remoto")
                
                # Detener la barra de progreso
                self.progress.stop()
                
                # Crear un resumen detallado de las operaciones realizadas
                resumen_operaciones = f"""
RESUMEN DE OPERACIONES REALIZADAS:
---------------------------------
                
1. CONFIGURACIÓN WAN:
   ✓ Activó VLAN (ID: 500)
   ✓ Configuró modo de canal: IPoE
   ✓ Activó mapeo de puertos para todos los puertos

2. CONFIGURACIÓN WIFI 5GHz:
   ✓ Nombre de red (SSID): {ssid_name}
   ✓ Ancho de canal: 160MHz
   ✓ Selección de canal: DFS (automático)
   ✓ Potencia de transmisión: 100%
   ✓ Seguridad WPA configurada con contraseña: {wpa_password}

3. CONFIGURACIÓN WIFI 2.4GHz:
   ✓ Nombre de red (SSID): {ssid_name}
   ✓ Ancho de canal: 40MHz
   ✓ Selección de canal: Automático
   ✓ Potencia de transmisión: 100%
   ✓ Seguridad WPA configurada con contraseña: {wpa_password}

4. CONFIGURACIÓN DE SEGURIDAD:
   ✓ Cambió contraseña de administrador de '{password}' a '{new_password}'
   ✓ Activó acceso remoto por HTTPS
"""

                # Guardar el resumen en el log
                logger.info("Resumen de operaciones:\n" + resumen_operaciones)
                
                # Mostrar el resumen en un cuadro de diálogo personalizado
                self.mostrar_resumen_personalizado(resumen_operaciones, username, password, new_password, ssid_name, wpa_password)
                
            except Exception as e:
                # En caso de error en el proceso
                error_msg = f"Error durante la configuración: {str(e)}"
                logger.error(error_msg)
                messagebox.showerror("Error durante la configuración", error_msg)
                self.actualizar_estado(f"ERROR: {str(e)}")
            finally:
                # Cerrar navegador
                self.actualizar_estado("Cerrando el navegador...")
                logger.info("Cerrando el navegador")
                driver.quit()
                # Restaurar botones
                if hasattr(self, 'configure_button'):
                    self.configure_button.config(state="normal")
                self.big_configure_button.config(state="normal", bg="#1976D2")  # Restaurar al azul principal
                self.progress.stop()
                logger.info("Proceso de configuración finalizado")
                
        except Exception as e:
            # En caso de error en la inicialización del navegador
            error_msg = f"No se pudo iniciar el navegador: {str(e)}"
            logger.error(error_msg)
            messagebox.showerror("Error de inicialización", error_msg)
            self.actualizar_estado(f"ERROR: {str(e)}")
            self.configure_button.config(state="normal")
            self.progress.stop()
    
    def mostrar_resumen_personalizado(self, resumen, username, password, new_password, ssid, wpa):
        """Muestra un diálogo personalizado con el resumen de la configuración"""
        logger.info("Mostrando ventana de resumen de configuración")
        # Crear una ventana de resumen más atractiva
        resumen_window = tk.Toplevel(self.root)
        resumen_window.title("Configuración Completada")
        resumen_window.geometry("600x500")
        resumen_window.configure(bg=self.bg_color)
        resumen_window.resizable(False, False)
        
        # Intentar establecer icono si existe
        try:
            resumen_window.iconbitmap("datacom_config.ico")
        except:
            pass
            
        # Encabezado
        header_frame = tk.Frame(resumen_window, bg=self.success_color)
        header_frame.pack(fill=tk.X)
        
        tk.Label(header_frame, 
                text="¡Configuración Completada con Éxito!", 
                font=("Segoe UI", 16, "bold"),
                bg=self.success_color,
                fg="white").pack(pady=15)
        
        # Contenido
        content_frame = tk.Frame(resumen_window, bg=self.bg_color)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Resumen
        tk.Label(content_frame, 
                text="Resumen de Operaciones", 
                font=("Segoe UI", 12, "bold"),
                bg=self.bg_color,
                fg=self.primary_color).pack(pady=(10, 5))
        
        # Área de texto para el resumen
        resumen_text = tk.Text(content_frame, 
                              wrap=tk.WORD, 
                              width=60, 
                              height=16, 
                              font=("Consolas", 10),
                              bg="white", 
                              bd=1, 
                              relief=tk.SOLID)
        resumen_text.pack(pady=5, padx=10, fill=tk.BOTH, expand=True)
        resumen_text.insert(tk.END, resumen)
        resumen_text.config(state=tk.DISABLED)
        
        # Mensaje final
        tk.Label(content_frame, 
                text="Gracias por usar este configurador", 
                font=("Segoe UI", 11),
                bg=self.bg_color,
                fg=self.text_color).pack(pady=(10, 0))
        
        tk.Label(content_frame, 
                text="miraglioluis1@gmail.com", 
                font=("Segoe UI", 10, "italic"),
                bg=self.bg_color,
                fg=self.primary_color).pack(pady=(0, 10))
        
        # Botón para cerrar
        tk.Button(content_frame, 
                 text="CERRAR", 
                 font=("Segoe UI", 10, "bold"),
                 bg=self.primary_color,
                 fg="white",
                 width=20,
                 height=2,
                 relief=tk.FLAT,
                 command=resumen_window.destroy).pack(pady=15)

# Función para mostrar la interfaz de visualización de logs
def mostrar_logs():
    """Abre una ventana para visualizar los logs recientes"""
    logger.info("Abriendo visor de logs")
    
    # Crear ventana
    log_window = tk.Toplevel()
    log_window.title("Visor de Logs - Configurador Datacom")
    log_window.geometry("800x600")
    log_window.configure(bg="#f5f5f5")
    
    # Intentar establecer icono si existe
    try:
        log_window.iconbitmap("datacom_config.ico")
    except:
        pass
    
    # Colores y estilos
    primary_color = "#1976D2"  # Azul principal
    bg_color = "#F5F5F5"  # Gris muy claro/casi blanco
    
    # Header
    header_frame = tk.Frame(log_window, bg=primary_color)
    header_frame.pack(fill=tk.X)
    
    tk.Label(header_frame, 
            text="Registros del Configurador", 
            font=("Segoe UI", 14, "bold"),
            bg=primary_color,
            fg="white").pack(pady=10)
    
    # Panel principal
    main_frame = tk.Frame(log_window, bg=bg_color)
    main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)
    
    # Obtener archivos de log disponibles
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
    log_files = []
    
    if os.path.exists(log_dir):
        log_files = [f for f in os.listdir(log_dir) if f.startswith('datacom_config_') and f.endswith('.log')]
        log_files.sort(reverse=True)  # Los más recientes primero
    
    # Panel de selección de archivo
    select_frame = tk.Frame(main_frame, bg=bg_color)
    select_frame.pack(fill=tk.X, pady=10)
    
    tk.Label(select_frame, 
            text="Seleccionar archivo de registro:", 
            font=("Segoe UI", 10),
            bg=bg_color).pack(side=tk.LEFT, padx=5)
    
    # Variable para el archivo seleccionado
    selected_log = tk.StringVar()
    if log_files:
        selected_log.set(log_files[0])  # Seleccionar el más reciente por defecto
    
    # Dropdown para seleccionar archivo
    log_dropdown = ttk.Combobox(select_frame, 
                              textvariable=selected_log,
                              values=log_files,
                              state="readonly",
                              width=40)
    log_dropdown.pack(side=tk.LEFT, padx=10)
    
    # Botón para cargar el archivo seleccionado
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
    
    ttk.Button(select_frame, 
              text="Cargar", 
              command=cargar_log).pack(side=tk.LEFT, padx=5)
    
    # Área de texto para mostrar los logs
    log_frame = tk.Frame(main_frame, bg=bg_color)
    log_frame.pack(fill=tk.BOTH, expand=True, pady=10)
    
    log_text = tk.Text(log_frame, 
                      wrap=tk.WORD, 
                      font=("Consolas", 9),
                      bg="white", 
                      fg="#212121", 
                      bd=1, 
                      relief=tk.SOLID)
    log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    
    # Barra de desplazamiento
    scrollbar = ttk.Scrollbar(log_frame, command=log_text.yview)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    log_text.config(yscrollcommand=scrollbar.set)
    
    # Botones de acción
    button_frame = tk.Frame(main_frame, bg=bg_color)
    button_frame.pack(fill=tk.X, pady=15)
    
    # Función para actualizar la lista de logs
    def actualizar_lista():
        if os.path.exists(log_dir):
            new_log_files = [f for f in os.listdir(log_dir) if f.startswith('datacom_config_') and f.endswith('.log')]
            new_log_files.sort(reverse=True)
            log_dropdown['values'] = new_log_files
            if new_log_files:
                selected_log.set(new_log_files[0])
                cargar_log()
    
    ttk.Button(button_frame, 
              text="Actualizar", 
              command=actualizar_lista).pack(side=tk.LEFT, padx=5)
    
    ttk.Button(button_frame, 
              text="Cerrar", 
              command=log_window.destroy).pack(side=tk.RIGHT, padx=5)
    
    # Cargar el log inicial si hay archivos disponibles
    if log_files:
        cargar_log()

# Función principal
if __name__ == "__main__":
    try:
        # Inicializar ventana principal
        root = tk.Tk()
        app = ConfiguradorModem(root)
        
        # Agregar menú para acceder al visor de logs
        menubar = tk.Menu(root)
        root.config(menu=menubar)
        
        # Menú Herramientas con opción para ver logs
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

# Comando para compilar el script en un ejecutable (PyInstaller)
# pyinstaller --onefile --noconsole --hidden-import=webdriver_manager.chrome --hidden-import=webdriver_manager.microsoft --hidden-import=webdriver_manager.firefox --hidden-import=tkinter --icon=datacom_config.ico "DM986-AX30.py"