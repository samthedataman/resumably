import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { skillsApi } from '../services/api';
import { Zap, TrendingUp, Plus, ArrowRight, Loader2 } from 'lucide-react';
import toast from 'react-hot-toast';

interface Skill {
  id: number;
  name: string;
  category: string;
  proficiency: string;
  years_experience: number | null;
  source: string;
}

interface LearnedSkill {
  id: number;
  skill_name: string;
  category: string;
  occurrence_count: number;
  last_seen: string;
}

export default function Skills() {
  const queryClient = useQueryClient();

  const { data: skills, isLoading: skillsLoading } = useQuery({
    queryKey: ['skills'],
    queryFn: () => skillsApi.list().then((r) => r.data),
  });

  const { data: learnedSkills, isLoading: learnedLoading } = useQuery({
    queryKey: ['learnedSkills'],
    queryFn: () => skillsApi.listLearned().then((r) => r.data),
  });

  const convertMutation = useMutation({
    mutationFn: ({ id, proficiency }: { id: number; proficiency: string }) =>
      skillsApi.convertLearned(id, proficiency),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['skills'] });
      queryClient.invalidateQueries({ queryKey: ['learnedSkills'] });
      toast.success('Skill added to your profile');
    },
    onError: () => {
      toast.error('Failed to add skill');
    },
  });

  const groupedSkills = skills?.reduce(
    (acc: Record<string, Skill[]>, skill: Skill) => {
      const category = skill.category || 'other';
      if (!acc[category]) acc[category] = [];
      acc[category].push(skill);
      return acc;
    },
    {} as Record<string, Skill[]>
  );

  const proficiencyColors: Record<string, string> = {
    beginner: 'bg-gray-100 text-gray-700',
    intermediate: 'bg-blue-100 text-blue-700',
    advanced: 'bg-purple-100 text-purple-700',
    expert: 'bg-green-100 text-green-700',
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Skills</h1>

      {/* Learned Skills Section */}
      <div className="card">
        <div className="flex items-center gap-2 mb-4">
          <TrendingUp className="w-5 h-5 text-orange-500" />
          <h2 className="text-lg font-semibold text-gray-900">
            Trending Skills (From Emails)
          </h2>
        </div>

        {learnedLoading ? (
          <div className="py-8 text-center">
            <Loader2 className="w-6 h-6 text-primary-500 mx-auto animate-spin" />
          </div>
        ) : learnedSkills?.length === 0 ? (
          <p className="text-gray-500 py-4">
            No skills learned yet. Process some recruiter emails to discover trending skills.
          </p>
        ) : (
          <div className="space-y-3">
            {learnedSkills?.slice(0, 10).map((skill: LearnedSkill) => (
              <div
                key={skill.id}
                className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
              >
                <div className="flex items-center gap-4">
                  <div className="flex-1">
                    <span className="font-medium text-gray-900 capitalize">
                      {skill.skill_name}
                    </span>
                    <span className="text-sm text-gray-500 ml-2">
                      ({skill.category})
                    </span>
                  </div>
                  <div className="flex items-center gap-2 text-sm text-gray-600">
                    <span className="px-2 py-1 bg-orange-100 text-orange-700 rounded-full">
                      {skill.occurrence_count}x requested
                    </span>
                  </div>
                </div>
                <button
                  onClick={() =>
                    convertMutation.mutate({ id: skill.id, proficiency: 'intermediate' })
                  }
                  disabled={convertMutation.isPending}
                  className="btn-secondary text-sm flex items-center gap-1"
                >
                  <Plus className="w-4 h-4" />
                  Add to Profile
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Your Skills Section */}
      <div className="card">
        <div className="flex items-center gap-2 mb-4">
          <Zap className="w-5 h-5 text-primary-500" />
          <h2 className="text-lg font-semibold text-gray-900">Your Skills</h2>
        </div>

        {skillsLoading ? (
          <div className="py-8 text-center">
            <Loader2 className="w-6 h-6 text-primary-500 mx-auto animate-spin" />
          </div>
        ) : !groupedSkills || Object.keys(groupedSkills).length === 0 ? (
          <p className="text-gray-500 py-4">
            No skills added yet. Add skills from trending or create a resume to import skills.
          </p>
        ) : (
          <div className="space-y-6">
            {Object.entries(groupedSkills).map(([category, categorySkills]) => (
              <div key={category}>
                <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
                  {category.replace(/_/g, ' ')}
                </h3>
                <div className="flex flex-wrap gap-2">
                  {(categorySkills as Skill[]).map((skill: Skill) => (
                    <div
                      key={skill.id}
                      className={`px-3 py-2 rounded-lg text-sm ${
                        proficiencyColors[skill.proficiency] || proficiencyColors.intermediate
                      }`}
                    >
                      <span className="font-medium capitalize">{skill.name}</span>
                      {skill.years_experience && (
                        <span className="text-xs ml-1 opacity-75">
                          ({skill.years_experience}y)
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Skill Gap Analysis */}
      {learnedSkills && learnedSkills.length > 0 && skills && (
        <div className="card">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Skill Gap Analysis
          </h2>
          <p className="text-gray-600 mb-4">
            Skills frequently requested by recruiters that you might want to highlight:
          </p>
          <div className="space-y-3">
            {learnedSkills
              .filter(
                (learned: LearnedSkill) =>
                  !skills.some(
                    (skill: Skill) =>
                      skill.name.toLowerCase() === learned.skill_name.toLowerCase()
                  )
              )
              .slice(0, 5)
              .map((skill: LearnedSkill) => (
                <div
                  key={skill.id}
                  className="flex items-center justify-between p-3 border border-orange-200 bg-orange-50 rounded-lg"
                >
                  <div>
                    <span className="font-medium text-gray-900 capitalize">
                      {skill.skill_name}
                    </span>
                    <span className="text-sm text-orange-600 ml-2">
                      Requested {skill.occurrence_count} times
                    </span>
                  </div>
                  <ArrowRight className="w-5 h-5 text-orange-500" />
                </div>
              ))}
          </div>
        </div>
      )}
    </div>
  );
}
