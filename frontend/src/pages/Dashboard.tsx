import { useQuery } from '@tanstack/react-query';
import { resultsApi } from '../services/api';
import { TrendingUp, Users, Target, CheckCircle } from 'lucide-react';

export default function Dashboard() {
  const { data: stats } = useQuery({
    queryKey: ['overview-stats'],
    queryFn: resultsApi.getOverviewStats,
  });

  const { data: classifierStats } = useQuery({
    queryKey: ['classifier-stats'],
    queryFn: resultsApi.getClassifierStats,
  });

  const { data: recentMatches } = useQuery({
    queryKey: ['recent-matches'],
    queryFn: () => resultsApi.getMatches(0, 4),
  });

  return (
    <div className="space-y-6">
      <h2 className="text-3xl font-bold text-gray-900 dark:text-white">Dashboard</h2>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Analyzed"
          value={stats?.total_classified || 0}
          icon={Users}
          color="blue"
        />
        <StatCard
          title="Matches"
          value={stats?.total_matches || 0}
          icon={CheckCircle}
          color="green"
        />
        <StatCard
          title="Match Rate"
          value={`${stats?.match_rate.toFixed(1) || 0}%`}
          icon={Target}
          color="purple"
        />
        <StatCard
          title="Avg Confidence"
          value={`${((stats?.avg_confidence ?? 0) * 100).toFixed(1)}%`}
          icon={TrendingUp}
          color="orange"
        />
      </div>

      {/* Classifier Info */}
      {classifierStats && (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">
            Classifier Status
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
            <div>
              <p className="text-gray-500 dark:text-gray-400">Reference Images</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {classifierStats.reference_images}
              </p>
            </div>
            <div>
              <p className="text-gray-500 dark:text-gray-400">Training Examples</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {classifierStats.total_training_data}
              </p>
            </div>
            <div>
              <p className="text-gray-500 dark:text-gray-400">Min Score</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {(classifierStats.min_score_threshold * 100).toFixed(0)}%
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Recent Matches */}
      {recentMatches && recentMatches.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">
            Recent Matches
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {recentMatches.map((match) => (
              <div
                key={match.id}
                className="border border-gray-200 dark:border-gray-700 rounded-lg p-4"
              >
                <div className="flex justify-between items-start">
                  <div>
                    <p className="font-semibold text-gray-900 dark:text-white">
                      {match.name || 'Unknown'}{match.age ? `, ${match.age}` : ''}
                    </p>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      {match.bio?.substring(0, 60)}...
                    </p>
                  </div>
                  <span className="text-green-600 dark:text-green-400 font-bold">
                    {(match.confidence_score * 100).toFixed(0)}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

interface StatCardProps {
  title: string;
  value: string | number;
  icon: React.ElementType;
  color: 'blue' | 'green' | 'purple' | 'orange';
}

function StatCard({ title, value, icon: Icon, color }: StatCardProps) {
  const colorClasses = {
    blue: 'bg-blue-100 text-blue-600 dark:bg-blue-900 dark:text-blue-300',
    green: 'bg-green-100 text-green-600 dark:bg-green-900 dark:text-green-300',
    purple: 'bg-purple-100 text-purple-600 dark:bg-purple-900 dark:text-purple-300',
    orange: 'bg-orange-100 text-orange-600 dark:bg-orange-900 dark:text-orange-300',
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-500 dark:text-gray-400">{title}</p>
          <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">{value}</p>
        </div>
        <div className={`p-3 rounded-full ${colorClasses[color]}`}>
          <Icon className="w-6 h-6" />
        </div>
      </div>
    </div>
  );
}
