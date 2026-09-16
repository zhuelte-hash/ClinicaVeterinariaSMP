import { Routes } from '@angular/router';
import { AdminLayoutComponent } from './layout/admin-layout.component';

export const ADMIN_ROUTES: Routes = [{
  path: '', component: AdminLayoutComponent, children: [
    { path: '', pathMatch: 'full', redirectTo: 'dashboard' },
    { path: 'dashboard', title: 'Dashboard | Clinica SMP', loadComponent: () => import('./pages/dashboard/dashboard.component').then((m) => m.DashboardComponent) },
    { path: 'productos', title: 'Productos | Clinica SMP', loadComponent: () => import('./pages/productos/productos.component').then((m) => m.ProductosComponent) },
    { path: 'inventario', title: 'Inventario | Clinica SMP', loadComponent: () => import('./pages/inventario/inventario.component').then((m) => m.InventarioComponent) },
    { path: 'categorias', title: 'Categorias | Clinica SMP', loadComponent: () => import('./pages/categorias/categorias.component').then((m) => m.CategoriasComponent) },
    { path: 'citas', title: 'Citas | Clinica SMP', loadComponent: () => import('./pages/citas/citas.component').then((m) => m.CitasComponent) },
    { path: 'ventas', title: 'Ventas | Clinica SMP', loadComponent: () => import('./pages/ventas/ventas.component').then((m) => m.VentasComponent) },
    { path: 'historial-clinico', title: 'Historial clinico | Clinica SMP', loadComponent: () => import('./pages/historial-clinico/historial-clinico.component').then((m) => m.HistorialClinicoComponent) },
    { path: 'notificaciones', title: 'Notificaciones | Clinica SMP', loadComponent: () => import('./pages/notificaciones/notificaciones.component').then((m) => m.NotificacionesComponent) },
    { path: 'usuarios', title: 'Usuarios | Clinica SMP', loadComponent: () => import('./pages/usuarios/usuarios.component').then((m) => m.UsuariosComponent) },
    { path: 'configuracion', title: 'Configuracion | Clinica SMP', loadComponent: () => import('./pages/configuracion/configuracion.component').then((m) => m.ConfiguracionComponent) },
  ],
}];

export default ADMIN_ROUTES;
