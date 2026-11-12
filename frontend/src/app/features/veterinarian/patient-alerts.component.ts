import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { Pet } from '../appointments/appointments.models';

@Component({
  selector: 'app-patient-alerts', standalone: true, changeDetection: ChangeDetectionStrategy.OnPush,
  template: `@if (pet().alergias || pet().condiciones_especiales) { <aside class="rounded-2xl border-2 border-amber-400 bg-amber-50 p-5 text-amber-950" role="alert"><h2 class="font-extrabold">⚠ Alertas clínicas de {{ pet().nombre }}</h2>@if (pet().alergias) { <p class="mt-2 whitespace-pre-line"><strong>Alergias:</strong> {{ pet().alergias }}</p> }@if (pet().condiciones_especiales) { <p class="mt-2 whitespace-pre-line"><strong>Condiciones especiales:</strong> {{ pet().condiciones_especiales }}</p> }<p class="mt-2 text-xs">Revisar antes de indicar medicamentos o procedimientos.</p></aside> }`,
})
export class PatientAlertsComponent { readonly pet = input.required<Pet>(); }
