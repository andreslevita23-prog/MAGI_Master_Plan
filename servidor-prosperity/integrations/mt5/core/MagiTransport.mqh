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
   StringToCharArray(payload, data, 0, WHOLE_ARRAY, CP_UTF8);

   string headers = "Content-Type: application/json\r\n";
   ResetLastError();
   http_status = WebRequest("POST", url, headers, timeout_ms, data, result, response_headers);
   last_error = GetLastError();
   response_body = CharArrayToString(result, 0, WHOLE_ARRAY, CP_UTF8);
   return (http_status != -1);
}

#endif
