import axios from 'axios';

const jsonDePrueba = {
  "timestamp": "2025.06.18 10:38:05",
  "pair": "XAUUSD",
  "price": 3382.90,
  "context": "waiting_for_entry",
  "allowed_actions": ["open"],
  "market_structure_H4": "uptrend",
  "rsi14_H4": 54.1,
  "ema20_H4": 3379.5,
  "ema50_H4": 3368.3,
  "candle_pattern_H4": "hammer",
  "market_structure_H1": "uptrend",
  "rsi14_H1": 58.6,
  "ema20_H1": 3381.1,
  "ema50_H1": 3376.9,
  "candle_pattern_H1": "bullish_engulfing",
  "market_structure_M15": "uptrend",
  "rsi14_M15": 63.4,
  "ema20_M15": 3383.0,
  "ema50_M15": 3381.6,
  "candle_pattern_M15": "none"
}


const url = "http://localhost:3000/analisis";

axios.post(url, JSON.stringify(jsonDePrueba), {
  headers: { "Content-Type": "application/json" }
})
.then(response => {
  console.log("✅ Respuesta de la API:", response.data);
})
.catch(error => {
  console.error("❌ Error al enviar entrada forzada:", error.message);
});
