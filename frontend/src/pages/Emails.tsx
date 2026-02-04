import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { emailApi, gmailApi } from '../services/api';
import {
  Mail,
  RefreshCw,
  CheckCircle,
  XCircle,
  Building,
  Briefcase,
  ChevronRight,
  FileText,
  Loader2,
} from 'lucide-react';
import toast from 'react-hot-toast';
import { Link } from 'react-router-dom';

interface ScannedEmail {
  gmail_id: string;
  subject: string;
  sender: string;
  snippet: string;
  date: string;
}

interface ProcessedEmail {
  id: number;
  gmail_id: string;
  subject: string;
  sender: string;
  job_title: string | null;
  company: string | null;
  is_recruiter_email: boolean;
  confidence: number;
  technologies: string[];
  processed_at: string;
}

export default function Emails() {
  const [activeTab, setActiveTab] = useState<'scan' | 'processed'>('scan');
  const [scannedEmails, setScannedEmails] = useState<ScannedEmail[]>([]);
  const queryClient = useQueryClient();

  const { data: gmailStatus } = useQuery({
    queryKey: ['gmailStatus'],
    queryFn: () => gmailApi.getStatus().then((r) => r.data),
  });

  const { data: processedEmails, isLoading: processedLoading } = useQuery({
    queryKey: ['processedEmails'],
    queryFn: () => emailApi.listProcessed(true).then((r) => r.data),
  });

  const scanMutation = useMutation({
    mutationFn: () => emailApi.scan(30),
    onSuccess: (data) => {
      setScannedEmails(data.data.emails);
      toast.success(`Found ${data.data.emails.length} emails`);
    },
    onError: () => {
      toast.error('Failed to scan emails');
    },
  });

  const classifyMutation = useMutation({
    mutationFn: (gmailId: string) => emailApi.classify(gmailId),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['processedEmails'] });
      queryClient.invalidateQueries({ queryKey: ['emailStats'] });
      const jobDetails = data.data.job_details;
      if (jobDetails.is_recruiter_email) {
        toast.success(`Recruiter email: ${jobDetails.job_title} at ${jobDetails.company}`);
      } else {
        toast.success('Not a recruiter email');
      }
    },
    onError: () => {
      toast.error('Failed to classify email');
    },
  });

  const createDraftMutation = useMutation({
    mutationFn: (processedEmailId: number) => emailApi.createDraft(processedEmailId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['emailStats'] });
      toast.success('Draft created with tailored resume!');
    },
    onError: () => {
      toast.error('Failed to create draft');
    },
  });

  if (!gmailStatus?.connected) {
    return (
      <div className="card text-center py-12">
        <Mail className="w-16 h-16 text-gray-300 mx-auto mb-4" />
        <h2 className="text-xl font-semibold text-gray-900 mb-2">
          Connect Gmail to Get Started
        </h2>
        <p className="text-gray-500 mb-6">
          Connect your Gmail account to scan for recruiter emails.
        </p>
        <Link to="/settings" className="btn-primary">
          Go to Settings
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Emails</h1>
        <button
          onClick={() => scanMutation.mutate()}
          disabled={scanMutation.isPending}
          className="btn-primary flex items-center gap-2"
        >
          <RefreshCw className={`w-4 h-4 ${scanMutation.isPending ? 'animate-spin' : ''}`} />
          Scan Inbox
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-4 border-b">
        <button
          onClick={() => setActiveTab('scan')}
          className={`pb-3 px-1 font-medium transition-colors ${
            activeTab === 'scan'
              ? 'text-primary-600 border-b-2 border-primary-600'
              : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          Scan & Classify
        </button>
        <button
          onClick={() => setActiveTab('processed')}
          className={`pb-3 px-1 font-medium transition-colors ${
            activeTab === 'processed'
              ? 'text-primary-600 border-b-2 border-primary-600'
              : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          Recruiter Emails
        </button>
      </div>

      {activeTab === 'scan' && (
        <div className="space-y-4">
          {scannedEmails.length === 0 ? (
            <div className="card text-center py-12">
              <Mail className="w-12 h-12 text-gray-300 mx-auto mb-4" />
              <p className="text-gray-500">
                Click "Scan Inbox" to find emails to classify
              </p>
            </div>
          ) : (
            scannedEmails.map((email) => (
              <div key={email.gmail_id} className="card">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-gray-900 truncate">
                      {email.subject}
                    </h3>
                    <p className="text-sm text-gray-500 truncate">{email.sender}</p>
                    <p className="text-sm text-gray-600 mt-2 line-clamp-2">
                      {email.snippet}
                    </p>
                  </div>
                  <button
                    onClick={() => classifyMutation.mutate(email.gmail_id)}
                    disabled={classifyMutation.isPending}
                    className="btn-primary text-sm flex items-center gap-2"
                  >
                    {classifyMutation.isPending ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <ChevronRight className="w-4 h-4" />
                    )}
                    Classify
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {activeTab === 'processed' && (
        <div className="space-y-4">
          {processedLoading ? (
            <div className="card text-center py-12">
              <Loader2 className="w-8 h-8 text-primary-500 mx-auto animate-spin" />
            </div>
          ) : processedEmails?.length === 0 ? (
            <div className="card text-center py-12">
              <CheckCircle className="w-12 h-12 text-gray-300 mx-auto mb-4" />
              <p className="text-gray-500">No recruiter emails found yet</p>
            </div>
          ) : (
            processedEmails?.map((email: ProcessedEmail) => (
              <div key={email.id} className="card">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      {email.is_recruiter_email ? (
                        <CheckCircle className="w-5 h-5 text-green-500" />
                      ) : (
                        <XCircle className="w-5 h-5 text-red-500" />
                      )}
                      <h3 className="font-semibold text-gray-900">
                        {email.subject}
                      </h3>
                    </div>

                    {email.job_title && (
                      <div className="flex items-center gap-4 text-sm text-gray-600 mb-2">
                        <span className="flex items-center gap-1">
                          <Briefcase className="w-4 h-4" />
                          {email.job_title}
                        </span>
                        {email.company && (
                          <span className="flex items-center gap-1">
                            <Building className="w-4 h-4" />
                            {email.company}
                          </span>
                        )}
                      </div>
                    )}

                    {email.technologies?.length > 0 && (
                      <div className="flex flex-wrap gap-2 mt-3">
                        {email.technologies.slice(0, 6).map((tech) => (
                          <span
                            key={tech}
                            className="text-xs px-2 py-1 bg-primary-50 text-primary-700 rounded-full"
                          >
                            {tech}
                          </span>
                        ))}
                        {email.technologies.length > 6 && (
                          <span className="text-xs px-2 py-1 bg-gray-100 text-gray-600 rounded-full">
                            +{email.technologies.length - 6} more
                          </span>
                        )}
                      </div>
                    )}
                  </div>

                  <button
                    onClick={() => createDraftMutation.mutate(email.id)}
                    disabled={createDraftMutation.isPending}
                    className="btn-primary text-sm flex items-center gap-2"
                  >
                    {createDraftMutation.isPending ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <FileText className="w-4 h-4" />
                    )}
                    Create Draft
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
