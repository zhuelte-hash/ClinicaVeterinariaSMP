export interface User {
  id: number;
  email: string;
  username: string;
  full_name: string | null;
  is_active: boolean;
  is_superuser: boolean;
  created_at: string;
  updated_at: string;
}

export interface UserCreate {
  email: string;
  username: string;
  full_name?: string;
  password: string;
}

export interface UserUpdate {
  email?: string;
  username?: string;
  full_name?: string;
  password?: string;
  is_active?: boolean;
}
