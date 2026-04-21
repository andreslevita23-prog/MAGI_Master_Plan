#ifndef __MAGI_FEATURE_ENGINE_MQH__
#define __MAGI_FEATURE_ENGINE_MQH__

#property strict

#include "MagiCommon.mqh"

bool MagiCopyRatesClosed(const string symbol,const ENUM_TIMEFRAMES timeframe,const int start_shift,const int count,MqlRates &rates[])
{
   ArraySetAsSeries(rates, true);
   int copied = CopyRates(symbol, timeframe, start_shift, count, rates);
   return (copied == count);
}

bool MagiReadIndicatorValue(const int handle,const int shift,double &value)
{
   if(handle == INVALID_HANDLE)
      return false;

   double buffer[];
   ArraySetAsSeries(buffer, true);
   int copied = CopyBuffer(handle, 0, shift, 1, buffer);
   value = (copied > 0 ? buffer[0] : 0.0);
   return (copied > 0);
}

bool MagiReadMA(const string symbol,const ENUM_TIMEFRAMES timeframe,const int period,const int shift,double &value)
{
   int handle = iMA(symbol, timeframe, period, 0, MODE_EMA, PRICE_CLOSE);
   bool ok = MagiReadIndicatorValue(handle, shift, value);
   if(handle != INVALID_HANDLE)
      IndicatorRelease(handle);
   return ok;
}

bool MagiReadRSI(const string symbol,const ENUM_TIMEFRAMES timeframe,const int period,const int shift,double &value)
{
   int handle = iRSI(symbol, timeframe, period, PRICE_CLOSE);
   bool ok = MagiReadIndicatorValue(handle, shift, value);
   if(handle != INVALID_HANDLE)
      IndicatorRelease(handle);
   return ok;
}

string MagiDetectCandlePattern(const MqlRates &bar1,const MqlRates &bar2)
{
   double body1 = MathAbs(bar1.close - bar1.open);
   double range1 = bar1.high - bar1.low;

   if(bar2.close < bar2.open &&
      bar1.close > bar1.open &&
      bar1.close >= bar2.open &&
      bar1.open <= bar2.close)
      return "bullish_engulfing";

   if(bar2.close > bar2.open &&
      bar1.close < bar1.open &&
      bar1.open >= bar2.close &&
      bar1.close <= bar2.open)
      return "bearish_engulfing";

   if(range1 > 0.0 && body1 <= range1 * 0.1)
      return "doji";

   return "none";
}

void MagiDetectStructure(const MqlRates &bar1,const MqlRates &bar2,const MqlRates &bar3,string &market_structure,string &direction)
{
   bool higher_highs = (bar1.high > bar2.high && bar2.high > bar3.high);
   bool higher_lows  = (bar1.low  > bar2.low  && bar2.low  > bar3.low);
   bool lower_highs  = (bar1.high < bar2.high && bar2.high < bar3.high);
   bool lower_lows   = (bar1.low  < bar2.low  && bar2.low  < bar3.low);

   if(higher_highs && higher_lows)
   {
      market_structure = "trend";
      direction = "bullish";
      return;
   }

   if(lower_highs && lower_lows)
   {
      market_structure = "trend";
      direction = "bearish";
      return;
   }

   if(bar1.high > bar2.high && bar1.close > bar2.close)
   {
      market_structure = "breakout";
      direction = "bullish";
      return;
   }

   if(bar1.low < bar2.low && bar1.close < bar2.close)
   {
      market_structure = "breakout";
      direction = "bearish";
      return;
   }

   market_structure = "range";
   direction = "neutral";
}

double MagiComputeRecentRange(const MqlRates &rates[],const int count)
{
   if(count <= 0)
      return 0.0;

   double highest = rates[0].high;
   double lowest  = rates[0].low;

   for(int i = 1; i < count; i++)
   {
      if(rates[i].high > highest)
         highest = rates[i].high;

      if(rates[i].low < lowest)
         lowest = rates[i].low;
   }

   return highest - lowest;
}

void MagiComputeSupportResistance(const MqlRates &rates[],const int count,const double min_distance,double &support1,double &support2,double &resistance1,double &resistance2)
{
   support1 = DBL_MAX;
   support2 = DBL_MAX;
   resistance1 = -DBL_MAX;
   resistance2 = -DBL_MAX;

   for(int i = 0; i < count; i++)
   {
      double low = rates[i].low;
      if(low < support1)
      {
         support2 = support1;
         support1 = low;
      }
      else if(low < support2 && MathAbs(low - support1) > min_distance)
      {
         support2 = low;
      }

      double high = rates[i].high;
      if(high > resistance1)
      {
         resistance2 = resistance1;
         resistance1 = high;
      }
      else if(high > resistance2 && MathAbs(high - resistance1) > min_distance)
      {
         resistance2 = high;
      }
   }

   if(support1 == DBL_MAX) support1 = 0.0;
   if(support2 == DBL_MAX) support2 = 0.0;
   if(resistance1 == -DBL_MAX) resistance1 = 0.0;
   if(resistance2 == -DBL_MAX) resistance2 = 0.0;
}

string MagiDetectMomentum(const double ema20,const double ema50,const double ema200,const double rsi14)
{
   if(ema20 > ema50 && ema50 > ema200 && rsi14 >= 55.0)
      return "bullish";

   if(ema20 < ema50 && ema50 < ema200 && rsi14 <= 45.0)
      return "bearish";

   return "weak";
}

bool MagiLoadTimeframeFeatures(const string symbol,const ENUM_TIMEFRAMES timeframe,MagiTimeframeFeatures &feature,MagiValidationState &validation)
{
   MagiInitializeTimeframeFeature(feature, timeframe);

   MqlRates rates[6];
   if(!MagiCopyRatesClosed(symbol, timeframe, 1, 6, rates))
   {
      MagiValidationAddIssue(validation, StringFormat("No se pudieron leer barras cerradas para %s en %s", symbol, MagiTimeframeToLabel(timeframe)));
      return false;
   }

   feature.bar_time = rates[0].time;
   feature.candle_pattern = MagiDetectCandlePattern(rates[0], rates[1]);
   MagiDetectStructure(rates[0], rates[1], rates[2], feature.market_structure, feature.structure_direction);
   feature.recent_range = MagiComputeRecentRange(rates, 6);

   if(!MagiReadMA(symbol, timeframe, 20, 1, feature.ema_20))
      MagiValidationAddIssue(validation, StringFormat("EMA 20 no disponible para %s en %s", symbol, MagiTimeframeToLabel(timeframe)));

   if(!MagiReadMA(symbol, timeframe, 50, 1, feature.ema_50))
      MagiValidationAddIssue(validation, StringFormat("EMA 50 no disponible para %s en %s", symbol, MagiTimeframeToLabel(timeframe)));

   if(!MagiReadMA(symbol, timeframe, 200, 1, feature.ema_200))
      MagiValidationAddIssue(validation, StringFormat("EMA 200 no disponible para %s en %s", symbol, MagiTimeframeToLabel(timeframe)));

   if(!MagiReadRSI(symbol, timeframe, 14, 1, feature.rsi_14))
      MagiValidationAddIssue(validation, StringFormat("RSI 14 no disponible para %s en %s", symbol, MagiTimeframeToLabel(timeframe)));

   return true;
}

bool MagiLoadAnchorBar(const string symbol,
                       const ENUM_TIMEFRAMES anchor_timeframe,
                       datetime &bar_time,
                       double &open_price,
                       double &high_price,
                       double &low_price,
                       double &close_price,
                       MagiValidationState &validation)
{
   MqlRates rates[1];
   if(!MagiCopyRatesClosed(symbol, anchor_timeframe, 1, 1, rates))
   {
      MagiValidationAddIssue(validation, StringFormat("No se pudo leer la barra ancla cerrada para %s en %s", symbol, MagiTimeframeToLabel(anchor_timeframe)));
      return false;
   }

   bar_time = rates[0].time;
   open_price = rates[0].open;
   high_price = rates[0].high;
   low_price = rates[0].low;
   close_price = rates[0].close;
   return true;
}

void MagiLoadPositionSnapshot(const string symbol,MagiPositionSnapshot &position,MagiValidationState &validation)
{
   MagiInitializePositionSnapshot(position);

   double entry_sum = 0.0;
   double volume_sum = 0.0;
   double pnl_sum = 0.0;
   double sl_value = 0.0;
   double tp_value = 0.0;
   int buy_count = 0;
   int sell_count = 0;

   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0 || !PositionSelectByTicket(ticket))
         continue;

      string position_symbol = PositionGetString(POSITION_SYMBOL);
      if(position_symbol != symbol)
         continue;

      position.has_open_position = true;
      position.open_positions_count++;

      double volume = PositionGetDouble(POSITION_VOLUME);
      entry_sum += PositionGetDouble(POSITION_PRICE_OPEN) * volume;
      volume_sum += volume;
      pnl_sum += PositionGetDouble(POSITION_PROFIT);

      if(position.open_positions_count == 1)
      {
         sl_value = PositionGetDouble(POSITION_SL);
         tp_value = PositionGetDouble(POSITION_TP);
      }

      long position_type = PositionGetInteger(POSITION_TYPE);
      if(position_type == POSITION_TYPE_BUY)
         buy_count++;
      else if(position_type == POSITION_TYPE_SELL)
         sell_count++;
   }

   if(!position.has_open_position)
      return;

   position.floating_pnl = pnl_sum;

   if(volume_sum > 0.0)
      position.entry_price = entry_sum / volume_sum;

   if(position.open_positions_count == 1)
   {
      position.sl = sl_value;
      position.tp = tp_value;
      position.position_type = (buy_count == 1 ? "buy" : "sell");
   }
   else
   {
      position.position_type = (buy_count > 0 && sell_count > 0 ? "mixed" : (buy_count > 0 ? "buy" : "sell"));
      MagiValidationAddIssue(validation, StringFormat("Hay %d posiciones abiertas en %s; SL/TP agregados no se serializan como valores unicos", position.open_positions_count, symbol));
   }
}

bool MagiBuildSnapshot(const string symbol,
                       const ENUM_TIMEFRAMES anchor_timeframe,
                       const ENUM_TIMEFRAMES primary_timeframe,
                       const string source_mode,
                       MagiSnapshot &snapshot)
{
   MagiInitializeSnapshot(snapshot);

   snapshot.symbol = MagiNormalizeSymbol(symbol);
   snapshot.source_mode = source_mode;
   snapshot.anchor_timeframe = MagiTimeframeToLabel(anchor_timeframe);
   snapshot.primary_timeframe = MagiTimeframeToLabel(primary_timeframe);
   snapshot.timestamp = TimeGMT();

   MagiLoadAnchorBar(snapshot.symbol,
                     anchor_timeframe,
                     snapshot.anchor_bar_timestamp,
                     snapshot.anchor_open,
                     snapshot.anchor_high,
                     snapshot.anchor_low,
                     snapshot.anchor_close,
                     snapshot.validation);

   MqlTick tick;
   if(!SymbolInfoTick(snapshot.symbol, tick))
   {
      MagiValidationAddIssue(snapshot.validation, StringFormat("No se pudo leer tick actual para %s", snapshot.symbol));
      return false;
   }

   snapshot.current_price = (tick.bid > 0.0 ? tick.bid : tick.last);
   if(snapshot.current_price <= 0.0)
      MagiValidationAddIssue(snapshot.validation, StringFormat("Precio actual invalido para %s", snapshot.symbol));

   ENUM_TIMEFRAMES feature_timeframes[MAGI_MAX_FEATURE_TFS] = {PERIOD_M15, PERIOD_H1, PERIOD_H4};
   snapshot.feature_count = MAGI_MAX_FEATURE_TFS;

   for(int i = 0; i < MAGI_MAX_FEATURE_TFS; i++)
      MagiLoadTimeframeFeatures(snapshot.symbol, feature_timeframes[i], snapshot.features[i], snapshot.validation);

   int primary_index = -1;
   for(int j = 0; j < snapshot.feature_count; j++)
   {
      if(snapshot.features[j].timeframe == primary_timeframe)
      {
         primary_index = j;
         break;
      }
   }

   if(primary_index == -1)
   {
      MagiValidationAddIssue(snapshot.validation, StringFormat("El timeframe primario %s no esta dentro del set de features", MagiTimeframeToLabel(primary_timeframe)));
      primary_index = 1;
   }

   snapshot.bar_timestamp = snapshot.features[primary_index].bar_time;
   snapshot.snapshot_id = MagiBuildSnapshotId(snapshot.symbol, snapshot.anchor_bar_timestamp, snapshot.anchor_timeframe, source_mode);
   snapshot.market_structure = snapshot.features[primary_index].market_structure;
   snapshot.structure_direction = snapshot.features[primary_index].structure_direction;
   snapshot.ema_20 = snapshot.features[primary_index].ema_20;
   snapshot.ema_50 = snapshot.features[primary_index].ema_50;
   snapshot.ema_200 = snapshot.features[primary_index].ema_200;
   snapshot.rsi_14 = snapshot.features[primary_index].rsi_14;
   snapshot.recent_range = snapshot.features[primary_index].recent_range;
   snapshot.momentum = MagiDetectMomentum(snapshot.ema_20, snapshot.ema_50, snapshot.ema_200, snapshot.rsi_14);

   MqlRates primary_rates[20];
   if(MagiCopyRatesClosed(snapshot.symbol, primary_timeframe, 1, 20, primary_rates))
   {
      double support1 = 0.0, support2 = 0.0, resistance1 = 0.0, resistance2 = 0.0;
      MagiComputeSupportResistance(primary_rates, 20, MagiSymbolPoint(snapshot.symbol), support1, support2, resistance1, resistance2);

      if(support1 > 0.0) snapshot.support_levels[snapshot.support_count++] = support1;
      if(support2 > 0.0) snapshot.support_levels[snapshot.support_count++] = support2;
      if(resistance1 > 0.0) snapshot.resistance_levels[snapshot.resistance_count++] = resistance1;
      if(resistance2 > 0.0) snapshot.resistance_levels[snapshot.resistance_count++] = resistance2;
   }
   else
   {
      MagiValidationAddIssue(snapshot.validation, StringFormat("No se pudieron calcular soportes y resistencias para %s", snapshot.symbol));
   }

   MagiLoadPositionSnapshot(snapshot.symbol, snapshot.position, snapshot.validation);

   if(snapshot.bar_timestamp == 0)
      MagiValidationAddIssue(snapshot.validation, StringFormat("No se pudo determinar la barra cerrada primaria para %s", snapshot.symbol));

   if(snapshot.anchor_bar_timestamp == 0)
      MagiValidationAddIssue(snapshot.validation, StringFormat("No se pudo determinar la barra cerrada ancla para %s", snapshot.symbol));

   if(snapshot.anchor_high < snapshot.anchor_low ||
      snapshot.anchor_open > snapshot.anchor_high ||
      snapshot.anchor_open < snapshot.anchor_low ||
      snapshot.anchor_close > snapshot.anchor_high ||
      snapshot.anchor_close < snapshot.anchor_low)
   {
      MagiValidationAddIssue(snapshot.validation, StringFormat("OHLC ancla inconsistente para %s", snapshot.symbol));
   }

   if(!MagiIsValidNumber(snapshot.ema_20) ||
      !MagiIsValidNumber(snapshot.ema_50) ||
      !MagiIsValidNumber(snapshot.ema_200) ||
      !MagiIsValidNumber(snapshot.rsi_14))
   {
      MagiValidationAddIssue(snapshot.validation, StringFormat("Indicadores invalidos para %s", snapshot.symbol));
   }

   return snapshot.validation.is_valid;
}

#endif
