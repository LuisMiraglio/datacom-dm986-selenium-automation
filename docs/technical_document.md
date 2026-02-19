# Documento técnico — Revisión senior del repositorio `Script-DATACOM-DM986-416-AX30`

## A) Resumen ejecutivo

Este proyecto automatiza la **configuración integral de módems Datacom DM986** usando Selenium (navegación web del CPE) y Tkinter (interfaz operativa para técnicos). El flujo cubre tareas típicas de provisión ISP: login al equipo, creación/configuración de enlaces WAN (VLAN 500 Internet + VLAN 600 TR-069), configuración de WiFi 5 GHz y 2.4 GHz, seguridad WPA, cambio de contraseña admin, parametrización TR-069 y habilitación de acceso remoto HTTPS. El objetivo es reducir errores manuales y estandarizar puestas en servicio.

La app toma entradas desde UI (`main.py`): modelo (`DM986-416 AX30`, `DM986-414`, `DM986-414 Q`), navegador (`chrome/edge/firefox/auto`), credenciales actuales del módem, SSID, clave WPA y nueva contraseña admin. Además, opcionalmente permite “extras WLAN” (channel width/channel number por banda), que luego se mapean a los `value` reales de `<select>` en el HTML del módem.

Como salidas, el proceso produce: (1) cambios de configuración aplicados en la UI web del módem, (2) feedback de estado en tiempo real en la GUI, (3) messagebox de error ante excepciones, y (4) stack trace en consola cuando falla la lógica. No genera reportes estructurados (JSON/CSV), ni logs persistentes en archivo.

Dependencias externas críticas: Selenium 4 + `webdriver-manager` para resolver drivers, navegador instalado en la PC, conectividad L2/L3 con `192.168.0.1`, y que el firmware del módem mantenga la estructura DOM esperada. Si cambian rutas/IDs/XPath del front del CPE, la automatización se rompe.

---

## B) Mapa del repositorio (archivo por archivo)

### 1. `main.py`
- **Propósito:** UI principal Tkinter + orquestación de ejecución en hilo secundario.
- **Clases/funciones principales:**
  - `ScrollableFrame`: contenedor con scroll vertical y wheel.
  - `MainApp`: construye UI, valida campos, adapta opciones WLAN por modelo, y dispara lógica específica.
  - `on_run()` / `_run_worker()`: punto de ejecución del proceso.
- **Dependencias (entrantes/salientes):**
  - Importa y llama `ConfiguradorModem414`, `ConfiguradorModem416`, `ConfiguradorModem414Q`.
  - Es consumido solo como entry point (`if __name__ == '__main__'`).
- **Configuraciones relevantes:**
  - Modelo default: `DM986-416 AX30`.
  - Navegador default: Chrome.
  - Mapeos de combos extras WLAN a `value` HTML por modelo.
- **Observación:** contiene lógica de UI + algo de lógica de negocio (mapeos extras), lo que acopla interfaz y dominio.

### 2. `logic_414.py`
- **Propósito:** automatización Selenium para firmware/modelo DM986-414.
- **Clases/funciones principales:**
  - `ConfiguradorModem414` con `run()`, `configurar_modem()`, helpers de driver/waits/click/select.
- **Dependencias:**
  - Llamado desde `MainApp._run_worker()`.
  - Llama Selenium API, webdriver_manager y métodos del adapter UI (`actualizar_estado`, `get_credentials`, etc.).
- **Configuraciones relevantes:**
  - URL login `http://192.168.0.1`.
  - TR-069 hardcodeado (`http://172.22.16.109:7995/`, user/pass admin).
  - Robustez puntual en DHCP VLAN600 con 3 reintentos.

### 3. `logic_416.py`
- **Propósito:** automatización Selenium para DM986-416 AX30.
- **Clases/funciones principales:**
  - `ConfiguradorModem416` con patrón similar a 414.
- **Dependencias:**
  - Llamado desde `MainApp._run_worker()`.
  - Usa Selenium + webdriver_manager + adapter UI.
- **Configuraciones relevantes:**
  - URL login `https://192.168.0.1/admin/login.asp`.
  - Flujo login con `encodePassword` (base64 + JS).
  - TR-069 también hardcodeado.
- **Posible código muerto:**
  - helper `_select_value_by_id()` no se usa en el archivo.
  - variable local `wait = WebDriverWait(d, 20)` en `configurar_modem()` no se usa luego.

### 4. `logic_414Q.py`
- **Propósito:** automatización para DM986-414 Q (interfaz tipo AX30).
- **Clases/funciones principales:**
  - `ConfiguradorModem414Q` con flujo casi gemelo de 416 + tramo extra OMCI.
- **Dependencias:**
  - Llamado desde `MainApp._run_worker()`.
  - Selenium + webdriver_manager + adapter UI.
- **Configuraciones relevantes:**
  - No cierra navegador en `run()` (modo debug) y nuevamente en `finally` del tramo OMCI.
  - Agrega paso `Admin -> OMCI Information`, setea `omci_vendor_id=ZNTS`, maneja alertas y polling de “equipo volvió”.
- **Posible código muerto/olor:**
  - mensaje de estado dice `(416)` en login aunque archivo es 414Q.
  - helper `_select_value_by_id()` tampoco se utiliza.

### 5. `requirements.txt`
- **Propósito:** dependencias Python del proyecto.
- **Contenido relevante:** Selenium, webdriver-manager, requests stack, etc.
- **Observación:** archivo en codificación UTF-16/Unicode con caracteres nulos (se ve como texto “intercalado”); puede generar problemas con tooling.
- **Posible código no usado:** incluye `PySide6`/`shiboken6`, pero la UI real es Tkinter.

### 6. `README.md`
- **Propósito:** documentación funcional, arquitectura de alto nivel, ejecución y build con PyInstaller.
- **Dependencias:** referencia `main.py` y lógicas por modelo.

### 7. `assets/icons/icono.ico`
- **Propósito:** ícono de la aplicación Tkinter / build.
- **Uso:** cargado por `self.root.iconbitmap(...)` en `main.py`.

### 8. `docs/images/app_interface.png`
- **Propósito:** imagen de interfaz para README.
- **Uso:** documental, no runtime.

---

## C) Diagrama de flujo del programa (real, basado en código)

### Punto de entrada
- Entry point exacto: bloque `if __name__ == '__main__': root = tk.Tk(); app = MainApp(root); root.mainloop()` en `main.py`.

### Orden de ejecución (numerado)
1. Se crea la ventana y todos los controles UI (`MainApp.__init__`).
2. Operador completa campos y hace click en **Configurar Modem**.
3. `on_run()` valida requeridos (`_validate_required`).
4. Si faltan datos: `safe_messagebox` y aborta.
5. Si OK: deshabilita botón, inicia progressbar y levanta hilo daemon `threading.Thread(..._run_worker...)`.
6. `_run_worker()` elige clase de lógica según `modelo`.
7. Llama `logic.run()`.
8. `run()` de cada lógica:
   - toma browser + creds + extras,
   - levanta driver (o autodetecta),
   - llama `configurar_modem(creds, extras)`.
9. `configurar_modem()` ejecuta secuencia Selenium (login → WAN500 → WAN600 → WLAN5 → seguridad5 → WLAN2.4 → seguridad2.4 → admin password → TR-069 → remote access; y en 414Q además OMCI).
10. Al terminar: status éxito; ante excepción: status error + messagebox + traceback.
11. `main.py` siempre frena barra de progreso y rehabilita botón.

### Call Flow (alto nivel)
`main.py::__main__` → `MainApp.on_run()` → `MainApp._run_worker()` → `ConfiguradorModemXXX.run()` → `ConfiguradorModemXXX.configurar_modem()` → pasos Selenium por módulo (login/WAN/WLAN/Admin/Advance/OMCI).

### Decisiones (if/else) relevantes
- Selección de clase lógica por modelo (`416`, `414`, `414Q`).
- Selección de navegador (`chrome/edge/firefox/auto`).
- Extras WLAN habilitados o no (`enabled`).
- Checkboxes: click solo si `not is_selected()`.
- VLAN600: validación de opción `lkname='new'` y errores explícitos si falta.
- 414Q: bucle de espera hasta 120s por retorno de login post-reinicio.

### Iteraciones importantes
- Iteración de opciones `<option>` para seleccionar valores (`ctype`, `adslConnectionMode`, `lkname`).
- Reintentos de click DHCP en 414 (`for _ in range(3)`).
- En 414Q, aceptación de hasta 2 alertas OMCI.
- Polling de disponibilidad login (cada 5s, máx 120s) en 414Q.

### Resultado final del proceso
- Resultado real: módem configurado en su propia UI, con status “Listo” y/o “Configuración completada”.
- No hay persistencia local de resultados, auditoría ni artefacto final.

---

## D) Selenium en detalle extremo (acción por acción)

> Para no inventar, detallo acciones reales visibles en código. Cuando la acción cambia por modelo, lo explicito.

### D.1 Login
1. **Objetivo:** abrir login del CPE.
   - **Selector/acción:** `driver.get("http://192.168.0.1")` (414) o `driver.get("https://192.168.0.1/admin/login.asp")` (416/414Q).
   - **Wait:** en 414 se espera campos por `presence_of_element_located`; en 416/414Q se hace `sleep(2)` + waits.
   - **Verificación:** presencia de `#nav` tras submit.
   - **Riesgo:** dependencia de URL fija/protocolo.
   - **Alternativa:** URL configurable por entorno.

2. **Objetivo:** completar usuario/contraseña.
   - **Selector exacto:** `By.NAME, "username"`; `By.NAME, "password"`.
   - **Wait:** `WebDriverWait(...).until(EC.presence_of_element_located(...))`.
   - **Acción:** `clear()` + `send_keys()`.
   - **Verificación:** implícita por login exitoso (aparece `nav`).
   - **Riesgo:** si cambia name rompe todo.
   - **Alternativa:** fallback selector por CSS/ID + verificación de mensaje de error.

3. **Objetivo:** enviar login.
   - **414:** `pass_field.send_keys(Keys.RETURN)`.
   - **416/414Q:** `By.XPATH, "//input[@type='submit' and @value='Login']"` + `_click_safe`.
   - **Wait:** no wait explícito para botón en 416/414Q (se usa `find_element` directo).
   - **Verificación:** `presence_of_element_located((By.ID, "nav"))`.
   - **Riesgo:** botón no listo al momento de click.
   - **Alternativa:** `element_to_be_clickable` antes de click.

4. **Específico 416/414Q – encodePassword**
   - **Objetivo:** alinear con mecanismo front.
   - **Acción:** JS que setea `encodePassword` y deshabilita input password.
   - **Riesgo:** fuerte acoplamiento a JS interno del firmware.
   - **Alternativa:** encapsular en helper con detección condicional de campo.

### D.2 WAN VLAN 500
1. **Objetivo:** entrar a sección WAN.
   - **Selector:** `//a[@rel='4' and normalize-space()='WAN']`.
   - **Wait:** `element_to_be_clickable` o presencia de `nav` + find interno.
   - **Acción:** click.
   - **Verificación:** cambio de contenido en `contentIframe`.

2. **Objetivo:** habilitar VLAN si no está.
   - **Selector:** `//input[@type='checkbox' and @name='vlan']`.
   - **Wait:** `element_to_be_clickable`.
   - **Acción:** click condicional por `is_selected()`.

3. **Objetivo:** setear VID 500.
   - **Selector:** `By.NAME, "vid"`.
   - **Wait:** `presence_of_element_located`.
   - **Acción:** `clear()` + `send_keys("500")`.

4. **Objetivo:** setear modo conexión ADSL=1.
   - **Selector:** `By.NAME, "adslConnectionMode"`.
   - **Wait:** `presence`.
   - **Acción:** `Select(...).select_by_value("1")` (414) o loop de options (416/414Q).

5. **Objetivo:** tipo de conexión Internet (`ctype=2`).
   - **Selector:** `By.NAME, "ctype"`.
   - **Acción:** select value `2`.
   - **Verificación:** en 416/414Q valida explícitamente que existe opción; si no, excepción.

6. **Objetivo:** DHCP (`ipMode=1`).
   - **Selector:** `//input[@type='radio' and @name='ipMode' and @value='1']`.
   - **Wait:** clickable.
   - **Acción:** click.

7. **Objetivo:** seleccionar puertos y aplicar.
   - **Selector:** `By.NAME, "chkpt_all"`; submit `//input[@type='submit' and @name='apply' and @value='Apply Changes']`.
   - **Acción:** click(s) + `sleep`.
   - **Riesgo:** sincronización por `sleep` fijo.
   - **Alternativa:** esperar toast/estado estable o recarga de form.

### D.3 WAN VLAN 600 (TR-069)
1. **Objetivo:** crear New Link.
   - **Selector:** `By.NAME, "lkname"` + buscar option `value='new'`.
   - **Riesgo:** si firmware renombra value.

2. **Objetivo:** VLAN/VID/adsl/ctype/dhcp.
   - **Selectores:** mismos patrones que VLAN500, con VID `600` y `ctype=1`.
   - **Particularidad 414:** reintenta DHCP hasta 3 veces.

3. **Objetivo:** aplicar cambios.
   - **Selector:** `chkpt_all` + botón apply.
   - **Particularidad 416/414Q:** doble click a `chkpt_all` para “estabilizar”.

### D.4 WLAN 5GHz
1. **Objetivo:** abrir WLAN.
   - **Selector:** `//a[@rel='3' and normalize-space()='WLAN']` (416/414Q) o `//*[@id='nav']/li[3]/a` (414).

2. **Objetivo:** configurar SSID.
   - **Selector:** `By.NAME, "ssid"`.
   - **Acción:** clear + send_keys(ssid).

3. **Objetivo:** channel width / channel number.
   - **414:** usa extras UI (`chanwid_5`, `chan_5`).
   - **416/414Q:** está hardcodeado a width `2` y canal `36` (no consume `extra["chanwid_5"]` / `extra["chan_5"]`).
   - **Wait:** `presence`, luego verificación por lambda de opción seleccionada.

4. **Objetivo:** TX power.
   - **Selector:** `name='txpower'`, value `0`.
   - **Acción:** select value.
   - **Riesgo:** atrapado por `try/except` silencioso si no existe.

5. **Objetivo:** aplicar WLAN.
   - **Selector:** `//input[@type='submit' and @name='save' and @value='Apply Changes']`.

### D.5 Seguridad WiFi (5 y 2.4)
1. **Objetivo:** abrir pantalla de seguridad por banda.
   - **5GHz selector:** `contains(@href,'wlwpa.asp') and contains(@href,'wlan_idx=0')`.
   - **2.4GHz selector:** similar con `wlan_idx=1`.

2. **Objetivo:** elegir método de seguridad.
   - **414:** `security_method` value `6`.
   - **416:** `security_method` value `20` (WPA2/WPA3).
   - **414Q:** value `6`.
   - **Acción adicional:** `dispatchEvent(change)` por JS para disparar lógica del front.

3. **Objetivo:** setear PSK.
   - **Selector:** `By.ID, "wpapsk"`.
   - **Acción:** clear + send_keys(wpa_password).

4. **Objetivo:** aplicar.
   - **Selector:** submit save Apply Changes.

### D.6 Admin Password
1. **Objetivo:** abrir Admin > password.
   - **Selectores:** tab admin `@rel='9'`, luego link `href='password.asp'`.

2. **Objetivo:** cargar old/new/conf pass.
   - **Selectores:** `oldpass`, `newpass`, `confpass` por `By.NAME`.

3. **Objetivo:** aplicar cambio.
   - **Selector:** botón save Apply Changes.

### D.7 TR-069
1. **Objetivo:** abrir Admin > TR-069.
   - **Selector:** link que contiene `tr069config.asp` en side.

2. **Objetivo:** cargar URL y credenciales.
   - **Selectors:** `url`, `username`, `password`, `conreqname`, `conreqpw`.
   - **Acción:** clear + send_keys (todos hardcodeados a `admin`, salvo URL).

3. **Objetivo:** aplicar y aceptar alert si aparece.
   - **Selector:** botón save (`Apply` o `Apply Changes`).
   - **Wait post:** `alert_is_present()` opcional.

### D.8 Advance > Remote Access
1. **Objetivo:** abrir Advance > Remote Access.
   - **Selectores:** tab `@rel='7'`; link `href='rmtacc.asp'`.

2. **Objetivo:** habilitar HTTPS remoto.
   - **Selector:** `By.NAME, "w_https"`.
   - **Acción:** click solo si no está seleccionado.

3. **Objetivo:** aplicar.
   - **Selector:** botón `name='set'` + `value='Apply Changes'`.

### D.9 Específico 414Q: OMCI
1. **Objetivo:** abrir `Admin -> OMCI Information`.
   - **Selector:** `href='omci_info.asp'`.
2. **Objetivo:** setear `omci_vendor_id` a `ZNTS`.
   - **Selector:** `By.NAME, "omci_vendor_id"`.
3. **Objetivo:** aplicar y aceptar hasta 2 alertas.
   - **Selector:** submit `name='apply'`.
4. **Objetivo:** esperar reinicio (máx 120s).
   - **Estrategia:** polling de login cada 5s con `driver.get(...)` + wait de username.

---

## E) Manejo de errores y robustez

### Excepciones manejadas hoy
- `run()` en las 3 lógicas encapsula todo en `try/except Exception` + `traceback.print_exc()`.
- Muchos bloques `try/except Exception: pass` para clicks JS, alertas, dispatch change, txpower opcional, scroll.
- Errores de negocio explícitos (`raise Exception`) cuando no encuentra opciones críticas (`ctype=2`, `lkname='new'`, DHCP en 414).

### Qué pasa si...
- **Falla login:** generalmente cae en timeout al buscar elementos siguientes (`nav`) y termina en mensaje genérico.
- **Cambia la página/DOM:** falla selector XPath/name y aborta flujo completo.
- **Se cae red/conectividad al módem:** `driver.get` o waits fallan; no hay reintento global ni circuito de recuperación (excepto polling final 414Q).

### Fragilidades detectadas
- Mucho `time.sleep` fijo en vez de esperas basadas en condición.
- XPaths absolutos o muy acoplados (`/html/body/...`, `//*[@id='nav']/li[3]/a`).
- Mezcla de responsabilidades (UI + mapeo + orquestación).
- Hardcode de datos sensibles TR-069.
- Inconsistencia: 416/414Q ignoran extras 5GHz de la UI (usan 80/36 fijo).

### Cómo fortalecerlo
- Envolver cada etapa en funciones atómicas con retries y timeouts consistentes.
- Reemplazar sleeps por waits de estado (ej. valor seleccionado, presencia de mensaje “applied”, stale frame).
- Estandarizar selectores (preferir `id/name/data-*` sobre XPaths absolutos).
- Logging estructurado (INFO/WARN/ERROR + etapa + selector + intento).
- Manejo específico de excepciones Selenium (`TimeoutException`, `NoSuchElementException`, `ElementClickInterceptedException`, etc.).

---

## F) Dependencias y configuración

### requirements / paquetes
- Core del proyecto: `selenium`, `webdriver-manager`.
- Dependencias de transporte derivadas de Selenium (trio, wsproto, urllib3, etc.).
- Paquetes no evidenciados en uso runtime actual: `PySide6`, `shiboken6`.

### Driver (ChromeDriver/Gecko/Edge)
- Se resuelve dinámicamente con `webdriver_manager` (`ChromeDriverManager`, `EdgeChromiumDriverManager`, `GeckoDriverManager`).
- Ventaja: evita instalar drivers manualmente.
- Riesgo: depende de internet/versionado en runtime.

### Variables de entorno / config / constantes
- No hay archivo de config ni `.env` consumido por código.
- URLs y credenciales de TR-069 están hardcodeadas en lógica.
- IP del módem también hardcodeada (`192.168.0.1`).

### Datos sensibles
- `admin/admin` de TR-069 embebido en código.
- Recomendación producción:
  - mover secretos a `.env` o vault,
  - separar config por entorno (`dev/test/prod`),
  - no versionar credenciales.

---

## G) Preguntas de entrevista basadas en ESTE repo (con respuestas modelo)

### 1) Funcionalidad y flujo
1. **¿Qué automatiza exactamente este proyecto?**
   - Junior: “Configura un módem Datacom con Selenium”.
   - Senior: “Orquesta end-to-end provisión de DM986 (414/416/414Q): login, WAN VLAN500/600 con DHCP, WLAN 5G+2.4G, seguridad, admin password, TR-069, remote access HTTPS y en 414Q también OMCI + espera de retorno post-reinicio.”

2. **¿Dónde arranca el flujo y cómo evita congelar la UI?**
   - Junior: “Arranca en main y usa un hilo”.
   - Senior: “Entry point en `main.py`; al presionar botón, `on_run()` dispara `_run_worker()` en `threading.Thread(daemon=True)`, deshabilita botón y usa `root.after` para actualizaciones thread-safe de estado/messagebox.”

3. **¿Cómo se selecciona el modelo y qué cambia?**
   - Junior: “Hay un combobox con 3 modelos”.
   - Senior: “El modelo define qué clase lógica se instancia y además cambia mapeos de extras WLAN en UI; 414 usa selectores/flujo algo distinto a 416/414Q.”

### 2) Selenium y DOM
4. **¿Qué estrategia de waits usa el repo?**
   - Junior: “WebDriverWait y algunos sleep”.
   - Senior: “Combina explicit waits (`presence`, `clickable`, `frame_to_be_available...`) con muchos `time.sleep`; eso funciona pero penaliza robustez y velocidad.”

5. **¿Qué harías con `_click_safe`?**
   - Junior: “Dejaría click normal y JS si falla”.
   - Senior: “Mantendría fallback JS pero logueando excepción raíz y limitando uso; click JS puede saltarse validaciones del front.”

6. **¿Qué selectores son más frágiles?**
   - Junior: “Los XPaths largos”.
   - Senior: “XPaths absolutos (`/html/body/...`) y por texto visible; prefiero `id/name` o XPaths anclados a atributos estables.”

7. **¿Cómo maneja iframes y por qué importa?**
   - Junior: “Hace switch al contentIframe”.
   - Senior: “Cada sección del CPE renderiza en iframe; por eso resetea `default_content()` y vuelve a `contentIframe`. Si olvidás esto, los selectores fallan aunque el elemento exista.”

8. **¿Ves inconsistencias en extras WLAN?**
   - Junior: “No estoy seguro”.
   - Senior: “Sí: 416/414Q en 5GHz hardcodean `chanwid=2` y `chan=36`, ignorando extras seleccionados por usuario; en 2.4 sí usan `extra[...]`.”

### 3) Arquitectura y calidad
9. **¿Cómo evaluarías la modularidad actual?**
   - Junior: “Está separado por modelo, eso está bien”.
   - Senior: “Correcta separación gruesa por modelo, pero hay duplicación alta entre 416/414Q y falta capa común (base class/page objects/steps).”

10. **¿Hay logging suficiente para soporte?**
   - Junior: “Hay mensajes de estado”.
   - Senior: “No alcanza para producción: falta log persistente con timestamps, selector usado, etapa, intento, excepción tipada y screenshot de falla.”

11. **¿Qué código muerto sospechás?**
   - Junior: “Capaz algunos imports”.
   - Senior: “`_select_value_by_id` no usado en 416/414Q, `wait` sin uso en 416, dependencias PySide6 no usadas en UI Tkinter.”

### 4) Escalabilidad/producción
12. **¿Qué cambiarías para correr 24/7?**
   - Junior: “Lo pondría en un servidor”.
   - Senior: “Config externa, retries transaccionales por etapa, observabilidad, headless configurable, screenshots on failure, timeouts centralizados y scheduler con cola de trabajos.”

13. **¿Cómo lo llevarías a CI/CD?**
   - Junior: “Con GitHub Actions”.
   - Senior: “Separaría tests unitarios (mapeos/parsers) de E2E mocked; CI corre lint + unit. E2E reales sólo en entorno de laboratorio con módem disponible.”

14. **¿Headless sí o no para este caso?**
   - Junior: “Sí para más rápido”.
   - Senior: “Depende firmware; algunos UIs legacy fallan en headless. Lo dejaría por feature flag y validaría compatibilidad por modelo.”

### 5) Seguridad
15. **¿Qué riesgo de seguridad más crítico ves?**
   - Junior: “Credenciales en código”.
   - Senior: “Hardcode de TR-069 (`admin/admin`) y endpoint interno. Debe salir a secretos externos, con rotación y mínimo privilegio.”

16. **¿Qué harías con contraseñas en UI?**
   - Junior: “Que se oculten”.
   - Senior: “Ya se ocultan visualmente, pero además evitaría logs de secretos, borrado seguro de variables y policy de complejidad/validación.”

17. **¿Cómo auditarías cambios aplicados al CPE?**
   - Junior: “Con logs”.
   - Senior: “Con reporte estructurado por etapa (OK/FAIL, timestamp, valores aplicados), hash de job y evidencia (captura HTML/screenshot) para trazabilidad.”

---

## H) Mejoras inmediatas (quick wins) y mejoras “nivel senior”

### 10 quick wins concretos
1. Reemplazar `time.sleep` por waits basados en condición (ej. selected value, elemento stale/visible).
2. Unificar manejo de errores Selenium con excepciones específicas y mensajes de contexto.
3. Agregar screenshots automáticos al fallar una etapa (`driver.save_screenshot`).
4. Parametrizar IP del módem y URL TR-069 en config externa.
5. Sacar credenciales hardcodeadas (`admin/admin`) a variables de entorno.
6. Corregir inconsistencia: usar `extra["chanwid_5"]` y `extra["chan_5"]` en 416/414Q.
7. Estandarizar selectores frágiles (evitar XPath absoluto de 414 en WLAN2.4).
8. Cerrar navegador también en 414Q fuera de modo debug (bandera `debug_keep_browser_open`).
9. Agregar validaciones previas en UI (longitud mínima de WPA/nueva clave).
10. Limpiar dependencias no usadas (`PySide6`) y normalizar codificación UTF-8 de `requirements.txt`.

### 5 mejoras estructurales (nivel senior)
1. Implementar **Page Object Model** por secciones (LoginPage, WanPage, WlanPage, AdminPage, AdvancePage).
2. Crear capa común `BaseConfigurator` para eliminar duplicación entre 416 y 414Q.
3. Diseñar sistema de configuración por entorno (`pydantic settings` + `.env`).
4. Incorporar logger estructurado (JSON) + correlación por job ID.
5. Separar orquestación de UI: servicio puro (CLI/API) + UI como cliente.

### Si mañana va a producción 24/7, ¿qué hago primero?
1. Externalizar secretos/config y eliminar hardcode crítico.
2. Endurecer waits/selectores y retries por etapa.
3. Añadir trazabilidad (logs + screenshots + reporte final).
4. Ejecutar pruebas de regresión con firmwares reales de cada modelo.
5. Instrumentar monitoreo operativo (tasa de éxito, tiempo medio, errores por etapa).

---

## Notas de “no se ve en el repo”
- No se ve suite de tests automatizados.
- No se ve pipeline CI/CD.
- No se ve manejo de secretos enterprise (vault/KMS).
- No se ve documentación de compatibilidad por versión de firmware.

Para investigar esos puntos: revisar repos satélite, scripts de despliegue internos o pedir evidencia de ejecución en laboratorio (videos/logs/snapshots).
