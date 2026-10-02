import { Routes } from '@angular/router';
import { VeterinarianLayoutComponent } from './veterinarian-layout.component';

const moduleRoute = (path: string, module: string, title: string) => ({
  path,
  title: `${title} | Clínica SMP`,
  data: { module },
  loadComponent: () => import('./veterinarian-module.component').then((m) => m.VeterinarianModuleComponent),
});

export const VETERINARIAN_ROUTES: Routes = [{
  path: '',
  component: VeterinarianLayoutComponent,
  children: [
    { path: '', pathMatch: 'full', redirectTo: 'consultas' },
    {
      path: 'nueva-atencion',
      title: 'Nueva atención | Clínica SMP',
      loadComponent: () => import('./veterinarian-new-attention.component').then((m) => m.VeterinarianNewAttentionComponent),
    },
    {
      path: 'atencion/:id',
      title: 'Atención clínica | Clínica SMP',
      loadComponent: () => import('./veterinarian-attention.component').then((m) => m.VeterinarianAttentionComponent),
    },
    {
      path: 'mascota/:id',
      title: 'Ficha clínica | Clínica SMP',
      loadComponent: () => import('./veterinarian-pet-history.component').then((m) => m.VeterinarianPetHistoryComponent),
    },
    {
      path: 'clientes',
      title: 'Clientes | Clínica SMP',
      loadComponent: () => import('./veterinarian-clients.component').then((m) => m.VeterinarianClientsComponent),
    },
    moduleRoute('mascotas', 'mascotas', 'Mascotas e historia clínica'),
    moduleRoute('consultas', 'consultas', 'Consultas y cirugías'),
  ],
}];

export default VETERINARIAN_ROUTES;
