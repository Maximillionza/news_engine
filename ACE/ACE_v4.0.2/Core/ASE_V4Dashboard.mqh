#ifndef ASE_V4DASHBOARD_MQH
#define ASE_V4DASHBOARD_MQH
#include "../Models/ASE_ConfluenceTypes.mqh"
#include "../Models/ASE_Config.mqh"
#include "../Utilities/ASE_Broker.mqh"

class CASE_V4Dashboard
{
private:
   string m_prefix;
   string m_lines[16];
   void Put(int idx,string text)
   {
      string name=m_prefix+IntegerToString(idx);
      if(ObjectFind(0,name)<0) ObjectCreate(0,name,OBJ_LABEL,0,0,0);
      ObjectSetInteger(0,name,OBJPROP_CORNER,CORNER_LEFT_UPPER);
      ObjectSetInteger(0,name,OBJPROP_XDISTANCE,12);
      ObjectSetInteger(0,name,OBJPROP_YDISTANCE,18+idx*16);
      ObjectSetInteger(0,name,OBJPROP_FONTSIZE,9);
      ObjectSetString(0,name,OBJPROP_FONT,"Consolas");
      ObjectSetString(0,name,OBJPROP_TEXT,text);
   }
public:
   CASE_V4Dashboard():m_prefix("ACE_V4_DASH_"){}
   void Initialize(){if(!InpShowV4Dashboard)return;for(int i=0;i<16;i++)Put(i,"");}
   void Update(const ConfluenceResult &c,string regime,string trigger,string authority,string adaptiveReason)
   {
      if(!InpShowV4Dashboard)return;
      string dir=(c.direction==DIR_LONG)?"BUY":(c.direction==DIR_SHORT)?"SELL":"NONE";
      string decision=c.qualified?"QUALIFIED":"BLOCK";
      if(c.executionDecision!="") decision=c.executionDecision;
      Put(0,"ACE v4.0 | MODE="+EnumToString(InpAceV4Mode));
      Put(1,"REGIME      "+regime);
      Put(2,"DIRECTION   "+dir);
      Put(3,"SETUP       "+ASE_ArchetypeName(c.archetype));
      Put(4,"GRADE       "+ASE_GradeName(c.grade));
      Put(5,StringFormat("CORE        %d/%d   CONF %d/%d",c.coreMet,c.coreTotal,c.enhancersMet,c.enhancersTotal));
      Put(6,StringFormat("LONG %.1f   SHORT %.1f   SEP %.1f",c.longScore,c.shortScore,c.separation));
      Put(7,"CONFLICT    "+(c.conflict.hasConflict?c.conflict.reason:"NONE"));
      Put(8,"DNA         "+c.setupDNA);
      Put(9,"SEQUENCE    "+DoubleToString(c.sequenceQuality,2)+(c.sequenceCoherent?" COHERENT":" INCOMPLETE"));
      Put(10,"TRIGGER     "+trigger);
      Put(11,"DECISION    "+decision);
      Put(12,"AUTHORITY   "+authority);
      Put(13,"ADAPT       "+adaptiveReason);
      Put(14,"SPREAD      "+DoubleToString(CASE_Broker::GetSpread(),1));
      Put(15,"FRESHNESS   "+DoubleToString(c.avgFreshness,2));
      ChartRedraw();
   }
   void Clear(){for(int i=0;i<16;i++){string n=m_prefix+IntegerToString(i);if(ObjectFind(0,n)>=0)ObjectDelete(0,n);}}
};
#endif
