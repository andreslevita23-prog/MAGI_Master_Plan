import axios from "axios";

const entradaForzada = {
  timestamp: "2025.06.17 12:00:00",
  pair: "EURUSD",
  price: 1.12,
  high: 1.125,
  low: 1.115,
  context: "waiting_for_entry",
  allowed_actions: ["open"],
  id_operacion: "2025.06.17 12:00:00_99999",
  candle_pattern_M15: "bullish_engulfing",
  market_structure_M15: "uptrend",
  ema20_M15: 1.1195,
  ema50_M15: 1.118,
  rsi14_M15: 58,
  candle_pattern_H1: "hammer",
  market_structure_H1: "uptrend",
  ema20_H1: 1.1185,
  ema50_H1: 1.117,
  rsi14_H1: 60.3,
  candle_pattern_H4: "bullish_engulfing",
  market_structure_H4: "uptrend",
  ema20_H4: 1.115,
  ema50_H4: 1.112,
  rsi14_H4: 62.7,
};

(async () => {
  try {
    const res = await axios.post("http://localhost:3000/analisis", entradaForzada, {
      headers: { "Content-Type": "application/json" },
    });
    console.log("Respuesta forzada para EURUSD:", res.data);
  } catch (err) {
    console.error("Error al enviar entrada forzada:", err.message);
  }
})();
