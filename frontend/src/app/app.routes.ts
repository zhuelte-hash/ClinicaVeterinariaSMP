import { Routes } from '@angular/router';
import { adminGuard } from './core/guards/admin.guard';
import { cashierGuard } from './core/guards/cashier.guard';
import { clientGuard } from './core/guards/client.guard';
import { veterinarianGuard } from './core/guards/veterinarian.guard';

export const routes: Routes = [
  { path: 'verificar-correo', loadComponent: () => import('./pages/account/account.component').then(m => m.AccountComponent) },
  { path: 'recuperar-clave', loadComponent: () => import('./pages/account/account.component').then(m => m.AccountComponent) },
  { path: 'mi-perfil', canActivate: [clientGuard], loadComponent: () => import('./pages/account/account.component').then(m => m.AccountComponent) },
  { path: 'mis-pagos', canActivate: [clientGuard], loadComponent: () => import('./features/billing/billing-orders.component').then(m => m.BillingOrdersComponent) },
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
    path: 'productos/:id',
    loadComponent: () => import('./features/products/product-detail.component').then(m => m.ProductDetailComponent),
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
    loadComponent: () =>
      import('./components/carrito/carrito.component').then((m) => m.CarritoComponent),
  },
  {
    path: 'login',
    loadComponent: () =>
      import('./pages/login/login.component').then((m) => m.LoginComponent),
  },
  {
    path: 'mis-mascotas', canActivate: [clientGuard],
    loadComponent: () => import('./features/appointments/my-pets.component').then(m => m.MyPetsComponent),
  },
  {
    path: 'mis-compras',
    canActivate: [clientGuard],
    loadComponent: () => import('./features/purchase/purchase-orders.component').then(m => m.PurchaseOrdersComponent),
  },
  {
    path: 'checkout',
    canActivate: [clientGuard],
    loadComponent: () =>
      import('./features/purchase/purchase-checkout.component').then((m) => m.PurchaseCheckoutComponent),
  },
  {
    path: 'compra/confirmacion',
    canActivate: [clientGuard],
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
    path: 'veterinario',
    canActivate: [veterinarianGuard],
    loadChildren: () => import('./features/veterinarian/veterinarian.routes').then((m) => m.VETERINARIAN_ROUTES),
  },
  {
    path: 'users',
    redirectTo: 'admin/usuarios',
  },
  { path: '**', redirectTo: 'inicio' },
];
