import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { NoticeService } from '../../core/services/notice.service';

@Component({
  selector: 'app-notice',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (notice.message()) {
      <div role="status" aria-live="polite" class="fixed bottom-6 left-1/2 z-[70] flex -translate-x-1/2 items-center gap-3 whitespace-nowrap rounded-2xl bg-[#0B1B6D] px-5 py-3 text-sm font-bold text-white shadow-2xl">
        <span class="grid h-6 w-6 place-items-center rounded-full bg-sky-400">✓</span>{{ notice.message() }}
      </div>
    }
  `,
})
export class NoticeComponent { readonly notice = inject(NoticeService); }
