import { ChangeDetectionStrategy, Component, input } from '@angular/core';

@Component({
  selector: 'app-service-menu-icon', standalone: true, changeDetection: ChangeDetectionStrategy.OnPush,
  host: { class: 'inline-grid shrink-0 place-items-center' },
  template: `
    @switch (icon()) {
      @case ('content_cut') { <svg viewBox="0 0 24 24"><circle cx="6" cy="7" r="3"/><circle cx="6" cy="17" r="3"/><path d="m8.5 8.5 11 7.5M8.5 15.5 19.5 8"/></svg> }
      @case ('bath') { <svg viewBox="0 0 24 24"><path d="M4 13h16v2a5 5 0 0 1-5 5H9a5 5 0 0 1-5-5v-2Zm3 0V7a3 3 0 0 1 6 0"/><path d="M13 7h3"/></svg> }
      @case ('medical_bath') { <svg viewBox="0 0 24 24"><path d="M4 13h16v2a5 5 0 0 1-5 5H9a5 5 0 0 1-5-5v-2Z"/><path d="M12 3v7m-3.5-3.5h7"/></svg> }
      @case ('brush') { <svg viewBox="0 0 24 24"><path d="m5 19 10-10 4 4L9 23H5v-4ZM14 10l3-5 2 2-4 4"/></svg> }
      @case ('ear') { <svg viewBox="0 0 24 24"><path d="M16.5 16c0 3-2 5-4.5 5-2 0-3.5-1.4-3.5-3.2 0-3 3.5-3.2 3.5-6.3 0-1.5-1-2.5-2.5-2.5S7 10 7 11.5M6 7a7 7 0 0 1 13 3"/></svg> }
      @case ('nail') { <svg viewBox="0 0 24 24"><path d="M8 3h8v9a4 4 0 0 1-8 0V3Zm0 5h8M6 21h12"/></svg> }
      @case ('science') { <svg viewBox="0 0 24 24"><path d="M9 3h6m-5 0v6l-5 9a2 2 0 0 0 1.7 3h10.6a2 2 0 0 0 1.7-3l-5-9V3M8 15h8"/></svg> }
      @case ('dentistry') { <svg viewBox="0 0 24 24"><path d="M7 3c2 0 3 1 5 1s3-1 5-1c3 0 4 3 4 6 0 4-2 12-5 12-2 0-1-6-4-6s-2 6-4 6C5 21 3 13 3 9c0-3 1-6 4-6Z"/></svg> }
      @case ('oral_surgery') { <svg viewBox="0 0 24 24"><path d="M7 3c2 0 3 1 5 1s3-1 5-1c3 0 4 3 4 6 0 4-2 12-5 12-2 0-1-6-4-6s-2 6-4 6C5 21 3 13 3 9c0-3 1-6 4-6Z"/><path d="m5 19 14-14"/></svg> }
      @case ('bed') { <svg viewBox="0 0 24 24"><path d="M3 19v-8m18 8v-6a2 2 0 0 0-2-2H9v8M3 15h18M5 11V7h4a2 2 0 0 1 2 2v2"/></svg> }
      @case ('medication') { <svg viewBox="0 0 24 24"><path d="m8 4 12 12-4 4L4 8l4-4Z"/><path d="m10 10 4-4M7 15h10"/></svg> }
      @case ('storefront') { <svg viewBox="0 0 24 24"><path d="M4 10v10h16V10M3 4h18l-2 6a3 3 0 0 1-4 0 3 3 0 0 1-6 0 3 3 0 0 1-4 0L3 4Zm5 16v-5h8v5"/></svg> }
      @case ('nutrition') { <svg viewBox="0 0 24 24"><path d="M5 8h14l-1 13H6L5 8Zm2-5h10l2 5H5l2-5Z"/><circle cx="12" cy="14" r="2.5"/></svg> }
      @case ('shield') { <svg viewBox="0 0 24 24"><path d="m12 3 8 3v6c0 5-3.4 8-8 10-4.6-2-8-5-8-10V6l8-3Z"/><path d="m9 12 2 2 4-4"/></svg> }
      @default { <svg viewBox="0 0 24 24"><path d="M12 3v18M3 12h18"/><circle cx="12" cy="12" r="9"/></svg> }
    }
  `,
  styles: [`svg { width: 100%; height: 100%; fill: none; stroke: currentColor; stroke-width: 1.8; stroke-linecap: round; stroke-linejoin: round; }`],
})
export class ServiceMenuIconComponent { readonly icon = input.required<string>(); }
