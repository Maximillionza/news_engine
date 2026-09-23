#ifndef ASE_DISCIPLINEENGINE_MQH
#define ASE_DISCIPLINEENGINE_MQH
#include "ASE_SessionEngine.mqh"
#include "ASE_NewsEngine.mqh"
#include "ASE_ValidationEngine.mqh"
#include "../Utilities/ASE_Broker.mqh"

struct DisciplineResult
{
   bool allowed;
   string reason;
   void Clear(){allowed=false;reason="";}
};

class CASE_DisciplineEngine
{
public:
   bool Check(CASE_SessionEngine &session, CASE_NewsEngine &news, CASE_ValidationEngine &valid, double maxSpread, DisciplineResult &out)
   {
      out.Clear();
      if(!session.IsTradingSession()){out.reason="Off-session";return false;}
      if(news.IsNewsBlocked()){out.reason=StringFormat("News block (%d min)",news.MinutesToEvent());return false;}
      if(!valid.SpreadAcceptable(maxSpread)){out.reason=StringFormat("Spread %.1f exceeds limit %d",CASE_Broker::GetSpread(),(int)maxSpread);return false;}
      out.allowed=true; out.reason="Safety conditions clear"; return true;
   }
};
#endif
