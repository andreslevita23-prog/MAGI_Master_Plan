# 07. Melchor

## Mision

Melchor v1 protege capital dentro de MAGI como modulo real de votacion de riesgo. No es ML, no es un filtro dentro de Bot A y no ejecuta decisiones finales: recibe snapshots normalizados, evalua reglas duras y emite una recomendacion JSON auditable.

Bot A sigue siendo sensor/generador de snapshots. CEO-MAGI lee el voto de Melchor como input y gobierna la decision operativa final.

## Contrato de voto

Melchor emite:

```json
{
  "module": "MELCHOR",
  "version": "v1.0",
  "vote": "ALLOW | BLOCK | PROTECT | CLOSE | NOTIFY",
  "risk_block_recommendation": true,
  "confidence": 1.0,
  "risk_level": "LOW | MEDIUM | HIGH | CRITICAL",
  "reason": "explicacion breve",
  "rules_triggered": [],
  "recommended_action": {
    "action": "hold",
    "details": {}
  }
}
```

`risk_block_recommendation` no es un veto operativo absoluto. Significa que Melchor recomienda no avanzar o recomienda proteccion por riesgo. La autoridad para bloquear, permitir, proteger o cerrar pertenece a CEO-MAGI.

Cada voto queda persistido en `servidor-prosperity/data/votes/melchor/` con `timestamp`, `symbol` y `snapshot_id`.

## Responsabilidades v1

- Validar sesiones Londres, Nueva York y solapamiento.
- Recomendar bloqueo ante riesgo, RR, spread o SL fuera de politica.
- Recomendar bloqueo de nuevas entradas si ya existe una operacion abierta.
- Notificar drawdown diario desde `0.7%`.
- Recomendar cierre/proteccion desde `1.0%` de drawdown diario.
- Recomendar bloqueo ante noticias de alto impacto USD, EUR o GBP en ventana de 30 minutos antes/despues.
- Pedir `move_to_breakeven` cuando una operacion llegue al 50% del TP.
- Recomendar bloqueo si faltan datos criticos.

## Gobierno CEO-MAGI

El decision engine puede construir un candidato preliminar y consultar a Melchor. CEO-MAGI toma la decision final usando `melchor_vote` como input de riesgo.

Por defecto, CEO-MAGI sigue una politica conservadora:

- `BLOCK`: normalmente `hold`
- `PROTECT`: `protect` o `move_to_breakeven`
- `CLOSE`: `close_for_safety`
- `NOTIFY`: no bloquea por si solo, pero queda registrado

CEO-MAGI puede abrir pese a `risk_block_recommendation: true` solamente si registra una justificacion obligatoria en campos planos:

```json
{
  "override_melchor": true,
  "override_reason": "justificacion operativa"
}
```

Sin esa justificacion, CEO-MAGI puede respetar la recomendacion y devolver una salida segura.

## Futuro

Melchor podra usar analitica mas avanzada en versiones futuras, pero sus reglas duras deben seguir siendo deterministicas, conservadoras y explicables.
