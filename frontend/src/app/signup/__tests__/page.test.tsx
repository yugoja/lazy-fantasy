import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useRouter } from 'next/navigation';
import SignupPage from '../page';
import { signup, login as apiLogin, ApiError } from '@/lib/api';

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
    signup: vi.fn(),
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

describe('SignupPage', () => {
  const mockPush = vi.fn();
  const mockSignup = vi.mocked(signup);
  const mockApiLogin = vi.mocked(apiLogin);

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

  it('renders all 4 fields and submit button', () => {
    render(<SignupPage />);
    expect(screen.getByLabelText(/username/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText('Password')).toBeInTheDocument();
    expect(screen.getByLabelText(/confirm password/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /create account/i })).toBeInTheDocument();
  });

  it('shows error when passwords do not match', async () => {
    const user = userEvent.setup();
    render(<SignupPage />);

    await user.type(screen.getByLabelText(/username/i), 'newuser');
    await user.type(screen.getByLabelText(/email/i), 'a@b.com');
    await user.type(screen.getByLabelText('Password'), 'password123');
    await user.type(screen.getByLabelText(/confirm password/i), 'different');
    await user.click(screen.getByRole('button', { name: /create account/i }));

    await waitFor(() => {
      expect(screen.getByText('Passwords do not match')).toBeInTheDocument();
    });
    expect(mockSignup).not.toHaveBeenCalled();
  });

  it('shows error when password is too short', async () => {
    const user = userEvent.setup();
    render(<SignupPage />);

    await user.type(screen.getByLabelText(/username/i), 'newuser');
    await user.type(screen.getByLabelText(/email/i), 'a@b.com');
    await user.type(screen.getByLabelText('Password'), 'abc');
    await user.type(screen.getByLabelText(/confirm password/i), 'abc');
    await user.click(screen.getByRole('button', { name: /create account/i }));

    await waitFor(() => {
      expect(screen.getByText('Password must be at least 6 characters')).toBeInTheDocument();
    });
    expect(mockSignup).not.toHaveBeenCalled();
  });

  it('signs up, auto-logs in, and redirects on success', async () => {
    mockSignup.mockResolvedValue({ id: 1, username: 'newuser', email: 'a@b.com' });
    mockApiLogin.mockResolvedValue({ access_token: 'tok', token_type: 'bearer' });
    const user = userEvent.setup();

    render(<SignupPage />);
    await user.type(screen.getByLabelText(/username/i), 'newuser');
    await user.type(screen.getByLabelText(/email/i), 'a@b.com');
    await user.type(screen.getByLabelText('Password'), 'password123');
    await user.type(screen.getByLabelText(/confirm password/i), 'password123');
    await user.click(screen.getByRole('button', { name: /create account/i }));

    await waitFor(() => {
      expect(mockSignup).toHaveBeenCalledWith('newuser', 'a@b.com', 'password123');
      expect(mockApiLogin).toHaveBeenCalledWith('newuser', 'password123');
      expect(mockAuthLogin).toHaveBeenCalledWith('tok', 'newuser');
      expect(mockPush).toHaveBeenCalledWith('/predictions');
    });
  });

  it('displays API error message', async () => {
    mockSignup.mockRejectedValue(new ApiError(409, 'Username already taken'));
    const user = userEvent.setup();

    render(<SignupPage />);
    await user.type(screen.getByLabelText(/username/i), 'taken');
    await user.type(screen.getByLabelText(/email/i), 'a@b.com');
    await user.type(screen.getByLabelText('Password'), 'password123');
    await user.type(screen.getByLabelText(/confirm password/i), 'password123');
    await user.click(screen.getByRole('button', { name: /create account/i }));

    await waitFor(() => {
      expect(screen.getByText('Username already taken')).toBeInTheDocument();
    });
  });

  it('shows loading state during submission', async () => {
    mockSignup.mockReturnValue(new Promise(() => {}));
    const user = userEvent.setup();

    render(<SignupPage />);
    await user.type(screen.getByLabelText(/username/i), 'newuser');
    await user.type(screen.getByLabelText(/email/i), 'a@b.com');
    await user.type(screen.getByLabelText('Password'), 'password123');
    await user.type(screen.getByLabelText(/confirm password/i), 'password123');
    await user.click(screen.getByRole('button', { name: /create account/i }));

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /creating account/i })).toBeDisabled();
    });
  });
});
