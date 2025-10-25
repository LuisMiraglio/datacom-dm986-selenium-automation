# DM986-416AX30 - Configurador Automático de Modem Datacom

## 📡 Descripción

El **Configurador Automático de Modem Datacom DM986-416AX30** es una herramienta avanzada diseñada para automatizar la configuración completa de este modelo de modem.  
Desarrollada en **Python** utilizando **Selenium** y con una interfaz gráfica amigable en **Tkinter**, esta aplicación interactúa directamente con la interfaz web del modem, ejecutando de forma automática y en un solo proceso todas las configuraciones necesarias para dejar el equipo listo para uso en entornos de producción.

El script realiza tareas críticas como:

- Configuración **WAN** con soporte para múltiples VLANs (500 y 600).
- Ajuste y optimización de las redes **WiFi** (2.4GHz y 5GHz).
- Configuración de seguridad inalámbrica y del panel de administración.
- Activación y configuración de **TR-069** para gestión remota.
- Mapeo de puertos y ajustes de rendimiento.
- Activación de acceso remoto seguro vía HTTPS.

- Salida útil: al finalizar, se guarda un .txt con SSID, contraseña Wi-Fi y contraseña de administrador en
Documentos/Datacom Configuradas/ (Windows).
En caso de error, se guardan capturas (.png y .html) en Documentos/Datacom Configuradas/Errores/.

Gracias a esta herramienta, se evita la configuración manual paso a paso y se reducen significativamente los tiempos de provisión del equipo.

## 📸 Capturas de Pantalla

### Interfaz principal de la aplicación
<img src="docs/images/app_interface.png" alt="Interfaz principal" width="600"/>

## ✨ Características Principales

- **Configuración WAN automática**:
  - Activación de **VLAN 500** y **VLAN 600** con IPoE.
  - Configuración de modo de canal IPoE.
  - Mapeo de puertos automático para todos los puertos.

- **Configuración WiFi completa**:
  - Configuración simultánea de bandas **2.4GHz** y **5GHz**.
  - Ancho de canal optimizado:
    - 2.4GHz: 20/40MHz (modo mixto).
    - 5GHz: 160MHz.
  - Potencia de transmisión configurada al **100%**.
  - Selección automática de canales y DFS para mejor rendimiento.

- **Configuración de Seguridad**:
  - Establecimiento de contraseñas WPA para redes WiFi.
  - Cambio de contraseña de administrador.
  - Activación de acceso remoto seguro vía HTTPS.

- **Gestión remota (TR-069)**:
  - Configuración de URL del ACS.
  - Credenciales de conexión para gestión remota.
  - Aplicación automática de cambios.

- **Funciones adicionales**:
  - Interfaz gráfica intuitiva y amigable.
  - Sistema de registros (logs) con visor integrado.
  - Soporte para múltiples navegadores (Chrome, Edge, Firefox).
  - Detección automática del navegador disponible.
  - Resumen detallado de todas las operaciones realizadas.

## 🔧 Requisitos Previos

- Windows 10/11
- Python 3.8+ (solo si corrés desde código fuente)
- Uno de los navegadores soportados instalado (Chrome recomendado)


### 📥 Instalación (código fuente)

1. Clonar el repo:
  ```
  git clone https://github.com/tuusuario/Script-DATACOM-DM986-416-AX30.git
cd Script-DATACOM-DM986-416-AX30
 ```

2. (Opcional) Crear entorno virtual e instalar dependencias:
  ```
  python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
 ```

3. 
  ```
python DM986-416AX30.py
```
## 🚀 Uso

1. Abrí la aplicación (desde el .py o desde el .exe si compilaste).
2. Elegí el navegador.
3. Completá los campos:
   - Usuario y contraseña actual del modem
   - SSID y contraseña WPA
   - Nueva contraseña de administrador
4. Haz clic en "Configurar Modem" para iniciar el proceso automático.
5. Verificá el archivo .txt generado en Documentos/Datacom Configuradas/.
   - Nota: si usás Chrome o Edge, la app está configurada para dejar la ventana del navegador abierta (modo detach) al terminar, para que puedas revisar la configuración. Cerrala manualmente cuando termines.


## 🔍 Logs y diagnósticos 🗂️

La aplicación incluye un visor de registros (logs) que puedes acceder desde el menú "Herramientas" > "Ver registros". Esta función te permite:

- Visor de logs: Herramientas → Ver registros (logs diarios en ./logs/ del proyecto).
- HTML de la página: error_YYYYMMDD_HHMMSS.html
en Documentos/Datacom Configuradas/Errores/.


## 🛠️ Compilación (PyInstaller)

Si deseas compilar tu propia versión del ejecutable:

La compilación genera dos carpetas en la raíz del proyecto:
 - build/ – artefactos intermedios
 - dist/ – acá queda el ejecutable (.exe)


Comando recomendado (Windows PowerShell/CMD)
```
    pyinstaller --onefile --noconsole --icon=datacom_config.ico --add-data "datacom_config.ico;." --hidden-import=webdriver_manager.chrome --hidden-import=webdriver_manager.microsoft --hidden-import=webdriver_manager.firefox --hidden-import=tkinter --name "Configurador Datacom DM986" "DM986-416AX30.py"
  ```

## ⚠️ Consideraciones
  - Diseñado específicamente para Datacom DM986-416AX30 en 192.168.0.1.
  - Ejecutar conectado al equipo (idealmente por cable de red).
  - Las opciones del navegador están preparadas para ignorar certificados (interfaz HTTPS del modem).


## 📞 Contacto

Luis Miraglio - miraglioluis1@gmail.com

---

⭐ Si este proyecto te resulta útil, considera darle una estrella en GitHub! ⭐
