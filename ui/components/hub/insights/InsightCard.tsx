
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface InsightCardProps {
  title: string;
  value: string | number;
  icon: React.ReactNode;
}

export const InsightCard: React.FC<InsightCardProps> = ({ title, value, icon }) => (
  <Card className="bg-gray-900 shadow-lg rounded-lg hover:shadow-orange-500/20 transition-shadow duration-300">
    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
      <CardTitle className="text-sm font-medium text-gray-400">{title}</CardTitle>
      {icon}
    </CardHeader>
    <CardContent>
      <div className="text-2xl font-bold text-white">{value}</div>
    </CardContent>
  </Card>
);
