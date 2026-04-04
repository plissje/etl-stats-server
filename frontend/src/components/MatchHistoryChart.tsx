import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  Tooltip, 
  ResponsiveContainer, 
  CartesianGrid,
  Cell
} from 'recharts';

interface MatchHistoryChartProps {
  data: { day: string; count: number }[];
}

export function MatchHistoryChart({ data }: MatchHistoryChartProps) {
  // Format dates for display
  const chartData = data.map(d => ({
    ...d,
    displayDay: new Date(d.day).toLocaleDateString([], { month: 'short', day: 'numeric' })
  }));

  // Ensure there's a minimum height even if the parent fails to provide one
  return (
    <div className="w-full h-[250px] mt-4">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart 
          data={chartData} 
          margin={{ top: 10, right: 10, left: -25, bottom: 0 }}
          barGap={2}
        >
          <CartesianGrid 
            strokeDasharray="3 3" 
            vertical={false} 
            stroke="#27272a" 
            opacity={0.5} 
          />
          <XAxis 
            dataKey="displayDay" 
            axisLine={false}
            tickLine={false}
            tick={{ fill: '#71717a', fontSize: 10 }}
            minTickGap={20}
          />
          <YAxis 
            axisLine={false}
            tickLine={false}
            tick={{ fill: '#71717a', fontSize: 10 }}
            allowDecimals={false}
          />
          <Tooltip 
            cursor={{ fill: '#27272a', opacity: 0.4 }}
            contentStyle={{ 
              backgroundColor: '#18181b', 
              border: '1px solid #3f3f46', 
              borderRadius: '8px',
              fontSize: '12px',
              color: '#f4f4f5',
              boxShadow: '0 10px 15px -3px rgb(0 0 0 / 0.1)'
            }}
            itemStyle={{ color: '#a78bfa', fontWeight: 'bold' }}
            labelStyle={{ color: '#71717a', marginBottom: '4px' }}
          />
          <Bar 
            dataKey="count" 
            name="Matches" 
            radius={[4, 4, 0, 0]}
            minPointSize={3}
          >
            {chartData.map((entry, index) => (
              <Cell 
                key={`cell-${index}`} 
                fill={entry.count > 0 ? '#8b5cf6' : '#27272a'} 
                fillOpacity={entry.count > 0 ? 0.8 : 0.2}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
