import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { Dialog } from '@angular/cdk/dialog';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ServiceCardComponent } from './service-card.component';
import { ServiceDetailDialogComponent } from './service-detail-dialog.component';
import { ServiceFilterComponent } from './service-filter.component';
import { SERVICE_CATEGORIES, ServiceCategoryFilter, VeterinaryService } from './service.model';
import { VETERINARY_SERVICES } from './services.data';
import { EstheticServiceCardComponent } from './esthetic-service-card.component';
import { ESTHETIC_SERVICES } from './services-menu.data';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../environments/environment';
import { ClinicService } from '../appointments/appointments.models';

@Component({
  selector: 'app-services-page',
  standalone: true,
  imports: [RouterLink, ServiceCardComponent, ServiceFilterComponent, EstheticServiceCardComponent],
  templateUrl: './services-page.component.html',
  styleUrl: './services-page.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ServicesPageComponent {
  private readonly dialog = inject(Dialog);
  readonly categories = SERVICE_CATEGORIES;
  readonly selectedCategory = signal<ServiceCategoryFilter>('Todos');
  readonly services = signal<VeterinaryService[]>([]);
  readonly loading = signal(true);
  readonly error = signal('');
  readonly emergencyService = VETERINARY_SERVICES.find((service) => service.emergency)!;
  readonly featuredService = computed(() => this.services().find(service => service.featured) || this.services()[0]);
  readonly estheticGroups = ['Cuidado e higiene', 'Cortes y arreglo'].map((label) => ({
    label,
    services: ESTHETIC_SERVICES.filter((service) => service.group === label),
  }));
  readonly filteredServices = computed(() => {
    const category = this.selectedCategory();
    return category === 'Todos'
      ? this.services()
      : this.services().filter((service) => service.category === category);
  });

  constructor() {
    inject(HttpClient).get<ClinicService[]>(`${environment.apiUrl}/portal/servicios`).subscribe({
      next: items => {
        this.services.set(items.map(item => {
          const design = VETERINARY_SERVICES.find(service => service.slug === item.codigo);
          return { ...(design || VETERINARY_SERVICES[0]), slug: item.codigo, name: item.nombre,
            summary: item.descripcion || 'Atención veterinaria profesional.', description: item.descripcion || 'Atención veterinaria profesional.',
            price: Number(item.precio_referencial), duration: item.duracion_estimada_min, featured: design?.featured };
        })); this.loading.set(false);
      }, error: () => { this.error.set('No se pudo cargar el catálogo de servicios y tarifas. Intenta actualizar la página.'); this.loading.set(false); },
    });
    inject(ActivatedRoute).fragment.pipe(takeUntilDestroyed()).subscribe((fragment) => {
      if (fragment) this.selectedCategory.set('Todos');
    });
  }

  selectCategory(category: ServiceCategoryFilter): void {
    this.selectedCategory.set(category);
  }

  openDetails(service: VeterinaryService): void {
    this.dialog.open(ServiceDetailDialogComponent, {
      data: service,
      ariaLabel: `Información sobre ${service.name}`,
      backdropClass: 'services-dialog-backdrop',
      panelClass: 'services-dialog-panel',
    });
  }
}
