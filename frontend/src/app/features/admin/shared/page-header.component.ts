import { Component, input, output } from '@angular/core';

@Component({
  selector: 'admin-page-header', standalone: true,
  template: `<div class="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between"><div><p class="text-xs font-bold uppercase tracking-[.2em] text-teal-600">Administracion</p><h1 class="mt-1 text-2xl font-bold tracking-tight text-slate-900">{{ title() }}</h1><p class="mt-1 text-sm text-slate-500">{{ description() }}</p></div>@if (action()) {<button type="button" (click)="actionClick.emit()" class="rounded-xl bg-teal-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-teal-700 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-2">+ {{ action() }}</button>}</div>`,
})
export class PageHeaderComponent { readonly title = input.required<string>(); readonly description = input(''); readonly action = input(''); readonly actionClick = output<void>(); }
