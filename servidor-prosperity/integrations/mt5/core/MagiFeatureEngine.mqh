#ifndef __MAGI_FEATURE_ENGINE_MQH__
#define __MAGI_FEATURE_ENGINE_MQH__

#property strict

#include "MagiCommon.mqh"
#include "MagiGasparContext.mqh"

int g_magi_mtf_debug_snapshots_logged = 0;
int g_magi_mtf_debug_limit = 20;

bool MagiCopyRatesClosed(const string symbol,const ENUM_TIMEFRAMES timeframe,const int start_shift,const int count,MqlRates &rates[])
{
   ArraySetAsSeries(rates, true);
   int copied = CopyRates(symbol, timeframe, start_shift, count, rates);
   return (copied == count);
}

bool MagiReadTimeframeAvailability(const string symbol,
                                   const ENUM_TIMEFRAMES timeframe,
                                   int &bars_available,
                                   datetime &oldest_bar_time,
                                   datetime &newest_bar_time,
                                   string &failure_reason)
{
   bars_available = Bars(symbol, timeframe);
   oldest_bar_time = 0;
   newest_bar_time = 0;
   failure_reason = "";

   if(bars_available <= 0)
   {
      failure_reason = "Bars() no devolvio historial disponible";
      return false;
   }

   newest_bar_time = iTime(symbol, timeframe, 0);
   oldest_bar_time = iTime(symbol, timeframe, bars_available - 1);

   if(oldest_bar_time <= 0 || newest_bar_time <= 0)
   {
      failure_reason = StringFormat("iTime no resolvio rango temporal con Bars=%d", bars_available);
      return false;
   }

   return true;
}

bool MagiAvailabilityCoversAnchor(const ENUM_TIMEFRAMES timeframe,
                                  const datetime anchor_bar_time,
                                  const int bars_available,
                                  const datetime oldest_bar_time,
                                  const datetime newest_bar_time,
                                  string &failure_reason)
{
   failure_reason = "";

   int seconds = PeriodSeconds(timeframe);
   if(seconds <= 0 || anchor_bar_time <= 0)
   {
      failure_reason = "timeframe o anchor invalidos";
      return false;
   }

   if(bars_available <= 0 || oldest_bar_time <= 0 || newest_bar_time <= 0)
   {
      failure_reason = "rango temporal MTF no disponible";
      return false;
   }

   datetime required_oldest = anchor_bar_time - seconds * 2;
   datetime latest_acceptable_open = anchor_bar_time - seconds;
   datetime newest_closed_time = newest_bar_time + seconds;

   if(oldest_bar_time > latest_acceptable_open)
   {
      failure_reason = StringFormat("historial empieza despues de la ultima vela cerrada requerida oldest=%s required_latest_open=%s",
                                    MagiDateTimeToIso(oldest_bar_time),
                                    MagiDateTimeToIso(latest_acceptable_open));
      return false;
   }

   if(newest_closed_time < latest_acceptable_open)
   {
      failure_reason = StringFormat("historial termina demasiado atras newest=%s newest_close=%s required_latest_open=%s",
                                    MagiDateTimeToIso(newest_bar_time),
                                    MagiDateTimeToIso(newest_closed_time),
                                    MagiDateTimeToIso(latest_acceptable_open));
      return false;
   }

   if(oldest_bar_time > required_oldest && newest_bar_time < latest_acceptable_open)
   {
      failure_reason = StringFormat("rango disponible no cubre ventana anchor oldest=%s newest=%s required_start=%s required_latest_open=%s",
                                    MagiDateTimeToIso(oldest_bar_time),
                                    MagiDateTimeToIso(newest_bar_time),
                                    MagiDateTimeToIso(required_oldest),
                                    MagiDateTimeToIso(latest_acceptable_open));
      return false;
   }

   return true;
}

bool MagiFindAlignedClosedBar(const string symbol,
                              const ENUM_TIMEFRAMES timeframe,
                              const datetime anchor_bar_time,
                              MqlRates &selected_bar,
                              int &anchor_ibar_shift,
                              int &selected_shift,
                              int &bars_available,
                              datetime &oldest_bar_time,
                              datetime &newest_bar_time,
                              string &data_source_status,
                              double &age_minutes,
                              string &failure_reason)
{
   failure_reason = "";
   anchor_ibar_shift = iBarShift(symbol, timeframe, anchor_bar_time, false);
   selected_shift = -1;
   bars_available = 0;
   oldest_bar_time = 0;
   newest_bar_time = 0;
   data_source_status = "PENDING";
   age_minutes = -1.0;

   int seconds = PeriodSeconds(timeframe);
   if(seconds <= 0 || anchor_bar_time <= 0)
   {
      failure_reason = "timeframe o anchor invalidos";
      data_source_status = "ALIGNMENT_ERROR";
      return false;
   }

   string availability_reason = "";
   if(!MagiReadTimeframeAvailability(symbol, timeframe, bars_available, oldest_bar_time, newest_bar_time, availability_reason))
   {
      failure_reason = availability_reason;
      data_source_status = "INSUFFICIENT_HISTORY";
      return false;
   }

   if(!MagiAvailabilityCoversAnchor(timeframe, anchor_bar_time, bars_available, oldest_bar_time, newest_bar_time, availability_reason))
   {
      failure_reason = availability_reason;
      data_source_status = "INSUFFICIENT_HISTORY";
      return false;
   }

   datetime window_start = anchor_bar_time - seconds * 4;
   MqlRates window_rates[];
   ArraySetAsSeries(window_rates, false);
   int copied = CopyRates(symbol, timeframe, window_start, anchor_bar_time, window_rates);
   if(copied <= 0)
   {
      failure_reason = StringFormat("sin velas en ventana temporal %s..%s", MagiDateTimeToIso(window_start), MagiDateTimeToIso(anchor_bar_time));
      data_source_status = "INSUFFICIENT_HISTORY";
      return false;
   }

   bool found = false;
   datetime best_open = 0;
   for(int i = 0; i < copied; i++)
   {
      datetime open_time = window_rates[i].time;
      datetime close_time = open_time + seconds;
      double candidate_age = ((double)(anchor_bar_time - close_time)) / 60.0;

      if(open_time <= anchor_bar_time &&
         close_time <= anchor_bar_time &&
         candidate_age >= -0.0001 &&
         candidate_age <= ((double)seconds / 60.0) + 0.0001 &&
         (!found || open_time > best_open))
      {
         selected_bar = window_rates[i];
         best_open = open_time;
         age_minutes = candidate_age;
         found = true;
      }
   }

   if(!found)
   {
      failure_reason = StringFormat("no hay vela cerrada dentro de 0..%.2f minutos previos al anchor", (double)seconds / 60.0);
      data_source_status = "ALIGNMENT_ERROR";
      return false;
   }

   selected_shift = iBarShift(symbol, timeframe, selected_bar.time, true);
   if(selected_shift < 0)
   {
      failure_reason = "iBarShift exact no resolvio la vela seleccionada";
      data_source_status = "ALIGNMENT_ERROR";
      return false;
   }

   data_source_status = "OK";
   return true;
}

bool MagiCopyRatesAlignedClosed(const string symbol,
                                const ENUM_TIMEFRAMES timeframe,
                                const datetime anchor_bar_time,
                                const int count,
                                MqlRates &rates[],
                                int &shift_used,
                                int &anchor_ibar_shift,
                                int &selected_array_index,
                                int &copied_array_size,
                                bool &rates_array_as_series,
                                int &bars_available,
                                datetime &oldest_bar_time,
                                datetime &newest_bar_time,
                                string &data_source_status,
                                double &age_minutes,
                                string &failure_reason)
{
   selected_array_index = -1;
   copied_array_size = 0;
   rates_array_as_series = false;

   MqlRates selected_bar;
   if(!MagiFindAlignedClosedBar(symbol, timeframe, anchor_bar_time, selected_bar, anchor_ibar_shift, shift_used, bars_available, oldest_bar_time, newest_bar_time, data_source_status, age_minutes, failure_reason))
      return false;

   int seconds = PeriodSeconds(timeframe);
   if(seconds <= 0)
   {
      failure_reason = "timeframe invalido al cargar ventana de velas";
      data_source_status = "ALIGNMENT_ERROR";
      return false;
   }

   int selected_shift = iBarShift(symbol, timeframe, selected_bar.time, true);
   if(selected_shift < 0 || selected_shift != shift_used)
   {
      failure_reason = StringFormat("selected_shift invalido: esperado=%d recalculado=%d selected_bar_time=%s",
                                    shift_used,
                                    selected_shift,
                                    MagiDateTimeToIso(selected_bar.time));
      data_source_status = "ALIGNMENT_ERROR";
      return false;
   }

   int requested_count = count * 8;
   if(requested_count < count + 16)
      requested_count = count + 16;

   MqlRates raw_rates[];
   ArraySetAsSeries(raw_rates, false);
   int copied = CopyRates(symbol, timeframe, selected_shift, requested_count, raw_rates);
   copied_array_size = copied;
   rates_array_as_series = ArrayGetAsSeries(raw_rates);

   if(copied <= 0)
   {
      failure_reason = StringFormat("CopyRates no pudo reconstruir buffer historico desde selected_shift=%d selected_bar_time=%s requested=%d",
                                    selected_shift,
                                    MagiDateTimeToIso(selected_bar.time),
                                    requested_count);
      data_source_status = "INSUFFICIENT_HISTORY";
      return false;
   }

   for(int raw = 0; raw < copied; raw++)
   {
      if(raw_rates[raw].time == selected_bar.time)
      {
         selected_array_index = raw;
         break;
      }
   }

   if(selected_array_index < 0)
   {
      failure_reason = StringFormat("CopyRates por selected_shift no incluyo selected_bar_time=%s selected_shift=%d array_size=%d as_series=%s",
                                    MagiDateTimeToIso(selected_bar.time),
                                    selected_shift,
                                    copied,
                                    rates_array_as_series ? "true" : "false");
      data_source_status = "ALIGNMENT_ERROR";
      return false;
   }

   MqlRates ordered[];
   ArrayResize(ordered, 0);
   for(int i = 0; i < copied; i++)
   {
      if(raw_rates[i].time > selected_bar.time)
         continue;

      int next = ArraySize(ordered);
      ArrayResize(ordered, next + 1);
      ordered[next] = raw_rates[i];
   }

   int ordered_count = ArraySize(ordered);
   for(int a = 0; a < ordered_count - 1; a++)
   {
      for(int b = a + 1; b < ordered_count; b++)
      {
         if(ordered[b].time > ordered[a].time)
         {
            MqlRates tmp = ordered[a];
            ordered[a] = ordered[b];
            ordered[b] = tmp;
         }
      }
   }

   if(ordered_count < count)
   {
      failure_reason = StringFormat("CopyRates por selected_shift solo produjo %d velas <= selected_bar_time=%s; requeridas=%d selected_shift=%d array_size=%d",
                                    ordered_count,
                                    MagiDateTimeToIso(selected_bar.time),
                                    count,
                                    selected_shift,
                                    copied);
      data_source_status = "INSUFFICIENT_HISTORY";
      return false;
   }

   if(ordered[0].time != selected_bar.time)
   {
      failure_reason = StringFormat("vela seleccionada inconsistente tras ordenar: selected=%s ordered0=%s selected_array_index=%d array_size=%d as_series=%s",
                                    MagiDateTimeToIso(selected_bar.time),
                                    MagiDateTimeToIso(ordered[0].time),
                                    selected_array_index,
                                    copied,
                                    rates_array_as_series ? "true" : "false");
      data_source_status = "ALIGNMENT_ERROR";
      return false;
   }

   ArraySetAsSeries(rates, false);
   for(int out = 0; out < count; out++)
      rates[out] = ordered[out];

   rates_array_as_series = ArrayGetAsSeries(rates);
   return true;
}

double MagiClosedBarAgeMinutes(const datetime anchor_bar_time,const ENUM_TIMEFRAMES timeframe,const datetime bar_open_time)
{
   int seconds = PeriodSeconds(timeframe);
   if(anchor_bar_time <= 0 || bar_open_time <= 0 || seconds <= 0)
      return -1.0;

   double age_seconds = (double)(anchor_bar_time - (bar_open_time + seconds));
   return age_seconds / 60.0;
}

double MagiMaxExpectedAgeMinutes(const ENUM_TIMEFRAMES timeframe)
{
   int seconds = PeriodSeconds(timeframe);
   return seconds > 0 ? (double)seconds / 60.0 : 0.0;
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

double MagiComputeSpreadPips(const string symbol,const MqlTick &tick)
{
   double point = MagiSymbolPoint(symbol);
   if(point <= 0.0 || tick.ask <= 0.0 || tick.bid <= 0.0)
      return 0.0;

   double pip_size = point;
   int digits = MagiSymbolDigits(symbol);
   if(digits == 3 || digits == 5)
      pip_size = point * 10.0;

   return (tick.ask - tick.bid) / pip_size;
}

string MagiBuildAllowedActions(const MagiPositionSnapshot &position)
{
   if(position.has_open_position)
      return "[\"maintain\",\"move_sl\",\"break_even\",\"close\"]";

   return "[\"open\",\"hold\"]";
}

void MagiLoadOperationalContext(MagiSnapshot &snapshot,const MqlTick &tick)
{
   snapshot.spread_pips = MagiComputeSpreadPips(snapshot.symbol, tick);
   snapshot.active_session = MagiGasparActiveSession(snapshot.anchor_bar_timestamp);
   snapshot.account_balance = AccountInfoDouble(ACCOUNT_BALANCE);
   snapshot.account_equity = AccountInfoDouble(ACCOUNT_EQUITY);
   snapshot.daily_drawdown_percent = 0.0;
   snapshot.risk_percent_per_trade = 0.0;
   snapshot.allowed_actions = MagiBuildAllowedActions(snapshot.position);
   snapshot.operational_notes = "daily_drawdown_percent,risk_percent_per_trade,news_context pending";
}

bool MagiLoadTimeframeFeatures(const string symbol,
                               const ENUM_TIMEFRAMES timeframe,
                               const datetime anchor_bar_time,
                               MagiTimeframeFeatures &feature,
                               MagiValidationState &validation)
{
   MagiInitializeTimeframeFeature(feature, timeframe);

   MqlRates rates[6];
   int shift_used = -1;
   int anchor_ibar_shift = -1;
   int selected_array_index = -1;
   int copied_array_size = 0;
   bool rates_array_as_series = false;
   int bars_available = 0;
   datetime oldest_bar_time = 0;
   datetime newest_bar_time = 0;
   string data_source_status = "PENDING";
   double age_minutes = -1.0;
   string alignment_reason = "";
   if(!MagiCopyRatesAlignedClosed(symbol, timeframe, anchor_bar_time, 6, rates, shift_used, anchor_ibar_shift, selected_array_index, copied_array_size, rates_array_as_series, bars_available, oldest_bar_time, newest_bar_time, data_source_status, age_minutes, alignment_reason))
   {
      feature.anchor_ibar_shift = anchor_ibar_shift;
      feature.selected_shift = shift_used;
      feature.selected_array_index = selected_array_index;
      feature.copied_array_size = copied_array_size;
      feature.rates_array_as_series = rates_array_as_series;
      feature.bars_available = bars_available;
      feature.oldest_bar_time = oldest_bar_time;
      feature.newest_bar_time = newest_bar_time;
      feature.data_source_status = data_source_status;
      feature.age_minutes = age_minutes;
      feature.alignment_status = "error";
      feature.alignment_warning = alignment_reason;
      MagiValidationAddIssue(validation, StringFormat("No se pudieron leer barras cerradas alineadas para %s en %s: %s", symbol, MagiTimeframeToLabel(timeframe), alignment_reason));
      return false;
   }

   feature.bar_time = rates[0].time;
   feature.bar_close_time = rates[0].time + PeriodSeconds(timeframe);
   feature.age_minutes = age_minutes;
   feature.anchor_ibar_shift = anchor_ibar_shift;
   feature.selected_shift = shift_used;
   feature.selected_array_index = selected_array_index;
   feature.copied_array_size = copied_array_size;
   feature.rates_array_as_series = rates_array_as_series;
   feature.bars_available = bars_available;
   feature.oldest_bar_time = oldest_bar_time;
   feature.newest_bar_time = newest_bar_time;
   feature.data_source_status = data_source_status;
   feature.alignment_status = "ok";
   feature.alignment_warning = "";
   feature.candle_pattern = MagiDetectCandlePattern(rates[0], rates[1]);
   MagiDetectStructure(rates[0], rates[1], rates[2], feature.market_structure, feature.structure_direction);
   feature.recent_range = MagiComputeRecentRange(rates, 6);

   if(!MagiReadMA(symbol, timeframe, 20, shift_used, feature.ema_20))
      MagiValidationAddIssue(validation, StringFormat("EMA 20 no disponible para %s en %s", symbol, MagiTimeframeToLabel(timeframe)));

   if(!MagiReadMA(symbol, timeframe, 50, shift_used, feature.ema_50))
      MagiValidationAddIssue(validation, StringFormat("EMA 50 no disponible para %s en %s", symbol, MagiTimeframeToLabel(timeframe)));

   if(!MagiReadMA(symbol, timeframe, 200, shift_used, feature.ema_200))
      MagiValidationAddIssue(validation, StringFormat("EMA 200 no disponible para %s en %s", symbol, MagiTimeframeToLabel(timeframe)));

   if(!MagiReadRSI(symbol, timeframe, 14, shift_used, feature.rsi_14))
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

   int anchor_seconds = PeriodSeconds(anchor_timeframe);
   bar_time = rates[0].time + (anchor_seconds > 0 ? anchor_seconds : 0);
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

   ENUM_TIMEFRAMES feature_timeframes[MAGI_MAX_FEATURE_TFS] = {PERIOD_M15, PERIOD_H1, PERIOD_H4, PERIOD_D1};
   snapshot.feature_count = MAGI_MAX_FEATURE_TFS;

   for(int i = 0; i < MAGI_MAX_FEATURE_TFS; i++)
      MagiLoadTimeframeFeatures(snapshot.symbol, feature_timeframes[i], snapshot.anchor_bar_timestamp, snapshot.features[i], snapshot.validation);

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
   int primary_rates_shift = -1;
   int primary_anchor_shift = -1;
   int primary_selected_array_index = -1;
   int primary_copied_array_size = 0;
   bool primary_rates_array_as_series = false;
   int primary_bars_available = 0;
   datetime primary_oldest_bar = 0;
   datetime primary_newest_bar = 0;
   string primary_data_source_status = "PENDING";
   double primary_age = -1.0;
   string primary_alignment_reason = "";
   if(MagiCopyRatesAlignedClosed(snapshot.symbol, primary_timeframe, snapshot.anchor_bar_timestamp, 20, primary_rates, primary_rates_shift, primary_anchor_shift, primary_selected_array_index, primary_copied_array_size, primary_rates_array_as_series, primary_bars_available, primary_oldest_bar, primary_newest_bar, primary_data_source_status, primary_age, primary_alignment_reason))
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
      MagiValidationAddIssue(snapshot.validation, StringFormat("No se pudieron calcular soportes y resistencias alineados para %s: %s", snapshot.symbol, primary_alignment_reason));
   }

   MagiLoadPositionSnapshot(snapshot.symbol, snapshot.position, snapshot.validation);
   MagiLoadOperationalContext(snapshot, tick);

   MagiBuildGasparContext(snapshot.symbol,
                          anchor_timeframe,
                          snapshot.anchor_bar_timestamp,
                          snapshot.anchor_close,
                          snapshot.snapshot_id,
                          20,
                          0.15,
                          snapshot.gaspar_context);

   snapshot.mtf_alignment_status = "ok";
   snapshot.mtf_alignment_warnings = "";
   snapshot.mtf_data_source_status = "OK";
   for(int k = 0; k < snapshot.feature_count; k++)
   {
      if(snapshot.features[k].alignment_status != "ok")
      {
         snapshot.mtf_alignment_status = "warning";
         if(snapshot.mtf_alignment_warnings != "")
            snapshot.mtf_alignment_warnings += " | ";
         snapshot.mtf_alignment_warnings += snapshot.features[k].timeframe_label + ": " + snapshot.features[k].alignment_warning;
      }

      if(snapshot.features[k].data_source_status == "INSUFFICIENT_HISTORY")
      {
         snapshot.mtf_data_source_status = "INSUFFICIENT_HISTORY";
      }
      else if(snapshot.features[k].data_source_status == "ALIGNMENT_ERROR" &&
              snapshot.mtf_data_source_status != "INSUFFICIENT_HISTORY")
      {
         snapshot.mtf_data_source_status = "ALIGNMENT_ERROR";
      }
      else if(snapshot.features[k].data_source_status != "OK" &&
              snapshot.mtf_data_source_status == "OK")
      {
         snapshot.mtf_data_source_status = "ALIGNMENT_ERROR";
      }
   }

   if(g_magi_mtf_debug_snapshots_logged < g_magi_mtf_debug_limit)
   {
      for(int dbg = 0; dbg < snapshot.feature_count; dbg++)
      {
         MagiTimeframeFeatures feature = snapshot.features[dbg];
         MagiLog("DEBUG",
                 snapshot.symbol,
                 StringFormat("MTF diagnostic snapshot=%s anchor=%s tf=%s bars_available=%d oldest_bar=%s newest_bar=%s iBarShift=%d selected_shift=%d selected_array_index=%d array_size=%d array_as_series=%s selected_bar=%s rates_used=%s selected_close=%s age_minutes=%.2f data_source_status=%s alignment_status=%s reason=%s",
                              snapshot.snapshot_id,
                              MagiDateTimeToIso(snapshot.anchor_bar_timestamp),
                              feature.timeframe_label,
                              feature.bars_available,
                              MagiDateTimeToIso(feature.oldest_bar_time),
                              MagiDateTimeToIso(feature.newest_bar_time),
                              feature.anchor_ibar_shift,
                              feature.selected_shift,
                              feature.selected_array_index,
                              feature.copied_array_size,
                              feature.rates_array_as_series ? "true" : "false",
                              MagiDateTimeToIso(feature.bar_time),
                              MagiDateTimeToIso(feature.bar_time),
                              MagiDateTimeToIso(feature.bar_close_time),
                              feature.age_minutes,
                              feature.data_source_status,
                              feature.alignment_status,
                              feature.alignment_warning));
      }
      g_magi_mtf_debug_snapshots_logged++;
   }

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
