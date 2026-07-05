import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';
import { User, UserCreate, UserUpdate } from '../../models/user.model';

@Component({
  selector: 'app-users',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="max-w-7xl mx-auto px-4 py-8">
      <div class="flex justify-between items-center mb-6">
        <h1 class="text-3xl font-bold text-gray-900">Users</h1>
        <button (click)="openCreateModal()"
                class="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors">
          + New User
        </button>
      </div>

      @if (loading) {
        <div class="text-center py-12">
          <div class="animate-spin w-8 h-8 border-4 border-primary-500 border-t-transparent rounded-full mx-auto"></div>
          <p class="mt-4 text-gray-500">Loading users...</p>
        </div>
      } @else if (error) {
        <div class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
          {{ error }}
        </div>
      } @else if (users.length === 0) {
        <div class="text-center py-12 text-gray-500">
          <p class="text-lg">No users found.</p>
          <p class="mt-2">Create your first user to get started.</p>
        </div>
      } @else {
        <div class="overflow-x-auto bg-white rounded-xl shadow-sm border border-gray-200">
          <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-50">
              <tr>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">ID</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Username</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Email</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Full Name</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-200">
              @for (user of users; track user.id) {
                <tr class="hover:bg-gray-50 transition-colors">
                  <td class="px-6 py-4 text-sm text-gray-500">{{ user.id }}</td>
                  <td class="px-6 py-4 text-sm font-medium text-gray-900">{{ user.username }}</td>
                  <td class="px-6 py-4 text-sm text-gray-700">{{ user.email }}</td>
                  <td class="px-6 py-4 text-sm text-gray-700">{{ user.full_name || '-' }}</td>
                  <td class="px-6 py-4">
                    <span [class]="user.is_active
                      ? 'px-2 py-1 text-xs font-medium rounded-full bg-green-100 text-green-800'
                      : 'px-2 py-1 text-xs font-medium rounded-full bg-red-100 text-red-800'">
                      {{ user.is_active ? 'Active' : 'Inactive' }}
                    </span>
                  </td>
                  <td class="px-6 py-4 text-right text-sm space-x-2">
                    <button (click)="openEditModal(user)"
                            class="text-primary-600 hover:text-primary-800 font-medium">Edit</button>
                    <button (click)="deleteUser(user.id)"
                            class="text-red-600 hover:text-red-800 font-medium">Delete</button>
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      }
    </div>

    @if (showModal) {
      <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
           (click)="closeModal()">
        <div class="bg-white rounded-xl shadow-xl p-6 w-full max-w-md mx-4" (click)="$event.stopPropagation()">
          <h2 class="text-xl font-bold text-gray-900 mb-4">
            {{ editingUser ? 'Edit User' : 'Create User' }}
          </h2>

          <form (ngSubmit)="submitForm()" class="space-y-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Username</label>
              <input type="text" [(ngModel)]="formData.username" name="username" required
                     class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500">
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Email</label>
              <input type="email" [(ngModel)]="formData.email" name="email" required
                     class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500">
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Full Name</label>
              <input type="text" [(ngModel)]="formData.full_name" name="full_name"
                     class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500">
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Password</label>
              <input type="password" [(ngModel)]="formData.password" name="password"
                     [required]="!editingUser"
                     class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500">
              @if (editingUser) {
                <p class="text-xs text-gray-500 mt-1">Leave blank to keep current password</p>
              }
            </div>

            @if (editingUser) {
              <div class="flex items-center gap-2">
                <input type="checkbox" [(ngModel)]="formData.is_active" name="is_active"
                       id="is_active" class="rounded border-gray-300 text-primary-600 focus:ring-primary-500">
                <label for="is_active" class="text-sm text-gray-700">Active</label>
              </div>
            }

            <div class="flex justify-end gap-3 pt-2">
              <button type="button" (click)="closeModal()"
                      class="px-4 py-2 text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors">
                Cancel
              </button>
              <button type="submit"
                      class="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors">
                {{ editingUser ? 'Save Changes' : 'Create' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    }
  `,
})
export class UsersComponent implements OnInit {
  users: User[] = [];
  loading = false;
  error = '';
  showModal = false;
  editingUser: User | null = null;
  formData: UserCreate & { is_active?: boolean } = {
    username: '',
    email: '',
    full_name: '',
    password: '',
  };

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.loadUsers();
  }

  loadUsers(): void {
    this.loading = true;
    this.error = '';
    this.api.getUsers().subscribe({
      next: (data) => {
        this.users = data;
        this.loading = false;
      },
      error: (err) => {
        this.error = 'Failed to load users. Make sure the backend is running.';
        this.loading = false;
        console.error(err);
      },
    });
  }

  openCreateModal(): void {
    this.editingUser = null;
    this.formData = { username: '', email: '', full_name: '', password: '' };
    this.showModal = true;
  }

  openEditModal(user: User): void {
    this.editingUser = user;
    this.formData = {
      username: user.username,
      email: user.email,
      full_name: user.full_name || '',
      password: '',
      is_active: user.is_active,
    };
    this.showModal = true;
  }

  closeModal(): void {
    this.showModal = false;
    this.editingUser = null;
  }

  submitForm(): void {
    if (this.editingUser) {
      const data: UserUpdate = {};
      if (this.formData.username !== this.editingUser.username) data.username = this.formData.username;
      if (this.formData.email !== this.editingUser.email) data.email = this.formData.email;
      if (this.formData.full_name !== (this.editingUser.full_name || '')) data.full_name = this.formData.full_name;
      if (this.formData.password) data.password = this.formData.password;
      data.is_active = this.formData.is_active;

      this.api.updateUser(this.editingUser.id, data).subscribe({
        next: () => {
          this.loadUsers();
          this.closeModal();
        },
        error: (err) => {
          this.error = 'Failed to update user.';
          console.error(err);
        },
      });
    } else {
      this.api.createUser(this.formData as UserCreate).subscribe({
        next: () => {
          this.loadUsers();
          this.closeModal();
        },
        error: (err) => {
          this.error = 'Failed to create user.';
          console.error(err);
        },
      });
    }
  }

  deleteUser(id: number): void {
    if (!confirm('Are you sure you want to delete this user?')) return;
    this.api.deleteUser(id).subscribe({
      next: () => this.loadUsers(),
      error: (err) => {
        this.error = 'Failed to delete user.';
        console.error(err);
      },
    });
  }
}
