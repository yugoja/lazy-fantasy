import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useRouter } from 'next/navigation';
import LoginPage from '../page';
import { login as apiLogin, ApiError } from '@/lib/api';

vi.mock('@/lib/api', () => {
  class ApiError extends Error {
    status: number;
    constructor(status: number, message: string) {
      super(message);
      this.name = 'ApiError';
      this.status = status;
    }
  }
  return {
    login: vi.fn(),
    ApiError,
  };
});

const mockAuthLogin = vi.fn();

vi.mock('@/lib/auth', () => ({
  useAuth: () => ({
    isAuthenticated: false,
    username: null,
    login: mockAuthLogin,
    logout: vi.fn(),
    isLoading: false,
  }),
}));

describe('LoginPage', () => {
  const mockPush = vi.fn();
  const mockLogin = vi.mocked(apiLogin);

  beforeEach(() => {
    vi.mocked(useRouter).mockReturnValue({
      push: mockPush,
      replace: vi.fn(),
      back: vi.fn(),
      prefetch: vi.fn(),
      forward: vi.fn(),
      refresh: vi.fn(),
    });
  });

  it('renders form fields and submit button', () => {
    render(<LoginPage />);
    expect(screen.getByLabelText(/username/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
  });

  it('calls login and redirects on success', async () => {
    mockLogin.mockResolvedValue({ access_token: 'tok123', token_type: 'bearer' });
    const user = userEvent.setup();

    render(<LoginPage />);
    await user.type(screen.getByLabelText(/username/i), 'testuser');
    await user.type(screen.getByLabelText(/password/i), 'password123');
    await user.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith('testuser', 'password123');
      expect(mockAuthLogin).toHaveBeenCalledWith('tok123', 'testuser');
      expect(mockPush).toHaveBeenCalledWith('/dashboard');
    });
  });

  it('shows loading state during submission', async () => {
    mockLogin.mockReturnValue(new Promise(() => {}));
    const user = userEvent.setup();

    render(<LoginPage />);
    await user.type(screen.getByLabelText(/username/i), 'testuser');
    await user.type(screen.getByLabelText(/password/i), 'password123');
    await user.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /signing in/i })).toBeDisabled();
    });
  });

  it('shows ApiError message on failure', async () => {
    mockLogin.mockRejectedValue(new ApiError(401, 'Invalid credentials'));
    const user = userEvent.setup();

    render(<LoginPage />);
    await user.type(screen.getByLabelText(/username/i), 'bad');
    await user.type(screen.getByLabelText(/password/i), 'wrong');
    await user.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByText('Invalid credentials')).toBeInTheDocument();
    });
  });

  it('shows generic error for non-ApiError exceptions', async () => {
    mockLogin.mockRejectedValue(new TypeError('network fail'));
    const user = userEvent.setup();

    render(<LoginPage />);
    await user.type(screen.getByLabelText(/username/i), 'user');
    await user.type(screen.getByLabelText(/password/i), 'pass');
    await user.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByText('An unexpected error occurred')).toBeInTheDocument();
    });
  });
});
