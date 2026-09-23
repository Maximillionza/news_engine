#ifndef ASE_SENSITIVITYMAP_MQH
#define ASE_SENSITIVITYMAP_MQH
//+------------------------------------------------------------------+
//| ASE v3 — Parameter Sensitivity / Stability Mapping               |
//| Checks whether a parameter set lives on a plateau vs a spike     |
//+------------------------------------------------------------------+
class CASE_SensitivityMap
{
public:
   // Returns true if the center fitness is within delta% of all neighbors
   bool IsStableRegion(
      double center,
      double neighbor1, double neighbor2, double neighbor3,
      double maxDeltaPct = 15.0)
   {
      if(center <= 0) return false;

      double avg = (neighbor1 + neighbor2 + neighbor3) / 3.0;
      double deltaPct = MathAbs(center - avg) / center * 100.0;

      return (deltaPct <= maxDeltaPct);
   }

   // Penalise the fitness score for living in a narrow spike
   double AdjustedFitness(
      double center,
      double neighbor1, double neighbor2, double neighbor3)
   {
      if(!IsStableRegion(center, neighbor1, neighbor2, neighbor3))
         return center * 0.5;   // 50% penalty for unstable region
      return center;
   }
};
#endif // ASE_SENSITIVITYMAP_MQH
