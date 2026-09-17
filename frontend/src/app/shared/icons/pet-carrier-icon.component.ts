import { ChangeDetectionStrategy, Component } from '@angular/core';

@Component({
  selector: 'app-pet-carrier-icon',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  styles: [':host { display: inline-block; } svg { display: block; width: 100%; height: 100%; }'],
  template: `
    <svg viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
      <path d="M11 8V6.8C11 5.8 11.8 5 12.8 5h6.4c1 0 1.8.8 1.8 1.8V8" stroke-width="2.2"/>
      <path d="M7.2 9.2h17.6c1.5 0 2.7 1.2 2.7 2.7v12.4c0 1.5-1.2 2.7-2.7 2.7H7.2a2.7 2.7 0 0 1-2.7-2.7V11.9c0-1.5 1.2-2.7 2.7-2.7Z" stroke-width="2.2"/>
      <path d="M10 14.2h12v12.3H10z" stroke-width="1.8"/>
      <path d="M13 15v10m3-10v10m3-10v10" stroke="#0799AE" stroke-width="1.5"/>
      <path d="M4.8 18h5m12.2 0h5" stroke-width="1.7"/>
      <circle cx="8.5" cy="28" r="1.2" fill="currentColor" stroke="none"/>
      <circle cx="23.5" cy="28" r="1.2" fill="currentColor" stroke="none"/>
    </svg>
  `,
})
export class PetCarrierIconComponent {}
