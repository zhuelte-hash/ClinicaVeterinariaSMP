import { Routes } from '@angular/router';
import { VeterinarianLayoutComponent } from './veterinarian-layout.component';

export const VETERINARIAN_ROUTES: Routes = [{
  path: '',
  component: VeterinarianLayoutComponent,
  children: [
    { path: '', pathMatch: 'full', redirectTo: 'dashboard' },
    {
      path: 'dashboard',
      title: 'Panel veterinario | Clínica SMP',
      loadComponent: () => import('./veterinarian-dashboard.component').then((m) => m.VeterinarianDashboardComponent),
    },
  ],
}];

export default VETERINARIAN_ROUTES;
