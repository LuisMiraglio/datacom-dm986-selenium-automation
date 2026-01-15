import os
import sys
import time
import base64
import datetime
import logging
import traceback
import subprocess
from dataclasses import dataclass
from typing import Optional, Dict
from logging.handlers import RotatingFileHandler

from PySide6.QtCore import Qt, QThread, QObject, Signal, QUrl
from PySide6.QtGui import QFont, QAction, QDesktopServices, QIcon
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QHBoxLayout, QVBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QComboBox,
    QTextEdit, QProgressBar, QMessageBox,
    QGroupBox, QFrame, QListWidget, QListWidgetItem,
    QCheckBox, QDialog, QDialogButtonBox
)

APP_NAME = "DATACOM DM986"
APP_SUBTITLE = "Configurador Automático"
APP_VERSION = "v1.0"


# =========================
# (Opcional) Verificar deps
# =========================
# En .exe NO conviene auto-instalar por pip.
# Mejor: avisar si falta algo en modo script.
def ensure_dependency(module_name: str, pip_name: str):
    try:
        __import__(module_name)
        return True
    except ImportError:
        if getattr(sys, 'frozen', False):
            return False
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", pip_name])
            return True
        except Exception:
            return False


# =========================
# Logger
# =========================
def get_app_dir() -> str:
    if getattr(sys, 'frozen', False):
        return os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'ConfiguradorDatacom')
    return os.path.dirname(os.path.abspath(__file__))


def setup_logger() -> logging.Logger:
    app_dir = get_app_dir()
    log_dir = os.path.join(app_dir, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f'datacom_config_{datetime.datetime.now().strftime("%Y%m%d")}.log')

    logger = logging.getLogger('DatacomConfig')
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=5 * 1024 * 1024,
            backupCount=5,
            encoding='utf-8'
        )
        file_formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(console_formatter)
        console_handler.setLevel(logging.INFO)
        logger.addHandler(console_handler)

    return logger


logger = setup_logger()
logger.info("=== Iniciando Configurador Automático de Modem Datacom DM986 (PySide6) ===")


# =========================
# Pasos (checklist)
# =========================
STEP_ORDER = [
    "init_driver",
    "login",
    "wan_vlan_500",
    "wan_tr069_vlan_600",
    "wifi_5ghz",
    "wifi_5ghz_security",
    "wifi_24ghz",
    "wifi_24ghz_security",
    "admin_password",
    "admin_tr069",
    "advance_remote_access",
    "save_summary",
]

STEP_LABELS = {
    "init_driver": "Inicializar navegador",
    "login": "Login al modem",
    "wan_vlan_500": "WAN (VLAN 500)",
    "wan_tr069_vlan_600": "WAN TR-069 (VLAN 600)",
    "wifi_5ghz": "WiFi 5GHz",
    "wifi_5ghz_security": "Seguridad 5GHz",
    "wifi_24ghz": "WiFi 2.4GHz",
    "wifi_24ghz_security": "Seguridad 2.4GHz",
    "admin_password": "Admin: Password",
    "admin_tr069": "Admin: TR-069",
    "advance_remote_access": "Advance: Remote Access",
    "save_summary": "Guardar resumen",
}

STATUS_ICON = {
    "idle": "⏸",
    "run": "⏳",
    "ok": "✅",
    "err": "❌",
}


@dataclass
class RunConfig:
    browser_choice: str  # "1","2","3","4"
    username: str
    password: str
    ssid: str
    wpa: str
    new_admin: str
    icon_path: str = "datacom_config.ico"


# =========================
# Worker Selenium (QThread)
# =========================
class ConfigWorker(QObject):
    log = Signal(str)
    status = Signal(str)
    step_update = Signal(str, str)   # step_key, status
    finished_ok = Signal(str)        # saved_path
    finished_err = Signal(str)       # error msg
    set_busy = Signal(bool)

    def __init__(self, cfg: RunConfig):
        super().__init__()
        self.cfg = cfg

    def _log(self, msg: str):
        logger.info(msg)
        self.log.emit(msg)

    def _status(self, msg: str):
        self.status.emit(msg)

    def _step(self, key: str, st: str):
        self.step_update.emit(key, st)

    def get_browser_name(self, choice: str) -> str:
        return {"1": "Google Chrome", "2": "Microsoft Edge", "3": "Firefox", "4": "Autodetectar"}.get(choice, "Desconocido")

    # ===== Guardado resumen =====
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

    def _save_error_diagnostics(self, driver):
        try:
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            documentos = os.path.join(os.path.expanduser("~"), "Documents")
            if not os.path.isdir(documentos):
                documentos = os.path.expanduser("~")
            base_dir = os.path.join(documentos, "Datacom Configuradas")
            os.makedirs(base_dir, exist_ok=True)

            screenshot_path = os.path.join(base_dir, f"error_{ts}.png")
            html_path = os.path.join(base_dir, f"error_{ts}.html")
            driver.save_screenshot(screenshot_path)
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(driver.page_source)

            logger.info(f"Capturas de error guardadas: {screenshot_path} / {html_path}")
            self._log(f"Se guardó diagnóstico: {screenshot_path} y {html_path}")
        except Exception as cap_err:
            logger.warning(f"No se pudieron guardar capturas de error: {cap_err}")
            self._log(f"No se pudieron guardar capturas de error: {cap_err}")

    def run(self):
        self.set_busy.emit(True)

        # Reset steps
        for key in STEP_ORDER:
            self._step(key, "idle")

        driver = None

        try:
            ok_selenium = ensure_dependency("selenium", "selenium")
            ok_wdm = ensure_dependency("webdriver_manager", "webdriver-manager")
            if not ok_selenium or not ok_wdm:
                raise Exception("Faltan dependencias (selenium / webdriver-manager). Reinstalá o recompilá incluyendo esas libs.")

            # Imports dentro del worker
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

            # Datos
            browser_choice = self.cfg.browser_choice
            username = self.cfg.username
            password = self.cfg.password
            ssid_name = self.cfg.ssid
            wpa_password = self.cfg.wpa
            new_password = self.cfg.new_admin

            self._status("Iniciando configuración…")
            self._log(f"Navegador: {self.get_browser_name(browser_choice)}")
            self._log(f"SSID: {ssid_name}")

            # Setup driver
            def setup_driver():
                if browser_choice == "1":
                    self._step("init_driver", "run")
                    self._status("Inicializando Google Chrome…")
                    self._log("Inicializando Google Chrome…")
                    options = ChromeOptions()
                    options.add_argument("--ignore-certificate-errors")
                    options.add_argument("--ignore-ssl-errors")
                    options.add_argument("--disable-web-security")
                    options.add_argument("--allow-running-insecure-content")
                    options.add_experimental_option("detach", True)
                    return webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)

                elif browser_choice == "2":
                    self._step("init_driver", "run")
                    self._status("Inicializando Microsoft Edge…")
                    self._log("Inicializando Microsoft Edge…")
                    options = EdgeOptions()
                    options.add_argument("--ignore-certificate-errors")
                    options.add_argument("--ignore-ssl-errors")
                    options.add_argument("--disable-web-security")
                    options.add_argument("--allow-running-insecure-content")
                    options.add_experimental_option("detach", True)
                    return webdriver.Edge(service=EdgeService(EdgeChromiumDriverManager().install()), options=options)

                elif browser_choice == "3":
                    self._step("init_driver", "run")
                    self._status("Inicializando Firefox…")
                    self._log("Inicializando Firefox…")
                    options = FirefoxOptions()
                    options.accept_insecure_certs = True
                    return webdriver.Firefox(service=FirefoxService(GeckoDriverManager().install()), options=options)

                else:
                    self._step("init_driver", "run")
                    self._status("Autodetectando navegador…")
                    self._log("Autodetectando navegador (Chrome → Edge → Firefox)…")
                    for browser in ['chrome', 'edge', 'firefox']:
                        try:
                            if browser == 'chrome':
                                options = ChromeOptions()
                                options.add_argument("--ignore-certificate-errors")
                                options.add_argument("--ignore-ssl-errors")
                                options.add_argument("--disable-web-security")
                                options.add_argument("--allow-running-insecure-content")
                                options.add_experimental_option("detach", True)
                                return webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)

                            if browser == 'edge':
                                options = EdgeOptions()
                                options.add_argument("--ignore-certificate-errors")
                                options.add_argument("--ignore-ssl-errors")
                                options.add_argument("--disable-web-security")
                                options.add_argument("--allow-running-insecure-content")
                                options.add_experimental_option("detach", True)
                                return webdriver.Edge(service=EdgeService(EdgeChromiumDriverManager().install()), options=options)

                            if browser == 'firefox':
                                options = FirefoxOptions()
                                options.accept_insecure_certs = True
                                return webdriver.Firefox(service=FirefoxService(GeckoDriverManager().install()), options=options)

                        except Exception as e:
                            self._log(f"No se pudo inicializar {browser}: {e}")
                            continue

                    raise Exception("No se encontró ningún navegador compatible instalado.")

            try:
                driver = setup_driver()
                self._step("init_driver", "ok")
                self._status("Navegador inicializado.")
                self._log("Navegador inicializado correctamente.")
            except Exception as e:
                self._step("init_driver", "err")
                raise Exception(f"Error al inicializar navegador: {e}")

            # ===== LOGIN =====
            self._step("login", "run")
            self._status("Accediendo al modem…")
            self._log("Abriendo https://192.168.0.1/admin/login.asp")
            driver.get("https://192.168.0.1/admin/login.asp")
            time.sleep(2)

            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            if iframes:
                driver.switch_to.frame(iframes[0])

            self._log("Completando credenciales…")
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

            self._status("Validando login…")
            nav_menu = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "nav")))
            self._step("login", "ok")
            self._log("Login exitoso.")

            # ===== WAN VLAN 500 =====
            self._step("wan_vlan_500", "run")
            self._status("Configurando WAN (VLAN 500)…")
            wan_link = nav_menu.find_element(By.XPATH, ".//a[@rel='4' and text()='WAN']")
            wan_link.click()

            content_iframe = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "contentIframe")))
            driver.switch_to.frame(content_iframe)

            vlan_checkbox = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//input[@type='checkbox' and @name='vlan' and @value='ON']"))
            )
            vlan_checkbox.click()
            time.sleep(1)

            vid_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "vid")))
            vid_input.clear()
            vid_input.send_keys("500")
            time.sleep(1)

            channel_mode_dropdown = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "adslConnectionMode")))
            for option in channel_mode_dropdown.find_elements(By.TAG_NAME, "option"):
                if option.get_attribute("value") == "1":
                    option.click()
                    break
            time.sleep(1)

            chkpt_all_checkbox = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//input[@name='chkpt_all']"))
            )
            chkpt_all_checkbox.click()
            time.sleep(1)

            apply_changes_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//input[@type='submit' and @value='Apply Changes' and @name='apply']"))
            )
            apply_changes_button.click()
            time.sleep(2)

            driver.switch_to.default_content()
            self._step("wan_vlan_500", "ok")
            self._log("WAN VLAN 500 aplicada.")

            # ===== WAN TR069 VLAN 600 =====
            self._step("wan_tr069_vlan_600", "run")
            self._status("Configurando WAN TR-069 (VLAN 600)…")

            nav_menu = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "nav")))
            wan_link = nav_menu.find_element(By.XPATH, ".//a[@rel='4' and text()='WAN']")
            wan_link.click()
            time.sleep(1)

            content_iframe = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "contentIframe")))
            driver.switch_to.frame(content_iframe)

            lkname_select = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "lkname")))
            for option in lkname_select.find_elements(By.TAG_NAME, "option"):
                if option.get_attribute("value") == "new":
                    option.click()
                    break
            time.sleep(1)

            vlan_checkbox_new = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//input[@type='checkbox' and @name='vlan' and @value='ON']"))
            )
            vlan_checkbox_new.click()
            time.sleep(1)

            vid_input_new = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "vid")))
            vid_input_new.clear()
            vid_input_new.send_keys("600")
            time.sleep(1)

            channel_mode_dropdown_new = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.NAME, "adslConnectionMode"))
            )
            for option in channel_mode_dropdown_new.find_elements(By.TAG_NAME, "option"):
                if option.get_attribute("value") == "1":
                    option.click()
                    break
            time.sleep(1)

            ctype_dropdown_new = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "ctype")))
            for option in ctype_dropdown_new.find_elements(By.TAG_NAME, "option"):
                if option.get_attribute("value") == "1":
                    option.click()
                    break
            time.sleep(1)

            dhcp_radio = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//input[@type='radio' and @name='ipMode' and @value='1']"))
            )
            dhcp_radio.click()
            time.sleep(1)

            checkbox_all = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//input[@type='checkbox' and @name='chkpt_all']"))
            )
            checkbox_all.click()
            WebDriverWait(driver, 5).until(lambda d: not checkbox_all.is_selected())
            checkbox_all.click()
            time.sleep(1)

            apply_changes_button_new = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//input[@type='submit' and @name='apply' and @value='Apply Changes']"))
            )
            apply_changes_button_new.click()
            time.sleep(2)

            driver.switch_to.default_content()
            self._step("wan_tr069_vlan_600", "ok")
            self._log("WAN TR-069 (VLAN 600) aplicada.")

            # ===== WLAN 5GHz =====
            self._step("wifi_5ghz", "run")
            self._status("Configurando red WiFi 5GHz…")

            nav_menu = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "nav")))
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
                EC.element_to_be_clickable((By.XPATH, "//input[@type='submit' and @value='Apply Changes' and @name='save']"))
            )
            apply_changes_button.click()
            time.sleep(10)

            driver.switch_to.default_content()
            self._step("wifi_5ghz", "ok")
            self._log("WiFi 5GHz configurado.")

            # ===== Seguridad WiFi 5GHz =====
            self._step("wifi_5ghz_security", "run")
            self._status("Configurando seguridad WiFi 5GHz…")

            side_menu = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "side")))
            security_link = WebDriverWait(side_menu, 10).until(
                EC.element_to_be_clickable((By.XPATH, ".//a[contains(@href, '/wlwpa.asp') and contains(@href, 'wlan_idx=0')]"))
            )
            security_link.click()
            time.sleep(1)

            content_iframe = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "contentIframe")))
            driver.switch_to.frame(content_iframe)

            wpa_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "wpapsk")))
            wpa_input.clear()
            wpa_input.send_keys(wpa_password)
            time.sleep(1)

            show_password_checkbox = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//input[@type='checkbox' and @onclick='show_password(1)']"))
            )
            show_password_checkbox.click()

            apply_changes_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//input[@type='submit' and @name='save' and @value='Apply Changes']"))
            )
            apply_changes_button.click()
            time.sleep(10)

            driver.switch_to.default_content()
            self._step("wifi_5ghz_security", "ok")
            self._log("Seguridad 5GHz configurada.")

            # ===== WLAN 2.4 GHz =====
            self._step("wifi_24ghz", "run")
            self._status("Configurando red WiFi 2.4GHz…")

            side_menu = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "side")))
            wlan1_header = WebDriverWait(side_menu, 10).until(
                EC.element_to_be_clickable((By.XPATH, ".//h3/a[text()='wlan1 (2.4GHz)']"))
            )
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
                EC.element_to_be_clickable((By.XPATH, "//input[@type='submit' and @name='save' and @value='Apply Changes']"))
            )
            apply_changes_button_wlan1.click()
            time.sleep(10)

            driver.switch_to.default_content()
            self._step("wifi_24ghz", "ok")
            self._log("WiFi 2.4GHz configurado.")

            # ===== Seguridad 2.4GHz =====
            self._step("wifi_24ghz_security", "run")
            self._status("Configurando seguridad WiFi 2.4GHz…")

            side_menu = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "side")))
            security_link_wlan1 = WebDriverWait(side_menu, 10).until(
                EC.element_to_be_clickable((By.XPATH, ".//a[contains(@href, '/wlwpa.asp') and contains(@href, 'wlan_idx=1')]"))
            )
            security_link_wlan1.click()

            content_iframe = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "contentIframe")))
            driver.switch_to.frame(content_iframe)

            wpa_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "wpapsk")))
            wpa_input.clear()
            wpa_input.send_keys(wpa_password)
            time.sleep(1)

            show_password_checkbox = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//input[@type='checkbox' and @onclick='show_password(1)']"))
            )
            show_password_checkbox.click()

            apply_changes_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//input[@type='submit' and @name='save' and @value='Apply Changes']"))
            )
            apply_changes_button.click()
            time.sleep(10)

            driver.switch_to.default_content()
            self._step("wifi_24ghz_security", "ok")
            self._log("Seguridad 2.4GHz configurada.")

            # ===== Admin -> Password =====
            self._step("admin_password", "run")
            self._status("Cambiando contraseña de administrador…")

            nav_menu = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "nav")))
            admin_link = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//a[@href='javascript:void(0)' and @rel='9']"))
            )
            admin_link.click()

            side_menu = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "side")))
            password_link = WebDriverWait(side_menu, 10).until(
                EC.element_to_be_clickable((By.XPATH, ".//a[@target='contentIframe' and @href='password.asp' and text()='Password']"))
            )
            password_link.click()

            content_iframe = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "contentIframe")))
            driver.switch_to.frame(content_iframe)

            old_password_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "oldpass")))
            old_password_input.clear()
            old_password_input.send_keys(password)
            time.sleep(1)

            show_old_password_checkbox = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//input[@type='checkbox' and @onclick='show_password(3)']"))
            )
            show_old_password_checkbox.click()

            new_password_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "newpass")))
            new_password_input.clear()
            new_password_input.send_keys(new_password)
            time.sleep(1)

            show_new_password_checkbox = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//input[@type='checkbox' and @onclick='show_password(1)']"))
            )
            show_new_password_checkbox.click()

            confirmed_password_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "confpass")))
            confirmed_password_input.clear()
            confirmed_password_input.send_keys(new_password)
            time.sleep(1)

            show_confirmed_password_checkbox = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//input[@type='checkbox' and @onclick='show_password(2)']"))
            )
            show_confirmed_password_checkbox.click()

            apply_changes_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//input[@type='submit' and @name='save' and @value='Apply Changes']"))
            )
            apply_changes_button.click()
            time.sleep(5)

            driver.switch_to.default_content()
            self._step("admin_password", "ok")
            self._log("Contraseña admin cambiada.")

            # ===== Admin -> TR-069 =====
            self._step("admin_tr069", "run")
            self._status("Configurando TR-069…")

            admin_tab = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.XPATH, "//ul[@id='nav']//a[@href='javascript:void(0)' and @rel='9' and normalize-space()='Admin']"))
            )
            admin_tab.click()

            side_menu = WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.ID, "side")))
            tr069_link = WebDriverWait(side_menu, 15).until(
                EC.element_to_be_clickable((By.XPATH, ".//a[@target='contentIframe' and contains(@href,'tr069config.asp') and normalize-space()='TR-069']"))
            )
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
                EC.element_to_be_clickable((By.XPATH, "//input[@type='submit' and @name='save' and @value='Apply']"))
            )
            apply_button.click()
            time.sleep(5)

            try:
                WebDriverWait(driver, 3).until(EC.alert_is_present())
                driver.switch_to.alert.accept()
            except Exception:
                pass

            driver.switch_to.default_content()
            self._step("admin_tr069", "ok")
            self._log("TR-069 configurado.")

            # ===== Advance -> Remote Access =====
            self._step("advance_remote_access", "run")
            self._status("Habilitando Remote Access (HTTPS WAN)…")

            nav_menu = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "nav")))
            advance_tab = WebDriverWait(nav_menu, 15).until(
                EC.element_to_be_clickable((By.XPATH, ".//a[@href='javascript:void(0)' and @rel='7' and normalize-space()='Advance']"))
            )
            try:
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", advance_tab)
                advance_tab.click()
            except Exception:
                driver.execute_script("arguments[0].click();", advance_tab)

            side_menu = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "side")))
            remote_access_link = WebDriverWait(side_menu, 15).until(
                EC.element_to_be_clickable((By.XPATH, ".//a[@target='contentIframe' and @href='rmtacc.asp' and normalize-space()='Remote Access']"))
            )
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
                EC.element_to_be_clickable((By.XPATH, "//input[@type='submit' and @name='set' and @value='Apply Changes']"))
            )
            apply_changes_button.click()

            driver.switch_to.default_content()
            self._step("advance_remote_access", "ok")
            self._log("Remote Access habilitado.")

            # ===== Guardar resumen =====
            self._step("save_summary", "run")
            self._status("Guardando resumen…")
            saved = self.guardar_resumen_configuracion(ssid_name, wpa_password, new_password)
            if saved:
                self._log(f"Resumen guardado en: {saved}")
            else:
                self._log("No se pudo guardar el resumen (sin ruta).")
            self._step("save_summary", "ok")

            self._status("Configuración completada ✅")
            self.finished_ok.emit(saved)

        except Exception as e:
            msg = str(e)
            logger.error(msg)
            logger.error(traceback.format_exc())

            self._status("Error durante la configuración ❌")
            self._log("ERROR: " + msg)

            try:
                if driver:
                    self._save_error_diagnostics(driver)
            except Exception:
                pass

            self.finished_err.emit(msg)

        finally:
            try:
                if driver:
                    driver.quit()
            except Exception as e:
                logger.warning(f"No se pudo cerrar el navegador: {e}")

            self.set_busy.emit(False)


# =========================
# Dialog visor de logs
# =========================
class LogsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Visor de Logs - Configurador Datacom")
        self.setMinimumSize(900, 580)

        layout = QVBoxLayout(self)

        top = QHBoxLayout()
        self.cmb = QComboBox()
        self.btn_load = QPushButton("Cargar")
        self.btn_refresh = QPushButton("Actualizar")
        self.btn_load.setObjectName("secondaryButton")
        self.btn_refresh.setObjectName("secondaryButton")

        top.addWidget(QLabel("Archivo:"))
        top.addWidget(self.cmb, 1)
        top.addWidget(self.btn_load)
        top.addWidget(self.btn_refresh)

        self.txt = QTextEdit()
        self.txt.setReadOnly(True)
        self.txt.setStyleSheet("font-family: Consolas; font-size: 10px;")

        btns = QDialogButtonBox(QDialogButtonBox.Close)
        btns.rejected.connect(self.reject)
        btns.accepted.connect(self.accept)

        layout.addLayout(top)
        layout.addWidget(self.txt, 1)
        layout.addWidget(btns)

        self.btn_load.clicked.connect(self.load_selected)
        self.btn_refresh.clicked.connect(self.refresh_list)

        self.refresh_list()

    def log_dir(self) -> str:
        return os.path.join(get_app_dir(), "logs")

    def refresh_list(self):
        d = self.log_dir()
        files = []
        if os.path.isdir(d):
            files = [f for f in os.listdir(d) if f.startswith("datacom_config_") and f.endswith(".log")]
            files.sort(reverse=True)
        self.cmb.clear()
        self.cmb.addItems(files)
        if files:
            self.load_selected()

    def load_selected(self):
        d = self.log_dir()
        name = self.cmb.currentText()
        if not name:
            self.txt.setPlainText("(No hay logs disponibles.)")
            return
        path = os.path.join(d, name)
        try:
            with open(path, "r", encoding="utf-8") as f:
                self.txt.setPlainText(f.read())
        except Exception as e:
            self.txt.setPlainText(f"Error al leer el archivo:\n{e}")


# =========================
# UI principal PySide6
# =========================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle(f"{APP_NAME} · {APP_SUBTITLE}")
        self.setMinimumSize(1100, 700)

        # icono
        try:
            if os.path.exists("datacom_config.ico"):
                self.setWindowIcon(QIcon("datacom_config.ico"))
        except Exception:
            pass

        QApplication.instance().setFont(QFont("Segoe UI", 10))

        # Menú
        menubar = self.menuBar()
        menu_tools = menubar.addMenu("Herramientas")

        act_logs = QAction("Ver registros", self)
        act_logs.triggered.connect(self.open_logs_dialog)
        menu_tools.addAction(act_logs)

        act_open_logs_folder = QAction("Abrir carpeta de logs", self)
        act_open_logs_folder.triggered.connect(self.open_logs_folder)
        menu_tools.addAction(act_open_logs_folder)

        act_open_configs_folder = QAction("Abrir carpeta 'Datacom Configuradas'", self)
        act_open_configs_folder.triggered.connect(self.open_configs_folder)
        menu_tools.addAction(act_open_configs_folder)

        # Central
        central = QWidget()
        self.setCentralWidget(central)

        main = QVBoxLayout(central)
        main.setContentsMargins(14, 14, 14, 14)
        main.setSpacing(12)

        # ===== Header pro =====
        header = QFrame()
        header.setObjectName("headerCard")
        hb = QHBoxLayout(header)
        hb.setContentsMargins(14, 12, 14, 12)

        title_box = QVBoxLayout()
        self.lbl_title = QLabel(f"{APP_NAME}")
        self.lbl_title.setObjectName("appTitle")
        self.lbl_sub = QLabel(f"{APP_SUBTITLE} · {APP_VERSION}")
        self.lbl_sub.setObjectName("appSubtitle")

        title_box.addWidget(self.lbl_title)
        title_box.addWidget(self.lbl_sub)

        hb.addLayout(title_box, 1)

        main.addWidget(header)

        # ===== 2 columnas =====
        root = QHBoxLayout()
        root.setSpacing(14)
        main.addLayout(root, 1)

        # Left
        left = QVBoxLayout()
        left.setSpacing(12)

        # Navegador
        gb_browser = QGroupBox("Navegador")
        vb_b = QVBoxLayout(gb_browser)
        self.cmb_browser = QComboBox()
        self.cmb_browser.addItems([
            "Google Chrome (recomendado)",
            "Microsoft Edge",
            "Firefox",
            "Autodetectar",
        ])
        vb_b.addWidget(self.cmb_browser)
        left.addWidget(gb_browser)

        # Datos (labels reales, no placeholders “raros”)
        gb_data = QGroupBox("Datos de configuración")
        grid = QGridLayout(gb_data)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)

        self.ed_user = QLineEdit()
        self.ed_pass = QLineEdit(); self.ed_pass.setEchoMode(QLineEdit.Password)
        self.ed_ssid = QLineEdit()
        self.ed_wpa = QLineEdit(); self.ed_wpa.setEchoMode(QLineEdit.Password)
        self.ed_new_admin = QLineEdit(); self.ed_new_admin.setEchoMode(QLineEdit.Password)

        # Placeholders (opcionales, pero útiles)
        self.ed_user.setPlaceholderText("Ej: admin")
        self.ed_ssid.setPlaceholderText("Ej: Conectar_5G")
        self.ed_pass.setPlaceholderText("Contraseña actual")
        self.ed_wpa.setPlaceholderText("Contraseña WiFi")
        self.ed_new_admin.setPlaceholderText("Nueva contraseña admin")

        grid.addWidget(QLabel("Usuario del modem"), 0, 0)
        grid.addWidget(self.ed_user, 0, 1)

        grid.addWidget(QLabel("Contraseña actual"), 1, 0)
        grid.addWidget(self.ed_pass, 1, 1)

        grid.addWidget(QLabel("SSID (WiFi)"), 2, 0)
        grid.addWidget(self.ed_ssid, 2, 1)

        grid.addWidget(QLabel("Contraseña WPA"), 3, 0)
        grid.addWidget(self.ed_wpa, 3, 1)

        grid.addWidget(QLabel("Nueva contraseña admin"), 4, 0)
        grid.addWidget(self.ed_new_admin, 4, 1)

        self.chk_show = QCheckBox("Mostrar contraseñas")
        self.chk_show.stateChanged.connect(self.on_toggle_show_passwords)
        grid.addWidget(self.chk_show, 5, 0, 1, 2)

        left.addWidget(gb_data)

        # Botones (jerarquía pro)
        self.btn_run = QPushButton("Iniciar configuración")
        self.btn_run.setMinimumHeight(44)
        self.btn_run.setObjectName("primaryButton")
        self.btn_run.clicked.connect(self.on_run_clicked)

        self.btn_open_configs = QPushButton("Abrir carpeta 'Datacom Configuradas'")
        self.btn_open_configs.setObjectName("secondaryButton")
        self.btn_open_configs.clicked.connect(self.open_configs_folder)

        left.addWidget(self.btn_run)
        left.addWidget(self.btn_open_configs)
        left.addStretch(1)

        # Right
        right = QVBoxLayout()
        right.setSpacing(12)

        gb_steps = QGroupBox("Pasos")
        vb_steps = QVBoxLayout(gb_steps)
        self.list_steps = QListWidget()
        self.list_steps.setObjectName("stepsList")
        vb_steps.addWidget(self.list_steps)
        right.addWidget(gb_steps, 2)

        gb_console = QGroupBox("Consola")
        vb_console = QVBoxLayout(gb_console)
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setObjectName("consoleBox")
        vb_console.addWidget(self.console)
        right.addWidget(gb_console, 3)

        root.addLayout(left, 1)
        root.addLayout(right, 2)

        # ===== Footer / Status =====
        footer = QFrame()
        footer.setObjectName("footerCard")
        hb_footer = QHBoxLayout(footer)
        hb_footer.setContentsMargins(12, 10, 12, 10)

        self.lbl_status = QLabel("Listo para iniciar.")
        self.lbl_status.setObjectName("statusText")

        self.pb = QProgressBar()
        self.pb.setRange(0, 0)  # indeterminado
        self.pb.setVisible(False)
        self.pb.setFixedWidth(240)

        hb_footer.addWidget(self.lbl_status, 1)
        hb_footer.addWidget(self.pb, 0)

        main.addWidget(footer)

        # Steps init
        self._step_items: Dict[str, QListWidgetItem] = {}
        self._current_running_step: Optional[str] = None

        for key in STEP_ORDER:
            item = QListWidgetItem(self._format_step_text(key, "idle"))
            item.setData(Qt.UserRole, key)
            self.list_steps.addItem(item)
            self._step_items[key] = item

        # Thread refs
        self._thread: Optional[QThread] = None
        self._worker: Optional[ConfigWorker] = None

        # ===== Style (clean + pro) =====
        self.setStyleSheet("""
            QMainWindow { background: #F7F9FC; }

            QFrame#headerCard, QFrame#footerCard {
                background: white;
                border: 1px solid #E5E7EB;
                border-radius: 14px;
            }

            QLabel#appTitle { font-size: 18px; font-weight: 800; }
            QLabel#appSubtitle { color: #6B7280; font-size: 11px; }

            QGroupBox {
                background: white;
                border: 1px solid #E5E7EB;
                border-radius: 14px;
                margin-top: 10px;
                font-weight: 700;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; }

            QLineEdit, QComboBox {
                background: white;
                border: 1px solid #D1D5DB;
                border-radius: 12px;
                padding: 9px;
            }

            QPushButton#primaryButton {
                background: #1976D2;
                color: white;
                border: none;
                border-radius: 14px;
                padding: 12px;
                font-weight: 800;
            }
            QPushButton#primaryButton:disabled { background: #9CA3AF; }

            QPushButton#secondaryButton {
                background: transparent;
                color: #111827;
                border: 1px solid #D1D5DB;
                border-radius: 14px;
                padding: 12px;
                font-weight: 700;
            }
            QPushButton#secondaryButton:disabled {
                color: #9CA3AF;
                border-color: #E5E7EB;
            }

            QListWidget#stepsList {
                background: white;
                border: 1px solid #E5E7EB;
                border-radius: 14px;
                padding: 6px;
            }
            QListWidget#stepsList::item {
                padding: 8px;
                border-radius: 10px;
            }
            QListWidget#stepsList::item:selected {
                background: #EEF2FF;
            }

            QTextEdit#consoleBox {
                background: #0B1220;
                color: #E5E7EB;
                border: 1px solid #111827;
                border-radius: 14px;
                padding: 10px;
                font-family: Consolas;
                font-size: 10px;
            }

            QLabel#statusText { font-weight: 700; }
        """)

    # ===== helpers UI =====
    def _format_step_text(self, key: str, st: str) -> str:
        return f"{STATUS_ICON.get(st, '⏳')}  {STEP_LABELS.get(key, key)}"

    def _clear_step_highlights(self):
        for k, item in self._step_items.items():
            # Reset background
            item.setBackground(Qt.transparent)

    def _highlight_running_step(self, key: Optional[str]):
        self._clear_step_highlights()
        if key and key in self._step_items:
            item = self._step_items[key]
            # Fondo suave para el paso actual
            item.setBackground(QtGuiColor("#EEF2FF"))  # se setea con helper abajo

    def on_toggle_show_passwords(self):
        show = self.chk_show.isChecked()
        mode = QLineEdit.Normal if show else QLineEdit.Password
        self.ed_pass.setEchoMode(mode)
        self.ed_wpa.setEchoMode(mode)
        self.ed_new_admin.setEchoMode(mode)

    def validate_inputs(self) -> Optional[str]:
        if not self.ed_user.text().strip():
            return "Falta el usuario del modem."
        if not self.ed_pass.text().strip():
            return "Falta la contraseña actual."
        if not self.ed_ssid.text().strip():
            return "Falta el SSID."
        if not self.ed_wpa.text().strip():
            return "Falta la contraseña WPA."
        if not self.ed_new_admin.text().strip():
            return "Falta la nueva contraseña admin."
        return None

    def browser_choice_value(self) -> str:
        idx = self.cmb_browser.currentIndex()
        return {0: "1", 1: "2", 2: "3", 3: "4"}.get(idx, "1")

    def on_run_clicked(self):
        err = self.validate_inputs()
        if err:
            QMessageBox.warning(self, "Campos incompletos", err)
            return

        cfg = RunConfig(
            browser_choice=self.browser_choice_value(),
            username=self.ed_user.text().strip(),
            password=self.ed_pass.text(),
            ssid=self.ed_ssid.text().strip(),
            wpa=self.ed_wpa.text(),
            new_admin=self.ed_new_admin.text(),
        )

        self.console.clear()
        self.append_log(">> Iniciando proceso…")
        logger.info("Iniciando proceso desde UI")

        self._current_running_step = None
        for key in STEP_ORDER:
            self.update_step(key, "idle")

        self._thread = QThread()
        self._worker = ConfigWorker(cfg)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.log.connect(self.append_log)
        self._worker.status.connect(self.set_status)
        self._worker.step_update.connect(self.update_step)
        self._worker.set_busy.connect(self.set_busy)
        self._worker.finished_ok.connect(self.on_finished_ok)
        self._worker.finished_err.connect(self.on_finished_err)

        self._worker.finished_ok.connect(self._thread.quit)
        self._worker.finished_err.connect(self._thread.quit)
        self._thread.finished.connect(self._thread.deleteLater)

        self._thread.start()

    def set_busy(self, busy: bool):
        self.pb.setVisible(busy)
        self.btn_run.setEnabled(not busy)
        self.cmb_browser.setEnabled(not busy)
        for w in [self.ed_user, self.ed_pass, self.ed_ssid, self.ed_wpa, self.ed_new_admin, self.chk_show]:
            w.setEnabled(not busy)
        self.btn_open_configs.setEnabled(not busy)

        if busy:
            self.btn_run.setText("Configurando…")
        else:
            self.btn_run.setText("Iniciar configuración")

    def append_log(self, msg: str):
        # Timestamp (pro)
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self.console.append(f"[{ts}] {msg}")
        self.console.verticalScrollBar().setValue(self.console.verticalScrollBar().maximum())

    def set_status(self, msg: str):
        self.lbl_status.setText(msg)

    def update_step(self, key: str, st: str):
        item = self._step_items.get(key)
        if not item:
            return

        item.setText(self._format_step_text(key, st))

        # Resaltar paso en ejecución
        if st == "run":
            self._current_running_step = key
            self._apply_running_highlight(key)
            # también centramos el paso para que se vea siempre
            self.list_steps.scrollToItem(item)
        else:
            # si dejó de estar en run, limpiamos el highlight si era el actual
            if self._current_running_step == key and st in ("ok", "err", "idle"):
                self._current_running_step = None
                self._clear_running_highlight()

            # si hay error, marcamos ese item con fondo suave rojo
            if st == "err":
                item.setBackground(QtGuiColor("#FEE2E2"))

            # si ok, fondo suave verde
            if st == "ok":
                item.setBackground(QtGuiColor("#DCFCE7"))

            # si idle y no tiene fondo (reset)
            if st == "idle":
                item.setBackground(Qt.transparent)

    def _clear_running_highlight(self):
        # no borramos verdes/rojos, solo quitamos el “run”
        for key, item in self._step_items.items():
            # Si era run, lo dejamos transparente (si no está ok/err)
            # Como ok/err ya setean fondo, esto no los pisa.
            # Para run usamos un color específico y lo removemos.
            pass
        # no hacemos nada global; la lógica de ok/err ya “pinta” cada item.

    def _apply_running_highlight(self, key: str):
        # fondo suave azul para el paso actual en ejecución
        if key in self._step_items:
            self._step_items[key].setBackground(QtGuiColor("#E0F2FE"))

    def on_finished_ok(self, saved_path: str):
        self.set_status("Proceso completado ✅")
        self.append_log(">> Proceso completado ✅")
        if saved_path:
            self.append_log(f"Resumen guardado en: {saved_path}")
            QMessageBox.information(self, "Finalizado", f"Configuración completada.\n\nResumen:\n{saved_path}")
        else:
            QMessageBox.information(self, "Finalizado", "Configuración completada.")
        logger.info("Proceso completado OK")

    def on_finished_err(self, msg: str):
        self.set_status("Error en el proceso ❌")
        self.append_log(">> ERROR: " + msg)
        QMessageBox.critical(self, "Error", f"Ocurrió un error durante la configuración:\n\n{msg}\n\nRevisá logs para más detalles.")
        logger.error(f"Proceso finalizó con error: {msg}")

    def open_logs_dialog(self):
        dlg = LogsDialog(self)
        dlg.exec()

    def open_logs_folder(self):
        d = os.path.join(get_app_dir(), "logs")
        os.makedirs(d, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(d))

    def open_configs_folder(self):
        documentos = os.path.join(os.path.expanduser("~"), "Documents")
        if not os.path.isdir(documentos):
            documentos = os.path.expanduser("~")
        base_dir = os.path.join(documentos, "Datacom Configuradas")
        os.makedirs(base_dir, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(base_dir))


# Helper: QtGui QColor sin importar QtGui globalmente
def QtGuiColor(hex_color: str):
    from PySide6.QtGui import QColor
    return QColor(hex_color)


def main():
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.critical(f"Error no controlado en la aplicación: {str(e)}")
        QMessageBox.critical(None, "Error crítico",
                             f"Ha ocurrido un error inesperado:\n{str(e)}\n\nConsultá logs para más detalles.")
