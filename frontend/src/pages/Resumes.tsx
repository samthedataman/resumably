import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { resumeApi } from '../services/api';
import {
  FileText,
  Plus,
  Star,
  Download,
  Trash2,
  Loader2,
  X,
} from 'lucide-react';
import toast from 'react-hot-toast';

interface Resume {
  id: number;
  name: string;
  is_default: boolean;
  personal_info: {
    name?: string;
    email?: string;
    location?: string;
  };
  summary: string;
  created_at: string;
  updated_at: string;
}

export default function Resumes() {
  const [showCreateModal, setShowCreateModal] = useState(false);
  const queryClient = useQueryClient();

  const { data: resumes, isLoading } = useQuery({
    queryKey: ['resumes'],
    queryFn: () => resumeApi.list().then((r) => r.data),
  });

  const setDefaultMutation = useMutation({
    mutationFn: (id: number) => resumeApi.setDefault(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['resumes'] });
      toast.success('Default resume updated');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => resumeApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['resumes'] });
      toast.success('Resume deleted');
    },
  });

  const downloadPdf = async (id: number, name: string) => {
    try {
      const response = await resumeApi.downloadPdf(id);
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${name.replace(/\s+/g, '_')}_Resume.pdf`;
      a.click();
      window.URL.revokeObjectURL(url);
      toast.success('PDF downloaded');
    } catch {
      toast.error('Failed to download PDF');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Resumes</h1>
        <button
          onClick={() => setShowCreateModal(true)}
          className="btn-primary flex items-center gap-2"
        >
          <Plus className="w-4 h-4" />
          Create Resume
        </button>
      </div>

      {isLoading ? (
        <div className="card text-center py-12">
          <Loader2 className="w-8 h-8 text-primary-500 mx-auto animate-spin" />
        </div>
      ) : resumes?.length === 0 ? (
        <div className="card text-center py-12">
          <FileText className="w-16 h-16 text-gray-300 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 mb-2">
            No Resumes Yet
          </h2>
          <p className="text-gray-500 mb-6">
            Create your first resume to get started with auto-tailoring.
          </p>
          <button
            onClick={() => setShowCreateModal(true)}
            className="btn-primary"
          >
            Create Resume
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {resumes?.map((resume: Resume) => (
            <div key={resume.id} className="card relative">
              {resume.is_default && (
                <div className="absolute top-4 right-4">
                  <Star className="w-5 h-5 text-yellow-500 fill-yellow-500" />
                </div>
              )}

              <h3 className="font-semibold text-gray-900 text-lg mb-2">
                {resume.name}
              </h3>

              {resume.personal_info?.name && (
                <p className="text-gray-600 mb-1">{resume.personal_info.name}</p>
              )}
              {resume.personal_info?.email && (
                <p className="text-sm text-gray-500 mb-3">
                  {resume.personal_info.email}
                </p>
              )}

              {resume.summary && (
                <p className="text-sm text-gray-600 line-clamp-3 mb-4">
                  {resume.summary}
                </p>
              )}

              <div className="flex items-center gap-2 pt-4 border-t">
                {!resume.is_default && (
                  <button
                    onClick={() => setDefaultMutation.mutate(resume.id)}
                    className="btn-secondary text-sm flex items-center gap-1"
                    title="Set as default"
                  >
                    <Star className="w-4 h-4" />
                  </button>
                )}
                <button
                  onClick={() => downloadPdf(resume.id, resume.personal_info?.name || 'Resume')}
                  className="btn-secondary text-sm flex items-center gap-1"
                  title="Download PDF"
                >
                  <Download className="w-4 h-4" />
                </button>
                <button
                  onClick={() => {
                    if (confirm('Are you sure you want to delete this resume?')) {
                      deleteMutation.mutate(resume.id);
                    }
                  }}
                  className="btn-secondary text-sm flex items-center gap-1 text-red-600 hover:bg-red-50"
                  title="Delete"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {showCreateModal && (
        <CreateResumeModal onClose={() => setShowCreateModal(false)} />
      )}
    </div>
  );
}

function CreateResumeModal({ onClose }: { onClose: () => void }) {
  const [formData, setFormData] = useState({
    name: 'My Resume',
    personal_info: {
      name: '',
      email: '',
      phone: '',
      location: '',
      linkedin: '',
      github: '',
      website: '',
    },
    summary: '',
    skills: {
      technical: [] as string[],
      tools: [] as string[],
    },
    experience: [] as Array<{
      company: string;
      title: string;
      location: string;
      start_date: string;
      end_date: string;
      highlights: string[];
    }>,
    education: [] as Array<{
      institution: string;
      degree: string;
      graduation_date: string;
      gpa: string;
    }>,
    projects: [] as Array<{
      name: string;
      description: string;
      technologies: string[];
      link: string;
    }>,
  });

  const queryClient = useQueryClient();

  const createMutation = useMutation({
    mutationFn: (data: typeof formData) => resumeApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['resumes'] });
      toast.success('Resume created');
      onClose();
    },
    onError: () => {
      toast.error('Failed to create resume');
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    createMutation.mutate(formData);
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="sticky top-0 bg-white border-b px-6 py-4 flex items-center justify-between">
          <h2 className="text-xl font-bold text-gray-900">Create Resume</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="w-6 h-6" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {/* Resume Name */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Resume Name
            </label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="input"
              placeholder="e.g., Software Engineer Resume"
              required
            />
          </div>

          {/* Personal Info */}
          <div>
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Personal Info</h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Full Name
                </label>
                <input
                  type="text"
                  value={formData.personal_info.name}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      personal_info: { ...formData.personal_info, name: e.target.value },
                    })
                  }
                  className="input"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Email
                </label>
                <input
                  type="email"
                  value={formData.personal_info.email}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      personal_info: { ...formData.personal_info, email: e.target.value },
                    })
                  }
                  className="input"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Phone
                </label>
                <input
                  type="tel"
                  value={formData.personal_info.phone}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      personal_info: { ...formData.personal_info, phone: e.target.value },
                    })
                  }
                  className="input"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Location
                </label>
                <input
                  type="text"
                  value={formData.personal_info.location}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      personal_info: { ...formData.personal_info, location: e.target.value },
                    })
                  }
                  className="input"
                  placeholder="e.g., NYC"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  GitHub Username
                </label>
                <input
                  type="text"
                  value={formData.personal_info.github}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      personal_info: { ...formData.personal_info, github: e.target.value },
                    })
                  }
                  className="input"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Website
                </label>
                <input
                  type="text"
                  value={formData.personal_info.website}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      personal_info: { ...formData.personal_info, website: e.target.value },
                    })
                  }
                  className="input"
                />
              </div>
            </div>
          </div>

          {/* Summary */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Professional Summary
            </label>
            <textarea
              value={formData.summary}
              onChange={(e) => setFormData({ ...formData, summary: e.target.value })}
              className="input min-h-[100px]"
              placeholder="Brief summary of your experience and skills..."
              required
            />
          </div>

          <div className="flex justify-end gap-4 pt-4 border-t">
            <button type="button" onClick={onClose} className="btn-secondary">
              Cancel
            </button>
            <button
              type="submit"
              disabled={createMutation.isPending}
              className="btn-primary"
            >
              {createMutation.isPending ? 'Creating...' : 'Create Resume'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
