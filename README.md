# MAGI Master Plan

MAGI es el nucleo operativo de decision del sistema Prosperity. El proyecto ya no esta solo en fase de arquitectura: actualmente corre en demo/live controlada con flujo real entre MT5, backend, decision MAGI, ejecucion, auditoria y dashboard.

La demo operativa actual debe continuar hasta el `2026-06-05`. El objetivo de esta etapa no es maximizar ganancias, sino validar estabilidad, trazabilidad, gobierno operativo y comportamiento real antes de considerar cualquier evaluacion fondeada.

## Estado Actual

- Bot A envia snapshots `magi.snapshot.v2` al backend local.
- El backend normaliza snapshots, genera decisiones CEO-MAGI y conserva compatibilidad legacy.
- Melchor evalua riesgo y gobernanza operativa.
- Baltasar y Gaspar aportan direccion/contexto segun la capa MVP disponible.
- Bot B consulta `GET /analisis/:symbol` y ejecuta solo acciones compatibles.
- Bot C funciona como caja negra operativa pasiva en MT5.
- El dashboard consume endpoints reales, no mocks, para estado, snapshots, ejecucion, logs y gobernanza.
- MAGI Guardrails v1 prudente ya esta implementado en backend para demo.

## Arquitectura Operativa

```text
Bot A -> Backend MAGI -> CEO-MAGI -> Bot B -> MT5 -> Bot C -> Auditoria/Dashboard
```

Componentes principales:

- `Bot A`: sensor MT5. Recoge precio, estructura, indicadores, contexto MTF, cuenta/posicion y envia snapshots.
- `Backend MAGI / CEO-MAGI`: normaliza datos, genera decision final, persiste auditoria cognitiva y expone payload para Bot B.
- `Melchor`: capa de riesgo, seguridad y gobernanza operativa.
- `Baltasar`: capa de direccion tecnica.
- `Gaspar`: capa de contexto H4/D1 y oportunidad.
- `Bot B`: ejecutor MT5 conservador, con dedupe, una posicion por simbolo y acciones seguras.
- `Bot C`: auditor pasivo. Registra aperturas, cierres, modificaciones, tickets, comentarios y anomalias.
- `Dashboard`: vista operativa de salud, snapshots, decisiones, ejecucion, logs y governance.

## Gobernanza Operativa

MAGI Guardrails v1 esta orientado a reducir dano operativo sin tocar el edge principal. No cambia reglas de entrada H1/H4, RSI, EMAs, direccion base ni RR principal.

Implementado:

- Memoria operativa persistente por simbolo/direccion/sesion.
- `daily_sl_count`, `daily_tp_count`, `session_sl_count`.
- `cluster_consecutive_sl`, `cluster_sequence`, `same_direction_recent_sl`.
- `safe_mode_active`, `safe_mode_reason`, `blocked_until`.
- `last_trade_result`, `last_trade_direction`, `last_trade_close_time`.
- SAFE_MODE real tras 3 SL consecutivos dentro de un cluster toxico.
- Shadow mode para Friday Guardrail.
- Shadow mode para Cluster 2SL.
- Lotaje demo `1.0` con `DEMO_MODE=true`.
- Ventana demo declarada con `MAGI_DEMO_MODE_UNTIL=2026-06-05`.

Pendiente como placeholder trazable:

- BE automatico: `be_auto_status=not_enabled_no_mfe_mae_dataset`.
- News guardrail: `news_guardrail_status=not_enabled_no_calendar`.

## Endpoints Principales

Backend:

- `GET /health`
- `POST /analisis`
- `GET /analisis/:symbol`
- `GET /api/overview`
- `GET /api/snapshots`
- `GET /api/execution`
- `GET /api/governance`
- `GET /api/logs`
- `GET /dashboard`

## Comandos

Desde `servidor-prosperity`:

```bash
npm install
npm run start
npm run start:demo
npm run check
npm run test:guardrails-v1
npm run test:melchor
npm run test:snapshot-v2
npm run test:e2e-demo
npm run verify:demo-ready
```

## Configuracion Demo

Variables recomendadas para demo local:

```bash
DEMO_MODE=true
MAGI_DEMO_LOT_SIZE=1.0
MAGI_DEMO_MODE_UNTIL=2026-06-05
MAGI_BOT_C_AUDIT_DIR=<ruta real a MQL5/Files/MAGI/audit>
```

`MAGI_BOT_C_AUDIT_DIR` debe apuntar a la ruta real de MT5 donde Bot C escribe su auditoria, por ejemplo:

```text
C:\Users\<usuario>\AppData\Roaming\MetaQuotes\Terminal\<terminal_id>\MQL5\Files\MAGI\audit
```

Esa ruta permite que la memoria operativa reconstruya cierres reales desde Bot C y alimente la gobernanza.

## Validaciones Recientes

Durante la demo se validaron:

- Integracion Bot A -> backend con contrato `magi.snapshot.v2`.
- Correccion del byte nulo en transporte MQL5.
- Fallback M15 para evitar invalidar snapshots por historico parcial.
- Compatibilidad legacy para Bot B.
- Bot B seguro con dedupe, bloqueo de duplicados y acciones `hold`, `open`, `close`, `protect`, `modify`, `move_to_breakeven`.
- Bot C como caja negra pasiva con eventos MT5.
- Dashboard conectado a datos reales.
- Journal cognitivo de decisiones.
- Simulaciones de fondeo, analisis de reentradas, viernes, clusters, equity diaria y guardrails.
- Experimentos Fausto como investigacion de sobreexposicion, no como estrategia productiva.

Hallazgo principal: en escenarios agresivos, el riesgo mas critico no es la perdida total lenta, sino el `daily DD`, los clusters violentos y sesiones toxicas. Los resultados historicos fueron interesantes, pero no garantizan rentabilidad futura.

## Roadmap Inmediato

- Mantener demo supervisada hasta el `2026-06-05`.
- Validar Guardrails v1 en vivo sin modificar reglas de entrada.
- Recolectar MFE/MAE real para estudiar BE formal.
- Integrar calendario de noticias antes de activar news guardrail.
- Mejorar trazabilidad Bot C `ticket -> decision_id`, especialmente en cierres.
- Monitorear SAFE_MODE, clusters y Friday shadow guardrail.
- Evaluar fondeo conservador solo despues de evidencia live suficiente.
- Mantener Fausto como modulo experimental futuro, nunca como core principal.

## Estructura Documental Base

- `docs/01_vision.md`: vision del sistema y objetivos.
- `docs/02_architecture_overview.md`: arquitectura de alto nivel.
- `docs/03_system_flow.md`: flujo operativo end-to-end.
- `docs/04_modules.md`: responsabilidades de cada modulo.
- `docs/05_magi_logic.md`: reglas MAGI y jerarquia.
- `docs/06_bot_a.md`: especificacion del sensor periodico.
- `docs/07_melchor.md`: diseno del mago de riesgo.
- `docs/08_baltasar.md`: diseno del mago tecnico.
- `docs/09_gaspar.md`: diseno del mago de oportunidad.
- `docs/10_ceo_magi.md`: motor de arbitraje y decision final.
- `docs/11_bot_b.md`: ejecutor operativo.
- `docs/12_bot_c.md`: auditoria y dataset.
- `docs/14_data_contracts.md`: contratos JSON entre modulos.
- `docs/15_risk_rules.md`: reglas duras de riesgo del MVP.
- `docs/17_roadmap.md`: roadmap por fases.

## Nota de Prudencia

MAGI esta vivo y operativo en demo, pero no esta validado para dinero real. La evidencia historica y las pruebas de simulacion sirven para orientar decisiones tecnicas; no reemplazan una fase demo suficiente, auditoria diaria ni control de riesgo real.
