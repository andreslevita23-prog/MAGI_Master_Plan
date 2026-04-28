#ifndef __MAGI_GASPAR_CONTEXT_MQH__
#define __MAGI_GASPAR_CONTEXT_MQH__

#property strict

#include "MagiCommon.mqh"

string MagiGasparStructureFromRates(const MqlRates &rates[])
{
   bool rising = rates[0].high > rates[1].high && rates[1].high > rates[2].high &&
                 rates[0].low > rates[1].low && rates[1].low > rates[2].low;
   bool falling = rates[0].high < rates[1].high && rates[1].high < rates[2].high &&
                  rates[0].low < rates[1].low && rates[1].low < rates[2].low;

   if(rising)
      return "bullish";
   if(falling)
      return "bearish";
   return "range";
}

string MagiGasparProposedDirection(const string h4_structure,const string d1_structure)
{
   if(d1_structure == "bullish" && h4_structure != "bearish")
      return "BUY";
   if(d1_structure == "bearish" && h4_structure != "bullish")
      return "SELL";
   return "NEUTRAL";
}

string MagiGasparDirectionalAlignment(const string proposed_direction,const string h4_structure,const string d1_structure)
{
   if(proposed_direction == "BUY" && d1_structure == "bullish" && h4_structure != "bearish")
      return "aligned";
   if(proposed_direction == "SELL" && d1_structure == "bearish" && h4_structure != "bullish")
      return "aligned";
   if(proposed_direction == "NEUTRAL")
      return "neutral";
   return "contradictory";
}

string MagiGasparActiveSession(const datetime bar_time)
{
   MqlDateTime parts;
   TimeToStruct(bar_time, parts);
   int hour = parts.hour;

   if(hour >= 12 && hour < 16)
      return "overlap";
   if(hour >= 7 && hour < 16)
      return "london";
   if(hour >= 13 && hour < 22)
      return "new_york";
   if(hour >= 0 && hour < 7)
      return "asia";
   return "inactive";
}

string MagiGasparDayOfWeekName(const datetime bar_time)
{
   MqlDateTime parts;
   TimeToStruct(bar_time, parts);

   if(parts.day_of_week == 1) return "monday";
   if(parts.day_of_week == 2) return "tuesday";
   if(parts.day_of_week == 3) return "wednesday";
   if(parts.day_of_week == 4) return "thursday";
   if(parts.day_of_week == 5) return "friday";
   return "inactive";
}

string MagiGasparH4CandlePattern(const MqlRates &bar,const MqlRates &previous)
{
   double range = bar.high - bar.low;
   double body = MathAbs(bar.close - bar.open);

   if(range > 0.0 && body <= range * 0.35)
   {
      double upper = bar.high - MathMax(bar.open, bar.close);
      double lower = MathMin(bar.open, bar.close) - bar.low;
      if(upper >= range * 0.45 || lower >= range * 0.45)
         return "rejection";
   }

   bool bullish = previous.close < previous.open && bar.close > bar.open &&
                  bar.close >= previous.open && bar.open <= previous.close;
   bool bearish = previous.close > previous.open && bar.close < bar.open &&
                  bar.open >= previous.close && bar.close <= previous.open;
   if(bullish || bearish)
      return "engulfing";

   if(bar.high <= previous.high && bar.low >= previous.low)
      return "inside";

   return "none";
}

void MagiGasparD1Levels(const MqlRates &rates[],const int count,double &support,double &resistance)
{
   support = rates[0].low;
   resistance = rates[0].high;

   for(int i = 1; i < count; i++)
   {
      if(rates[i].low < support)
         support = rates[i].low;
      if(rates[i].high > resistance)
         resistance = rates[i].high;
   }
}

double MagiGasparAverageDailyTrueRange(const MqlRates &rates[],const int count,const int lookback_bars)
{
   double sum = 0.0;
   int usable = MathMin(count - 1, lookback_bars);

   for(int i = 0; i < usable; i++)
   {
      double high_low = rates[i].high - rates[i].low;
      double high_close = MathAbs(rates[i].high - rates[i + 1].close);
      double low_close = MathAbs(rates[i].low - rates[i + 1].close);
      sum += MathMax(high_low, MathMax(high_close, low_close));
   }

   return usable > 0 ? sum / usable : 0.0;
}

bool MagiGasparFindAlignedClosedBar(const string symbol,
                                    const ENUM_TIMEFRAMES timeframe,
                                    const datetime anchor_bar_time,
                                    MqlRates &selected_bar,
                                    int &selected_shift,
                                    double &age_minutes,
                                    string &failure_reason)
{
   selected_shift = -1;
   age_minutes = -1.0;
   failure_reason = "";

   int seconds = PeriodSeconds(timeframe);
   if(seconds <= 0 || anchor_bar_time <= 0)
   {
      failure_reason = "timeframe o anchor invalidos";
      return false;
   }

   datetime window_start = anchor_bar_time - seconds * 4;
   MqlRates window_rates[];
   ArraySetAsSeries(window_rates, false);
   int copied = CopyRates(symbol, timeframe, window_start, anchor_bar_time, window_rates);
   if(copied <= 0)
   {
      failure_reason = StringFormat("sin velas en ventana temporal %s..%s", MagiDateTimeToIso(window_start), MagiDateTimeToIso(anchor_bar_time));
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
      return false;
   }

   selected_shift = iBarShift(symbol, timeframe, selected_bar.time, true);
   if(selected_shift < 0)
   {
      failure_reason = "iBarShift exact no resolvio la vela seleccionada";
      return false;
   }

   return true;
}

bool MagiGasparCopyRatesAlignedClosed(const string symbol,
                                      const ENUM_TIMEFRAMES timeframe,
                                      const datetime anchor_bar_time,
                                      const int count,
                                      MqlRates &rates[],
                                      double &age_minutes,
                                      string &failure_reason)
{
   MqlRates selected_bar;
   int shift = -1;
   if(!MagiGasparFindAlignedClosedBar(symbol, timeframe, anchor_bar_time, selected_bar, shift, age_minutes, failure_reason))
      return false;

   int seconds = PeriodSeconds(timeframe);
   if(seconds <= 0)
   {
      failure_reason = "timeframe invalido al cargar ventana Gaspar";
      return false;
   }

   int selected_shift = iBarShift(symbol, timeframe, selected_bar.time, true);
   if(selected_shift < 0 || selected_shift != shift)
   {
      failure_reason = StringFormat("selected_shift Gaspar invalido: esperado=%d recalculado=%d selected_bar_time=%s",
                                    shift,
                                    selected_shift,
                                    MagiDateTimeToIso(selected_bar.time));
      return false;
   }

   int requested_count = count * 8;
   if(requested_count < count + 16)
      requested_count = count + 16;

   MqlRates raw_rates[];
   ArraySetAsSeries(raw_rates, false);
   int copied = CopyRates(symbol, timeframe, selected_shift, requested_count, raw_rates);
   if(copied <= 0)
   {
      failure_reason = StringFormat("CopyRates no pudo reconstruir buffer Gaspar desde selected_shift=%d selected_bar_time=%s requested=%d",
                                    selected_shift,
                                    MagiDateTimeToIso(selected_bar.time),
                                    requested_count);
      return false;
   }

   int selected_array_index = -1;
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
      failure_reason = StringFormat("CopyRates Gaspar por selected_shift no incluyo selected_bar_time=%s selected_shift=%d array_size=%d as_series=%s",
                                    MagiDateTimeToIso(selected_bar.time),
                                    selected_shift,
                                    copied,
                                    ArrayGetAsSeries(raw_rates) ? "true" : "false");
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
      failure_reason = StringFormat("CopyRates Gaspar por selected_shift solo produjo %d velas <= selected_bar_time=%s; requeridas=%d selected_shift=%d array_size=%d",
                                    ordered_count,
                                    MagiDateTimeToIso(selected_bar.time),
                                    count,
                                    selected_shift,
                                    copied);
      return false;
   }

   if(ordered[0].time != selected_bar.time)
   {
      failure_reason = StringFormat("vela Gaspar inconsistente tras ordenar: selected=%s ordered0=%s selected_array_index=%d array_size=%d as_series=%s",
                                    MagiDateTimeToIso(selected_bar.time),
                                    MagiDateTimeToIso(ordered[0].time),
                                    selected_array_index,
                                    copied,
                                    ArrayGetAsSeries(raw_rates) ? "true" : "false");
      return false;
   }

   ArraySetAsSeries(rates, false);
   for(int out = 0; out < count; out++)
      rates[out] = ordered[out];

   return true;
}

double MagiGasparClosedBarAgeMinutes(const datetime anchor_bar_time,const ENUM_TIMEFRAMES timeframe,const datetime bar_open_time)
{
   int seconds = PeriodSeconds(timeframe);
   if(anchor_bar_time <= 0 || bar_open_time <= 0 || seconds <= 0)
      return -1.0;

   return ((double)(anchor_bar_time - (bar_open_time + seconds))) / 60.0;
}

bool MagiBuildGasparContext(const string symbol,
                            const ENUM_TIMEFRAMES anchor_timeframe,
                            const datetime anchor_bar_time,
                            const double anchor_close,
                            const string context_id,
                            const int d1_lookback_bars,
                            const double near_level_pct,
                            MagiGasparContext &context)
{
   MagiInitializeGasparContext(context);

   context.symbol = MagiNormalizeSymbol(symbol);
   context.timestamp = anchor_bar_time;
   context.anchor_timeframe = MagiTimeframeToLabel(anchor_timeframe);
   context.context_id = context_id;
   context.proposed_direction_source = "fallback_h4_d1_shadow";

   MqlRates h4[4];
   string h4_failure = "";
   if(!MagiGasparCopyRatesAlignedClosed(context.symbol, PERIOD_H4, anchor_bar_time, 4, h4, context.h4_age_minutes, h4_failure))
   {
      context.data_quality_flags = "missing_or_misaligned_h4_rates:" + h4_failure;
      return false;
   }

   MqlRates d1[];
   int d1_count = d1_lookback_bars + 2;
   ArrayResize(d1, d1_count);
   string d1_failure = "";
   if(!MagiGasparCopyRatesAlignedClosed(context.symbol, PERIOD_D1, anchor_bar_time, d1_count, d1, context.d1_age_minutes, d1_failure))
   {
      context.data_quality_flags = "missing_or_misaligned_d1_rates:" + d1_failure;
      return false;
   }

   context.h4_bar_timestamp = h4[0].time;
   context.d1_bar_timestamp = d1[0].time;
   context.h4_structure = MagiGasparStructureFromRates(h4);
   context.d1_structure = MagiGasparStructureFromRates(d1);
   context.proposed_direction = MagiGasparProposedDirection(context.h4_structure, context.d1_structure);
   context.directional_alignment = MagiGasparDirectionalAlignment(context.proposed_direction, context.h4_structure, context.d1_structure);

   double support = 0.0;
   double resistance = 0.0;
   MagiGasparD1Levels(d1, d1_lookback_bars, support, resistance);

   double close_price = anchor_close;
   double point = MagiSymbolPoint(context.symbol);
   double d1_range = MathMax(resistance - support, point);
   context.distance_to_d1_support = MathMax(0.0, close_price - support);
   context.distance_to_d1_resistance = MathMax(0.0, resistance - close_price);
   context.position_in_d1_range = MathMax(0.0, MathMin(1.0, (close_price - support) / d1_range));
   context.near_key_level = context.distance_to_d1_support <= d1_range * near_level_pct ||
                            context.distance_to_d1_resistance <= d1_range * near_level_pct;

   double avg_daily_range = MagiGasparAverageDailyTrueRange(d1, d1_count, d1_lookback_bars);
   double current_d1_range = d1[0].high - d1[0].low;
   double daily_consumed_raw = avg_daily_range > 0.0 ? current_d1_range / avg_daily_range : 0.0;
   context.daily_atr_consumed_pct = MathMax(0.0, MathMin(1.0, daily_consumed_raw));
   context.available_range_to_next_level = (context.proposed_direction == "SELL")
      ? context.distance_to_d1_support
      : (context.proposed_direction == "BUY" ? context.distance_to_d1_resistance : MathMin(context.distance_to_d1_support, context.distance_to_d1_resistance));
   context.h4_candle_pattern = MagiGasparH4CandlePattern(h4[0], h4[1]);
   context.active_session = MagiGasparActiveSession(anchor_bar_time);
   context.day_of_week = MagiGasparDayOfWeekName(anchor_bar_time);
   context.d1_volatility_vs_20d_avg = avg_daily_range > 0.0 ? (d1[1].high - d1[1].low) / avg_daily_range : 0.0;
   context.current_d1_range_vs_atr = avg_daily_range > 0.0 ? current_d1_range / avg_daily_range : 0.0;
   context.data_quality_flags = "";
   context.is_available = true;

   return true;
}

#endif
