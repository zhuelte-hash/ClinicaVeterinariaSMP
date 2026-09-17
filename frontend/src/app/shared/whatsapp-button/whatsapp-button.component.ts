import { ChangeDetectionStrategy, Component } from '@angular/core';

@Component({
  selector: 'app-whatsapp-button',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <a
      href="https://wa.me/51965939522?text=Hola%20necesito%20m%C3%A1s%20informaci%C3%B3n"
      target="_blank"
      rel="noopener noreferrer"
      class="fixed bottom-[max(1rem,env(safe-area-inset-bottom))] right-4 z-50 grid h-[50px] w-[50px] place-items-center rounded-full bg-[#25D366] text-white shadow-[0_8px_24px_rgba(37,211,102,0.35)] transition duration-200 hover:-translate-y-1 hover:shadow-[0_12px_28px_rgba(37,211,102,0.45)] focus-visible:outline focus-visible:outline-3 focus-visible:outline-offset-3 focus-visible:outline-[#0B1B6D] sm:bottom-6 sm:right-6 sm:h-[54px] sm:w-[54px]"
      title="Escríbenos por WhatsApp"
      aria-label="Contactar por WhatsApp"
    >
      <svg class="h-7 w-7" viewBox="0 0 32 32" fill="currentColor" aria-hidden="true">
        <path d="M16.04 3C8.85 3 3 8.73 3 15.78c0 2.25.6 4.45 1.75 6.38L3 28.5l6.55-1.68a13.18 13.18 0 0 0 6.48 1.68h.01C23.23 28.5 29 22.77 29 15.72 29 8.69 23.22 3 16.04 3Zm0 23.34c-2.02 0-4-.54-5.72-1.55l-.41-.24-3.89 1 1.04-3.7-.27-.42a10.55 10.55 0 0 1-1.67-5.65c0-5.86 4.9-10.62 10.93-10.62 6.02 0 10.82 4.73 10.82 10.56 0 5.86-4.82 10.62-10.83 10.62Zm6-7.94c-.33-.16-1.96-.95-2.27-1.06-.3-.1-.52-.16-.74.16-.22.32-.85 1.05-1.04 1.27-.19.21-.38.24-.71.08-1.93-.94-3.2-1.68-4.48-3.82-.34-.57.34-.53.98-1.76.11-.22.05-.4-.03-.56-.08-.16-.74-1.74-1.01-2.38-.27-.64-.54-.55-.74-.56h-.63c-.22 0-.58.08-.88.4-.3.32-1.15 1.1-1.15 2.68s1.18 3.11 1.34 3.32c.17.21 2.32 3.47 5.62 4.87 2.09.88 2.91.96 3.96.81.64-.09 1.96-.78 2.24-1.53.27-.76.27-1.4.19-1.54-.08-.13-.3-.21-.63-.37Z"/>
      </svg>
    </a>
  `,
})
export class WhatsappButtonComponent {}
