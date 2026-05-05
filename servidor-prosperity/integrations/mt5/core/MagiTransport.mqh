#ifndef __MAGI_TRANSPORT_MQH__
#define __MAGI_TRANSPORT_MQH__

#property strict

#include "MagiCommon.mqh"

bool MagiHttpPostJson(const string url,
                      const string payload,
                      const int timeout_ms,
                      int &http_status,
                      string &response_body,
                      string &response_headers,
                      int &last_error)
{
   char data[];
   char result[];
   int copied = StringToCharArray(payload, data, 0, WHOLE_ARRAY, CP_UTF8);
   bool removed_null_terminator = false;

   if(copied > 0 && ArraySize(data) > 0 && data[ArraySize(data) - 1] == 0)
   {
      ArrayResize(data, ArraySize(data) - 1);
      removed_null_terminator = true;
   }

   Print("[MAGI][DEBUG][TRANSPORT] StringLen=", StringLen(payload),
         " ArraySize=", ArraySize(data),
         " removed_null=", removed_null_terminator);

   string headers = "Content-Type: application/json\r\n";
   ResetLastError();
   http_status = WebRequest("POST", url, headers, timeout_ms, data, result, response_headers);
   last_error = GetLastError();
   response_body = CharArrayToString(result, 0, WHOLE_ARRAY, CP_UTF8);
   return (http_status != -1);
}

#endif
