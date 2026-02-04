import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '../context/AuthContext';
import { authApi, gmailApi } from '../services/api';
import {
  Mail,
  Shield,
  CheckCircle,
  XCircle,
  Loader2,
  AlertTriangle,
} from 'lucide-react';
import { QRCodeSVG } from 'qrcode.react';
import toast from 'react-hot-toast';

export default function Settings() {
  const { user, refreshUser } = useAuth();

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Settings</h1>

      <GmailConnection />
      <TwoFactorAuth user={user} onUpdate={refreshUser} />
    </div>
  );
}

function GmailConnection() {
  const queryClient = useQueryClient();

  const { data: status, isLoading } = useQuery({
    queryKey: ['gmailStatus'],
    queryFn: () => gmailApi.getStatus().then((r) => r.data),
  });

  const connectMutation = useMutation({
    mutationFn: async () => {
      const response = await gmailApi.getAuthUrl();
      window.location.href = response.data.auth_url;
    },
    onError: () => {
      toast.error('Failed to get auth URL');
    },
  });

  const disconnectMutation = useMutation({
    mutationFn: () => gmailApi.disconnect(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['gmailStatus'] });
      toast.success('Gmail disconnected');
    },
    onError: () => {
      toast.error('Failed to disconnect Gmail');
    },
  });

  return (
    <div className="card">
      <div className="flex items-center gap-3 mb-4">
        <Mail className="w-6 h-6 text-primary-500" />
        <h2 className="text-lg font-semibold text-gray-900">Gmail Connection</h2>
      </div>

      {isLoading ? (
        <div className="py-4">
          <Loader2 className="w-6 h-6 text-primary-500 animate-spin" />
        </div>
      ) : status?.connected ? (
        <div className="space-y-4">
          <div className="flex items-center gap-3 p-4 bg-green-50 rounded-lg">
            <CheckCircle className="w-6 h-6 text-green-500" />
            <div>
              <p className="font-medium text-green-900">Gmail Connected</p>
              <p className="text-sm text-green-700">
                Your Gmail account is connected and ready to scan emails.
              </p>
            </div>
          </div>

          <button
            onClick={() => disconnectMutation.mutate()}
            disabled={disconnectMutation.isPending}
            className="btn-secondary text-red-600 hover:bg-red-50"
          >
            {disconnectMutation.isPending ? 'Disconnecting...' : 'Disconnect Gmail'}
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="flex items-center gap-3 p-4 bg-yellow-50 rounded-lg">
            <AlertTriangle className="w-6 h-6 text-yellow-500" />
            <div>
              <p className="font-medium text-yellow-900">Gmail Not Connected</p>
              <p className="text-sm text-yellow-700">
                Connect your Gmail to scan for recruiter emails and create draft replies.
              </p>
            </div>
          </div>

          <button
            onClick={() => connectMutation.mutate()}
            disabled={connectMutation.isPending}
            className="btn-primary"
          >
            {connectMutation.isPending ? 'Connecting...' : 'Connect Gmail'}
          </button>
        </div>
      )}
    </div>
  );
}

interface TwoFactorAuthProps {
  user: { is_2fa_enabled: boolean } | null;
  onUpdate: () => void;
}

function TwoFactorAuth({ user, onUpdate }: TwoFactorAuthProps) {
  const [showSetup, setShowSetup] = useState(false);
  const [setupData, setSetupData] = useState<{
    secret: string;
    qr_code: string;
    uri: string;
  } | null>(null);
  const [verifyCode, setVerifyCode] = useState('');
  const [disableCode, setDisableCode] = useState('');

  const setupMutation = useMutation({
    mutationFn: () => authApi.setup2FA(),
    onSuccess: (response) => {
      setSetupData(response.data);
      setShowSetup(true);
    },
    onError: () => {
      toast.error('Failed to setup 2FA');
    },
  });

  const verifyMutation = useMutation({
    mutationFn: (code: string) => authApi.verify2FA(code),
    onSuccess: () => {
      toast.success('2FA enabled successfully');
      setShowSetup(false);
      setSetupData(null);
      setVerifyCode('');
      onUpdate();
    },
    onError: () => {
      toast.error('Invalid verification code');
    },
  });

  const disableMutation = useMutation({
    mutationFn: (code: string) => authApi.disable2FA(code),
    onSuccess: () => {
      toast.success('2FA disabled');
      setDisableCode('');
      onUpdate();
    },
    onError: () => {
      toast.error('Invalid code');
    },
  });

  return (
    <div className="card">
      <div className="flex items-center gap-3 mb-4">
        <Shield className="w-6 h-6 text-primary-500" />
        <h2 className="text-lg font-semibold text-gray-900">
          Two-Factor Authentication
        </h2>
      </div>

      {user?.is_2fa_enabled ? (
        <div className="space-y-4">
          <div className="flex items-center gap-3 p-4 bg-green-50 rounded-lg">
            <CheckCircle className="w-6 h-6 text-green-500" />
            <div>
              <p className="font-medium text-green-900">2FA Enabled</p>
              <p className="text-sm text-green-700">
                Your account is protected with two-factor authentication.
              </p>
            </div>
          </div>

          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-700">
              Enter code to disable 2FA
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                value={disableCode}
                onChange={(e) => setDisableCode(e.target.value)}
                className="input w-40"
                placeholder="6-digit code"
                maxLength={6}
              />
              <button
                onClick={() => disableMutation.mutate(disableCode)}
                disabled={disableMutation.isPending || disableCode.length !== 6}
                className="btn-secondary text-red-600 hover:bg-red-50"
              >
                {disableMutation.isPending ? 'Disabling...' : 'Disable 2FA'}
              </button>
            </div>
          </div>
        </div>
      ) : showSetup && setupData ? (
        <div className="space-y-6">
          <div className="flex items-center gap-3 p-4 bg-blue-50 rounded-lg">
            <Shield className="w-6 h-6 text-blue-500" />
            <div>
              <p className="font-medium text-blue-900">Setup 2FA</p>
              <p className="text-sm text-blue-700">
                Scan the QR code with your authenticator app, then enter the code below.
              </p>
            </div>
          </div>

          <div className="flex justify-center">
            <div className="p-4 bg-white border-2 border-gray-200 rounded-lg">
              <QRCodeSVG value={setupData.uri} size={200} />
            </div>
          </div>

          <div className="text-center">
            <p className="text-sm text-gray-500 mb-2">
              Or enter this code manually:
            </p>
            <code className="px-3 py-2 bg-gray-100 rounded font-mono text-sm">
              {setupData.secret}
            </code>
          </div>

          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-700">
              Verification Code
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                value={verifyCode}
                onChange={(e) => setVerifyCode(e.target.value)}
                className="input w-40"
                placeholder="6-digit code"
                maxLength={6}
              />
              <button
                onClick={() => verifyMutation.mutate(verifyCode)}
                disabled={verifyMutation.isPending || verifyCode.length !== 6}
                className="btn-primary"
              >
                {verifyMutation.isPending ? 'Verifying...' : 'Verify & Enable'}
              </button>
            </div>
          </div>

          <button
            onClick={() => {
              setShowSetup(false);
              setSetupData(null);
            }}
            className="text-sm text-gray-500 hover:text-gray-700"
          >
            Cancel
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="flex items-center gap-3 p-4 bg-yellow-50 rounded-lg">
            <XCircle className="w-6 h-6 text-yellow-500" />
            <div>
              <p className="font-medium text-yellow-900">2FA Not Enabled</p>
              <p className="text-sm text-yellow-700">
                Add an extra layer of security to your account.
              </p>
            </div>
          </div>

          <button
            onClick={() => setupMutation.mutate()}
            disabled={setupMutation.isPending}
            className="btn-primary"
          >
            {setupMutation.isPending ? 'Setting up...' : 'Enable 2FA'}
          </button>
        </div>
      )}
    </div>
  );
}
