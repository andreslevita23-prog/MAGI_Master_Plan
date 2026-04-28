#ifndef __MAGI_COMMON_MQH__
#define __MAGI_COMMON_MQH__

#property strict

#define MAGI_SCHEMA_VERSION "magi.snapshot.v2"
#define MAGI_MAX_LEVELS 2
#define MAGI_MAX_FEATURE_TFS 4
#define MAGI_MAX_ISSUES 16

struct MagiValidationState
{
   bool   is_valid;
   int    issue_count;
   string issues[MAGI_MAX_ISSUES];
};

struct MagiPositionSnapshot
{
   bool   has_open_position;
   int    open_positions_count;
   string position_type;
   double entry_price;
   double sl;
   double tp;
   double floating_pnl;
};

struct MagiTimeframeFeatures
{
   string          timeframe_label;
   ENUM_TIMEFRAMES timeframe;
   datetime        bar_time;
   datetime        bar_close_time;
   double          age_minutes;
   int             anchor_ibar_shift;
   int             selected_shift;
   int             selected_array_index;
   int             copied_array_size;
   bool            rates_array_as_series;
   int             bars_available;
   datetime        oldest_bar_time;
   datetime        newest_bar_time;
   string          data_source_status;
   string          alignment_status;
   string          alignment_warning;
   string          candle_pattern;
   string          market_structure;
   string          structure_direction;
   double          ema_20;
   double          ema_50;
   double          ema_200;
   double          rsi_14;
   double          recent_range;
};

struct MagiGasparContext
{
   bool     is_available;
   string   schema_version;
   string   module;
   string   role;
   string   symbol;
   datetime timestamp;
   string   anchor_timeframe;
   string   h4_timeframe;
   string   d1_timeframe;
   datetime h4_bar_timestamp;
   datetime d1_bar_timestamp;
   double   h4_age_minutes;
   double   d1_age_minutes;
   string   context_id;
   string   proposed_direction;
   string   proposed_direction_source;
   string   h4_structure;
   string   d1_structure;
   string   directional_alignment;
   double   distance_to_d1_support;
   double   distance_to_d1_resistance;
   double   position_in_d1_range;
   bool     near_key_level;
   string   active_session;
   double   daily_atr_consumed_pct;
   double   available_range_to_next_level;
   string   h4_candle_pattern;
   string   day_of_week;
   double   d1_volatility_vs_20d_avg;
   double   current_d1_range_vs_atr;
   string   data_quality_flags;
};

struct MagiSnapshot
{
   string               schema_version;
   string               snapshot_id;
   string               symbol;
   string               source_mode;
   string               trigger_type;
   datetime             timestamp;
   datetime             anchor_bar_timestamp;
   datetime             bar_timestamp;
   string               anchor_timeframe;
   string               primary_timeframe;
   double               anchor_open;
   double               anchor_high;
   double               anchor_low;
   double               anchor_close;
   string               market_structure;
   string               structure_direction;
   double               support_levels[MAGI_MAX_LEVELS];
   int                  support_count;
   double               resistance_levels[MAGI_MAX_LEVELS];
   int                  resistance_count;
   double               ema_20;
   double               ema_50;
   double               ema_200;
   double               rsi_14;
   string               momentum;
   double               current_price;
   double               recent_range;
   double               spread_pips;
   string               active_session;
   double               account_balance;
   double               account_equity;
   double               daily_drawdown_percent;
   double               risk_percent_per_trade;
   string               allowed_actions;
   string               operational_notes;
   string               mtf_alignment_status;
   string               mtf_alignment_warnings;
   string               mtf_data_source_status;
   MagiPositionSnapshot position;
   MagiGasparContext    gaspar_context;
   MagiTimeframeFeatures features[MAGI_MAX_FEATURE_TFS];
   int                  feature_count;
   MagiValidationState  validation;
};

void MagiLog(const string level,const string scope,const string message)
{
   PrintFormat("[MAGI][%s][%s] %s", level, scope, message);
}

void MagiValidationReset(MagiValidationState &validation)
{
   validation.is_valid   = true;
   validation.issue_count = 0;

   for(int i = 0; i < MAGI_MAX_ISSUES; i++)
      validation.issues[i] = "";
}

void MagiValidationAddIssue(MagiValidationState &validation,const string issue)
{
   if(validation.issue_count < MAGI_MAX_ISSUES)
      validation.issues[validation.issue_count] = issue;

   validation.issue_count++;
   validation.is_valid = false;
}

int MagiValidationStoredIssueCount(const MagiValidationState &validation)
{
   return MathMin(validation.issue_count, MAGI_MAX_ISSUES);
}

string MagiJoinValidationIssues(const MagiValidationState &validation,const string separator = "; ")
{
   string result = "";
   int count = MagiValidationStoredIssueCount(validation);

   for(int i = 0; i < count; i++)
   {
      if(i > 0)
         result += separator;

      result += validation.issues[i];
   }

   return result;
}

string MagiTimeframeToLabel(const ENUM_TIMEFRAMES timeframe)
{
   switch(timeframe)
   {
      case PERIOD_M1:  return "M1";
      case PERIOD_M5:  return "M5";
      case PERIOD_M15: return "M15";
      case PERIOD_M30: return "M30";
      case PERIOD_H1:  return "H1";
      case PERIOD_H4:  return "H4";
      case PERIOD_D1:  return "D1";
      default:         return "UNKNOWN";
   }
}

string MagiDateTimeToIso(const datetime value)
{
   MqlDateTime parts;
   TimeToStruct(value, parts);

   return StringFormat("%04d-%02d-%02dT%02d:%02d:%02d",
                       parts.year,
                       parts.mon,
                       parts.day,
                       parts.hour,
                       parts.min,
                       parts.sec);
}

string MagiNowUtcIso()
{
   return MagiDateTimeToIso(TimeGMT()) + "Z";
}

string MagiDateTimeToUtcIso(const datetime value)
{
   return MagiDateTimeToIso(value) + "Z";
}

string MagiBoolToJson(const bool value)
{
   return value ? "true" : "false";
}

bool MagiIsValidNumber(const double value)
{
   return (value == value && value != DBL_MAX && value != -DBL_MAX);
}

string MagiEscapeJson(const string value)
{
   string result = value;
   StringReplace(result, "\\", "\\\\");
   StringReplace(result, "\"", "\\\"");
   StringReplace(result, "\r", "\\r");
   StringReplace(result, "\n", "\\n");
   StringReplace(result, "\t", "\\t");
   return result;
}

string MagiCsvEscape(const string value)
{
   string escaped = value;
   StringReplace(escaped, "\"", "\"\"");
   return "\"" + escaped + "\"";
}

string MagiNormalizeSymbol(const string raw_symbol)
{
   string symbol = raw_symbol;
   StringTrimLeft(symbol);
   StringTrimRight(symbol);
   StringToUpper(symbol);
   return symbol;
}

int MagiSymbolDigits(const string symbol)
{
   long digits = 0;
   if(!SymbolInfoInteger(symbol, SYMBOL_DIGITS, digits))
      return _Digits;

   return (int)digits;
}

double MagiSymbolPoint(const string symbol)
{
   double point = 0.0;
   if(!SymbolInfoDouble(symbol, SYMBOL_POINT, point) || point <= 0.0)
      return _Point;

   return point;
}

string MagiDoubleToSymbolString(const string symbol,const double value)
{
   return DoubleToString(value, MagiSymbolDigits(symbol));
}

void MagiInitializePositionSnapshot(MagiPositionSnapshot &position)
{
   position.has_open_position   = false;
   position.open_positions_count = 0;
   position.position_type       = "";
   position.entry_price         = 0.0;
   position.sl                  = 0.0;
   position.tp                  = 0.0;
   position.floating_pnl        = 0.0;
}

void MagiInitializeTimeframeFeature(MagiTimeframeFeatures &feature,const ENUM_TIMEFRAMES timeframe)
{
   feature.timeframe_label    = MagiTimeframeToLabel(timeframe);
   feature.timeframe          = timeframe;
   feature.bar_time           = 0;
   feature.bar_close_time     = 0;
   feature.age_minutes        = 0.0;
   feature.anchor_ibar_shift  = -1;
   feature.selected_shift     = -1;
   feature.selected_array_index = -1;
   feature.copied_array_size  = 0;
   feature.rates_array_as_series = false;
   feature.bars_available     = 0;
   feature.oldest_bar_time    = 0;
   feature.newest_bar_time    = 0;
   feature.data_source_status = "PENDING";
   feature.alignment_status   = "pending";
   feature.alignment_warning  = "";
   feature.candle_pattern     = "unknown";
   feature.market_structure   = "unknown";
   feature.structure_direction = "neutral";
   feature.ema_20             = 0.0;
   feature.ema_50             = 0.0;
   feature.ema_200            = 0.0;
   feature.rsi_14             = 0.0;
   feature.recent_range       = 0.0;
}

void MagiInitializeGasparContext(MagiGasparContext &context)
{
   context.is_available = false;
   context.schema_version = "1.0";
   context.module = "GASPAR";
   context.role = "opportunity_quality";
   context.symbol = "";
   context.timestamp = 0;
   context.anchor_timeframe = "";
   context.h4_timeframe = "H4";
   context.d1_timeframe = "D1";
   context.h4_bar_timestamp = 0;
   context.d1_bar_timestamp = 0;
   context.h4_age_minutes = 0.0;
   context.d1_age_minutes = 0.0;
   context.context_id = "";
   context.proposed_direction = "NEUTRAL";
   context.proposed_direction_source = "pending";
   context.h4_structure = "range";
   context.d1_structure = "range";
   context.directional_alignment = "neutral";
   context.distance_to_d1_support = 0.0;
   context.distance_to_d1_resistance = 0.0;
   context.position_in_d1_range = 0.0;
   context.near_key_level = false;
   context.active_session = "inactive";
   context.daily_atr_consumed_pct = 0.0;
   context.available_range_to_next_level = 0.0;
   context.h4_candle_pattern = "none";
   context.day_of_week = "inactive";
   context.d1_volatility_vs_20d_avg = 0.0;
   context.current_d1_range_vs_atr = 0.0;
   context.data_quality_flags = "pending";
}

void MagiInitializeSnapshot(MagiSnapshot &snapshot)
{
   snapshot.schema_version    = MAGI_SCHEMA_VERSION;
   snapshot.snapshot_id       = "";
   snapshot.symbol            = "";
   snapshot.source_mode       = "";
   snapshot.trigger_type      = "closed_bar";
   snapshot.timestamp         = 0;
   snapshot.anchor_bar_timestamp = 0;
   snapshot.bar_timestamp     = 0;
   snapshot.anchor_timeframe  = "";
   snapshot.primary_timeframe = "";
   snapshot.anchor_open       = 0.0;
   snapshot.anchor_high       = 0.0;
   snapshot.anchor_low        = 0.0;
   snapshot.anchor_close      = 0.0;
   snapshot.market_structure  = "unknown";
   snapshot.structure_direction = "neutral";
   snapshot.support_count     = 0;
   snapshot.resistance_count  = 0;
   snapshot.ema_20            = 0.0;
   snapshot.ema_50            = 0.0;
   snapshot.ema_200           = 0.0;
   snapshot.rsi_14            = 0.0;
   snapshot.momentum          = "weak";
   snapshot.current_price     = 0.0;
   snapshot.recent_range      = 0.0;
   snapshot.spread_pips       = 0.0;
   snapshot.active_session    = "inactive";
   snapshot.account_balance   = 0.0;
   snapshot.account_equity    = 0.0;
   snapshot.daily_drawdown_percent = 0.0;
   snapshot.risk_percent_per_trade = 0.0;
   snapshot.allowed_actions   = "[]";
   snapshot.operational_notes = "";
   snapshot.mtf_alignment_status = "pending";
   snapshot.mtf_alignment_warnings = "";
   snapshot.mtf_data_source_status = "PENDING";
   snapshot.feature_count     = 0;

   for(int i = 0; i < MAGI_MAX_LEVELS; i++)
   {
      snapshot.support_levels[i] = 0.0;
      snapshot.resistance_levels[i] = 0.0;
   }

   for(int j = 0; j < MAGI_MAX_FEATURE_TFS; j++)
      MagiInitializeTimeframeFeature(snapshot.features[j], PERIOD_CURRENT);

   MagiInitializePositionSnapshot(snapshot.position);
   MagiInitializeGasparContext(snapshot.gaspar_context);
   MagiValidationReset(snapshot.validation);
}

string MagiBuildSnapshotId(const string symbol,const datetime anchor_bar_time,const string anchor_timeframe,const string source_mode)
{
   return StringFormat("%s_%s_%s_%s",
                       symbol,
                       anchor_timeframe,
                       MagiDateTimeToIso(anchor_bar_time),
                       source_mode);
}

#endif
