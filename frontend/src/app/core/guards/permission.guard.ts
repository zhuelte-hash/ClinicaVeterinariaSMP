import { inject } from '@angular/core';
import { CanActivateChildFn, Router } from '@angular/router';
import { catchError, map, of } from 'rxjs';
import { AuthService } from '../auth/auth.service';

export function routeModule(url: string): string | null {
  const path = url.split('?')[0].split('/').filter(Boolean);
  if (path[0] === 'admin') {
    return ({ productos: 'productos', categorias: 'productos', proveedores: 'productos', inventario: 'inventario', citas: 'citas', ventas: 'ventas', ordenes: 'ventas', dashboard: 'ventas', usuarios: 'usuarios', clientes: 'usuarios', configuracion: 'usuarios', 'historial-clinico': 'historias_clinicas' } as Record<string, string>)[path[1]] || null;
  }
  if (path[0] === 'caja') return 'ventas';
  if (path[0] === 'veterinario') {
    return path[1] === 'clientes' ? 'usuarios' : path[1] === 'mascotas' ? 'mascotas' : path[1] === 'ordenes' ? 'ventas' : ['inicio', 'agenda'].includes(path[1]) ? 'citas' : 'historias_clinicas';
  }
  return null;
}

export const permissionGuard: CanActivateChildFn = (_route, state) => {
  const auth = inject(AuthService);
  const router = inject(Router);
  const denied = router.createUrlTree(['/no-autorizado']);
  return auth.refreshPermissions().pipe(
    map(() => { const module = routeModule(state.url); return !module || auth.can(module) ? true : denied; }),
    catchError(() => of(denied)),
  );
};
