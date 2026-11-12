import { Routes } from '@angular/router';
import { CashierLayoutComponent } from './cashier-layout.component';
import { permissionGuard } from '../../core/guards/permission.guard';

export const CASHIER_ROUTES: Routes = [{
  path: '',
  component: CashierLayoutComponent,
  canActivateChild: [permissionGuard],
  children: [
    { path: 'ordenes', title: 'Órdenes y pagos | Clínica SMP', loadComponent: () => import('../billing/billing-orders.component').then(m => m.BillingOrdersComponent) },
    { path: 'pedidos-web', title: 'Pedidos web | Clínica SMP', loadComponent: () => import('../purchase/purchase-orders.component').then(m => m.PurchaseOrdersComponent) },
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
