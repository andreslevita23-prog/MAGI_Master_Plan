# Plataforma web MAGI Fase 1

## Objetivo

La plataforma web MAGI Fase 1 es un centro de mando operativo para demo local. Su prioridad no es vender el producto ni mostrar una landing page, sino responder rapido:

- si MAGI esta vivo;
- si esta en observacion, demo activo, pausado o error;
- si existe operacion abierta;
- cual fue la ultima decision CEO-MAGI;
- que riesgo esta reportado;
- si Bot A, backend CEO-MAGI, Bot B y Bot C tienen evidencia de conexion;
- que eventos reales registro Bot C cuando el archivo de auditoria MT5 esta disponible.

## Arquitectura del dashboard

La plataforma queda dividida en cinco rutas de monitoreo:

- `/dashboard`: vista ejecutiva limpia para monitoreo diario.
- `/bot_A`: ultimos snapshots/eventos de Bot A.
- `/magi`: ultimas decisiones CEO-MAGI.
- `/bot_B`: payloads/eventos enviados a Bot B.
- `/bot_C`: auditoria real de Bot C.

Los archivos principales viven en:

- `src/client/dashboard.html`
- `src/client/bot_A.html`
- `src/client/bot_B.html`
- `src/client/bot_C.html`
- `src/client/magi.html`
- `src/client/scripts/platform.js`
- `src/client/styles/main.css`

El frontend es JavaScript estatico servido por Express desde `/dashboard`. No introduce build step, login ni librerias nuevas.

Componentes reutilizables en `platform.js`:

- tarjetas ejecutivas de estado y metricas;
- tablas reutilizables para registros amplios;
- listas compactas de ultimos registros;
- graficas simples con SVG cuando existen datos reales.

## Endpoints usados

El dashboard consume endpoints existentes y mantiene compatibilidad legacy:

| Endpoint | Uso |
| --- | --- |
| `GET /api/platform/summary?range=day|week|month` | Resumen ejecutivo para `/dashboard`, con filtros simples de dia, semana o mes. |
| `GET /api/overview` | Estado del backend, uptime, ultimo snapshot, estado Bot A y ejecucion reciente. |
| `GET /api/snapshots?limit=20` | Lista reciente de snapshots reales persistidos desde Bot A. |
| `GET /api/snapshots/:id` | Detalle del ultimo snapshot para posicion, riesgo, cuenta y contexto. |
| `GET /api/execution` | Ultima respuesta preparada para Bot B y bitacora de decisiones resumida. |
| `GET /api/position/current` | Contrato estable de posicion actual, con fuente y nivel de confianza. |
| `GET /api/bot-a/events?limit=100` | Registros amplios para `/bot_A`. |
| `GET /api/magi/decisions?limit=100` | Registros amplios para `/magi`. |
| `GET /api/bot-b/events?limit=100` | Registros amplios para `/bot_B`. |
| `GET /api/bot-c/events?limit=100` | Registros amplios para `/bot_C`. |
| `GET /api/logs` | Eventos del sistema, errores recientes y auditoria Bot C si existe archivo local. |
| `GET /api/bot-c/audit?date=YYYY-MM-DD` | Auditoria formal de Bot C para una fecha, con eventos reales y resumen diario si existen. |
| `GET /health` | Verificacion externa de salud del backend. |

Endpoints legacy preservados:

- `POST /analisis`
- `GET /analisis/:symbol`
- `GET /api/overview`
- `GET /api/snapshots`
- `GET /api/execution`
- `GET /api/cases`
- `GET /api/logs`
- `GET /health`

## Datos disponibles

Datos reales usados:

- ultimo `snapshot_id`;
- ultimo `decision_id`;
- accion final de CEO-MAGI;
- razon de decision;
- payload enviado a Bot B;
- estado de validacion del snapshot;
- posicion actual desde `GET /api/position/current`;
- `daily_drawdown_percent` y `risk_percent_per_trade` cuando Bot A los informa;
- votos disponibles desde estado de ejecucion, actualmente Melchor cuando existe;
- errores y eventos del sistema.
- ultimos 100 registros por modulo en paginas dedicadas.

Los valores faltantes se muestran como `dato no disponible` o como placeholder explicitamente marcado.

## Dashboard ejecutivo

`/dashboard` queda deliberadamente liviano:

- estado general y conexiones de Bot A, MAGI/backend, Bot B y Bot C;
- tiempo encendido del backend/MAGI desde el ultimo arranque;
- hero operativo institucional con estado general, posicion, uptime y contadores reales del rango;
- franja de modulos MAGI destacados para Bot A, CEO-MAGI, Bot B, Bot C y operacion actual;
- metricas principales disponibles;
- filtro simple `dia`, `semana`, `mes`;
- auto-actualizacion cada 30 segundos con boton manual `Actualizar ahora`;
- graficas de senales por hora/dia, decisiones por accion, PnL, drawdown y ganadoras/perdedoras solo si hay datos reales;
- ultimos 5 registros de Bot A, MAGI, Bot B y Bot C con enlace `Ver mas`.

Las auditorias profundas ya no viven en el dashboard principal:

- `/bot_A` muestra hasta 100 snapshots con timestamp, simbolo, `snapshot_id`, estado, `source_mode`, validacion, issues, precio y timeframe.
- `/magi` muestra hasta 100 decisiones con `decision_id`, `snapshot_id`, accion, razon, votos disponibles, payload Bot B y confidence/score si existe.
- `/bot_B` muestra hasta 100 payloads/eventos con action, `decision_id`, estado, comment MAGI, errores/rechazos y dedupe si aplica.
- `/bot_C` muestra hasta 100 eventos reales de auditoria, resaltando eventos sin `decision_id`.

El lenguaje visual del dashboard ejecutivo recupera jerarquia de centro de mando, pero mantiene la arquitectura modular y la honestidad de datos de la version nueva: no hay mocks, placeholders operativos ni conteos inferidos desde limites de respuesta.

### Conteos y metricas ejecutivas

`GET /api/platform/summary?range=day|week|month` separa los conceptos de conteo para evitar metricas enganhosas:

| Campo | Significado |
| --- | --- |
| `total_count` | Total real encontrado para el rango solicitado en la fuente consultada. Es el valor que debe mostrar el dashboard. |
| `returned_count` | Cantidad de registros incluidos en la respuesta resumida para pintar ultimos eventos. Puede ser menor por limite de UI. |
| `limit` | Maximo de registros que el endpoint devuelve para listas recientes. No representa el total real. |

Fuentes actuales por metrica:

| Metrica | Fuente | Regla |
| --- | --- | --- |
| Senales Bot A | `data/logs/YYYY-MM-DD/botA.jsonl` | Cuenta registros dentro del rango. |
| Decisiones MAGI | `data/audit/decisions/YYYY-MM-DD/magi_decisions.jsonl` | Cuenta decisiones dentro del rango. |
| Operaciones abiertas | `GET /api/position/current` | `1` solo si la posicion actual reporta `status=open`; `0` si reporta `closed`; `null` si la fuente no permite confirmarlo. |
| Operaciones cerradas | Bot C audit via `MAGI_BOT_C_AUDIT_DIR` | Cuenta eventos `close` dentro del rango solo cuando Bot C esta disponible. |
| Ganadoras | Bot C audit | `profit > 0`. |
| Perdedoras | Bot C audit | `profit < 0`. |
| Breakeven | Bot C audit | `profit == 0`. |
| Profit desconocido | Bot C audit | Evento `close` sin `profit` numerico. |
| PnL diario | Bot C audit | Suma de `profit` numerico en cierres del rango; `null` si no hay profit real. |
| Drawdown diario | Curva derivada de cierres Bot C | `null` si no hay curva real de profit. |
| Profit factor | Bot C audit | Calculado solo si existen ganancias y perdidas reales. |
| Win rate | Bot C audit | Calculado solo sobre cierres con profit numerico. |

Cuando una fuente confiable no existe o no esta accesible, el backend devuelve `null` y `available=false` cuando aplica. El frontend muestra `no disponible`, nunca `0`, para evitar confundir ausencia de datos con resultado operativo real.

Graficas del dashboard:

- senales por hora cuando `range=day`;
- senales por dia cuando `range=week` o `range=month`;
- decisiones por accion (`HOLD`, `OPEN`, `CLOSE`, `PROTECT`, etc.);
- curva PnL y drawdown solo desde cierres Bot C con `profit` real;
- barras de ganadoras/perdedoras/breakeven solo cuando Bot C esta disponible.

### Auto-actualizacion y uptime

El dashboard ejecutivo consulta:

```text
GET /api/platform/summary?range=day|week|month
```

Frecuencia:

- `/dashboard` refresca el summary automaticamente cada 30 segundos.
- El boton `Actualizar ahora` fuerza una nueva lectura inmediata.
- El contador `MAGI encendido hace` se actualiza visualmente cada 1 segundo sin llamar al backend cada segundo.
- Si una peticion falla, la vista existente permanece visible y el estado cambia a `error de actualizacion`.

El backend expone tiempo real de proceso en:

| Campo | Endpoint | Uso |
| --- | --- | --- |
| `started_at` | `/health` y `/api/platform/summary` | Fecha/hora del ultimo arranque del proceso Node. |
| `uptime_seconds` | `/health` y `/api/platform/summary` | Segundos activos del backend al momento de generar la respuesta. |

`/api/platform/summary` tambien incluye `data_quality`:

| Campo | Significado |
| --- | --- |
| `bot_a` | `disponible` si hay registros Bot A reales en el rango. |
| `magi_decisions` | `disponible` si hay decisiones MAGI reales en el rango. |
| `bot_b` | `disponible` si hay registros Bot B reales en el rango. |
| `bot_c` | `disponible` solo si la auditoria Bot C esta accesible para el rango. |
| `last_update` | Timestamp real de generacion del summary. |
| `latest_snapshot_id` | Ultimo snapshot conocido por almacenamiento local. |
| `latest_snapshot_age_seconds` | Edad del ultimo snapshot, calculada desde su timestamp disponible. |
| `incomplete_metrics` | `true` cuando faltan fuentes confiables para metricas de trading cerradas. |

Si Bot C no esta disponible, la tarjeta `Calidad de datos` muestra advertencia porque cierres, win/loss, PnL, profit factor y win rate quedan incompletos.

## Posicion actual

El endpoint formal de posicion actual es:

```text
GET /api/position/current
```

No modifica trading ni ejecuta acciones. Solo compone el estado mas confiable posible desde fuentes ya disponibles.

Contrato estable:

```json
{
  "status": "open | closed | unknown | not_available",
  "source": "bot_c:floating_snapshot | bot_c:open | bot_c:close | snapshot:normalized_position | execution:bot_b_payload | none",
  "confidence": "high | medium | low",
  "symbol": null,
  "ticket": null,
  "side": null,
  "entry_price": null,
  "sl": null,
  "tp": null,
  "lot_size": null,
  "floating_profit": null,
  "open_time": null,
  "duration_seconds": null,
  "decision_id": null,
  "snapshot_id": null,
  "comment": null,
  "protection_state": null,
  "warnings": []
}
```

Fuentes usadas, en orden de confianza:

| Fuente | Confianza | Uso |
| --- | --- | --- |
| Bot C `floating_snapshot`, `open`, `close` | Alta | Evidencia real de MT5 cuando `MAGI_BOT_C_AUDIT_DIR` esta configurado y hay eventos. |
| Snapshot normalizado Bot A `position` | Media | Estado reportado por Bot A en snapshots recientes. Sirve para saber si Bot A ve posicion abierta o cerrada, pero puede no incluir ticket ni tiempo de apertura. |
| Execution state / payload Bot B | Baja | Ultima intencion/respuesta enviada a Bot B. No confirma ejecucion real, por eso el endpoint devuelve `unknown` y agrega advertencia. |

Limitaciones:

- Sin Bot C accesible, el backend no puede confirmar tickets reales ni cierres MT5.
- Los snapshots actuales pueden informar `has_open_position`, `entry_price`, `sl`, `tp` y `floating_pnl`, pero no siempre `open_time`, `ticket`, `side` o proteccion.
- El payload Bot B no es una fuente de verdad de mercado; se usa solo como trazabilidad de baja confianza.
- `protection_state` se infiere solo cuando hay entrada, SL y lado suficientes. Si faltan datos, queda `null`.

## Auditoria Bot C

Bot C esta disenado para escribir eventos MT5 en:

```text
MAGI/audit/YYYY-MM-DD/bot_c_events.jsonl
MAGI/audit/YYYY-MM-DD/bot_c_daily_summary.json
```

En el EA actual, `integrations/mt5/Bot_C.mq5` usa:

```text
input string AuditRootFolder = "MAGI\\audit";
```

Bot C abre archivos con `FileOpen` sin `FILE_COMMON`, por lo que la ruta real queda dentro del sandbox del terminal MT5, normalmente:

```text
<MT5 terminal data folder>/MQL5/Files/MAGI/audit/YYYY-MM-DD/bot_c_events.jsonl
<MT5 terminal data folder>/MQL5/Files/MAGI/audit/YYYY-MM-DD/bot_c_daily_summary.json
```

Como esa carpeta puede estar fuera del workspace del servidor, el backend lee Bot C desde una variable configurable:

```text
MAGI_BOT_C_AUDIT_DIR=C:\Users\Asus\AppData\Roaming\MetaQuotes\Terminal\<terminal_id>\MQL5\Files\MAGI\audit
```

Si `MAGI_BOT_C_AUDIT_DIR` no esta configurada, el backend usa una ruta segura dentro del workspace:

```text
data/audit/bot_c
```

Esa ruta por defecto sirve para pruebas locales o para copiar archivos exportados, pero no representa automaticamente la carpeta real de MT5.

### Endpoint `GET /api/bot-c/audit`

Parametros:

- `date` opcional en formato `YYYY-MM-DD`; por defecto usa la fecha UTC actual.
- `limit` opcional; por defecto `100`, maximo `500`.

Respuesta:

- `status`: `disponible`, `sin_archivos` o `no_disponible`.
- `audit_root`: ruta leida por el backend.
- `expected_files`: rutas esperadas para eventos y resumen diario.
- `files`: existencia de raiz, carpeta de fecha, eventos y resumen.
- `events`: eventos reales normalizados desde `bot_c_events.jsonl`.
- `daily_summary`: contenido de `bot_c_daily_summary.json` si existe.
- `missing_decision_id`: conteo de eventos sin `decision_id`.
- `events_without_decision_id`: subconjunto de eventos con trazabilidad incompleta.

Cuando no existe ruta o archivo, el endpoint no falla: devuelve estado no disponible o sin archivos y listas vacias. Solo responde `400` si `date` no cumple `YYYY-MM-DD`.

## Endpoints faltantes propuestos

Antes de ejecutar acciones o depender de datos operativos completos, conviene implementar estos endpoints con contrato explicito:

| Endpoint propuesto | Motivo |
| --- | --- |
| `GET /api/risk/daily` | PnL del dia, drawdown diario real, limite de perdida y estado de bloqueo. |
| `POST /api/safety/confirm-intent` | Primera fase de doble confirmacion para acciones peligrosas. |
| `POST /api/safety/execute` | Ejecucion segura de pausar, bloquear operaciones o cerrar todo, solo cuando exista control de permisos y confirmacion. |

## Modo seguridad

En Fase 1 el panel de seguridad es visual. Los botones:

- bloquear operaciones por hoy;
- cerrar todo;

estan deshabilitados y marcados como `pendiente de backend seguro`. No llaman endpoints ni modifican trading.

## Acceso privado solo lectura

Para ver MAGI desde celular en `prosperity.lat` sin exponer trading, se debe levantar un segundo proceso del backend en modo solo lectura. El proceso operativo local de MT5/Bot A/Bot B/Bot C permanece en su puerto local normal, por ejemplo `3000`; el proceso publico de dashboard usa otro puerto, por ejemplo `3001`, y solo lee los archivos/estado ya persistidos.

Variables:

```text
READ_ONLY_DASHBOARD=true
PORT=3001
DASHBOARD_USERS_JSON=[{"user":"demo","password":"change-me"}]
# opcional si se prefiere token:
DASHBOARD_AUTH_TOKEN=<token_largo_aleatorio>
```

`DASHBOARD_USERS_JSON` es leido solo por el servidor. No se envia al frontend ni aparece en las respuestas del dashboard. La autenticacion se mantiene como Basic Auth, pero ahora cualquier par `user/password` incluido en ese JSON es valido.

Comando sugerido para el proceso privado de lectura:

```powershell
$env:READ_ONLY_DASHBOARD="true"
$env:PORT="3001"
$env:DASHBOARD_USERS_JSON='[{"user":"demo","password":"change-me"}]'
npm start
```

En `READ_ONLY_DASHBOARD=true`:

- solo se aceptan `GET`, `HEAD` y `OPTIONS`;
- `/analisis` y `/analisis/:symbol` responden `404`;
- no se expone publicamente el contrato legacy usado por Bot A/Bot B;
- las rutas del dashboard, assets y APIs de lectura requieren autenticacion;
- si no existe `DASHBOARD_USERS_JSON`, `DASHBOARD_AUTH_TOKEN` ni usuario/password basico legacy, el servidor responde `503`;
- si `DASHBOARD_USERS_JSON` no es JSON valido, el servidor responde `503` y falla cerrado;
- si el usuario/password no coincide con ningun par autorizado, el servidor responde `401`;
- no se habilita CORS; el dashboard debe consumirse desde el mismo origen publicado por el tunel;
- se agregan cabeceras defensivas: `X-Robots-Tag: noindex`, `X-Frame-Options: DENY`, `Cross-Origin-Resource-Policy: same-origin` y `Referrer-Policy: no-referrer`.

Rutas permitidas en modo solo lectura:

| Ruta | Uso |
| --- | --- |
| `/dashboard`, `/bot_A`, `/magi`, `/bot_B`, `/bot_C` | Paginas web privadas. |
| `/static/*`, `/assets/*` | JS, CSS y logo del dashboard. |
| `/api/platform/summary` | Resumen ejecutivo con metricas honestas. |
| `/api/overview`, `/api/snapshots`, `/api/execution` | Datos de lectura heredados. |
| `/api/position/current` | Posicion actual compuesta de fuentes disponibles. |
| `/api/bot-a/events`, `/api/magi/decisions`, `/api/bot-b/events`, `/api/bot-c/events` | Paginas modulares. |
| `/api/logs`, `/api/bot-c/audit` | Auditoria y eventos de lectura. |
| `/health` | Salud del proceso de dashboard privado. |

Rutas bloqueadas:

| Ruta | Motivo |
| --- | --- |
| `POST /analisis` | Entrada operativa de Bot A; debe quedar solo local. |
| `GET /analisis/:symbol` | Contrato operativo de Bot B; debe quedar solo local. |
| `/api/connectors`, `/api/settings`, `/api/cases` | No son necesarias para la vista movil privada. |
| Cualquier `POST`, `PUT`, `PATCH`, `DELETE` | No hay acciones desde el dashboard publico. |

### Cloudflare Tunnel / prosperity.lat

Configuracion recomendada:

1. Mantener MAGI operativo local:

```powershell
$env:PORT="3000"
npm start
```

2. Levantar dashboard privado solo lectura en otro puerto:

```powershell
$env:READ_ONLY_DASHBOARD="true"
$env:PORT="3001"
$env:DASHBOARD_USERS_JSON='[{"user":"demo","password":"change-me"}]'
npm start
```

3. Publicar solo el puerto `3001` con Cloudflare Tunnel:

```powershell
cloudflared tunnel --url http://localhost:3001
```

4. Para dominio propio, apuntar un subdominio privado, por ejemplo:

```text
magi.prosperity.lat -> http://localhost:3001
```

Recomendaciones:

- Usar HTTPS terminado por Cloudflare.
- Preferir Basic Auth para celular; el navegador reutiliza la sesion y las llamadas `fetch` quedan autenticadas. Configurar usuarios reales fuera de Git.
- Si se usa `DASHBOARD_AUTH_TOKEN`, entrar primero a `/dashboard?token=<token_largo>` para que el servidor cree una cookie `HttpOnly`.
- No tunelar el puerto operativo `3000`.
- No publicar rutas `/analisis`.
- No activar acciones peligrosas hasta tener backend seguro con doble confirmacion y permisos.

### Scripts Windows para arranque rapido

Se agregaron scripts en:

```text
scripts/windows/
```

Flujo recomendado para Andres:

1. Mantener el backend operativo local de MAGI/MT5 como siempre, por ejemplo en `PORT=3000`. Ese proceso es el que usan Bot A y Bot B localmente.

2. En una segunda terminal PowerShell, levantar el dashboard privado solo lectura:

```powershell
.\scripts\windows\start-dashboard-readonly.ps1
```

Este script configura automaticamente:

```text
READ_ONLY_DASHBOARD=true
PORT=3001
DASHBOARD_USERS_JSON=[demo]
MAGI_BOT_C_AUDIT_DIR=<ruta-real-a-MQL5\Files\MAGI\audit>
```

Usuarios habilitados por Basic Auth:

| Usuario | Password |
| --- | --- |
| `demo` | `change-me` |

Las credenciales reales no deben versionarse. Definir `DASHBOARD_USERS_JSON` en `.env` local o variables del sistema.

3. Verificar que `cloudflared` exista:

```powershell
.\scripts\windows\check-cloudflared.ps1
```

Si no existe, el script muestra la URL oficial de descarga y los pasos para validar:

```powershell
cloudflared --version
```

4. En una tercera terminal PowerShell, abrir el tunel:

```powershell
.\scripts\windows\start-cloudflare-tunnel.ps1
```

Este script ejecuta:

```powershell
cloudflared tunnel --url http://localhost:3001
```

Notas:

- El tunel debe apuntar solo a `3001`, nunca al puerto operativo `3000`.
- `READ_ONLY_DASHBOARD=true` bloquea `/analisis`, `/analisis/:symbol` y cualquier metodo no lectura.
- El dashboard publicado sigue usando datos reales persistidos por el backend local; no usa mocks.
- Para dominio fijo `magi.prosperity.lat`, configurar un tunnel nombrado en Cloudflare y apuntarlo al servicio local `http://localhost:3001`.

### Modo Andres: magi.prosperity.lat con tunel nombrado

Objetivo final:

```text
https://magi.prosperity.lat -> Cloudflare Tunnel magi-dashboard -> http://localhost:3001
```

No publicar el backend operativo:

```text
Backend MAGI/MT5 local: http://localhost:3000
Dashboard privado read-only: http://localhost:3001
```

Scripts disponibles:

| Script | Uso |
| --- | --- |
| `scripts/windows/cloudflare-login.ps1` | Ejecuta login de Cloudflare. |
| `scripts/windows/create-named-tunnel.ps1` | Crea el tunel nombrado `magi-dashboard`. |
| `scripts/windows/route-dns-magi.ps1` | Crea la ruta DNS `magi.prosperity.lat`. |
| `scripts/windows/run-magi-named-tunnel.ps1` | Ejecuta el tunel nombrado hacia `http://localhost:3001`. |
| `scripts/windows/setup-cloudflare-magi.ps1` | Asistente de setup: login, create tunnel y route dns. |
| `scripts/windows/start-cloudflare-tunnel.ps1` | Quick tunnel temporal para pruebas con `trycloudflare.com`. |

Lo unico manual:

1. Ejecutar:

```powershell
.\scripts\windows\cloudflare-login.ps1
```

2. Se abre navegador.
3. Andres inicia sesion en Cloudflare.
4. Selecciona `prosperity.lat`.
5. Autoriza `cloudflared`.

Setup inicial recomendado, una sola vez:

```powershell
.\scripts\windows\setup-cloudflare-magi.ps1
```

Ese script ejecuta:

```powershell
& "C:\Program Files\cloudflared\cloudflared.exe" tunnel login
& "C:\Program Files\cloudflared\cloudflared.exe" tunnel create magi-dashboard
& "C:\Program Files\cloudflared\cloudflared.exe" tunnel route dns magi-dashboard magi.prosperity.lat
```

Uso diario en tres terminales:

Terminal 1: backend operativo local, no publicado.

```powershell
$env:PORT="3000"
npm run start
```

Terminal 2: dashboard privado read-only.

```powershell
.\scripts\windows\start-dashboard-readonly.ps1
```

Terminal 3: tunel nombrado hacia `magi.prosperity.lat`.

```powershell
.\scripts\windows\run-magi-named-tunnel.ps1
```

El script `run-magi-named-tunnel.ps1` genera un archivo local:

```text
%USERPROFILE%\.cloudflared\magi-dashboard-config.yml
```

con esta configuracion:

```yaml
tunnel: 6eb582eb-0de5-43ce-9a26-d5dfe388d827
credentials-file: C:\Users\Asus\.cloudflared\6eb582eb-0de5-43ce-9a26-d5dfe388d827.json

ingress:
  - hostname: magi.prosperity.lat
    service: http://localhost:3001
  - service: http_status:404
```

Luego ejecuta el comando correcto para tunel nombrado local:

```powershell
& "C:\Program Files\cloudflared\cloudflared.exe" tunnel --config "%USERPROFILE%\.cloudflared\magi-dashboard-config.yml" run 6eb582eb-0de5-43ce-9a26-d5dfe388d827
```

`cloudflared tunnel --url http://localhost:3001` queda solo para pruebas temporales porque crea una URL aleatoria `trycloudflare.com`; no sirve como publicacion estable de `magi.prosperity.lat`.

### Diagnostico 404 en magi.prosperity.lat

Si `cloudflared` muestra conexiones activas pero `https://magi.prosperity.lat/dashboard` devuelve `404`, revisar primero que DNS, credenciales y config apunten al mismo tunnel ID.

Estado esperado:

| Nombre | Tunnel ID | Uso |
| --- | --- | --- |
| `magi-dashboard` | `6eb582eb-0de5-43ce-9a26-d5dfe388d827` | Dashboard privado `magi.prosperity.lat -> localhost:3001`. |
| `prosperity-tunnel` | `975fc218-1d98-47bb-9bcc-985659f45f1c` | Tunel antiguo; no debe usarse para MAGI dashboard. |

Causa detectada:

- Existian dos archivos JSON en `%USERPROFILE%\.cloudflared`.
- El script anterior elegia el JSON mas reciente.
- El mas reciente podia ser `975fc218...json`, correspondiente a `prosperity-tunnel`.
- Entonces `run-magi-named-tunnel.ps1` podia arrancar con credenciales antiguas aunque el objetivo fuera `magi-dashboard`.
- Si DNS apuntaba a un tunel y el proceso corria con otro/config antigua, Cloudflare llegaba a un ingress `http_status:404`.

Correccion aplicada:

- `run-magi-named-tunnel.ps1` usa explicitamente:

```text
C:\Users\Asus\.cloudflared\6eb582eb-0de5-43ce-9a26-d5dfe388d827.json
```

- El config generado usa:

```yaml
tunnel: 6eb582eb-0de5-43ce-9a26-d5dfe388d827
```

- `route-dns-magi.ps1` usa:

```powershell
cloudflared tunnel route dns --overwrite-dns 6eb582eb-0de5-43ce-9a26-d5dfe388d827 magi.prosperity.lat
```

Comandos de verificacion:

```powershell
& "C:\Program Files\cloudflared\cloudflared.exe" tunnel list
Get-Content "$env:USERPROFILE\.cloudflared\magi-dashboard-config.yml"
```

El archivo `%USERPROFILE%\.cloudflared\config.yml` puede existir para tuneles antiguos. Para MAGI dashboard se usa `magi-dashboard-config.yml`, pasado explicitamente con `--config`.

## Proximos pasos

1. Configurar una ruta segura para leer archivos reales de Bot C desde MT5.
2. Enriquecer `GET /api/position/current` con `open_time`, ticket y lado cuando Bot C o snapshots los reporten.
3. Agregar PnL diario real y drawdown real desde cuenta demo.
4. Implementar backend seguro con doble confirmacion para controles peligrosos.
5. Agregar pruebas de contrato para `/api/overview`, `/api/execution`, `/api/logs` y futuro `/api/bot-c/audit`.

## Riesgos tecnicos detectados

- Bot C puede estar escribiendo fuera del workspace, por lo que el dashboard no puede auditar eventos reales hasta configurar ruta de lectura.
- `daily_drawdown_percent` y `risk_percent_per_trade` llegan como `0.0` en snapshots actuales y deben tratarse como placeholders hasta validacion operativa.
- La posicion actual puede tener confianza media o baja si Bot C no esta accesible; el endpoint lo declara en `confidence` y `warnings`.
- La bitacora actual muestra votos disponibles, pero Baltasar y Gaspar todavia pueden aparecer como no disponibles si la decision MVP no los persiste.
- El endpoint `/api/execution` conserva un estado por simbolo, no necesariamente una lista completa de todas las decisiones historicas.
