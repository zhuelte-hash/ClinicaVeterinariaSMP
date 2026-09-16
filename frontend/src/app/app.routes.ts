import { Routes } from '@angular/router';
import { adminGuard } from './core/guards/admin.guard';

export const routes: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./components/home/home.component').then((m) => m.HomeComponent),
  },
  {
    path: 'contacto',
    loadComponent: () =>
      import('./components/contacto/contacto.component').then((m) => m.ContactoComponent),
  },
  {
    path: 'carrito',
    loadComponent: () =>
      import('./components/carrito/carrito.component').then((m) => m.CarritoComponent),
  },
  {
    path: 'login',
    loadComponent: () =>
      import('./pages/login/login.component').then((m) => m.LoginComponent),
  },
  {
    path: 'no-autorizado',
    loadComponent: () =>
      import('./pages/no-authorized/no-authorized.component').then((m) => m.NoAuthorizedComponent),
  },
  {
    path: 'admin',
    canActivate: [adminGuard],
    loadChildren: () =>
      import('./features/admin/admin.routes').then((m) => m.ADMIN_ROUTES),
  },
  {
    path: 'users',
    redirectTo: 'admin/usuarios',
  },
  { path: '**', redirectTo: '' },
];
