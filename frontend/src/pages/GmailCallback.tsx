import { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { CheckCircle, XCircle, Loader2 } from 'lucide-react';

export default function GmailCallback() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const success = searchParams.get('success') === 'true';
  const error = searchParams.get('error');

  useEffect(() => {
    const timer = setTimeout(() => {
      navigate('/settings');
    }, 3000);

    return () => clearTimeout(timer);
  }, [navigate]);

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="card text-center max-w-md">
        {success ? (
          <>
            <CheckCircle className="w-16 h-16 text-green-500 mx-auto mb-4" />
            <h1 className="text-2xl font-bold text-gray-900 mb-2">
              Gmail Connected!
            </h1>
            <p className="text-gray-600 mb-4">
              Your Gmail account has been successfully connected.
            </p>
          </>
        ) : (
          <>
            <XCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
            <h1 className="text-2xl font-bold text-gray-900 mb-2">
              Connection Failed
            </h1>
            <p className="text-gray-600 mb-4">
              {error || 'Failed to connect Gmail. Please try again.'}
            </p>
          </>
        )}

        <div className="flex items-center justify-center gap-2 text-sm text-gray-500">
          <Loader2 className="w-4 h-4 animate-spin" />
          Redirecting to settings...
        </div>
      </div>
    </div>
  );
}
