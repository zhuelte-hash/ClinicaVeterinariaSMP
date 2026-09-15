import { Routes } from '@angular/router';

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
    path: 'users',
    loadComponent: () =>
      import('./components/users/users.component').then((m) => m.UsersComponent),
  },
  { path: '**', redirectTo: '' },
];
