import type { User } from '../../models/user.model';

export const AUTH_TOKEN_KEY = 'clinic_access_token';

export interface AuthUser extends User {
  role?: string | null;
  rol?: string | null;
  es_admin?: boolean;
}

export interface LoginCredentials {
  identifier: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: AuthUser;
}
