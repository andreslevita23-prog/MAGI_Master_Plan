# Baltasar v2 + Gaspar v2.1c Integration

## Scope

- Baltasar v2 rich_policy_medium threshold `0.40` generates trades.
- Gaspar v2.1c blocks trades when `P(DETERIORATING) >= 0.50`.
- No model training is performed.

## Validation/Test Comparison

| Split | System | Trades | Avg R | Total R | PF | Max DD | Win rate | Blocked |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| validation | Baltasar v2 solo | 11,425 | 0.0556 | 635.08 | 1.1011 | 348.18 | 0.4084 | 0 |
| validation | Baltasar+Gaspar | 10,939 | 0.0728 | 796.34 | 1.1337 | 332.30 | 0.4155 | 486 |
| test | Baltasar v2 solo | 19,967 | 0.0932 | 1860.35 | 1.1621 | 266.14 | 0.3989 | 0 |
| test | Baltasar+Gaspar | 18,588 | 0.1152 | 2141.65 | 1.2033 | 240.14 | 0.4073 | 1,379 |

## Direction Impact

| Split | Direction | System | Trades | Avg R | PF | Max DD | Blocked |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| validation | BUY | solo | 6,706 | 0.1097 | 1.2075 | 237.59 | 0 |
| validation | BUY | integrated | 6,314 | 0.1371 | 1.2640 | 222.59 | 392 |
| validation | SELL | solo | 4,719 | -0.0213 | 0.9633 | 517.05 | 0 |
| validation | SELL | integrated | 4,625 | -0.0150 | 0.9741 | 486.60 | 94 |
| test | BUY | solo | 7,587 | 0.1226 | 1.2161 | 190.86 | 0 |
| test | BUY | integrated | 7,111 | 0.1321 | 1.2345 | 168.93 | 476 |
| test | SELL | solo | 12,380 | 0.0751 | 1.1296 | 410.55 | 0 |
| test | SELL | integrated | 11,477 | 0.1047 | 1.1842 | 314.77 | 903 |

## 2026Q2 Diagnostic

| System | Trades | Avg R | Total R | PF | Max DD | Blocked |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Baltasar v2 solo | 459 | -0.0572 | -26.26 | 0.9003 | 93.66 | 0.3420 | 0 |
| Baltasar+Gaspar | 459 | -0.0572 | -26.26 | 0.9003 | 93.66 | 0.3420 | 0 |

## Interpretation

On test, integration changes Avg R from `0.0932` to `0.1152`, PF from `1.1621` to `1.2033`, and max DD from `266.14` to `240.14`. In 2026Q2 it changes Avg R from `-0.0572` to `-0.0572` and blocks `0` trades.
