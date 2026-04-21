//+------------------------------------------------------------------+
//|                                                    Bot_A.mq5     |
//| Sensor de mercado MAGI basado en barras cerradas                 |
//+------------------------------------------------------------------+
#property strict

#include "core/MagiFeatureEngine.mqh"
#include "core/MagiSerializer.mqh"
#include "core/MagiTransport.mqh"

input string          InpSymbols               = "EURUSD,XAUUSD";
input ENUM_TIMEFRAMES InpAnchorTimeframe       = PERIOD_M5;
input ENUM_TIMEFRAMES InpPrimaryTimeframe      = PERIOD_H1;
input string          InpServerUrl             = "https://prosperity.lat/analisis";
input int             InpHttpTimeoutMs         = 5000;
input bool            InpSkipInvalidSnapshots  = true;
input bool            InpVerbosePayloadLog     = false;

string   g_symbols[];
datetime g_last_processed_bar[];

bool SelectConfiguredSymbols()
{
   string raw_symbols[];
   int total = StringSplit(InpSymbols, ',', raw_symbols);
   if(total <= 0)
      return false;

   ArrayResize(g_symbols, 0);
   ArrayResize(g_last_processed_bar, 0);

   for(int i = 0; i < total; i++)
   {
      string symbol = MagiNormalizeSymbol(raw_symbols[i]);
      if(symbol == "")
         continue;

      if(!SymbolSelect(symbol, true))
      {
         MagiLog("ERROR", "INIT", StringFormat("No se pudo seleccionar el simbolo %s", symbol));
         continue;
      }

      int next_index = ArraySize(g_symbols);
      ArrayResize(g_symbols, next_index + 1);
      ArrayResize(g_last_processed_bar, next_index + 1);
      g_symbols[next_index] = symbol;
      g_last_processed_bar[next_index] = 0;
   }

   return (ArraySize(g_symbols) > 0);
}

bool IsNewClosedBar(const string symbol,const int symbol_index,datetime &bar_time)
{
   bar_time = iTime(symbol, InpAnchorTimeframe, 1);
   if(bar_time <= 0)
      return false;

   if(g_last_processed_bar[symbol_index] == bar_time)
      return false;

   g_last_processed_bar[symbol_index] = bar_time;
   return true;
}

void ProcessSymbol(const string symbol)
{
   MagiSnapshot snapshot;
   bool build_ok = MagiBuildSnapshot(symbol, InpAnchorTimeframe, InpPrimaryTimeframe, "live", snapshot);

   if(!build_ok)
   {
      MagiLog("WARN", symbol, "Snapshot marcado como invalido: " + MagiJoinValidationIssues(snapshot.validation));
      if(InpSkipInvalidSnapshots)
         return;
   }

   string payload = MagiSerializeSnapshotJson(snapshot);
   if(InpVerbosePayloadLog)
      MagiLog("INFO", symbol, payload);

   int http_status = -1;
   int last_error = 0;
   string response_body = "";
   string response_headers = "";

   if(!MagiHttpPostJson(InpServerUrl, payload, InpHttpTimeoutMs, http_status, response_body, response_headers, last_error))
   {
      MagiLog("ERROR", symbol, StringFormat("WebRequest fallo. GetLastError=%d", last_error));
      return;
   }

   MagiLog("INFO", symbol, StringFormat("Snapshot enviado. HTTP=%d | snapshot_id=%s", http_status, snapshot.snapshot_id));
}

int OnInit()
{
   if(!SelectConfiguredSymbols())
   {
      MagiLog("ERROR", "INIT", "No hay simbolos configurados validos para Bot_A");
      return INIT_FAILED;
   }

   MagiLog("INFO", "INIT", StringFormat("Bot_A listo. Simbolos=%d | anchor=%s | primary=%s",
                                        ArraySize(g_symbols),
                                        MagiTimeframeToLabel(InpAnchorTimeframe),
                                        MagiTimeframeToLabel(InpPrimaryTimeframe)));
   return INIT_SUCCEEDED;
}

void OnTick()
{
   for(int i = 0; i < ArraySize(g_symbols); i++)
   {
      datetime bar_time = 0;
      if(!IsNewClosedBar(g_symbols[i], i, bar_time))
         continue;

      ProcessSymbol(g_symbols[i]);
   }
}
