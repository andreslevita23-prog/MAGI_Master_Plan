#ifndef __MAGI_COMMON_MQH__
#define __MAGI_COMMON_MQH__

#property strict

#define MAGI_SCHEMA_VERSION "magi.snapshot.v2"
#define MAGI_MAX_LEVELS 2
#define MAGI_MAX_FEATURE_TFS 3
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
   string          candle_pattern;
   string          market_structure;
   string          structure_direction;
   double          ema_20;
   double          ema_50;
   double          ema_200;
   double          rsi_14;
   double          recent_range;
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
   MagiPositionSnapshot position;
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
   feature.candle_pattern     = "unknown";
   feature.market_structure   = "unknown";
   feature.structure_direction = "neutral";
   feature.ema_20             = 0.0;
   feature.ema_50             = 0.0;
   feature.ema_200            = 0.0;
   feature.rsi_14             = 0.0;
   feature.recent_range       = 0.0;
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
   snapshot.feature_count     = 0;

   for(int i = 0; i < MAGI_MAX_LEVELS; i++)
   {
      snapshot.support_levels[i] = 0.0;
      snapshot.resistance_levels[i] = 0.0;
   }

   for(int j = 0; j < MAGI_MAX_FEATURE_TFS; j++)
      MagiInitializeTimeframeFeature(snapshot.features[j], PERIOD_CURRENT);

   MagiInitializePositionSnapshot(snapshot.position);
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
