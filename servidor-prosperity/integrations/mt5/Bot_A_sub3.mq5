//+------------------------------------------------------------------+
//|                                               Bot_A_sub3.mq5     |
//| Dataset operativo simple: Bot_A_sub1 + gaspar_context            |
//+------------------------------------------------------------------+
#property strict

#include "core/MagiCommon.mqh"
#include "core/MagiGasparContext.mqh"
#include "core/MagiFeatureEngine.mqh"
#include "core/MagiSerializer.mqh"
#include "core/MagiDatasetWriter.mqh"

#define BOT_A_SUB3_RUNTIME_BUILD_TAG "bot_a_sub3_simple_sub1_sub2_2026-04-28_v1"

input string           InpSymbols                     = "EURUSD";
input ENUM_TIMEFRAMES  InpAnchorTimeframe             = PERIOD_M5;
input ENUM_TIMEFRAMES  InpPrimaryTimeframe            = PERIOD_H1;
input bool             InpWriteCsv                    = true;
input bool             InpWriteJsonl                  = true;
input bool             InpSkipInvalidSnapshots        = false;
input string           InpStorageRootFolder           = "MAGI";
input string           InpStorageSubfolder            = "datasets\\bot_a_sub3";
input bool             InpSplitPathBySymbol           = true;
input bool             InpSplitPathByTimeframe        = true;
input bool             InpSplitPathByDate             = true;
input string           InpDatasetPrefix               = "magi_bot_a_sub3_simple";

string   g_symbols_sub3[];
datetime g_last_processed_bar_sub3[];
datetime g_last_persisted_bar_sub3[];
MagiStoragePolicy g_storage_policy_sub3;
string   g_run_id_sub3 = "";
datetime g_run_started_at_sub3 = 0;

bool SelectDatasetSymbolsSub3()
{
   string raw_symbols[];
   int total = StringSplit(InpSymbols, ',', raw_symbols);
   if(total <= 0)
      return false;

   ArrayResize(g_symbols_sub3, 0);
   ArrayResize(g_last_processed_bar_sub3, 0);
   ArrayResize(g_last_persisted_bar_sub3, 0);

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

      int next_index = ArraySize(g_symbols_sub3);
      ArrayResize(g_symbols_sub3, next_index + 1);
      ArrayResize(g_last_processed_bar_sub3, next_index + 1);
      ArrayResize(g_last_persisted_bar_sub3, next_index + 1);
      g_symbols_sub3[next_index] = symbol;
      g_last_processed_bar_sub3[next_index] = 0;
      g_last_persisted_bar_sub3[next_index] = 0;
   }

   return (ArraySize(g_symbols_sub3) > 0);
}

string BuildRunIdSub3(const datetime run_start_time)
{
   MqlDateTime parts;
   TimeToStruct(run_start_time, parts);

   return StringFormat("run_%04d-%02d-%02d_%02d-%02d-%02d_%u",
                       parts.year,
                       parts.mon,
                       parts.day,
                       parts.hour,
                       parts.min,
                       parts.sec,
                       GetTickCount());
}

void InitializeRunContextSub3()
{
   g_run_started_at_sub3 = TimeLocal();
   g_run_id_sub3 = BuildRunIdSub3(g_run_started_at_sub3);
}

void BuildStoragePolicySub3()
{
   string resolved_subfolder = InpStorageSubfolder;
   if(StringLen(g_run_id_sub3) > 0)
      resolved_subfolder = resolved_subfolder + "\\" + g_run_id_sub3;

   g_storage_policy_sub3.mode = MAGI_STORAGE_COMMON;
   g_storage_policy_sub3.fallback_to_local = false;
   g_storage_policy_sub3.root_folder = InpStorageRootFolder;
   g_storage_policy_sub3.subfolder = resolved_subfolder;
   g_storage_policy_sub3.split_by_symbol = InpSplitPathBySymbol;
   g_storage_policy_sub3.split_by_timeframe = InpSplitPathByTimeframe;
   g_storage_policy_sub3.split_by_date = InpSplitPathByDate;
   g_storage_policy_sub3.dataset_prefix = InpDatasetPrefix;
}

string BuildRunRootRelativePathSub3()
{
   string run_root = MagiNormalizeFolderPath(g_storage_policy_sub3.root_folder);
   string subfolder = MagiNormalizeFolderPath(g_storage_policy_sub3.subfolder);
   if(subfolder != "")
      run_root = (run_root == "" ? subfolder : run_root + "\\" + subfolder);

   return run_root;
}

bool WriteRuntimeMarkerSub3()
{
   string run_root_relative = BuildRunRootRelativePathSub3();
   string marker_name = "__runtime_marker__" + BOT_A_SUB3_RUNTIME_BUILD_TAG + ".txt";
   string marker_relative = (run_root_relative == "" ? marker_name : run_root_relative + "\\" + marker_name);
   string marker_effective = MagiResolveStorageBasePath(true) + "\\" + marker_relative;
   int open_flags = FILE_READ | FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_COMMON;

   ResetLastError();
   int handle = FileOpen(marker_relative, open_flags);
   if(handle == INVALID_HANDLE)
   {
      int error = GetLastError();
      MagiLog("ERROR", "INIT", StringFormat("No se pudo escribir runtime marker | path=%s | error=%d",
                                            marker_effective,
                                            error));
      return false;
   }

   FileSeek(handle, 0, SEEK_SET);
   string marker_body =
      "runtime_build_tag=" + BOT_A_SUB3_RUNTIME_BUILD_TAG + "\r\n" +
      "run_id=" + g_run_id_sub3 + "\r\n" +
      "storage_mode=COMMON_FILES\r\n" +
      "contract_source=Bot_A_sub1_dataset_flow+MagiBuildSnapshot+gaspar_context\r\n" +
      "skip_invalid_snapshots=" + (InpSkipInvalidSnapshots ? "true" : "false") + "\r\n" +
      "run_start_local=" + MagiDateTimeToIso(g_run_started_at_sub3) + "\r\n";

   ResetLastError();
   if(FileWriteString(handle, marker_body) == 0)
   {
      int write_error = GetLastError();
      FileClose(handle);
      MagiLog("ERROR", "INIT", StringFormat("No se pudo persistir runtime marker | path=%s | error=%d",
                                            marker_effective,
                                            write_error));
      return false;
   }

   FileClose(handle);
   MagiLog("INFO", "INIT", "Runtime marker persistido: " + marker_effective);
   return true;
}

void LogStoragePolicySub3()
{
   string base_path = MagiResolveStorageBasePath(true);
   string runtime_mode = ((bool)MQLInfoInteger(MQL_TESTER) ? "TESTER" : "LIVE_OR_CHART");
   string run_root_relative = BuildRunRootRelativePathSub3();
   string run_root = base_path + "\\" + run_root_relative;

   MagiLog("INFO", "INIT", "Politica de almacenamiento: " + MagiBuildStorageDescription(g_storage_policy_sub3));
   MagiLog("INFO", "INIT", "Modo de ejecucion detectado: " + runtime_mode);
   MagiLog("INFO", "INIT", "Modo de storage forzado para Bot_A_sub3: COMMON_FILES");
   MagiLog("INFO", "INIT", "RUNTIME_BUILD_TAG: " + BOT_A_SUB3_RUNTIME_BUILD_TAG);
   MagiLog("INFO", "INIT", "Run ID generado: " + g_run_id_sub3);
   MagiLog("INFO", "INIT", "Run start local: " + MagiDateTimeToIso(g_run_started_at_sub3));
   MagiLog("INFO", "INIT", "Ruta base COMMON_FILES para esta corrida: " + run_root);
   MagiLog("INFO", "INIT", "Sub3 simple: flujo de dataset de sub1 con gaspar_context en el snapshot.");
}

bool IsNewClosedBarForSub3(const string symbol,const int symbol_index,datetime &bar_time)
{
   bar_time = iTime(symbol, InpAnchorTimeframe, 1);
   if(bar_time <= 0)
      return false;

   if(g_last_processed_bar_sub3[symbol_index] == bar_time)
      return false;

   g_last_processed_bar_sub3[symbol_index] = bar_time;
   return true;
}

bool WasBarAlreadyPersistedSub3(const int symbol_index,const datetime bar_time)
{
   return (g_last_persisted_bar_sub3[symbol_index] == bar_time && bar_time > 0);
}

void MarkBarAsPersistedSub3(const int symbol_index,const datetime bar_time)
{
   g_last_persisted_bar_sub3[symbol_index] = bar_time;
}

void LogExpectedPathsSub3(const string symbol,const datetime bar_time)
{
   MagiSnapshot preview;
   MagiInitializeSnapshot(preview);
   preview.symbol = symbol;
   preview.anchor_timeframe = MagiTimeframeToLabel(InpAnchorTimeframe);
   preview.primary_timeframe = MagiTimeframeToLabel(InpPrimaryTimeframe);
   preview.bar_timestamp = bar_time;

   if(InpWriteCsv)
   {
      string csv_relative = MagiBuildDatasetDirectory(g_storage_policy_sub3, preview);
      string csv_name = MagiBuildDatasetBaseName(g_storage_policy_sub3, preview) + ".csv";
      string csv_path = MagiResolveStorageBasePath(true) + "\\" +
                        (csv_relative == "" ? csv_name : csv_relative + "\\" + csv_name);
      MagiLog("INFO", symbol, "Ruta esperada CSV: " + csv_path);
   }

   if(InpWriteJsonl)
   {
      string jsonl_relative = MagiBuildDatasetDirectory(g_storage_policy_sub3, preview);
      string jsonl_name = MagiBuildDatasetBaseName(g_storage_policy_sub3, preview) + ".jsonl";
      string jsonl_path = MagiResolveStorageBasePath(true) + "\\" +
                          (jsonl_relative == "" ? jsonl_name : jsonl_relative + "\\" + jsonl_name);
      MagiLog("INFO", symbol, "Ruta esperada JSONL: " + jsonl_path);
   }
}

void PersistSnapshotSub3(const MagiSnapshot &snapshot,const int symbol_index,const datetime trigger_bar_time)
{
   if(WasBarAlreadyPersistedSub3(symbol_index, trigger_bar_time))
   {
      MagiLog("WARN", snapshot.symbol, StringFormat("Barra ancla ya persistida y omitida: %s", MagiDateTimeToUtcIso(trigger_bar_time)));
      return;
   }

   string validation_reason = "";
   if(!MagiValidateSnapshotForDatasetDiagnosticWrite(snapshot, validation_reason))
   {
      MagiLog("ERROR", snapshot.symbol, "Snapshot omitido por validacion minima de escritura: " + validation_reason);
      return;
   }

   bool write_ok = true;
   string csv_path = "";
   string jsonl_path = "";

   if(InpWriteCsv)
      write_ok = write_ok && MagiAppendSnapshotCsv(g_storage_policy_sub3, snapshot, csv_path);

   if(InpWriteJsonl)
      write_ok = write_ok && MagiAppendSnapshotJsonl(g_storage_policy_sub3, snapshot, jsonl_path);

   if(!write_ok)
   {
      MagiLog("ERROR", snapshot.symbol, StringFormat("No se pudo persistir snapshot %s en dataset", snapshot.snapshot_id));
      return;
   }

   MarkBarAsPersistedSub3(symbol_index, trigger_bar_time);

   if(csv_path != "")
      MagiLog("INFO", snapshot.symbol, "Ruta final CSV efectiva: " + csv_path);

   if(jsonl_path != "")
      MagiLog("INFO", snapshot.symbol, "Ruta final JSONL efectiva: " + jsonl_path);
}

void ProcessDatasetSymbolSub3(const string symbol,const int symbol_index,const datetime bar_time)
{
   MagiSnapshot snapshot;
   bool build_ok = MagiBuildSnapshot(symbol, InpAnchorTimeframe, InpPrimaryTimeframe, "tester", snapshot);

   if(!build_ok)
   {
      MagiLog("WARN", symbol, "Snapshot con datos parciales: " + MagiJoinValidationIssues(snapshot.validation));
      if(InpSkipInvalidSnapshots)
         return;
   }

   PersistSnapshotSub3(snapshot, symbol_index, bar_time);
}

int OnInit()
{
   if(!InpWriteCsv && !InpWriteJsonl)
   {
      MagiLog("ERROR", "INIT", "Bot_A_sub3 requiere al menos un formato activo: CSV o JSONL");
      return INIT_FAILED;
   }

   if(!SelectDatasetSymbolsSub3())
   {
      MagiLog("ERROR", "INIT", "No hay simbolos validos para Bot_A_sub3");
      return INIT_FAILED;
   }

   InitializeRunContextSub3();
   BuildStoragePolicySub3();
   LogStoragePolicySub3();
   WriteRuntimeMarkerSub3();

   for(int i = 0; i < ArraySize(g_symbols_sub3); i++)
   {
      datetime preview_bar = iTime(g_symbols_sub3[i], InpAnchorTimeframe, 1);
      if(preview_bar > 0)
         LogExpectedPathsSub3(g_symbols_sub3[i], preview_bar);
   }

   MagiLog("INFO", "INIT", StringFormat("Bot_A_sub3 simple listo. Simbolos=%d | anchor=%s | primary=%s",
                                        ArraySize(g_symbols_sub3),
                                        MagiTimeframeToLabel(InpAnchorTimeframe),
                                        MagiTimeframeToLabel(InpPrimaryTimeframe)));
   return INIT_SUCCEEDED;
}

void OnTick()
{
   for(int i = 0; i < ArraySize(g_symbols_sub3); i++)
   {
      datetime bar_time = 0;
      if(!IsNewClosedBarForSub3(g_symbols_sub3[i], i, bar_time))
         continue;

      ProcessDatasetSymbolSub3(g_symbols_sub3[i], i, bar_time);
   }
}
