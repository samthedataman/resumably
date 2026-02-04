import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || '';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Auth API
export const authApi = {
  register: (email: string, password: string) =>
    api.post('/api/auth/register', { email, password }),

  login: (email: string, password: string, totpCode?: string) =>
    api.post('/api/auth/login', { email, password, totp_code: totpCode }),

  getMe: () => api.get('/api/auth/me'),

  setup2FA: () => api.post('/api/auth/2fa/setup'),

  verify2FA: (code: string) => api.post('/api/auth/2fa/verify', { code }),

  disable2FA: (code: string) => api.post('/api/auth/2fa/disable', { code }),

  // Password Reset
  forgotPassword: (email: string) =>
    api.post('/api/auth/forgot-password', { email }),

  resetPassword: (token: string, newPassword: string) =>
    api.post('/api/auth/reset-password', { token, new_password: newPassword }),

  // Google OAuth
  googleAuth: (credential: string) =>
    api.post('/api/auth/google', { credential }),

  getGoogleClientId: () => api.get('/api/auth/google/client-id'),
};

// Gmail API
export const gmailApi = {
  getAuthUrl: () => api.get('/api/gmail/auth/url'),

  getStatus: () => api.get('/api/gmail/status'),

  connect: (tokenData: object) => api.post('/api/gmail/connect', tokenData),

  disconnect: () => api.delete('/api/gmail/disconnect'),
};

// Resume API
export const resumeApi = {
  list: () => api.get('/api/resumes'),

  getDefault: () => api.get('/api/resumes/default'),

  get: (id: number) => api.get(`/api/resumes/${id}`),

  create: (data: object) => api.post('/api/resumes', data),

  update: (id: number, data: object) => api.put(`/api/resumes/${id}`, data),

  delete: (id: number) => api.delete(`/api/resumes/${id}`),

  setDefault: (id: number) => api.post(`/api/resumes/${id}/set-default`),

  downloadPdf: (id: number) =>
    api.get(`/api/resumes/${id}/pdf`, { responseType: 'blob' }),
};

// Email API
export const emailApi = {
  scan: (maxResults = 20, query = 'is:unread category:primary') =>
    api.get('/api/emails/scan', { params: { max_results: maxResults, query } }),

  classify: (gmailId: string) =>
    api.post(`/api/emails/classify/${gmailId}`),

  batchClassify: (gmailIds: string[]) =>
    api.post('/api/emails/batch-classify', gmailIds),

  listProcessed: (recruiterOnly = false, limit = 50) =>
    api.get('/api/emails/processed', { params: { recruiter_only: recruiterOnly, limit } }),

  getProcessed: (id: number) =>
    api.get(`/api/emails/processed/${id}`),

  createDraft: (processedEmailId: number, resumeId?: number) =>
    api.post('/api/emails/draft', { processed_email_id: processedEmailId, resume_id: resumeId }),

  listDrafts: () => api.get('/api/emails/drafts'),

  getDraft: (id: number) => api.get(`/api/emails/drafts/${id}`),

  getStats: () => api.get('/api/emails/stats'),
};

// Skills API
export const skillsApi = {
  list: (category?: string) =>
    api.get('/api/skills', { params: { category } }),

  create: (data: object) => api.post('/api/skills', data),

  update: (id: number, data: object) => api.put(`/api/skills/${id}`, data),

  delete: (id: number) => api.delete(`/api/skills/${id}`),

  listLearned: (category?: string) =>
    api.get('/api/skills/learned', { params: { category } }),

  convertLearned: (id: number, proficiency: string, yearsExperience?: number) =>
    api.post(`/api/skills/learned/${id}/convert`, { proficiency, years_experience: yearsExperience }),

  getCategories: () => api.get('/api/skills/categories'),

  bulkImport: (skills: object[]) => api.post('/api/skills/bulk-import', skills),
};

export default api;
