//+------------------------------------------------------------------+
//|                                                      Bot_C.mq5    |
//|   Caja negra operativa MAGI: observador MT5, no ejecuta ordenes   |
//+------------------------------------------------------------------+
#property strict

input string AuditRootFolder = "MAGI\\audit";
input long MagicNumberFilter = 0;      // 0 = auditar todos los magic numbers
input int SummaryRefreshSeconds = 60;
input double BreakevenTolerance = 0.01;

struct BotCStats
{
    int opened;
    int closed;
    int modified;
    int winners;
    int losers;
    int breakeven;
    int anomalies;
    double net_profit;
    double peak_profit;
    double max_drawdown;
    string symbols;
    string decisions;
};

BotCStats g_stats;

int OnInit()
{
    ResetStats();
    EventSetTimer(SummaryRefreshSeconds);
    RebuildDailySummary();
    Print("Bot C caja negra MAGI iniciado. AuditRootFolder=", AuditRootFolder, " MagicNumberFilter=", MagicNumberFilter);
    return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
    EventKillTimer();
    WriteDailySummary();
    Print("Bot C detenido");
}

void OnTimer()
{
    WriteFloatingSnapshotEvents();
    WriteDailySummary();
}

void OnTradeTransaction(const MqlTradeTransaction &trans,
                        const MqlTradeRequest &request,
                        const MqlTradeResult &result)
{
    if (trans.type != TRADE_TRANSACTION_DEAL_ADD &&
        trans.type != TRADE_TRANSACTION_ORDER_UPDATE &&
        trans.type != TRADE_TRANSACTION_POSITION)
    {
        return;
    }

    string symbol = trans.symbol;
    ulong deal = trans.deal;
    ulong order = trans.order;
    ulong position_id = trans.position;
    long magic = 0;
    string comment = "";
    double price = trans.price;
    double volume = trans.volume;
    double profit = 0.0;
    string event_type = TransactionTypeToText(trans.type);
    string anomaly = "";

    if (deal > 0 && HistoryDealSelect(deal))
    {
        symbol = HistoryDealGetString(deal, DEAL_SYMBOL);
        magic = HistoryDealGetInteger(deal, DEAL_MAGIC);
        comment = HistoryDealGetString(deal, DEAL_COMMENT);
        price = HistoryDealGetDouble(deal, DEAL_PRICE);
        volume = HistoryDealGetDouble(deal, DEAL_VOLUME);
        profit = HistoryDealGetDouble(deal, DEAL_PROFIT) + HistoryDealGetDouble(deal, DEAL_SWAP) + HistoryDealGetDouble(deal, DEAL_COMMISSION);
        long entry = HistoryDealGetInteger(deal, DEAL_ENTRY);
        event_type = DealEntryToEvent(entry);
    }
    else if (PositionSelect(symbol))
    {
        magic = PositionGetInteger(POSITION_MAGIC);
        comment = PositionGetString(POSITION_COMMENT);
        price = PositionGetDouble(POSITION_PRICE_CURRENT);
        volume = PositionGetDouble(POSITION_VOLUME);
    }

    if (!ShouldAuditMagic(magic))
        return;

    string decision_id = ExtractDecisionIdFromComment(comment);
    if (decision_id == "")
        anomaly = AppendAnomaly(anomaly, "orden_sin_decision_id");

    double sl = 0.0;
    double tp = 0.0;
    double floating_profit = 0.0;
    if (PositionSelect(symbol))
    {
        sl = PositionGetDouble(POSITION_SL);
        tp = PositionGetDouble(POSITION_TP);
        floating_profit = PositionGetDouble(POSITION_PROFIT);
    }

    if (result.retcode != TRADE_RETCODE_DONE && result.retcode != 0)
        anomaly = AppendAnomaly(anomaly, "retcode_no_done_" + IntegerToString((int)result.retcode));

    UpdateStats(event_type, symbol, decision_id, profit, anomaly);

    string json = "{";
    json += JsonPair("schema_version", "magi.bot_c.event.v1") + ",";
    json += JsonPair("event_type", event_type) + ",";
    json += JsonPair("timestamp", UtcNowIso()) + ",";
    json += JsonPair("symbol", symbol) + ",";
    json += JsonNumber("magic_number", (double)magic) + ",";
    json += JsonNumber("ticket", (double)position_id) + ",";
    json += JsonNumber("deal", (double)deal) + ",";
    json += JsonNumber("order", (double)order) + ",";
    json += JsonPair("comment", comment) + ",";
    json += JsonPair("decision_id", decision_id) + ",";
    json += JsonPair("snapshot_id", "") + ",";
    json += JsonNumber("price", price) + ",";
    json += JsonNumber("volume", volume) + ",";
    json += JsonNumber("sl", sl) + ",";
    json += JsonNumber("tp", tp) + ",";
    json += JsonNumber("profit", profit) + ",";
    json += JsonNumber("floating_profit", floating_profit) + ",";
    json += JsonNumber("retcode", (double)result.retcode) + ",";
    json += JsonPair("anomaly", anomaly);
    json += "}";

    AppendJsonLine(EventsPath(), json);
    WriteDailySummary();
}

void WriteFloatingSnapshotEvents()
{
    for (int i = PositionsTotal() - 1; i >= 0; i--)
    {
        ulong ticket = PositionGetTicket(i);
        if (ticket == 0 || !PositionSelectByTicket(ticket))
            continue;

        long magic = PositionGetInteger(POSITION_MAGIC);
        if (!ShouldAuditMagic(magic))
            continue;

        string symbol = PositionGetString(POSITION_SYMBOL);
        string comment = PositionGetString(POSITION_COMMENT);
        string decision_id = ExtractDecisionIdFromComment(comment);
        string anomaly = (decision_id == "" ? "posicion_abierta_sin_decision_id" : "");

        string json = "{";
        json += JsonPair("schema_version", "magi.bot_c.event.v1") + ",";
        json += JsonPair("event_type", "floating_snapshot") + ",";
        json += JsonPair("timestamp", UtcNowIso()) + ",";
        json += JsonPair("symbol", symbol) + ",";
        json += JsonNumber("magic_number", (double)magic) + ",";
        json += JsonNumber("ticket", (double)ticket) + ",";
        json += JsonNumber("deal", 0.0) + ",";
        json += JsonNumber("order", 0.0) + ",";
        json += JsonPair("comment", comment) + ",";
        json += JsonPair("decision_id", decision_id) + ",";
        json += JsonPair("snapshot_id", "") + ",";
        json += JsonNumber("price", PositionGetDouble(POSITION_PRICE_CURRENT)) + ",";
        json += JsonNumber("volume", PositionGetDouble(POSITION_VOLUME)) + ",";
        json += JsonNumber("sl", PositionGetDouble(POSITION_SL)) + ",";
        json += JsonNumber("tp", PositionGetDouble(POSITION_TP)) + ",";
        json += JsonNumber("profit", 0.0) + ",";
        json += JsonNumber("floating_profit", PositionGetDouble(POSITION_PROFIT)) + ",";
        json += JsonNumber("retcode", 0.0) + ",";
        json += JsonPair("anomaly", anomaly);
        json += "}";

        AppendJsonLine(EventsPath(), json);
    }
}

void ResetStats()
{
    g_stats.opened = 0;
    g_stats.closed = 0;
    g_stats.modified = 0;
    g_stats.winners = 0;
    g_stats.losers = 0;
    g_stats.breakeven = 0;
    g_stats.anomalies = 0;
    g_stats.net_profit = 0.0;
    g_stats.peak_profit = 0.0;
    g_stats.max_drawdown = 0.0;
    g_stats.symbols = "";
    g_stats.decisions = "";
}

void UpdateStats(const string event_type,const string symbol,const string decision_id,const double profit,const string anomaly)
{
    if (event_type == "open")
        g_stats.opened++;
    else if (event_type == "close")
    {
        g_stats.closed++;
        g_stats.net_profit += profit;
        if (profit > BreakevenTolerance)
            g_stats.winners++;
        else if (profit < -BreakevenTolerance)
            g_stats.losers++;
        else
            g_stats.breakeven++;
    }
    else if (event_type == "modify" || event_type == "position_update" || event_type == "order_update")
        g_stats.modified++;

    if (anomaly != "")
        g_stats.anomalies++;

    g_stats.peak_profit = MathMax(g_stats.peak_profit, g_stats.net_profit);
    g_stats.max_drawdown = MathMax(g_stats.max_drawdown, g_stats.peak_profit - g_stats.net_profit);
    AddUniqueToken(g_stats.symbols, symbol);
    AddUniqueToken(g_stats.decisions, decision_id);
}

void WriteDailySummary()
{
    int open_positions = CountAuditedOpenPositions();
    string json = "{";
    json += JsonPair("schema_version", "magi.bot_c.daily_summary.v1") + ",";
    json += JsonPair("date", DateSegment()) + ",";
    json += JsonPair("updated_at", UtcNowIso()) + ",";
    json += JsonNumber("operaciones_abiertas", (double)g_stats.opened) + ",";
    json += JsonNumber("operaciones_cerradas", (double)g_stats.closed) + ",";
    json += JsonNumber("ganadoras", (double)g_stats.winners) + ",";
    json += JsonNumber("perdedoras", (double)g_stats.losers) + ",";
    json += JsonNumber("breakeven", (double)g_stats.breakeven) + ",";
    json += JsonNumber("profit_neto", g_stats.net_profit) + ",";
    json += JsonNumber("drawdown_aproximado", g_stats.max_drawdown) + ",";
    json += JsonPair("simbolos_operados", g_stats.symbols) + ",";
    json += JsonPair("decisiones_ejecutadas", g_stats.decisions) + ",";
    json += JsonNumber("decisiones_sin_ejecutar_detectables", 0.0) + ",";
    json += JsonNumber("posiciones_abiertas_al_cierre", (double)open_positions) + ",";
    json += JsonNumber("anomalias", (double)g_stats.anomalies);
    json += "}";

    WriteTextFile(SummaryPath(), json);
}

void RebuildDailySummary()
{
    WriteDailySummary();
}

int CountAuditedOpenPositions()
{
    int total = 0;
    for (int i = PositionsTotal() - 1; i >= 0; i--)
    {
        ulong ticket = PositionGetTicket(i);
        if (ticket == 0 || !PositionSelectByTicket(ticket))
            continue;
        if (ShouldAuditMagic(PositionGetInteger(POSITION_MAGIC)))
            total++;
    }
    return total;
}

bool ShouldAuditMagic(const long magic)
{
    return (MagicNumberFilter == 0 || magic == MagicNumberFilter);
}

string DealEntryToEvent(const long entry)
{
    if (entry == DEAL_ENTRY_IN)
        return "open";
    if (entry == DEAL_ENTRY_OUT || entry == DEAL_ENTRY_OUT_BY)
        return "close";
    if (entry == DEAL_ENTRY_INOUT)
        return "close_open";
    return "deal";
}

string TransactionTypeToText(const ENUM_TRADE_TRANSACTION_TYPE type)
{
    if (type == TRADE_TRANSACTION_ORDER_UPDATE)
        return "order_update";
    if (type == TRADE_TRANSACTION_POSITION)
        return "position_update";
    if (type == TRADE_TRANSACTION_DEAL_ADD)
        return "deal";
    return "trade_transaction";
}

string ExtractDecisionIdFromComment(const string comment)
{
    int pos = StringFind(comment, "MAGI|");
    if (pos < 0)
        return "";
    int start = pos + 5;
    int end = StringFind(comment, "|", start);
    if (end < 0)
        end = StringLen(comment);
    return StringSubstr(comment, start, end - start);
}

string AppendAnomaly(string current,const string next)
{
    if (next == "")
        return current;
    if (current == "")
        return next;
    return current + ";" + next;
}

void AddUniqueToken(string &target,const string token)
{
    if (token == "")
        return;
    string wrapped = ";" + target + ";";
    if (StringFind(wrapped, ";" + token + ";") >= 0)
        return;
    if (target != "")
        target += ";";
    target += token;
}

string EventsPath()
{
    return DayFolder() + "\\bot_c_events.jsonl";
}

string SummaryPath()
{
    return DayFolder() + "\\bot_c_daily_summary.json";
}

string DayFolder()
{
    return AuditRootFolder + "\\" + DateSegment();
}

string DateSegment()
{
    MqlDateTime parts;
    TimeToStruct(TimeGMT(), parts);
    return StringFormat("%04d-%02d-%02d", parts.year, parts.mon, parts.day);
}

string UtcNowIso()
{
    MqlDateTime parts;
    TimeToStruct(TimeGMT(), parts);
    return StringFormat("%04d-%02d-%02dT%02d:%02d:%02dZ", parts.year, parts.mon, parts.day, parts.hour, parts.min, parts.sec);
}

void AppendJsonLine(const string relative_path,const string line)
{
    EnsureFoldersFor(relative_path);
    int handle = FileOpen(relative_path, FILE_READ | FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_SHARE_READ | FILE_SHARE_WRITE);
    if (handle == INVALID_HANDLE)
    {
        Print("Bot C no pudo abrir ", relative_path, " | error=", GetLastError());
        return;
    }
    FileSeek(handle, 0, SEEK_END);
    FileWriteString(handle, line + "\r\n");
    FileClose(handle);
}

void WriteTextFile(const string relative_path,const string content)
{
    EnsureFoldersFor(relative_path);
    int handle = FileOpen(relative_path, FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_SHARE_READ | FILE_SHARE_WRITE);
    if (handle == INVALID_HANDLE)
    {
        Print("Bot C no pudo escribir ", relative_path, " | error=", GetLastError());
        return;
    }
    FileWriteString(handle, content);
    FileClose(handle);
}

void EnsureFoldersFor(const string relative_path)
{
    string normalized = relative_path;
    StringReplace(normalized, "/", "\\");
    string parts[];
    int total = StringSplit(normalized, '\\', parts);
    string current = "";
    for (int i = 0; i < total - 1; i++)
    {
        if (parts[i] == "")
            continue;
        current = (current == "" ? parts[i] : current + "\\" + parts[i]);
        FolderCreate(current);
    }
}

string JsonPair(const string key,const string value)
{
    return "\"" + EscapeJson(key) + "\":\"" + EscapeJson(value) + "\"";
}

string JsonNumber(const string key,const double value)
{
    return "\"" + EscapeJson(key) + "\":" + DoubleToString(value, 8);
}

string EscapeJson(string value)
{
    StringReplace(value, "\\", "\\\\");
    StringReplace(value, "\"", "\\\"");
    StringReplace(value, "\r", "\\r");
    StringReplace(value, "\n", "\\n");
    StringReplace(value, "\t", "\\t");
    return value;
}
