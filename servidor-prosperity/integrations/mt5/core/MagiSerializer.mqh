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
   return StringFormat("{\"timeframe\":\"%s\",\"bar_timestamp\":\"%s\",\"candle_pattern\":\"%s\",\"market_structure\":\"%s\",\"structure_direction\":\"%s\",\"ema_20\":%s,\"ema_50\":%s,\"ema_200\":%s,\"rsi_14\":%s,\"recent_range\":%s}",
                       feature.timeframe_label,
                       MagiDateTimeToIso(feature.bar_time),
                       MagiEscapeJson(feature.candle_pattern),
                       MagiEscapeJson(feature.market_structure),
                       MagiEscapeJson(feature.structure_direction),
                       DoubleToString(feature.ema_20, 8),
                       DoubleToString(feature.ema_50, 8),
                       DoubleToString(feature.ema_200, 8),
                       DoubleToString(feature.rsi_14, 2),
                       DoubleToString(feature.recent_range, 8));
}

string MagiSerializeFeaturesJson(const MagiSnapshot &snapshot)
{
   string json = "\"features\":[";

   for(int i = 0; i < snapshot.feature_count; i++)
   {
      if(i > 0)
         json += ",";

      json += MagiSerializeFeatureJson(snapshot.features[i]);
   }

   json += "]";
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
   json += MagiSerializePositionJson(snapshot.position) + ",";
   json += MagiSerializeFeaturesJson(snapshot) + ",";
   json += MagiSerializeValidationJson(snapshot.validation);
   json += "}";
   return json;
}

string MagiBuildCsvHeader()
{
   return "schema_version,snapshot_id,symbol,source_mode,trigger_type,timestamp,anchor_bar_timestamp,bar_timestamp,anchor_timeframe,primary_timeframe,anchor_open,anchor_high,anchor_low,anchor_close,market_structure,structure_direction,ema_20,ema_50,ema_200,rsi_14,momentum,current_price,recent_range,has_open_position,open_positions_count,position_type,entry_price,sl,tp,floating_pnl,support_levels,resistance_levels,validation_is_valid,validation_issues,features_json";
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
      MagiCsvEscape(snapshot.position.has_open_position ? "true" : "false") + "," +
      IntegerToString(snapshot.position.open_positions_count) + "," +
      MagiCsvEscape(position_type) + "," +
      MagiCsvEscape(entry_value) + "," +
      MagiCsvEscape(sl_value) + "," +
      MagiCsvEscape(tp_value) + "," +
      MagiCsvEscape(pnl_value) + "," +
      MagiCsvEscape(MagiSerializeLevelsJson(snapshot.support_levels, snapshot.support_count)) + "," +
      MagiCsvEscape(MagiSerializeLevelsJson(snapshot.resistance_levels, snapshot.resistance_count)) + "," +
      MagiCsvEscape(snapshot.validation.is_valid ? "true" : "false") + "," +
      MagiCsvEscape(MagiJoinValidationIssues(snapshot.validation)) + "," +
      MagiCsvEscape(MagiSerializeFeaturesJson(snapshot));
}

#endif
