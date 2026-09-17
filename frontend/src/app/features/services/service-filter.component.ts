import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { ServiceCategoryFilter } from './service.model';

@Component({
  selector: 'app-service-filter',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="flex gap-2 overflow-x-auto pb-2 sm:flex-wrap sm:justify-center" role="group" aria-label="Filtrar servicios por categoría">
      @for (category of categories(); track category) {
        <button
          type="button"
          class="shrink-0 rounded-full border px-4 py-2.5 text-sm font-semibold transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#1A98A2]"
          [class.bg-[#1A1E27]]="selected() === category"
          [class.text-white]="selected() === category"
          [class.border-[#1A1E27]]="selected() === category"
          [class.bg-white]="selected() !== category"
          [class.text-[#1A1E27]]="selected() !== category"
          [class.border-[#D5D2D3]]="selected() !== category"
          [attr.aria-pressed]="selected() === category"
          (click)="categoryChange.emit(category)"
        >{{ category }}</button>
      }
    </div>
  `,
})
export class ServiceFilterComponent {
  readonly categories = input.required<readonly ServiceCategoryFilter[]>();
  readonly selected = input.required<ServiceCategoryFilter>();
  readonly categoryChange = output<ServiceCategoryFilter>();
}
