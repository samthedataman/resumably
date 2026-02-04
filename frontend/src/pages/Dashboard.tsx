import { useQuery } from '@tanstack/react-query';
import { emailApi, gmailApi } from '../services/api';
import { Mail, FileText, Zap, TrendingUp, CheckCircle, AlertCircle } from 'lucide-react';
import { Link } from 'react-router-dom';

export default function Dashboard() {
  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['emailStats'],
    queryFn: () => emailApi.getStats().then((r) => r.data),
  });

  const { data: gmailStatus } = useQuery({
    queryKey: ['gmailStatus'],
    queryFn: () => gmailApi.getStatus().then((r) => r.data),
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        {!gmailStatus?.connected && (
          <Link to="/settings" className="btn-primary">
            Connect Gmail
          </Link>
        )}
      </div>

      {/* Gmail Status */}
      <div className={`card flex items-center gap-4 ${gmailStatus?.connected ? 'border-l-4 border-green-500' : 'border-l-4 border-yellow-500'}`}>
        {gmailStatus?.connected ? (
          <>
            <CheckCircle className="w-8 h-8 text-green-500" />
            <div>
              <h3 className="font-semibold text-gray-900">Gmail Connected</h3>
              <p className="text-gray-500">Your Gmail account is connected and ready to scan emails.</p>
            </div>
          </>
        ) : (
          <>
            <AlertCircle className="w-8 h-8 text-yellow-500" />
            <div>
              <h3 className="font-semibold text-gray-900">Gmail Not Connected</h3>
              <p className="text-gray-500">Connect your Gmail to start scanning for recruiter emails.</p>
            </div>
          </>
        )}
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Emails Processed"
          value={statsLoading ? '-' : stats?.total_emails_processed || 0}
          icon={Mail}
          color="blue"
        />
        <StatCard
          title="Recruiter Emails"
          value={statsLoading ? '-' : stats?.recruiter_emails_found || 0}
          icon={TrendingUp}
          color="green"
        />
        <StatCard
          title="Drafts Created"
          value={statsLoading ? '-' : stats?.drafts_created || 0}
          icon={FileText}
          color="purple"
        />
        <StatCard
          title="Skills Learned"
          value={statsLoading ? '-' : stats?.skills_learned || 0}
          icon={Zap}
          color="orange"
        />
      </div>

      {/* Top Requested Skills */}
      {stats?.top_requested_skills && stats.top_requested_skills.length > 0 && (
        <div className="card">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Top Requested Skills
          </h2>
          <div className="space-y-3">
            {stats.top_requested_skills.map((skill: { name: string; category: string; count: number }) => (
              <div key={skill.name} className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="font-medium text-gray-900 capitalize">
                    {skill.name}
                  </span>
                  <span className="text-xs px-2 py-1 bg-gray-100 rounded-full text-gray-600">
                    {skill.category}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-32 h-2 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-primary-500 rounded-full"
                      style={{
                        width: `${Math.min(100, (skill.count / (stats.top_requested_skills[0]?.count || 1)) * 100)}%`,
                      }}
                    />
                  </div>
                  <span className="text-sm text-gray-600 w-8 text-right">
                    {skill.count}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Link to="/emails" className="card hover:shadow-lg transition-shadow group">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center group-hover:bg-blue-200 transition-colors">
              <Mail className="w-6 h-6 text-blue-600" />
            </div>
            <div>
              <h3 className="font-semibold text-gray-900">Scan Emails</h3>
              <p className="text-sm text-gray-500">Find recruiter emails</p>
            </div>
          </div>
        </Link>

        <Link to="/resumes" className="card hover:shadow-lg transition-shadow group">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center group-hover:bg-purple-200 transition-colors">
              <FileText className="w-6 h-6 text-purple-600" />
            </div>
            <div>
              <h3 className="font-semibold text-gray-900">Manage Resumes</h3>
              <p className="text-sm text-gray-500">Edit your templates</p>
            </div>
          </div>
        </Link>

        <Link to="/skills" className="card hover:shadow-lg transition-shadow group">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-orange-100 rounded-lg flex items-center justify-center group-hover:bg-orange-200 transition-colors">
              <Zap className="w-6 h-6 text-orange-600" />
            </div>
            <div>
              <h3 className="font-semibold text-gray-900">View Skills</h3>
              <p className="text-sm text-gray-500">Track skill trends</p>
            </div>
          </div>
        </Link>
      </div>
    </div>
  );
}

interface StatCardProps {
  title: string;
  value: number | string;
  icon: React.ComponentType<{ className?: string }>;
  color: 'blue' | 'green' | 'purple' | 'orange';
}

function StatCard({ title, value, icon: Icon, color }: StatCardProps) {
  const colors = {
    blue: 'bg-blue-100 text-blue-600',
    green: 'bg-green-100 text-green-600',
    purple: 'bg-purple-100 text-purple-600',
    orange: 'bg-orange-100 text-orange-600',
  };

  return (
    <div className="card">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-500">{title}</p>
          <p className="text-3xl font-bold text-gray-900 mt-1">{value}</p>
        </div>
        <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${colors[color]}`}>
          <Icon className="w-6 h-6" />
        </div>
      </div>
    </div>
  );
}
