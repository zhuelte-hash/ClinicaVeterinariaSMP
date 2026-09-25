import { Routes } from '@angular/router';
import { CashierLayoutComponent } from './cashier-layout.component';

export const CASHIER_ROUTES: Routes = [{
  path: '',
  component: CashierLayoutComponent,
  children: [
    { path: '', pathMatch: 'full', redirectTo: 'dashboard' },
    {
      path: 'dashboard',
      title: 'Caja | Clinica SMP',
      loadComponent: () => import('./cashier-dashboard.component').then((m) => m.CashierDashboardComponent),
    },
    {
      path: 'ventas',
      title: 'Punto de venta | Clinica SMP',
      loadComponent: () => import('./cashier-sales.component').then((m) => m.CashierSalesComponent),
    },
  ],
}];

export default CASHIER_ROUTES;
