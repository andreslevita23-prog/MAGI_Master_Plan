//+------------------------------------------------------------------+
//|                                               Bot_A_sub1.mq5     |
//| Generador de dataset historico MAGI para Strategy Tester         |
//+------------------------------------------------------------------+
#property strict

#include "core/MagiFeatureEngine.mqh"
#include "core/MagiDatasetWriter.mqh"

input string           InpSymbols                     = "EURUSD";
input ENUM_TIMEFRAMES  InpAnchorTimeframe             = PERIOD_M5;
input ENUM_TIMEFRAMES  InpPrimaryTimeframe            = PERIOD_H1;
input bool             InpWriteCsv                    = true;
input bool             InpWriteJsonl                  = true;
input bool             InpSkipInvalidSnapshots        = true;
input MagiStorageMode  InpStorageMode                 = MAGI_STORAGE_COMMON;
input bool             InpFallbackToLocalIfCommonFails = false;
input string           InpStorageRootFolder           = "MAGI";
input string           InpStorageSubfolder            = "datasets\\bot_a_sub1";
input bool             InpSplitPathBySymbol           = true;
input bool             InpSplitPathByTimeframe        = true;
input bool             InpSplitPathByDate             = true;
input string           InpStorageAttemptFolder        = "prueba_1";
input string           InpDatasetPrefix               = "magi_bot_a_sub1";

string   g_symbols_sub1[];
datetime g_last_processed_bar_sub1[];
datetime g_last_persisted_bar_sub1[];
MagiStoragePolicy g_storage_policy;

bool SelectDatasetSymbols()
{
   string raw_symbols[];
   int total = StringSplit(InpSymbols, ',', raw_symbols);
   if(total <= 0)
      return false;

   ArrayResize(g_symbols_sub1, 0);
   ArrayResize(g_last_processed_bar_sub1, 0);
   ArrayResize(g_last_persisted_bar_sub1, 0);

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

      int next_index = ArraySize(g_symbols_sub1);
      ArrayResize(g_symbols_sub1, next_index + 1);
      ArrayResize(g_last_processed_bar_sub1, next_index + 1);
      ArrayResize(g_last_persisted_bar_sub1, next_index + 1);
      g_symbols_sub1[next_index] = symbol;
      g_last_processed_bar_sub1[next_index] = 0;
      g_last_persisted_bar_sub1[next_index] = 0;
   }

   return (ArraySize(g_symbols_sub1) > 0);
}

void BuildStoragePolicy()
{
   string resolved_subfolder = InpStorageSubfolder;
   if(StringLen(InpStorageAttemptFolder) > 0)
      resolved_subfolder = resolved_subfolder + "\\" + InpStorageAttemptFolder;

   g_storage_policy.mode = InpStorageMode;
   g_storage_policy.fallback_to_local = InpFallbackToLocalIfCommonFails;
   g_storage_policy.root_folder = InpStorageRootFolder;
   g_storage_policy.subfolder = resolved_subfolder;
   g_storage_policy.split_by_symbol = InpSplitPathBySymbol;
   g_storage_policy.split_by_timeframe = InpSplitPathByTimeframe;
   g_storage_policy.split_by_date = InpSplitPathByDate;
   g_storage_policy.dataset_prefix = InpDatasetPrefix;
}

void LogStoragePolicy()
{
   string base_path = MagiResolveStorageBasePath(g_storage_policy.mode == MAGI_STORAGE_COMMON);
   string runtime_mode = ((bool)MQLInfoInteger(MQL_TESTER) ? "TESTER" : "LIVE_OR_CHART");
   string fallback_text = (g_storage_policy.mode == MAGI_STORAGE_COMMON && g_storage_policy.fallback_to_local)
                        ? "Si Common Files falla, se intentara Local Files."
                        : "No habra fallback automatico a Local Files.";

   MagiLog("INFO", "INIT", "Politica de almacenamiento: " + MagiBuildStorageDescription(g_storage_policy));
    MagiLog("INFO", "INIT", "Modo de ejecucion detectado: " + runtime_mode);
   MagiLog("INFO", "INIT", "Base path efectiva primaria: " + base_path);
   MagiLog("INFO", "INIT", fallback_text);
}

bool IsNewClosedBarForDataset(const string symbol,const int symbol_index,datetime &bar_time)
{
   bar_time = iTime(symbol, InpAnchorTimeframe, 1);
   if(bar_time <= 0)
      return false;

   if(g_last_processed_bar_sub1[symbol_index] == bar_time)
      return false;

   g_last_processed_bar_sub1[symbol_index] = bar_time;
   return true;
}

bool WasBarAlreadyPersisted(const int symbol_index,const datetime bar_time)
{
   return (g_last_persisted_bar_sub1[symbol_index] == bar_time && bar_time > 0);
}

void MarkBarAsPersisted(const int symbol_index,const datetime bar_time)
{
   g_last_persisted_bar_sub1[symbol_index] = bar_time;
}

void LogExpectedPaths(const string symbol,const datetime bar_time)
{
   MagiSnapshot preview;
   MagiInitializeSnapshot(preview);
   preview.symbol = symbol;
   preview.anchor_timeframe = MagiTimeframeToLabel(InpAnchorTimeframe);
   preview.primary_timeframe = MagiTimeframeToLabel(InpPrimaryTimeframe);
   preview.bar_timestamp = bar_time;

   if(InpWriteCsv)
   {
      string csv_relative = MagiBuildDatasetDirectory(g_storage_policy, preview);
      string csv_name = MagiBuildDatasetBaseName(g_storage_policy, preview) + ".csv";
      string csv_path = MagiResolveStorageBasePath(g_storage_policy.mode == MAGI_STORAGE_COMMON) + "\\" +
                        (csv_relative == "" ? csv_name : csv_relative + "\\" + csv_name);
      MagiLog("INFO", symbol, "Ruta esperada CSV: " + csv_path);
   }

   if(InpWriteJsonl)
   {
      string jsonl_relative = MagiBuildDatasetDirectory(g_storage_policy, preview);
      string jsonl_name = MagiBuildDatasetBaseName(g_storage_policy, preview) + ".jsonl";
      string jsonl_path = MagiResolveStorageBasePath(g_storage_policy.mode == MAGI_STORAGE_COMMON) + "\\" +
                          (jsonl_relative == "" ? jsonl_name : jsonl_relative + "\\" + jsonl_name);
      MagiLog("INFO", symbol, "Ruta esperada JSONL: " + jsonl_path);
   }
}

void PersistSnapshot(const MagiSnapshot &snapshot,const int symbol_index,const datetime trigger_bar_time)
{
   if(WasBarAlreadyPersisted(symbol_index, trigger_bar_time))
   {
      MagiLog("WARN", snapshot.symbol, StringFormat("Barra ancla ya persistida y omitida: %s", MagiDateTimeToUtcIso(trigger_bar_time)));
      return;
   }

   string validation_reason = "";
   if(!MagiValidateSnapshotForDatasetWrite(snapshot, validation_reason))
   {
      MagiLog("ERROR", snapshot.symbol, "Snapshot omitido por validacion previa a escritura: " + validation_reason);
      return;
   }

   bool write_ok = true;
   string csv_path = "";
   string jsonl_path = "";

   if(InpWriteCsv)
      write_ok = write_ok && MagiAppendSnapshotCsv(g_storage_policy, snapshot, csv_path);

   if(InpWriteJsonl)
      write_ok = write_ok && MagiAppendSnapshotJsonl(g_storage_policy, snapshot, jsonl_path);

   if(!write_ok)
   {
      MagiLog("ERROR", snapshot.symbol, StringFormat("No se pudo persistir snapshot %s en dataset", snapshot.snapshot_id));
      return;
   }

   MarkBarAsPersisted(symbol_index, trigger_bar_time);

   if(csv_path != "")
      MagiLog("INFO", snapshot.symbol, "Ruta final CSV efectiva: " + csv_path);

   if(jsonl_path != "")
      MagiLog("INFO", snapshot.symbol, "Ruta final JSONL efectiva: " + jsonl_path);
}

void ProcessDatasetSymbol(const string symbol,const int symbol_index,const datetime bar_time)
{
   MagiSnapshot snapshot;
   bool build_ok = MagiBuildSnapshot(symbol, InpAnchorTimeframe, InpPrimaryTimeframe, "tester", snapshot);

   if(!build_ok)
   {
      MagiLog("WARN", symbol, "Snapshot invalido en tester: " + MagiJoinValidationIssues(snapshot.validation));
      if(InpSkipInvalidSnapshots)
         return;
   }

   PersistSnapshot(snapshot, symbol_index, bar_time);
}

int OnInit()
{
   if(!InpWriteCsv && !InpWriteJsonl)
   {
      MagiLog("ERROR", "INIT", "Bot_A_sub1 requiere al menos un formato activo: CSV o JSONL");
      return INIT_FAILED;
   }

   if(!SelectDatasetSymbols())
   {
      MagiLog("ERROR", "INIT", "No hay simbolos validos para Bot_A_sub1");
      return INIT_FAILED;
   }

   BuildStoragePolicy();
   LogStoragePolicy();

   for(int i = 0; i < ArraySize(g_symbols_sub1); i++)
   {
      datetime preview_bar = iTime(g_symbols_sub1[i], InpAnchorTimeframe, 1);
      if(preview_bar > 0)
         LogExpectedPaths(g_symbols_sub1[i], preview_bar);
   }

   MagiLog("INFO", "INIT", StringFormat("Bot_A_sub1 listo. Simbolos=%d | anchor=%s | primary=%s",
                                        ArraySize(g_symbols_sub1),
                                        MagiTimeframeToLabel(InpAnchorTimeframe),
                                        MagiTimeframeToLabel(InpPrimaryTimeframe)));
   return INIT_SUCCEEDED;
}

void OnTick()
{
   for(int i = 0; i < ArraySize(g_symbols_sub1); i++)
   {
      datetime bar_time = 0;
      if(!IsNewClosedBarForDataset(g_symbols_sub1[i], i, bar_time))
         continue;

      ProcessDatasetSymbol(g_symbols_sub1[i], i, bar_time);
   }
}
