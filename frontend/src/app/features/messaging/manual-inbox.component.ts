import { HttpClient } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { finalize } from 'rxjs';
import { environment } from '../../../environments/environment';
import { AuthService } from '../../core/auth/auth.service';
import { operationError } from '../admin/services/operations-api.service';

interface ManualRow { id: number; evento: string; estado: string; destinatario: string; entidad_id: number | null; fecha: string; documento_disponible: boolean; error: string | null; }
interface ManualInbox { modo: string; puede_gestionar: boolean; mensajes: ManualRow[]; alcance: string; }
interface PreparedMessage { id: number; evento: string; destinatario: string; contenido: string; whatsapp_url: string; documento_disponible: boolean; instrucciones: string; }

@Component({ selector: 'app-manual-inbox', standalone: true, imports: [FormsModule, RouterLink], styleUrl: '../admin/shared/admin-ui.css', template: `
  <section class="admin-card grid gap-4 p-5" aria-labelledby="manual-inbox-title">
    <div class="flex flex-wrap items-center justify-between gap-3"><h1 id="manual-inbox-title" class="text-2xl font-bold">WhatsApp manual</h1><button type="button" class="admin-secondary" (click)="load()" [disabled]="busy()">Actualizar bandeja manual</button></div>
    <p>Prepara tus mensajes, abre WhatsApp normal y pulsa Enviar. Los PDF se descargan y se adjuntan con el clip del chat.</p>
    @if (context) { <div class="flex flex-wrap items-center gap-3 rounded-xl bg-slate-50 p-3"><b>{{ contextLabel() }} #{{ reference }}</b><button type="button" class="admin-secondary" (click)="clearContext()" [disabled]="busy()">Ver todos los avisos</button></div> }
    @if (auth.isAdmin()) { <div class="flex flex-wrap gap-3"><a routerLink="/admin/citas" class="admin-secondary">Registrar asistencia recibida</a><a routerLink="/admin/ordenes" class="admin-secondary">Registrar comprobante recibido</a><a routerLink="/admin/configuracion" class="admin-secondary">Personalizar textos de WhatsApp</a></div> }
    @else if (auth.isCashier()) { <a routerLink="/caja/ordenes" class="admin-secondary justify-self-start">Registrar comprobante recibido</a> }
    @if (auth.currentUser()?.tipo === 'administrador' && auth.can('usuarios', 'editar')) { <div><button type="button" class="admin-secondary" (click)="prepareScheduled()" [disabled]="busy()">Preparar avisos programados ahora</button><p class="mt-2 text-sm text-slate-600">Actualiza recordatorios de citas y vacunas, órdenes pendientes y encuestas. Cada mensaje necesita un envío humano.</p></div> }
    @if (busy()) { <p role="status">Consultando comunicaciones…</p> }
    @if (error()) { <p role="alert" class="text-rose-700">{{ error() }}</p> }
    @if (notice()) { <p role="status" class="text-teal-800">{{ notice() }}</p> }
    <form class="flex flex-wrap items-end gap-3" (ngSubmit)="load()">
      <label>Tipo de aviso<select aria-label="Tipo de aviso" class="admin-input" name="event" [(ngModel)]="event"><option value="">Todos</option>@for (option of events; track option.key) { <option [value]="option.key">{{ option.label }}</option> }</select></label>
      <label>Estado de gestión<select aria-label="Estado de gestión" class="admin-input" name="state" [(ngModel)]="state"><option value="pendientes">Pendientes de gestión</option><option value="gestionado_manual">Gestionados manualmente</option><option value="cancelado">Avisos cancelados</option><option value="">Todos los estados</option></select></label>
      <button class="admin-secondary" [disabled]="busy()">Filtrar bandeja manual</button>
    </form>
    @if (prepared(); as selected) {
      <section class="grid gap-3 rounded-xl border border-teal-300 bg-teal-50 p-4" aria-labelledby="prepared-message-title">
        <h2 id="prepared-message-title" class="font-bold">Mensaje preparado #{{ selected.id }}</h2><p>Destinatario: {{ selected.destinatario }}</p>
        <label>Texto para WhatsApp<textarea class="admin-input" rows="4" readonly [value]="selected.contenido"></textarea></label><p class="text-sm">{{ selected.instrucciones }}</p>
        <div class="flex flex-wrap gap-3"><a class="admin-primary" [href]="selected.whatsapp_url" target="_blank" rel="noopener noreferrer">Abrir chat de WhatsApp</a><button type="button" class="admin-secondary" (click)="copy()" [disabled]="busy()">Copiar mensaje</button>@if (selected.documento_disponible) { <button type="button" class="admin-secondary" (click)="download()" [disabled]="busy()">Descargar PDF del aviso</button> }<button type="button" class="admin-secondary" (click)="finish()" [disabled]="busy()">Registrar gestión manual</button></div>
        @if (selected.evento === 'laboratorio' || selected.evento === 'encuesta') { <p class="break-words text-sm">Dirección usada en el enlace: {{ applicationUrl }}. Abre la aplicación desde una dirección accesible para el destinatario.</p> }
      </section>
    }
    @if (inbox(); as data) { <p class="text-sm text-slate-600">{{ data.alcance }}</p><div class="grid gap-3 lg:grid-cols-2">@for (item of data.mensajes; track item.id) { <article class="grid min-w-0 gap-2 rounded-xl border p-4"><h2 class="font-bold">{{ label(item.evento) }} · #{{ item.id }}</h2><p class="text-sm">{{ item.destinatario }} · {{ item.estado }}</p>@if (item.entidad_id) { <p class="text-sm text-slate-600">{{ operationLabel(item) }}</p> }<p class="text-sm text-slate-500">{{ date(item.fecha) }}</p>@if (item.error) { <p class="text-sm text-amber-800">{{ item.error }}</p> }@if (data.puede_gestionar && pending(item.estado)) { <div class="flex flex-wrap gap-2"><button type="button" class="admin-secondary" [disabled]="busy()" (click)="prepare(item.id)">Preparar aviso #{{ item.id }}</button><button type="button" class="admin-primary" [disabled]="busy()" (click)="prepare(item.id, true)">Abrir WhatsApp #{{ item.id }}</button></div> }</article> } @empty { <p>No hay avisos en la sede y filtros seleccionados.</p> }</div> }
  </section>
` })
export class ManualInboxComponent {
  readonly auth = inject(AuthService); private readonly http = inject(HttpClient);
  private readonly route = inject(ActivatedRoute); private readonly router = inject(Router);
  private readonly base = `${environment.apiUrl}/operaciones/comunicaciones/manuales`;
  readonly inbox = signal<ManualInbox | null>(null); readonly prepared = signal<PreparedMessage | null>(null);
  readonly busy = signal(false); readonly error = signal(''); readonly notice = signal('');
  event = ''; state = 'pendientes';
  context = ''; reference = 0;
  readonly applicationUrl = window.location.origin;
  private readonly preparation = { url_aplicacion: this.applicationUrl };
  private loadVersion = 0;
  readonly events = [
    { key: 'cita_confirmada', label: 'Confirmación de cita' }, { key: 'cita_reprogramada', label: 'Reprogramación de cita' }, { key: 'cita_cancelada', label: 'Cancelación de cita' },
    { key: 'receta', label: 'Receta y orden' }, { key: 'recordatorio_24h', label: 'Recordatorio de cita 24 h' }, { key: 'recordatorio_2h', label: 'Recordatorio de cita 2 h' }, { key: 'vacuna', label: 'Próxima vacuna' },
    { key: 'orden_creada', label: 'Orden de pago' }, { key: 'orden_recordatorio', label: 'Orden pendiente' }, { key: 'pago_validado', label: 'Pago y boleta' },
    { key: 'bienvenida', label: 'Bienvenida' }, { key: 'laboratorio', label: 'Laboratorio disponible' }, { key: 'encuesta', label: 'Encuesta posterior' },
    { key: 'veterinario_reprogramacion', label: 'Aviso de reprogramación al veterinario' }, { key: 'veterinario_cancelacion', label: 'Aviso de cancelación al veterinario' },
  ];
  constructor() {
    this.route.queryParamMap.pipe(takeUntilDestroyed()).subscribe(params => {
      this.event = this.events.some(item => item.key === params.get('evento')) ? params.get('evento')! : '';
      const context = params.get('tipo') || ''; const reference = Number(params.get('referencia'));
      this.context = ['cita', 'atencion', 'orden', 'venta', 'cliente'].includes(context) && Number.isSafeInteger(reference) && reference > 0 ? context : '';
      this.reference = this.context ? reference : 0; this.load();
    });
  }
  load(): void {
    const version = ++this.loadVersion;
    this.busy.set(true); this.error.set(''); this.prepared.set(null);
    const params: Record<string, string> = {}; if (this.event) params['evento'] = this.event; if (this.state) params['estado'] = this.state;
    if (this.context) { params['tipo'] = this.context; params['referencia'] = String(this.reference); }
    this.http.get<ManualInbox>(this.base, { params }).pipe(finalize(() => { if (version === this.loadVersion) this.busy.set(false); })).subscribe({ next: data => { if (version === this.loadVersion) this.inbox.set(data); }, error: error => { if (version === this.loadVersion) { this.inbox.set(null); this.error.set(operationError(error)); } } });
  }
  prepare(id: number, open = false): void {
    if (this.busy()) return; this.busy.set(true); this.error.set(''); this.notice.set(''); this.prepared.set(null);
    const popup = open ? window.open('about:blank', '_blank') : null;
    if (popup) popup.opener = null;
    this.http.post<PreparedMessage>(`${this.base}/${id}/preparar`, this.preparation).pipe(finalize(() => this.busy.set(false))).subscribe({ next: data => { this.prepared.set(data); if (popup) popup.location.replace(data.whatsapp_url); else if (open) this.notice.set('El navegador bloqueó la ventana. Usa Abrir chat de WhatsApp en el mensaje preparado.'); }, error: error => { popup?.close(); this.error.set(operationError(error)); } });
  }
  copy(): void {
    const selected = this.prepared(); if (!selected) return;
    if (!navigator.clipboard) { this.notice.set('Selecciona el texto preparado y cópialo para pegarlo en WhatsApp.'); return; }
    navigator.clipboard.writeText(selected.contenido).then(() => this.notice.set('Mensaje copiado.'), () => this.notice.set('Selecciona el texto preparado y cópialo para pegarlo en WhatsApp.'));
  }
  download(): void {
    const selected = this.prepared(); if (!selected || this.busy()) return; this.busy.set(true); this.error.set('');
    this.http.post(`${this.base}/${selected.id}/pdf`, this.preparation, { responseType: 'blob' }).pipe(finalize(() => this.busy.set(false))).subscribe({ next: blob => { const url = URL.createObjectURL(blob); const anchor = document.createElement('a'); anchor.href = url; anchor.download = `aviso-${selected.id}.pdf`; anchor.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); }, error: () => this.error.set('No se pudo descargar el PDF. Actualiza y vuelve a preparar el aviso.') });
  }
  finish(): void {
    const selected = this.prepared(); if (!selected || this.busy()) return; this.busy.set(true); this.error.set('');
    this.http.post(`${this.base}/${selected.id}/gestionar`, this.preparation).subscribe({ next: () => { this.notice.set('Gestión manual registrada. La entrega y lectura no se comprueban automáticamente.'); this.load(); }, error: error => { this.busy.set(false); this.error.set(operationError(error)); } });
  }
  prepareScheduled(): void {
    if (this.busy()) return; this.busy.set(true); this.error.set('');
    this.http.post<{ mensajes_preparados: number }>(`${environment.apiUrl}/admin/operaciones/automatizaciones`, {}).subscribe({ next: data => { this.notice.set(`Avisos programados actualizados. ${data.mensajes_preparados} nuevos en esta sede. Prepara y envía los que sigan vigentes.`); this.load(); }, error: error => { this.busy.set(false); this.error.set(operationError(error)); } });
  }
  clearContext(): void { this.router.navigate([], { relativeTo: this.route, queryParams: {} }); }
  contextLabel(): string { return ({ cita: 'Cita', atencion: 'Atención', orden: 'Orden', venta: 'Venta', cliente: 'Bienvenida del cliente' } as Record<string, string>)[this.context] || ''; }
  operationLabel(item: ManualRow): string { return `${['receta', 'laboratorio', 'encuesta'].includes(item.evento) ? 'Atención' : item.evento === 'vacuna' ? 'Vacuna' : ['orden_creada', 'orden_recordatorio', 'pago_validado'].includes(item.evento) ? 'Operación de pago' : item.evento === 'bienvenida' ? 'Cliente' : 'Cita'} #${item.entidad_id}`; }
  pending(state: string): boolean { return ['pendiente', 'pendiente_configuracion', 'error', 'pendiente_manual'].includes(state); }
  label(event: string): string { return this.events.find(item => item.key === event)?.label || event; }
  date(value: string): string { return new Intl.DateTimeFormat('es-PE', { dateStyle: 'short', timeStyle: 'short', timeZone: 'America/Lima' }).format(new Date(value)); }
}
