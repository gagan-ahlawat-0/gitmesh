
"use client";

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

interface ContributorSpotlightProps {
  data: any[];
}

export default function ContributorSpotlight({ data }: ContributorSpotlightProps) {
  return (
    <Card className="bg-gray-900 shadow-lg rounded-lg">
      <CardHeader>
        <CardTitle className="text-xl font-bold text-white">Contributor Spotlight</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#4A5568" />
            <XAxis dataKey="login" stroke="#A0AEC0" />
            <YAxis stroke="#A0AEC0" />
            <Tooltip contentStyle={{ backgroundColor: '#1A202C', border: '1px solid #4A5568' }} />
            <Legend wrapperStyle={{ color: '#A0AEC0' }} />
            <Bar dataKey="contributions" fill="#FF8C00" />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
