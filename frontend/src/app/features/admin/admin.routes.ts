import { Routes } from '@angular/router';
import { AdminLayoutComponent } from './layout/admin-layout.component';
import { permissionGuard } from '../../core/guards/permission.guard';

export const ADMIN_ROUTES: Routes = [{
  path: '', component: AdminLayoutComponent, canActivateChild: [permissionGuard], children: [
    { path: 'reportes', title: 'Reportes Excel | Clínica SMP', loadComponent: () => import('./pages/reportes/reportes.component').then(m => m.ReportesComponent) },
    { path: 'ordenes', title: 'Órdenes y pagos | Clínica SMP', loadComponent: () => import('../billing/billing-orders.component').then(m => m.BillingOrdersComponent) },
    { path: 'pedidos-web', title: 'Pedidos web | Clínica SMP', loadComponent: () => import('../purchase/purchase-orders.component').then(m => m.PurchaseOrdersComponent) },
    { path: '', pathMatch: 'full', redirectTo: 'dashboard' },
    { path: 'dashboard', title: 'Dashboard | Clinica SMP', loadComponent: () => import('./pages/dashboard/dashboard.component').then((m) => m.DashboardComponent) },
    { path: 'productos', title: 'Productos | Clinica SMP', loadComponent: () => import('./pages/productos/productos.component').then((m) => m.ProductosComponent) },
    { path: 'inventario', title: 'Inventario | Clinica SMP', loadComponent: () => import('./pages/inventario/inventario.component').then((m) => m.InventarioComponent) },
    { path: 'categorias', title: 'Categorias | Clinica SMP', loadComponent: () => import('./pages/categorias/categorias.component').then((m) => m.CategoriasComponent) },
    { path: 'proveedores', title: 'Proveedores | Clínica SMP', loadComponent: () => import('./pages/proveedores/proveedores.component').then(m => m.ProveedoresComponent) },
    { path: 'citas', title: 'Citas | Clinica SMP', loadComponent: () => import('./pages/citas/citas.component').then((m) => m.CitasComponent) },
    { path: 'ventas', title: 'Ventas | Clinica SMP', loadComponent: () => import('./pages/ventas/ventas.component').then((m) => m.VentasComponent) },
    { path: 'notificaciones', title: 'Notificaciones | Clinica SMP', loadComponent: () => import('./pages/notificaciones/notificaciones.component').then((m) => m.NotificacionesComponent) },
    { path: 'usuarios', title: 'Usuarios | Clinica SMP', loadComponent: () => import('./pages/usuarios/usuarios.component').then((m) => m.UsuariosComponent) },
    { path: 'clientes', title: 'Clientes | Clinica SMP', loadComponent: () => import('./pages/clientes/clientes.component').then((m) => m.ClientesComponent) },
    { path: 'historial-clinico', title: 'Historial clínico | Clínica SMP', loadComponent: () => import('./pages/historial-clinico/historial-clinico.component').then((m) => m.HistorialClinicoComponent) },
    { path: 'configuracion', title: 'Configuracion | Clinica SMP', loadComponent: () => import('./pages/configuracion/configuracion.component').then((m) => m.ConfiguracionComponent) },
  ],
}];

export default ADMIN_ROUTES;
