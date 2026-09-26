import { Component, input, output } from '@angular/core';

@Component({
  selector: 'admin-page-header', standalone: true,
  template: `<header class="mb-7 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between"><div class="min-w-0"><div class="mb-2 flex items-center gap-2"><span class="h-2 w-2 rounded-full bg-[#56c4d8] ring-4 ring-[#56c4d8]/15"></span><p class="text-[11px] font-bold uppercase tracking-[.24em] text-[#168ba1]">Centro de control</p></div><h1 class="text-3xl font-extrabold tracking-[-.035em] text-[#111827] sm:text-[2rem]">{{ title() }}</h1><p class="mt-1.5 max-w-2xl text-sm leading-6 text-slate-500">{{ description() }}</p></div>@if (action()) {<button type="button" (click)="actionClick.emit()" class="group inline-flex min-h-11 items-center justify-center gap-2 rounded-2xl bg-[#111827] px-5 py-2.5 text-sm font-bold text-white shadow-[0_10px_24px_rgb(17_24_39/.22)] transition hover:-translate-y-0.5 hover:bg-[#56c4d8] hover:text-[#111827] hover:shadow-[0_14px_30px_rgb(86_196_216/.3)] sm:self-auto"><span class="grid h-5 w-5 place-items-center rounded-full bg-white/15 text-base leading-none transition group-hover:rotate-90">+</span>{{ action() }}</button>}</header>`,
})
export class PageHeaderComponent { readonly title = input.required<string>(); readonly description = input(''); readonly action = input(''); readonly actionClick = output<void>(); }
