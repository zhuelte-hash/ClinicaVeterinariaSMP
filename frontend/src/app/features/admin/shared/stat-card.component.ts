import { Component, input } from '@angular/core';

@Component({
  selector: 'admin-stat-card',
  standalone: true,
  template: `<article class="group rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"><div class="flex items-start justify-between"><div><p class="text-sm font-medium text-slate-500">{{ label() }}</p><p class="mt-2 text-2xl font-bold tracking-tight text-slate-900">{{ value() }}</p></div><div class="grid h-11 w-11 place-items-center rounded-xl bg-teal-50 text-xl text-teal-700">{{ icon() }}</div></div><p class="mt-3 text-xs font-medium" [class.text-emerald-600]="positive()" [class.text-rose-600]="!positive()">{{ change() }} <span class="font-normal text-slate-400">vs. periodo anterior</span></p></article>`,
})
export class StatCardComponent { readonly label = input.required<string>(); readonly value = input.required<string>(); readonly icon = input('•'); readonly change = input('+0%'); readonly positive = input(true); }
