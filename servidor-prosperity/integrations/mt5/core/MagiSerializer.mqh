#ifndef __MAGI_SERIALIZER_MQH__
#define __MAGI_SERIALIZER_MQH__

#property strict

#include "MagiCommon.mqh"

string MagiSerializeLevelsJson(const double &levels[],const int count)
{
   string json = "[";

   for(int i = 0; i < count; i++)
   {
      if(i > 0)
         json += ",";

      json += DoubleToString(levels[i], 8);
   }

   json += "]";
   return json;
}

string MagiSerializeValidationJson(const MagiValidationState &validation)
{
   string json = StringFormat("\"validation\":{\"is_valid\":%s,\"issues\":[",
                              MagiBoolToJson(validation.is_valid));

   int count = MagiValidationStoredIssueCount(validation);
   for(int i = 0; i < count; i++)
   {
      if(i > 0)
         json += ",";

      json += "\"" + MagiEscapeJson(validation.issues[i]) + "\"";
   }

   json += "]}";
   return json;
}

string MagiSerializePositionJson(const MagiPositionSnapshot &position)
{
   string entry_value = (position.has_open_position && position.open_positions_count == 1 ? DoubleToString(position.entry_price, 8) : "null");
   string sl_value = (position.has_open_position && position.open_positions_count == 1 ? DoubleToString(position.sl, 8) : "null");
   string tp_value = (position.has_open_position && position.open_positions_count == 1 ? DoubleToString(position.tp, 8) : "null");
   string pnl_value = (position.has_open_position ? DoubleToString(position.floating_pnl, 2) : "null");
   string type_value = (position.has_open_position ? "\"" + MagiEscapeJson(position.position_type) + "\"" : "null");

   return StringFormat("\"position\":{\"has_open_position\":%s,\"open_positions_count\":%d,\"position_type\":%s,\"entry_price\":%s,\"sl\":%s,\"tp\":%s,\"floating_pnl\":%s}",
                       MagiBoolToJson(position.has_open_position),
                       position.open_positions_count,
                       type_value,
                       entry_value,
                       sl_value,
                       tp_value,
                       pnl_value);
}

string MagiSerializeFeatureJson(const MagiTimeframeFeatures &feature)
{
   return StringFormat("{\"timeframe\":\"%s\",\"bar_timestamp\":\"%s\",\"bar_close_timestamp\":\"%s\",\"age_minutes\":%s,\"anchor_ibar_shift\":%d,\"selected_shift\":%d,\"selected_array_index\":%d,\"copied_array_size\":%d,\"rates_array_as_series\":%s,\"bars_available\":%d,\"oldest_bar_time\":\"%s\",\"newest_bar_time\":\"%s\",\"data_source_status\":\"%s\",\"alignment_status\":\"%s\",\"alignment_warning\":\"%s\",\"candle_pattern\":\"%s\",\"market_structure\":\"%s\",\"structure_direction\":\"%s\",\"ema_20\":%s,\"ema_50\":%s,\"ema_200\":%s,\"rsi_14\":%s,\"recent_range\":%s}",
                       feature.timeframe_label,
                       MagiDateTimeToIso(feature.bar_time),
                       MagiDateTimeToIso(feature.bar_close_time),
                       DoubleToString(feature.age_minutes, 2),
                       feature.anchor_ibar_shift,
                       feature.selected_shift,
                       feature.selected_array_index,
                       feature.copied_array_size,
                       MagiBoolToJson(feature.rates_array_as_series),
                       feature.bars_available,
                       MagiDateTimeToIso(feature.oldest_bar_time),
                       MagiDateTimeToIso(feature.newest_bar_time),
                       MagiEscapeJson(feature.data_source_status),
                       MagiEscapeJson(feature.alignment_status),
                       MagiEscapeJson(feature.alignment_warning),
                       MagiEscapeJson(feature.candle_pattern),
                       MagiEscapeJson(feature.market_structure),
                       MagiEscapeJson(feature.structure_direction),
                       DoubleToString(feature.ema_20, 8),
                       DoubleToString(feature.ema_50, 8),
                       DoubleToString(feature.ema_200, 8),
                       DoubleToString(feature.rsi_14, 2),
                       DoubleToString(feature.recent_range, 8));
}

string MagiSerializeFeaturesArrayJson(const MagiSnapshot &snapshot)
{
   string json = "[";

   for(int i = 0; i < snapshot.feature_count; i++)
   {
      if(i > 0)
         json += ",";

      json += MagiSerializeFeatureJson(snapshot.features[i]);
   }

   json += "]";
   return json;
}

string MagiSerializeFeaturesJson(const MagiSnapshot &snapshot)
{
   return "\"features\":" + MagiSerializeFeaturesArrayJson(snapshot);
}

string MagiJsonNumberOrNull(const bool available,const double value,const int digits = 8)
{
   if(!available)
      return "null";
   return DoubleToString(value, digits);
}

string MagiSerializeGasparContextJson(const MagiGasparContext &context)
{
   string timestamp_value = (context.timestamp > 0 ? MagiDateTimeToUtcIso(context.timestamp) : "");
   string json = "\"gaspar_context\":{";
   json += StringFormat("\"is_available\":%s,", MagiBoolToJson(context.is_available));
   json += StringFormat("\"schema_version\":\"%s\",", MagiEscapeJson(context.schema_version));
   json += StringFormat("\"module\":\"%s\",", MagiEscapeJson(context.module));
   json += StringFormat("\"role\":\"%s\",", MagiEscapeJson(context.role));
   json += StringFormat("\"symbol\":\"%s\",", MagiEscapeJson(context.symbol));
   json += StringFormat("\"timestamp\":%s,", context.timestamp > 0 ? "\"" + timestamp_value + "\"" : "null");
   json += StringFormat("\"anchor_timeframe\":\"%s\",", MagiEscapeJson(context.anchor_timeframe));
   json += StringFormat("\"structure_timeframes\":{\"h4\":\"%s\",\"d1\":\"%s\"},", MagiEscapeJson(context.h4_timeframe), MagiEscapeJson(context.d1_timeframe));
   json += StringFormat("\"h4_bar_timestamp\":%s,", context.h4_bar_timestamp > 0 ? "\"" + MagiDateTimeToUtcIso(context.h4_bar_timestamp) + "\"" : "null");
   json += StringFormat("\"d1_bar_timestamp\":%s,", context.d1_bar_timestamp > 0 ? "\"" + MagiDateTimeToUtcIso(context.d1_bar_timestamp) + "\"" : "null");
   json += StringFormat("\"h4_age_minutes\":%s,", MagiJsonNumberOrNull(context.is_available, context.h4_age_minutes, 2));
   json += StringFormat("\"d1_age_minutes\":%s,", MagiJsonNumberOrNull(context.is_available, context.d1_age_minutes, 2));
   json += StringFormat("\"context_id\":\"%s\",", MagiEscapeJson(context.context_id));
   json += StringFormat("\"proposed_direction\":\"%s\",", MagiEscapeJson(context.proposed_direction));
   json += StringFormat("\"proposed_direction_source\":\"%s\",", MagiEscapeJson(context.proposed_direction_source));
   json += StringFormat("\"higher_timeframe_confluence\":{\"h4_structure\":\"%s\",\"d1_structure\":\"%s\",\"directional_alignment\":\"%s\"},",
                        MagiEscapeJson(context.h4_structure),
                        MagiEscapeJson(context.d1_structure),
                        MagiEscapeJson(context.directional_alignment));
   json += StringFormat("\"price_structure_position\":{\"distance_to_d1_support\":%s,\"distance_to_d1_resistance\":%s,\"position_in_d1_range\":%s,\"near_key_level\":%s},",
                        MagiJsonNumberOrNull(context.is_available, context.distance_to_d1_support, 8),
                        MagiJsonNumberOrNull(context.is_available, context.distance_to_d1_resistance, 8),
                        MagiJsonNumberOrNull(context.is_available, context.position_in_d1_range, 6),
                        MagiBoolToJson(context.near_key_level));
   json += StringFormat("\"timing_quality\":{\"active_session\":\"%s\",\"daily_atr_consumed_pct\":%s,\"available_range_to_next_level\":%s,\"h4_candle_pattern\":\"%s\"},",
                        MagiEscapeJson(context.active_session),
                        MagiJsonNumberOrNull(context.is_available, context.daily_atr_consumed_pct, 6),
                        MagiJsonNumberOrNull(context.is_available, context.available_range_to_next_level, 8),
                        MagiEscapeJson(context.h4_candle_pattern));
   json += StringFormat("\"day_context\":{\"day_of_week\":\"%s\",\"d1_volatility_vs_20d_avg\":%s,\"current_d1_range_vs_atr\":%s},",
                        MagiEscapeJson(context.day_of_week),
                        MagiJsonNumberOrNull(context.is_available, context.d1_volatility_vs_20d_avg, 6),
                        MagiJsonNumberOrNull(context.is_available, context.current_d1_range_vs_atr, 6));
   json += StringFormat("\"data_quality_flags\":\"%s\"", MagiEscapeJson(context.data_quality_flags));
   json += "}";
   return json;
}

string MagiSerializeSnapshotJson(const MagiSnapshot &snapshot)
{
   string json = "{";
   json += StringFormat("\"schema_version\":\"%s\",", MagiEscapeJson(snapshot.schema_version));
   json += StringFormat("\"snapshot_id\":\"%s\",", MagiEscapeJson(snapshot.snapshot_id));
   json += StringFormat("\"symbol\":\"%s\",", MagiEscapeJson(snapshot.symbol));
   json += StringFormat("\"source_mode\":\"%s\",", MagiEscapeJson(snapshot.source_mode));
   json += StringFormat("\"trigger_type\":\"%s\",", MagiEscapeJson(snapshot.trigger_type));
   json += StringFormat("\"timestamp\":\"%s\",", MagiDateTimeToUtcIso(snapshot.timestamp));
   json += StringFormat("\"anchor_bar_timestamp\":\"%s\",", MagiDateTimeToIso(snapshot.anchor_bar_timestamp));
   json += StringFormat("\"bar_timestamp\":\"%s\",", MagiDateTimeToIso(snapshot.bar_timestamp));
   json += StringFormat("\"anchor_timeframe\":\"%s\",", MagiEscapeJson(snapshot.anchor_timeframe));
   json += StringFormat("\"primary_timeframe\":\"%s\",", MagiEscapeJson(snapshot.primary_timeframe));
   json += StringFormat("\"anchor_open\":%s,", MagiDoubleToSymbolString(snapshot.symbol, snapshot.anchor_open));
   json += StringFormat("\"anchor_high\":%s,", MagiDoubleToSymbolString(snapshot.symbol, snapshot.anchor_high));
   json += StringFormat("\"anchor_low\":%s,", MagiDoubleToSymbolString(snapshot.symbol, snapshot.anchor_low));
   json += StringFormat("\"anchor_close\":%s,", MagiDoubleToSymbolString(snapshot.symbol, snapshot.anchor_close));
   json += StringFormat("\"market_structure\":\"%s\",", MagiEscapeJson(snapshot.market_structure));
   json += StringFormat("\"structure_direction\":\"%s\",", MagiEscapeJson(snapshot.structure_direction));
   json += StringFormat("\"support_levels\":%s,", MagiSerializeLevelsJson(snapshot.support_levels, snapshot.support_count));
   json += StringFormat("\"resistance_levels\":%s,", MagiSerializeLevelsJson(snapshot.resistance_levels, snapshot.resistance_count));
   json += StringFormat("\"ema_20\":%s,", MagiDoubleToSymbolString(snapshot.symbol, snapshot.ema_20));
   json += StringFormat("\"ema_50\":%s,", MagiDoubleToSymbolString(snapshot.symbol, snapshot.ema_50));
   json += StringFormat("\"ema_200\":%s,", MagiDoubleToSymbolString(snapshot.symbol, snapshot.ema_200));
   json += StringFormat("\"rsi_14\":%s,", DoubleToString(snapshot.rsi_14, 2));
   json += StringFormat("\"momentum\":\"%s\",", MagiEscapeJson(snapshot.momentum));
   json += StringFormat("\"current_price\":%s,", MagiDoubleToSymbolString(snapshot.symbol, snapshot.current_price));
   json += StringFormat("\"recent_range\":%s,", MagiDoubleToSymbolString(snapshot.symbol, snapshot.recent_range));
   json += StringFormat("\"spread_pips\":%s,", DoubleToString(snapshot.spread_pips, 2));
   json += StringFormat("\"active_session\":\"%s\",", MagiEscapeJson(snapshot.active_session));
   json += StringFormat("\"mtf_alignment_status\":\"%s\",", MagiEscapeJson(snapshot.mtf_alignment_status));
   json += StringFormat("\"mtf_alignment_warnings\":\"%s\",", MagiEscapeJson(snapshot.mtf_alignment_warnings));
   json += StringFormat("\"mtf_data_source_status\":\"%s\",", MagiEscapeJson(snapshot.mtf_data_source_status));
   json += StringFormat("\"allowed_actions\":%s,", snapshot.allowed_actions);
   json += StringFormat("\"account\":{\"balance\":%s,\"equity\":%s,\"daily_drawdown_percent\":%s,\"risk_percent_per_trade\":%s},",
                        DoubleToString(snapshot.account_balance, 2),
                        DoubleToString(snapshot.account_equity, 2),
                        DoubleToString(snapshot.daily_drawdown_percent, 4),
                        DoubleToString(snapshot.risk_percent_per_trade, 4));
   json += "\"news\":[],";
   json += StringFormat("\"operational_notes\":\"%s\",", MagiEscapeJson(snapshot.operational_notes));
   json += MagiSerializePositionJson(snapshot.position) + ",";
   json += MagiSerializeGasparContextJson(snapshot.gaspar_context) + ",";
   json += MagiSerializeFeaturesJson(snapshot) + ",";
   json += MagiSerializeValidationJson(snapshot.validation);
   json += "}";
   return json;
}

string MagiBuildCsvHeader()
{
   return "schema_version,snapshot_id,symbol,source_mode,trigger_type,timestamp,anchor_bar_timestamp,bar_timestamp,anchor_timeframe,primary_timeframe,anchor_open,anchor_high,anchor_low,anchor_close,market_structure,structure_direction,ema_20,ema_50,ema_200,rsi_14,momentum,current_price,recent_range,spread_pips,active_session,mtf_alignment_status,mtf_alignment_warnings,mtf_data_source_status,allowed_actions,account_balance,account_equity,daily_drawdown_percent,risk_percent_per_trade,has_open_position,open_positions_count,position_type,entry_price,sl,tp,floating_pnl,support_levels,resistance_levels,gaspar_is_available,gaspar_proposed_direction,gaspar_proposed_direction_source,gaspar_h4_structure,gaspar_d1_structure,gaspar_directional_alignment,gaspar_h4_bar_timestamp,gaspar_d1_bar_timestamp,gaspar_h4_age_minutes,gaspar_d1_age_minutes,gaspar_distance_to_d1_support,gaspar_distance_to_d1_resistance,gaspar_position_in_d1_range,gaspar_near_key_level,gaspar_active_session,gaspar_daily_atr_consumed_pct,gaspar_available_range_to_next_level,gaspar_h4_candle_pattern,gaspar_day_of_week,gaspar_d1_volatility_vs_20d_avg,gaspar_current_d1_range_vs_atr,gaspar_data_quality_flags,validation_is_valid,validation_issues,features_json";
}

string MagiSerializeSnapshotCsvRow(const MagiSnapshot &snapshot)
{
   string position_type = (snapshot.position.has_open_position ? snapshot.position.position_type : "");
   string entry_value = (snapshot.position.has_open_position && snapshot.position.open_positions_count == 1 ? MagiDoubleToSymbolString(snapshot.symbol, snapshot.position.entry_price) : "");
   string sl_value = (snapshot.position.has_open_position && snapshot.position.open_positions_count == 1 ? MagiDoubleToSymbolString(snapshot.symbol, snapshot.position.sl) : "");
   string tp_value = (snapshot.position.has_open_position && snapshot.position.open_positions_count == 1 ? MagiDoubleToSymbolString(snapshot.symbol, snapshot.position.tp) : "");
   string pnl_value = (snapshot.position.has_open_position ? DoubleToString(snapshot.position.floating_pnl, 2) : "");

   return
      MagiCsvEscape(snapshot.schema_version) + "," +
      MagiCsvEscape(snapshot.snapshot_id) + "," +
      MagiCsvEscape(snapshot.symbol) + "," +
      MagiCsvEscape(snapshot.source_mode) + "," +
      MagiCsvEscape(snapshot.trigger_type) + "," +
      MagiCsvEscape(MagiDateTimeToUtcIso(snapshot.timestamp)) + "," +
      MagiCsvEscape(MagiDateTimeToIso(snapshot.anchor_bar_timestamp)) + "," +
      MagiCsvEscape(MagiDateTimeToIso(snapshot.bar_timestamp)) + "," +
      MagiCsvEscape(snapshot.anchor_timeframe) + "," +
      MagiCsvEscape(snapshot.primary_timeframe) + "," +
      MagiDoubleToSymbolString(snapshot.symbol, snapshot.anchor_open) + "," +
      MagiDoubleToSymbolString(snapshot.symbol, snapshot.anchor_high) + "," +
      MagiDoubleToSymbolString(snapshot.symbol, snapshot.anchor_low) + "," +
      MagiDoubleToSymbolString(snapshot.symbol, snapshot.anchor_close) + "," +
      MagiCsvEscape(snapshot.market_structure) + "," +
      MagiCsvEscape(snapshot.structure_direction) + "," +
      MagiDoubleToSymbolString(snapshot.symbol, snapshot.ema_20) + "," +
      MagiDoubleToSymbolString(snapshot.symbol, snapshot.ema_50) + "," +
      MagiDoubleToSymbolString(snapshot.symbol, snapshot.ema_200) + "," +
      DoubleToString(snapshot.rsi_14, 2) + "," +
      MagiCsvEscape(snapshot.momentum) + "," +
      MagiDoubleToSymbolString(snapshot.symbol, snapshot.current_price) + "," +
      MagiDoubleToSymbolString(snapshot.symbol, snapshot.recent_range) + "," +
      DoubleToString(snapshot.spread_pips, 2) + "," +
      MagiCsvEscape(snapshot.active_session) + "," +
      MagiCsvEscape(snapshot.mtf_alignment_status) + "," +
      MagiCsvEscape(snapshot.mtf_alignment_warnings) + "," +
      MagiCsvEscape(snapshot.mtf_data_source_status) + "," +
      MagiCsvEscape(snapshot.allowed_actions) + "," +
      DoubleToString(snapshot.account_balance, 2) + "," +
      DoubleToString(snapshot.account_equity, 2) + "," +
      DoubleToString(snapshot.daily_drawdown_percent, 4) + "," +
      DoubleToString(snapshot.risk_percent_per_trade, 4) + "," +
      MagiCsvEscape(snapshot.position.has_open_position ? "true" : "false") + "," +
      IntegerToString(snapshot.position.open_positions_count) + "," +
      MagiCsvEscape(position_type) + "," +
      MagiCsvEscape(entry_value) + "," +
      MagiCsvEscape(sl_value) + "," +
      MagiCsvEscape(tp_value) + "," +
      MagiCsvEscape(pnl_value) + "," +
      MagiCsvEscape(MagiSerializeLevelsJson(snapshot.support_levels, snapshot.support_count)) + "," +
      MagiCsvEscape(MagiSerializeLevelsJson(snapshot.resistance_levels, snapshot.resistance_count)) + "," +
      MagiCsvEscape(snapshot.gaspar_context.is_available ? "true" : "false") + "," +
      MagiCsvEscape(snapshot.gaspar_context.proposed_direction) + "," +
      MagiCsvEscape(snapshot.gaspar_context.proposed_direction_source) + "," +
      MagiCsvEscape(snapshot.gaspar_context.h4_structure) + "," +
      MagiCsvEscape(snapshot.gaspar_context.d1_structure) + "," +
      MagiCsvEscape(snapshot.gaspar_context.directional_alignment) + "," +
      MagiCsvEscape(snapshot.gaspar_context.h4_bar_timestamp > 0 ? MagiDateTimeToUtcIso(snapshot.gaspar_context.h4_bar_timestamp) : "") + "," +
      MagiCsvEscape(snapshot.gaspar_context.d1_bar_timestamp > 0 ? MagiDateTimeToUtcIso(snapshot.gaspar_context.d1_bar_timestamp) : "") + "," +
      DoubleToString(snapshot.gaspar_context.h4_age_minutes, 2) + "," +
      DoubleToString(snapshot.gaspar_context.d1_age_minutes, 2) + "," +
      DoubleToString(snapshot.gaspar_context.distance_to_d1_support, 8) + "," +
      DoubleToString(snapshot.gaspar_context.distance_to_d1_resistance, 8) + "," +
      DoubleToString(snapshot.gaspar_context.position_in_d1_range, 6) + "," +
      MagiCsvEscape(snapshot.gaspar_context.near_key_level ? "true" : "false") + "," +
      MagiCsvEscape(snapshot.gaspar_context.active_session) + "," +
      DoubleToString(snapshot.gaspar_context.daily_atr_consumed_pct, 6) + "," +
      DoubleToString(snapshot.gaspar_context.available_range_to_next_level, 8) + "," +
      MagiCsvEscape(snapshot.gaspar_context.h4_candle_pattern) + "," +
      MagiCsvEscape(snapshot.gaspar_context.day_of_week) + "," +
      DoubleToString(snapshot.gaspar_context.d1_volatility_vs_20d_avg, 6) + "," +
      DoubleToString(snapshot.gaspar_context.current_d1_range_vs_atr, 6) + "," +
      MagiCsvEscape(snapshot.gaspar_context.data_quality_flags) + "," +
      MagiCsvEscape(snapshot.validation.is_valid ? "true" : "false") + "," +
      MagiCsvEscape(MagiJoinValidationIssues(snapshot.validation)) + "," +
      MagiCsvEscape(MagiSerializeFeaturesArrayJson(snapshot));
}

#endif
