#ifndef ASE_ORCHESTRATOR_MQH
#define ASE_ORCHESTRATOR_MQH
#include "ASE_PositionClusterProtection.mqh"
#include "ASE_RiskEngine.mqh"

struct OrchestratorResult
{
   bool allowed;
   string reason;
   void Clear(){allowed=false;reason="";}
};

class CASE_Orchestrator
{
public:
   bool CheckPortfolio(CASE_PositionClusterProtection &cluster, int maxPositions, OrchestratorResult &out)
   {
      out.Clear();
      if(!cluster.AllowNewTrade(maxPositions)){out.reason="Portfolio position limit / cluster protection";return false;}
      out.allowed=true; out.reason="Portfolio risk state clear"; return true;
   }
};
#endif
