export const AUTH_TOKEN_KEY = 'clinic_access_token';

export interface AuthUser {
  id: number;
  nombre: string;
  correo: string;
  tipo: 'cliente' | 'veterinario' | 'cajero' | 'administrador';
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
