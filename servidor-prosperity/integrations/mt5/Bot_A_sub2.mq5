//+------------------------------------------------------------------+
//|                                               Bot_A_sub2.mq5     |
//| Generador de dataset estructural/temporal para Gaspar            |
//+------------------------------------------------------------------+
#property strict

#define BOT_A_SUB2_BUILD_TAG "bot_a_sub2_gaspar_2026-04-27_v1"

input string           InpSymbols               = "EURUSD";
input ENUM_TIMEFRAMES  InpAnchorTimeframe       = PERIOD_M5;
input bool             InpWriteCsv              = true;
input bool             InpWriteJsonl            = true;
input string           InpStorageRootFolder     = "MAGI";
input string           InpStorageSubfolder      = "datasets\\bot_a_sub2";
input string           InpDatasetPrefix         = "magi_bot_a_sub2_gaspar";
input int              InpD1LookbackBars        = 20;
input double           InpNearLevelPct          = 0.15;

string   g_symbols[];
datetime g_last_bar[];
string   g_run_id = "";

string Trimmed(string value)
{
   StringTrimLeft(value);
   StringTrimRight(value);
   return value;
}

string SanitizePathSegment(string value)
{
   value = Trimmed(value);
   string invalid = "<>:\"/\\|?*";
   for(int i = 0; i < StringLen(invalid); i++)
      StringReplace(value, StringSubstr(invalid, i, 1), "_");
   StringReplace(value, " ", "_");
   return value;
}

string TimeframeLabel(const ENUM_TIMEFRAMES timeframe)
{
   if(timeframe == PERIOD_M1) return "M1";
   if(timeframe == PERIOD_M5) return "M5";
   if(timeframe == PERIOD_M15) return "M15";
   if(timeframe == PERIOD_M30) return "M30";
   if(timeframe == PERIOD_H1) return "H1";
   if(timeframe == PERIOD_H4) return "H4";
   if(timeframe == PERIOD_D1) return "D1";
   return "TF";
}

string IsoTime(const datetime value)
{
   MqlDateTime parts;
   TimeToStruct(value, parts);
   return StringFormat("%04d-%02d-%02dT%02d:%02d:%02dZ",
                       parts.year, parts.mon, parts.day, parts.hour, parts.min, parts.sec);
}

string BuildRunId()
{
   MqlDateTime parts;
   TimeToStruct(TimeLocal(), parts);
   return StringFormat("run_%04d-%02d-%02d_%02d-%02d-%02d",
                       parts.year, parts.mon, parts.day, parts.hour, parts.min, parts.sec);
}

string CommonFilesBase()
{
   return TerminalInfoString(TERMINAL_COMMONDATA_PATH) + "\\Files";
}

bool EnsureDirectoryTree(const string relative_directory)
{
   string normalized = relative_directory;
   StringReplace(normalized, "/", "\\");
   string parts[];
   int total = StringSplit(normalized, '\\', parts);
   string current = "";
   for(int i = 0; i < total; i++)
   {
      string segment = SanitizePathSegment(parts[i]);
      if(segment == "")
         continue;
      current = (current == "" ? segment : current + "\\" + segment);
      ResetLastError();
      if(FolderCreate(current, FILE_COMMON))
         continue;
      int error = GetLastError();
      if(error == 5019)
         continue;
      PrintFormat("Bot_A_sub2: no se pudo crear carpeta %s error=%d", current, error);
      return false;
   }
   return true;
}

string BuildDirectory(const string symbol,const datetime bar_time)
{
   MqlDateTime parts;
   TimeToStruct(bar_time, parts);
   return SanitizePathSegment(InpStorageRootFolder) + "\\" +
          InpStorageSubfolder + "\\" +
          g_run_id + "\\" +
          SanitizePathSegment(symbol) + "\\" +
          "anchor_" + TimeframeLabel(InpAnchorTimeframe) + "__h4_d1" + "\\" +
          StringFormat("%04d\\%02d\\%02d", parts.year, parts.mon, parts.day);
}

string BuildBaseName(const string symbol,const datetime bar_time)
{
   MqlDateTime parts;
   TimeToStruct(bar_time, parts);
   return StringFormat("%s__symbol_%s__anchor_%s__date_%04d-%02d-%02d",
                       SanitizePathSegment(InpDatasetPrefix),
                       symbol,
                       TimeframeLabel(InpAnchorTimeframe),
                       parts.year,
                       parts.mon,
                       parts.day);
}

bool SelectSymbols()
{
   string raw[];
   int total = StringSplit(InpSymbols, ',', raw);
   ArrayResize(g_symbols, 0);
   ArrayResize(g_last_bar, 0);
   for(int i = 0; i < total; i++)
   {
      string symbol = Trimmed(raw[i]);
      if(symbol == "")
         continue;
      if(!SymbolSelect(symbol, true))
      {
         Print("Bot_A_sub2: simbolo no disponible: ", symbol);
         continue;
      }
      int next = ArraySize(g_symbols);
      ArrayResize(g_symbols, next + 1);
      ArrayResize(g_last_bar, next + 1);
      g_symbols[next] = symbol;
      g_last_bar[next] = 0;
   }
   return ArraySize(g_symbols) > 0;
}

bool CopyClosedRates(const string symbol,const ENUM_TIMEFRAMES timeframe,const int count,MqlRates &rates[])
{
   ArraySetAsSeries(rates, true);
   return CopyRates(symbol, timeframe, 1, count, rates) == count;
}

string StructureFromRates(const MqlRates &rates[])
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

string ProposedDirectionFromStructure(const string h4_structure,const string d1_structure)
{
   if(d1_structure == "bullish" && h4_structure != "bearish")
      return "BUY";
   if(d1_structure == "bearish" && h4_structure != "bullish")
      return "SELL";
   return "NEUTRAL";
}

string DirectionalAlignment(const string proposed_direction,const string h4_structure,const string d1_structure)
{
   if(proposed_direction == "BUY" && d1_structure == "bullish" && h4_structure != "bearish")
      return "aligned";
   if(proposed_direction == "SELL" && d1_structure == "bearish" && h4_structure != "bullish")
      return "aligned";
   if(proposed_direction == "NEUTRAL")
      return "neutral";
   return "contradictory";
}

void D1Levels(const MqlRates &rates[],const int count,double &support,double &resistance)
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

double AverageDailyTrueRange(const MqlRates &rates[],const int count)
{
   double sum = 0.0;
   int usable = MathMin(count - 1, InpD1LookbackBars);
   for(int i = 0; i < usable; i++)
   {
      double high_low = rates[i].high - rates[i].low;
      double high_close = MathAbs(rates[i].high - rates[i + 1].close);
      double low_close = MathAbs(rates[i].low - rates[i + 1].close);
      sum += MathMax(high_low, MathMax(high_close, low_close));
   }
   return usable > 0 ? sum / usable : 0.0;
}

string ActiveSession(const datetime bar_time)
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

string DayOfWeekName(const datetime bar_time)
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

string H4CandlePattern(const MqlRates &bar,const MqlRates &previous)
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

string JsonEscape(string value)
{
   StringReplace(value, "\\", "\\\\");
   StringReplace(value, "\"", "\\\"");
   return value;
}

string CsvHeader()
{
   return "module,role,symbol,timestamp,proposed_direction,h4_structure,d1_structure,directional_alignment," +
          "distance_to_d1_support,distance_to_d1_resistance,position_in_d1_range,near_key_level," +
          "active_session,daily_atr_consumed_pct,available_range_to_next_level,h4_candle_pattern," +
          "day_of_week,d1_volatility_vs_20d_avg,current_d1_range_vs_atr\n";
}

string CsvRow(const string symbol,const datetime bar_time,const string proposed_direction,const string h4_structure,const string d1_structure,
              const string alignment,const double support_distance,const double resistance_distance,
              const double range_position,const bool near_key_level,const string session,
              const double daily_consumed,const double available_range,const string pattern,
              const string day_name,const double volatility_ratio,const double current_range_ratio)
{
   return StringFormat("GASPAR,opportunity_quality,%s,%s,%s,%s,%s,%s,%.8f,%.8f,%.6f,%s,%s,%.6f,%.8f,%s,%s,%.6f,%.6f\n",
                       symbol,
                       IsoTime(bar_time),
                       proposed_direction,
                       h4_structure,
                       d1_structure,
                       alignment,
                       support_distance,
                       resistance_distance,
                       range_position,
                       (near_key_level ? "true" : "false"),
                       session,
                       daily_consumed,
                       available_range,
                       pattern,
                       day_name,
                       volatility_ratio,
                       current_range_ratio);
}

string JsonLine(const string symbol,const datetime bar_time,const string proposed_direction,const string h4_structure,const string d1_structure,
                const string alignment,const double support_distance,const double resistance_distance,
                const double range_position,const bool near_key_level,const string session,
                const double daily_consumed,const double available_range,const string pattern,
                const string day_name,const double volatility_ratio,const double current_range_ratio)
{
   return StringFormat("{\"module\":\"GASPAR\",\"role\":\"opportunity_quality\",\"symbol\":\"%s\",\"timestamp\":\"%s\",\"proposed_direction\":\"%s\",\"higher_timeframe_confluence\":{\"h4_structure\":\"%s\",\"d1_structure\":\"%s\",\"directional_alignment\":\"%s\"},\"price_structure_position\":{\"distance_to_d1_support\":%.8f,\"distance_to_d1_resistance\":%.8f,\"position_in_d1_range\":%.6f,\"near_key_level\":%s},\"timing_quality\":{\"active_session\":\"%s\",\"daily_atr_consumed_pct\":%.6f,\"available_range_to_next_level\":%.8f,\"h4_candle_pattern\":\"%s\"},\"day_context\":{\"day_of_week\":\"%s\",\"d1_volatility_vs_20d_avg\":%.6f,\"current_d1_range_vs_atr\":%.6f}}\n",
                       JsonEscape(symbol),
                       IsoTime(bar_time),
                       JsonEscape(proposed_direction),
                       h4_structure,
                       d1_structure,
                       alignment,
                       support_distance,
                       resistance_distance,
                       range_position,
                       (near_key_level ? "true" : "false"),
                       session,
                       daily_consumed,
                       available_range,
                       pattern,
                       day_name,
                       volatility_ratio,
                       current_range_ratio);
}

bool AppendText(const string relative_path,const string body,const bool write_header,const string header)
{
   bool existed = FileIsExist(relative_path, FILE_COMMON);
   int handle = FileOpen(relative_path, FILE_READ | FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_COMMON);
   if(handle == INVALID_HANDLE)
   {
      PrintFormat("Bot_A_sub2: FileOpen fallo path=%s error=%d", CommonFilesBase() + "\\" + relative_path, GetLastError());
      return false;
   }
   FileSeek(handle, 0, SEEK_END);
   if(write_header && !existed)
      FileWriteString(handle, header);
   FileWriteString(handle, body);
   FileClose(handle);
   return true;
}

void ProcessSymbol(const string symbol,const int index)
{
   datetime bar_time = iTime(symbol, InpAnchorTimeframe, 1);
   if(bar_time <= 0 || g_last_bar[index] == bar_time)
      return;
   g_last_bar[index] = bar_time;

   MqlRates h4[4];
   MqlRates d1[];
   ArrayResize(d1, InpD1LookbackBars + 2);
   if(!CopyClosedRates(symbol, PERIOD_H4, 4, h4))
      return;
   if(!CopyClosedRates(symbol, PERIOD_D1, InpD1LookbackBars + 2, d1))
      return;

   string h4_structure = StructureFromRates(h4);
   string d1_structure = StructureFromRates(d1);
   string proposed_direction = ProposedDirectionFromStructure(h4_structure, d1_structure);
   string alignment = DirectionalAlignment(proposed_direction, h4_structure, d1_structure);

   double support = 0.0;
   double resistance = 0.0;
   D1Levels(d1, InpD1LookbackBars, support, resistance);
   double close_price = iClose(symbol, InpAnchorTimeframe, 1);
   double support_distance = MathMax(0.0, close_price - support);
   double resistance_distance = MathMax(0.0, resistance - close_price);
   double point = SymbolInfoDouble(symbol, SYMBOL_POINT);
   double d1_range = MathMax(resistance - support, point);
   double range_position = MathMax(0.0, MathMin(1.0, (close_price - support) / d1_range));
   bool near_key_level = support_distance <= d1_range * InpNearLevelPct || resistance_distance <= d1_range * InpNearLevelPct;

   double avg_daily_range = AverageDailyTrueRange(d1, InpD1LookbackBars + 2);
   double current_d1_range = d1[0].high - d1[0].low;
   double daily_consumed_raw = avg_daily_range > 0.0 ? current_d1_range / avg_daily_range : 0.0;
   double daily_consumed = MathMax(0.0, MathMin(1.0, daily_consumed_raw));
   double available_range = (proposed_direction == "SELL") ? support_distance : resistance_distance;
   string pattern = H4CandlePattern(h4[0], h4[1]);
   string session = ActiveSession(bar_time);
   string day_name = DayOfWeekName(bar_time);
   double volatility_ratio = avg_daily_range > 0.0 ? (d1[1].high - d1[1].low) / avg_daily_range : 0.0;
   double current_range_ratio = avg_daily_range > 0.0 ? current_d1_range / avg_daily_range : 0.0;

   string directory = BuildDirectory(symbol, bar_time);
   if(!EnsureDirectoryTree(directory))
      return;
   string base = BuildBaseName(symbol, bar_time);

   if(InpWriteCsv)
   {
      string csv_path = directory + "\\" + base + ".csv";
      AppendText(csv_path,
                 CsvRow(symbol, bar_time, proposed_direction, h4_structure, d1_structure, alignment, support_distance, resistance_distance,
                        range_position, near_key_level, session, daily_consumed, available_range, pattern,
                        day_name, volatility_ratio, current_range_ratio),
                 true,
                 CsvHeader());
   }

   if(InpWriteJsonl)
   {
      string jsonl_path = directory + "\\" + base + ".jsonl";
      AppendText(jsonl_path,
                 JsonLine(symbol, bar_time, proposed_direction, h4_structure, d1_structure, alignment, support_distance, resistance_distance,
                          range_position, near_key_level, session, daily_consumed, available_range, pattern,
                          day_name, volatility_ratio, current_range_ratio),
                 false,
                 "");
   }
}

int OnInit()
{
   if(!InpWriteCsv && !InpWriteJsonl)
   {
      Print("Bot_A_sub2 requiere CSV o JSONL activo.");
      return INIT_FAILED;
   }
   if(!SelectSymbols())
   {
      Print("Bot_A_sub2 no tiene simbolos validos.");
      return INIT_FAILED;
   }
   g_run_id = BuildRunId();
   Print("Bot_A_sub2 listo para Gaspar. build=", BOT_A_SUB2_BUILD_TAG, " run_id=", g_run_id);
   Print("Salida base: ", CommonFilesBase(), "\\", InpStorageRootFolder, "\\", InpStorageSubfolder, "\\", g_run_id);
   return INIT_SUCCEEDED;
}

void OnTick()
{
   for(int i = 0; i < ArraySize(g_symbols); i++)
      ProcessSymbol(g_symbols[i], i);
}
