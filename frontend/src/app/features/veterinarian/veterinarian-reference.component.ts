import { Component } from '@angular/core';

@Component({
  selector: 'app-veterinarian-reference',
  standalone: true,
  template: '<iframe class="reference-panel" src="/panel-veterinario/index.html?v=4" title="Panel veterinario"></iframe>',
  styles: [`
    :host { display: block; width: 100%; height: 100dvh; overflow: hidden; }
    .reference-panel { display: block; width: 100%; height: 100%; border: 0; }
  `],
})
export class VeterinarianReferenceComponent {}
