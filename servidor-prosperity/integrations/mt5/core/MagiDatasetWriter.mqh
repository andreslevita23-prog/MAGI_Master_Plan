#ifndef __MAGI_DATASET_WRITER_MQH__
#define __MAGI_DATASET_WRITER_MQH__

#property strict

#include "MagiSerializer.mqh"

enum MagiStorageMode
{
   MAGI_STORAGE_LOCAL = 0,
   MAGI_STORAGE_COMMON = 1
};

struct MagiStoragePolicy
{
   MagiStorageMode mode;
   bool            fallback_to_local;
   string          root_folder;
   string          subfolder;
   bool            split_by_symbol;
   bool            split_by_timeframe;
   bool            split_by_date;
   string          dataset_prefix;
};

struct MagiDatasetTarget
{
   string file_name;
   string directory;
   string relative_path;
   string effective_path;
   bool   use_common;
   bool   existed_before_open;
};

string MagiStorageModeToString(const MagiStorageMode mode)
{
   return (mode == MAGI_STORAGE_COMMON ? "COMMON_FILES" : "LOCAL_FILES");
}

string MagiSanitizePathSegment(const string raw_value)
{
   string value = raw_value;
   StringTrimLeft(value);
   StringTrimRight(value);

   string invalid_chars = "<>:\"/\\|?*";
   for(int i = 0; i < StringLen(invalid_chars); i++)
   {
      string current = StringSubstr(invalid_chars, i, 1);
      StringReplace(value, current, "_");
   }

   StringReplace(value, " ", "_");
   while(StringFind(value, "__") >= 0)
      StringReplace(value, "__", "_");

   return value;
}

string MagiNormalizeFolderPath(const string raw_path)
{
   string normalized = raw_path;
   StringReplace(normalized, "/", "\\");
   while(StringFind(normalized, "\\\\") >= 0)
      StringReplace(normalized, "\\\\", "\\");

   StringTrimLeft(normalized);
   StringTrimRight(normalized);

   while(StringLen(normalized) > 0 && StringSubstr(normalized, 0, 1) == "\\")
      normalized = StringSubstr(normalized, 1);

   while(StringLen(normalized) > 0 && StringSubstr(normalized, StringLen(normalized) - 1, 1) == "\\")
      normalized = StringSubstr(normalized, 0, StringLen(normalized) - 1);

   return normalized;
}

string MagiResolveStorageBasePath(const bool use_common)
{
   if(use_common)
      return TerminalInfoString(TERMINAL_COMMONDATA_PATH) + "\\Files";

   string root = TerminalInfoString(TERMINAL_DATA_PATH);
   return root + "\\MQL5\\Files";
}

string MagiBuildStorageDescription(const MagiStoragePolicy &policy)
{
   return StringFormat("mode=%s | fallback_to_local=%s | root='%s' | subfolder='%s' | split_symbol=%s | split_timeframe=%s | split_date=%s | prefix='%s'",
                       MagiStorageModeToString(policy.mode),
                       (policy.fallback_to_local ? "true" : "false"),
                       policy.root_folder,
                       policy.subfolder,
                       (policy.split_by_symbol ? "true" : "false"),
                       (policy.split_by_timeframe ? "true" : "false"),
                       (policy.split_by_date ? "true" : "false"),
                       policy.dataset_prefix);
}

string MagiBuildDatasetDirectory(const MagiStoragePolicy &policy,const MagiSnapshot &snapshot)
{
   MqlDateTime parts;
   TimeToStruct(snapshot.bar_timestamp, parts);

   string path = MagiNormalizeFolderPath(MagiSanitizePathSegment(policy.root_folder));
   string subfolder = MagiNormalizeFolderPath(policy.subfolder);
   if(subfolder != "")
      path = (path == "" ? subfolder : path + "\\" + subfolder);

   if(policy.split_by_symbol)
      path = (path == "" ? snapshot.symbol : path + "\\" + snapshot.symbol);

   if(policy.split_by_timeframe)
   {
      string timeframe_segment = StringFormat("anchor_%s__primary_%s", snapshot.anchor_timeframe, snapshot.primary_timeframe);
      path = (path == "" ? timeframe_segment : path + "\\" + timeframe_segment);
   }

   if(policy.split_by_date)
   {
      string date_segment = StringFormat("%04d\\%02d\\%02d", parts.year, parts.mon, parts.day);
      path = (path == "" ? date_segment : path + "\\" + date_segment);
   }

   return path;
}

string MagiBuildDatasetBaseName(const MagiStoragePolicy &policy,const MagiSnapshot &snapshot)
{
   MqlDateTime parts;
   TimeToStruct(snapshot.bar_timestamp, parts);

   return StringFormat("%s__symbol_%s__anchor_%s__primary_%s__date_%04d-%02d-%02d",
                       MagiSanitizePathSegment(policy.dataset_prefix),
                       snapshot.symbol,
                       snapshot.anchor_timeframe,
                       snapshot.primary_timeframe,
                       parts.year,
                       parts.mon,
                       parts.day);
}

bool MagiBuildDatasetTarget(const MagiStoragePolicy &policy,
                            const MagiSnapshot &snapshot,
                            const string extension,
                            const bool use_common,
                            MagiDatasetTarget &target)
{
   string directory = MagiBuildDatasetDirectory(policy, snapshot);
   string file_name = MagiBuildDatasetBaseName(policy, snapshot) + "." + extension;
   target.directory = directory;
   target.relative_path = (directory == "" ? file_name : directory + "\\" + file_name);
   target.file_name = target.relative_path;
   target.effective_path = MagiResolveStorageBasePath(use_common) + "\\" + target.relative_path;
   target.use_common = use_common;
   target.existed_before_open = FileIsExist(target.relative_path, use_common ? FILE_COMMON : 0);
   return true;
}

bool MagiEnsureDirectoryTreeExists(const string relative_directory,const bool use_common,string &failure_reason)
{
   failure_reason = "";

   string normalized = MagiNormalizeFolderPath(relative_directory);
   if(normalized == "")
      return true;

   string parts[];
   int total = StringSplit(normalized, '\\', parts);
   if(total <= 0)
   {
      failure_reason = "no se pudo dividir la ruta relativa";
      return false;
   }

   string current = "";
   int common_flag = (use_common ? FILE_COMMON : 0);

   for(int i = 0; i < total; i++)
   {
      string segment = MagiSanitizePathSegment(parts[i]);
      if(segment == "")
         continue;

      current = (current == "" ? segment : current + "\\" + segment);

      ResetLastError();
      if(FolderCreate(current, common_flag))
         continue;

      int error = GetLastError();
      if(error == 5019)
         continue;

      failure_reason = StringFormat("FolderCreate fallo en '%s' con error=%d", current, error);
      return false;
   }

   return true;
}

bool MagiTryGetBarOhlc(const string symbol,const ENUM_TIMEFRAMES timeframe,const datetime bar_time,MqlRates &bar)
{
   int shift = iBarShift(symbol, timeframe, bar_time, true);
   if(shift < 0)
      return false;

   MqlRates rates[1];
   ArraySetAsSeries(rates, true);
   if(CopyRates(symbol, timeframe, shift, 1, rates) != 1)
      return false;

   bar = rates[0];
   return (bar.time == bar_time);
}

ENUM_TIMEFRAMES MagiLabelToTimeframe(const string label)
{
   if(label == "M1")  return PERIOD_M1;
   if(label == "M5")  return PERIOD_M5;
   if(label == "M15") return PERIOD_M15;
   if(label == "M30") return PERIOD_M30;
   if(label == "H1")  return PERIOD_H1;
   if(label == "H4")  return PERIOD_H4;
   if(label == "D1")  return PERIOD_D1;
   return PERIOD_CURRENT;
}

bool MagiValidateSnapshotForDatasetWrite(const MagiSnapshot &snapshot,string &reason)
{
   reason = "";

   if(snapshot.timestamp <= 0)
   {
      reason = "timestamp invalido";
      return false;
   }

   if(snapshot.symbol == "")
   {
      reason = "symbol vacio";
      return false;
   }

   if(snapshot.anchor_timeframe == "" || snapshot.primary_timeframe == "")
   {
      reason = "timeframe vacio";
      return false;
   }

   if(snapshot.bar_timestamp <= 0)
   {
      reason = "bar_timestamp invalido";
      return false;
   }

   if(snapshot.anchor_bar_timestamp <= 0)
   {
      reason = "anchor_bar_timestamp invalido";
      return false;
   }

   if(snapshot.anchor_open <= 0.0 || snapshot.anchor_high <= 0.0 || snapshot.anchor_low <= 0.0 || snapshot.anchor_close <= 0.0)
   {
      reason = "anchor OHLC invalido";
      return false;
   }

   if(snapshot.anchor_high < snapshot.anchor_low ||
      snapshot.anchor_open > snapshot.anchor_high ||
      snapshot.anchor_open < snapshot.anchor_low ||
      snapshot.anchor_close > snapshot.anchor_high ||
      snapshot.anchor_close < snapshot.anchor_low)
   {
      reason = "anchor OHLC inconsistente";
      return false;
   }

   ENUM_TIMEFRAMES primary_tf = MagiLabelToTimeframe(snapshot.primary_timeframe);
   if(primary_tf == PERIOD_CURRENT)
   {
      reason = "primary_timeframe no reconocido";
      return false;
   }

   MqlRates bar;
   if(!MagiTryGetBarOhlc(snapshot.symbol, primary_tf, snapshot.bar_timestamp, bar))
   {
      reason = "no se pudo reconstruir OHLC de la barra objetivo";
      return false;
   }

   if(bar.open <= 0.0 || bar.high <= 0.0 || bar.low <= 0.0 || bar.close <= 0.0)
   {
      reason = "OHLC invalido";
      return false;
   }

   if(bar.high < bar.low)
   {
      reason = "OHLC inconsistente: high < low";
      return false;
   }

   if(bar.open > bar.high || bar.open < bar.low || bar.close > bar.high || bar.close < bar.low)
   {
      reason = "OHLC inconsistente: open/close fuera del rango";
      return false;
   }

   return true;
}

bool MagiAppendTextLineWithPolicy(const MagiStoragePolicy &policy,
                                  const MagiSnapshot &snapshot,
                                  const string extension,
                                  const string line,
                                  const bool write_header,
                                  const string header,
                                  string &effective_path_used)
{
   bool target_modes[2];
   int mode_count = 0;

   target_modes[mode_count++] = (policy.mode == MAGI_STORAGE_COMMON);
   if(policy.mode == MAGI_STORAGE_COMMON && policy.fallback_to_local)
      target_modes[mode_count++] = false;

   for(int i = 0; i < mode_count; i++)
   {
      bool use_common = target_modes[i];
      MagiDatasetTarget target;
      if(!MagiBuildDatasetTarget(policy, snapshot, extension, use_common, target))
      {
         if(i + 1 < mode_count)
            MagiLog("WARN", snapshot.symbol, "Fallo la preparacion en Common Files. Se intentara Local Files sin fallback implicito adicional.");
         continue;
      }

      string mkdir_reason = "";
      if(!MagiEnsureDirectoryTreeExists(target.directory, use_common, mkdir_reason))
      {
         MagiLog("ERROR", snapshot.symbol, StringFormat("No se pudo preparar carpeta dataset | path=%s | mode=%s | detail=%s",
                                                        target.effective_path,
                                                        MagiStorageModeToString(use_common ? MAGI_STORAGE_COMMON : MAGI_STORAGE_LOCAL),
                                                        mkdir_reason));
         continue;
      }

      int open_flags = FILE_READ | FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_SHARE_READ | FILE_SHARE_WRITE;
      if(use_common)
         open_flags |= FILE_COMMON;

      ResetLastError();
      int handle = FileOpen(target.file_name, open_flags);
      if(handle == INVALID_HANDLE)
      {
         int error = GetLastError();
         MagiLog("ERROR", snapshot.symbol, StringFormat("No se pudo abrir archivo dataset | path=%s | relative=%s | mode=%s | error=%d",
                                                        target.effective_path,
                                                        target.relative_path,
                                                        MagiStorageModeToString(use_common ? MAGI_STORAGE_COMMON : MAGI_STORAGE_LOCAL),
                                                        error));
         if(i + 1 < mode_count)
            MagiLog("WARN", snapshot.symbol, "Fallo apertura en Common Files. Se intenta Local Files porque fallback_to_local=true.");
         continue;
      }

      bool is_empty = (FileSize(handle) == 0);
      FileSeek(handle, 0, SEEK_END);

      if(write_header && is_empty)
      {
         ResetLastError();
         if(FileWriteString(handle, header + "\r\n") == 0)
         {
            int header_error = GetLastError();
            FileClose(handle);
            MagiLog("ERROR", snapshot.symbol, StringFormat("No se pudo escribir cabecera CSV | path=%s | error=%d",
                                                           target.effective_path,
                                                           header_error));
            continue;
         }
      }

      ResetLastError();
      if(FileWriteString(handle, line + "\r\n") == 0)
      {
         int write_error = GetLastError();
         FileClose(handle);
         MagiLog("ERROR", snapshot.symbol, StringFormat("No se pudo escribir fila dataset | path=%s | error=%d",
                                                        target.effective_path,
                                                        write_error));
         continue;
      }

      FileClose(handle);
      effective_path_used = target.effective_path;

      MagiLog("INFO",
              snapshot.symbol,
              StringFormat("Dataset %s | path=%s | mode=%s",
                           (target.existed_before_open ? "append" : "create"),
                           target.effective_path,
                           MagiStorageModeToString(use_common ? MAGI_STORAGE_COMMON : MAGI_STORAGE_LOCAL)));
      return true;
   }

   effective_path_used = "";
   return false;
}

bool MagiAppendSnapshotJsonl(const MagiStoragePolicy &policy,const MagiSnapshot &snapshot,string &effective_path_used)
{
   return MagiAppendTextLineWithPolicy(policy,
                                       snapshot,
                                       "jsonl",
                                       MagiSerializeSnapshotJson(snapshot),
                                       false,
                                       "",
                                       effective_path_used);
}

bool MagiAppendSnapshotCsv(const MagiStoragePolicy &policy,const MagiSnapshot &snapshot,string &effective_path_used)
{
   return MagiAppendTextLineWithPolicy(policy,
                                       snapshot,
                                       "csv",
                                       MagiSerializeSnapshotCsvRow(snapshot),
                                       true,
                                       MagiBuildCsvHeader(),
                                       effective_path_used);
}

#endif
