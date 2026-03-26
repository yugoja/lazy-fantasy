import { Card } from '@/components/ui/card';
import { Trophy, Target, TrendingUp, Flame, type LucideIcon } from 'lucide-react';

interface StatCardProps {
  icon: LucideIcon;
  value: string | number;
  label: string;
  meta?: string;
  change?: string;
  iconColor?: string;
}

function StatCard({ icon: Icon, value, label, meta, change, iconColor = 'bg-primary/10 text-primary' }: StatCardProps) {
  return (
    <Card className="p-4 hover:border-primary/30 transition-all">
      <div className="flex items-start gap-3">
        <div className={`p-2 rounded-lg ${iconColor}`}>
          <Icon className="h-5 w-5" />
        </div>

        <div className="flex-1 min-w-0">
          <div className="text-2xl font-bold font-mono leading-none mb-1">{value}</div>
          <div className="text-[10px] font-medium text-muted-foreground uppercase tracking-wide mb-1">
            {label}
          </div>
          {meta && (
            <div className="text-[10px] text-muted-foreground/70">{meta}</div>
          )}
          {change && (
            <div className="text-[10px] font-semibold text-primary mt-1">{change}</div>
          )}
        </div>
      </div>
    </Card>
  );
}

interface StatsOverviewProps {
  totalPoints: number;
  accuracy: number;
  totalPredictions: number;
  processedPredictions: number;
}

export function StatsOverview({
  totalPoints,
  accuracy,
  totalPredictions,
  processedPredictions,
}: StatsOverviewProps) {
  return (
    <div className="grid grid-cols-2 gap-3">
      <StatCard
        icon={Trophy}
        value={totalPoints}
        label="Points"
        meta={`${totalPredictions} predictions`}
        iconColor="bg-amber-500/10 text-amber-500"
      />

      <StatCard
        icon={Target}
        value={`${accuracy}%`}
        label="Accuracy"
        meta={`${processedPredictions} of ${totalPredictions} scored`}
        iconColor="bg-blue-500/10 text-blue-500"
      />

      <StatCard
        icon={TrendingUp}
        value={totalPredictions}
        label="Predictions"
        meta={processedPredictions > 0 ? `${processedPredictions} completed` : 'Make your first!'}
        iconColor="bg-green-500/10 text-green-500"
      />

      <StatCard
        icon={Flame}
        value={processedPredictions > 0 ? Math.round(totalPoints / processedPredictions) : 0}
        label="Avg Points"
        meta={processedPredictions > 0 ? 'per match' : 'Start predicting'}
        iconColor="bg-orange-500/10 text-orange-500"
      />
    </div>
  );
}
