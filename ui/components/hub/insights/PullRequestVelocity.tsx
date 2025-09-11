
"use client";

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

interface PullRequestVelocityProps {
  data: any[];
}

export default function PullRequestVelocity({ data }: PullRequestVelocityProps) {
  return (
    <Card className="bg-gray-900 shadow-lg rounded-lg">
      <CardHeader>
        <CardTitle className="text-xl font-bold text-white">Pull Request Velocity</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#4A5568" />
            <XAxis dataKey="date" stroke="#A0AEC0" />
            <YAxis stroke="#A0AEC0" />
            <Tooltip contentStyle={{ backgroundColor: '#1A202C', border: '1px solid #4A5568' }} />
            <Legend wrapperStyle={{ color: '#A0AEC0' }} />
            <Line type="monotone" dataKey="opened" stroke="#FF8C00" />
            <Line type="monotone" dataKey="closed" stroke="#4ADE80" />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
