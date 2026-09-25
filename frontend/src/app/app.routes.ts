import { Routes } from '@angular/router';
import { adminGuard } from './core/guards/admin.guard';
import { cashierGuard } from './core/guards/cashier.guard';
import { clientGuard } from './core/guards/client.guard';
import { purchaseGuard } from './core/guards/purchase.guard';

export const routes: Routes = [
  {
    path: '',
    pathMatch: 'full',
    redirectTo: 'inicio',
  },
  {
    path: 'inicio',
    loadComponent: () =>
      import('./components/home/home.component').then((m) => m.HomeComponent),
  },
  {
    path: 'productos',
    loadComponent: () =>
      import('./features/products/products-page.component').then((m) => m.ProductsPageComponent),
  },
  {
    path: 'farmacia',
    loadComponent: () =>
      import('./features/pharmacy/pharmacy-page.component').then((m) => m.PharmacyPageComponent),
  },
  {
    path: 'blog',
    loadComponent: () =>
      import('./features/blog/blog-page.component').then((m) => m.BlogPageComponent),
  },
  {
    path: 'blog/:slug',
    loadComponent: () =>
      import('./features/blog/blog-detail.component').then((m) => m.BlogDetailComponent),
  },
  {
    path: 'contacto',
    loadComponent: () =>
      import('./components/contacto/contacto.component').then((m) => m.ContactoComponent),
  },
  {
    path: 'carrito',
    canActivate: [purchaseGuard],
    loadComponent: () =>
      import('./components/carrito/carrito.component').then((m) => m.CarritoComponent),
  },
  {
    path: 'login',
    loadComponent: () =>
      import('./pages/login/login.component').then((m) => m.LoginComponent),
  },
  {
    path: 'checkout',
    canActivate: [purchaseGuard],
    loadComponent: () =>
      import('./features/purchase/purchase-checkout.component').then((m) => m.PurchaseCheckoutComponent),
  },
  {
    path: 'compra/confirmacion',
    canActivate: [purchaseGuard],
    loadComponent: () =>
      import('./features/purchase/purchase-confirmation.component').then((m) => m.PurchaseConfirmationComponent),
  },
  {
    path: 'servicios',
    loadComponent: () =>
      import('./features/services/services-page.component').then((m) => m.ServicesPageComponent),
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
    path: 'reservar-cita',
    canActivate: [clientGuard],
    loadComponent: () =>
      import('./features/appointments/appointments-page.component').then((m) => m.AppointmentsPageComponent),
  },
  {
    path: 'registro',
    loadComponent: () =>
      import('./pages/register/register.component').then((m) => m.RegisterComponent),
  },
  {
    path: 'caja',
    canActivate: [cashierGuard],
    loadChildren: () =>
      import('./features/cashier/cashier.routes').then((m) => m.CASHIER_ROUTES),
  },
  {
    path: 'users',
    redirectTo: 'admin/usuarios',
  },
  { path: '**', redirectTo: 'inicio' },
];
