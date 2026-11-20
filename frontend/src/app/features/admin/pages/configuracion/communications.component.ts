import { HttpClient } from '@angular/common/http';
import { Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { finalize, forkJoin } from 'rxjs';
import { environment } from '../../../../../environments/environment';
import { AuthService } from '../../../../core/auth/auth.service';
import { operationError } from '../../services/operations-api.service';

interface ChannelStatus { configurado: boolean; faltantes: string[]; }
interface MessageTemplate { evento: string; nombre_proveedor: string; contenido: string; variables: string[]; idioma: string; activa: boolean; }
interface Readiness { correo: ChannelStatus; whatsapp: ChannelStatus; webhook: ChannelStatus; telefono_clinica_valido: boolean; plantillas: MessageTemplate[]; alcance: string; }
interface OutgoingMessage { id: number; evento: string; destinatario: string; estado: string; intentos: number; error: string | null; proveedor_id: string | null; enviado_en: string | null; entregado_en: string | null; }
interface IncomingMessage { id: number; proveedor_id: string; telefono: string; resultado: string | null; }
interface TemplatePreview { contenido: string; parametros: { posicion: number; variable: string; valor: string }[]; encabezado: string; alcance: string; }

@Component({ selector: 'app-communications', standalone: true, imports: [FormsModule], styleUrl: '../../shared/admin-ui.css', template: `
  <section class="admin-card mt-6 grid max-w-4xl gap-4 p-5" aria-labelledby="communications-title">
    <div class="flex flex-wrap items-center justify-between gap-3"><h2 id="communications-title" class="text-xl font-bold">Comunicaciones de la primera entrega</h2><button type="button" class="admin-secondary" (click)="load()" [disabled]="busy()">Actualizar comunicaciones</button></div>
    <p class="text-sm text-slate-600">HU-002 y HU-004: correo de acceso. HU-036: cancelación. HU-039: asistencia entrante. HU-050: receta PDF.</p>
    <p class="text-sm text-slate-600">HU-067: comprobantes entrantes. HU-098: avisos al cliente. HU-104: todas las plantillas. HU-105/HU-106: avisos al veterinario; verificar su teléfono en Personal.</p>
    <div class="grid gap-3 rounded-xl border p-4" aria-labelledby="operational-title">
      <h3 id="operational-title" class="font-bold">Recordatorios y cobros prioritarios</h3>
      <p class="text-sm">El worker revisa cada intervalo configurado. Recordatorio de 24 h: entre más de 2 y hasta 24 horas antes; el de 2 h: hasta 2 horas antes. No se acumulan ambos al iniciar tarde el worker. Los reintentos comprueban horario, estado y contacto actuales.</p>
      <div class="flex flex-wrap gap-2">@for (flow of operationalFlows; track flow.event) { <button type="button" class="admin-secondary" [disabled]="busy()" (click)="focusFlow(flow.event)">{{ flow.label }}</button> }</div>
      <p class="text-sm">Orden sin comprobante: aviso desde las 2 h y antes de las 48 h; sin abonos validados ni comprobantes en revisión. A las 48 h vence si sigue sin pago/comprobante. El pago completo confirmado encola una boleta PDF; cargar un comprobante o registrar un abono parcial todavía no confirma el pago total.</p>
      <p class="text-sm">Las plantillas deben estar aprobadas en Meta. «cancelado» en el seguimiento indica que el mensaje dejó de corresponder al estado actual; no debe reenviarse.</p>
    </div>
    @if (error()) { <p role="alert" class="text-rose-700">{{ error() }}</p> }
    @if (message()) { <p role="status" class="text-teal-800">{{ message() }}</p> }
    @if (busy()) { <p role="status">Consultando o guardando comunicaciones…</p> }
    @if (status(); as data) {
      <div class="grid gap-3 sm:grid-cols-3">
        @for (channel of channels; track channel.key) { <div class="rounded-xl border p-3"><b>{{ channel.label }}</b><p>{{ data[channel.key].configurado ? 'Variables presentes' : 'Configuración incompleta' }}</p>@for (missing of data[channel.key].faltantes; track missing) { <small class="block break-words text-amber-800">{{ missing }}</small> }</div> }
      </div>
      <p class="text-sm">Teléfono público para asistencia: {{ data.telefono_clinica_valido ? 'formato válido; comprobar que sea el número Business receptor' : 'configurar un teléfono válido en Información de la clínica' }}.</p>
      <p class="text-sm text-slate-500">{{ data.alcance }} Las credenciales se configuran en backend/.env y requieren reiniciar API y worker.</p>
      <details><summary class="cursor-pointer font-bold">Preparar plantillas de cancelación y receta</summary>
        <p class="my-3 text-sm">Usa el nombre e idioma aprobados en Meta y el orden exacto de variables de su cuerpo. La receta exige encabezado de documento PDF. Guardar aquí no crea ni aprueba plantillas en Meta.</p>
        <label>Plantilla a configurar<select aria-label="Plantilla a configurar" class="admin-input" [ngModel]="templateEvent()" (ngModelChange)="templateEvent.set($event); preview.set(null)" [disabled]="busy()">@for (template of templates(); track template.evento) { <option [value]="template.evento">{{ templateLabel(template.evento) }}</option> }</select></label>
        @for (template of visibleTemplates(); track template.evento) {
          <form class="mt-4 grid gap-3 rounded-xl border p-4" #templateForm="ngForm" (ngSubmit)="templateForm.valid && save(template)">
            <h3 class="font-bold">{{ templateLabel(template.evento) }}</h3>
            <fieldset class="grid gap-3 sm:grid-cols-2" [disabled]="busy() || !auth.can('usuarios', 'editar')">
              <label>Nombre aprobado en Meta<input class="admin-input" name="provider" pattern="[a-z0-9_]*" maxlength="150" [(ngModel)]="template.nombre_proveedor"></label>
              <label>Idioma aprobado<input class="admin-input" name="language" required pattern="[a-z]{2}(_[A-Z]{2})?" [(ngModel)]="template.idioma"></label>
              <label class="sm:col-span-2">Contenido con variables<textarea class="admin-input" name="content" required minlength="3" maxlength="4000" rows="3" [(ngModel)]="template.contenido"></textarea></label>
              <label class="sm:col-span-2">Variables del cuerpo en orden (separadas por coma)<input class="admin-input" name="variables" required [ngModel]="template.variables.join(', ')" (ngModelChange)="setVariables(template, $event)"></label>
              <label><input type="checkbox" name="active" [(ngModel)]="template.activa"> Activar plantilla</label>
              @if (auth.can('usuarios', 'editar')) { <button class="admin-primary" [disabled]="templateForm.invalid">Guardar plantilla {{ template.evento }}</button> }
            </fieldset>
            <div class="grid gap-3 border-t pt-3">
              <h4 class="font-bold">Vista previa de la plantilla guardada</h4>
              <p class="text-sm">Usa datos ficticios. Guarda primero los cambios de plantilla; esta consulta no envía mensajes ni comprueba aprobación en Meta.</p>
              @for (variable of template.variables; track $index) { <label>Ejemplo de {{ variable }}<input class="admin-input" [name]="'example_' + $index" maxlength="500" [(ngModel)]="examples[variable]" (ngModelChange)="preview.set(null)" [disabled]="busy()"></label> }
              <button type="button" class="admin-secondary" (click)="showPreview(template)" [disabled]="busy()">Ver vista previa guardada</button>
              @if (preview(); as result) { <div role="status" class="rounded-xl bg-slate-50 p-3"><p class="whitespace-pre-wrap">{{ result.contenido }}</p><p class="mt-2 text-sm">Encabezado: {{ result.encabezado }}</p><ol class="mt-2 text-sm">@for (parameter of result.parametros; track parameter.posicion) { <li>{{ parameter.posicion }}. {{ parameter.variable }}: {{ parameter.valor }}</li> }</ol><p class="mt-2 text-sm">{{ result.alcance }}</p></div> }
            </div>
          </form>
        }
      </details>
    }
    <form class="flex flex-wrap items-end gap-3" (ngSubmit)="load()">
      <label>Evento de comunicación<select class="admin-input" name="event" [(ngModel)]="event"><option value="">Todos los eventos</option><option value="verificar">Verificación de correo</option><option value="recuperar">Recuperación de contraseña</option>@for (template of templates(); track template.evento) { <option [value]="template.evento">{{ templateLabel(template.evento) }}</option> }</select></label>
      <label>Estado del envío<select class="admin-input" name="state" [(ngModel)]="state"><option value="">Todos los estados</option>@for (value of states; track value) { <option [value]="value">{{ value }}</option> }</select></label>
      <button class="admin-secondary" [disabled]="busy()">Filtrar envíos</button>
    </form>
    <p class="text-sm text-slate-500">Últimos 200 registros del filtro. «enviado» acredita aceptación por proveedor; «entregado/leido» requiere webhook de WhatsApp. SMTP no acredita recepción en buzón. Reintentar prepara la cola: debe ejecutarse el worker.</p>
    <div class="overflow-x-auto"><table class="admin-table"><thead><tr><th>Evento / ID</th><th>Destinatario</th><th>Estado</th><th>Intentos</th><th>Referencia / detalle</th><th>Acción</th></tr></thead><tbody>
      @for (item of messages(); track item.id) { <tr><td>{{ item.evento }} #{{ item.id }}</td><td>{{ item.destinatario }}</td><td>{{ item.estado }} @if (item.entregado_en) { <small class="block">Entrega: {{ item.entregado_en }}</small> }</td><td>{{ item.intentos }}</td><td class="break-all">{{ item.proveedor_id || 'Sin referencia del proveedor' }} @if (item.error) { <small class="block text-rose-700">{{ item.error }}</small> }</td><td>@if (auth.can('usuarios', 'editar') && retryable(item)) { <button type="button" class="admin-secondary" [disabled]="busy()" (click)="retry(item.id)">Reintentar #{{ item.id }}</button> }</td></tr> }
      @empty { <tr><td colspan="6">Sin envíos para este filtro.</td></tr> }
    </tbody></table></div>
    <h3 class="font-bold">Recepción de WhatsApp y comprobantes</h3>
    <p class="text-sm text-slate-500">Últimos 200 mensajes procesados. «comprobante_vinculado» significa recibido para revisión, no pago validado. Los errores transitorios de descarga permiten que Meta reentregue el evento.</p>
    <div class="overflow-x-auto"><table class="admin-table"><thead><tr><th>Referencia entrante</th><th>Remitente</th><th>Resultado</th></tr></thead><tbody>
      @for (item of incoming(); track item.id) { <tr><td class="break-all">{{ item.proveedor_id }}</td><td>{{ item.telefono }}</td><td>{{ item.resultado || 'Sin resultado' }}</td></tr> }
      @empty { <tr><td colspan="3">Sin mensajes entrantes registrados.</td></tr> }
    </tbody></table></div>
  </section>
` })
export class CommunicationsComponent {
  readonly auth = inject(AuthService);
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiUrl}/admin/operaciones`;
  readonly status = signal<Readiness | null>(null); readonly templates = signal<MessageTemplate[]>([]); readonly messages = signal<OutgoingMessage[]>([]);
  readonly incoming = signal<IncomingMessage[]>([]); readonly templateEvent = signal('receta');
  readonly visibleTemplates = computed(() => this.templates().filter(template => template.evento === this.templateEvent()));
  readonly busy = signal(false); readonly error = signal(''); readonly message = signal('');
  readonly preview = signal<TemplatePreview | null>(null);
  readonly examples: Record<string, string> = { nombre: 'Cliente de prueba', mascota: 'Mascota de prueba', fecha: '20/11/2026 10:00', motivo: 'Cambio solicitado', codigo: 'OC-PRUEBA', cita: '123', producto: 'Vacuna de prueba', total: '40.00', enlace: 'https://ejemplo.invalid/encuesta/muestra' };
  // Los enlaces de vista previa son ficticios; el token real solo viaja en el mensaje al destinatario.
  readonly operationalFlows = [
    { event: 'bienvenida', label: 'Bienvenida (HU-099)' },
    { event: 'laboratorio', label: 'Resultado disponible (HU-107)' },
    { event: 'encuesta', label: 'Encuesta posterior (HU-108)' },
    { event: 'recordatorio_24h', label: 'Recordatorio 24 h (HU-032 / HU-097)' },
    { event: 'recordatorio_2h', label: 'Recordatorio 2 h (HU-097)' },
    { event: 'orden_creada', label: 'Orden creada (HU-066)' },
    { event: 'orden_recordatorio', label: 'Orden sin comprobante (HU-100)' },
    { event: 'pago_validado', label: 'Pago y boleta PDF (HU-101)' },
  ];
  readonly channels = [{ key: 'correo', label: 'Correo SMTP' }, { key: 'whatsapp', label: 'WhatsApp saliente' }, { key: 'webhook', label: 'Webhook entrante' }] as const;
  readonly states = ['pendiente', 'pendiente_configuracion', 'error', 'enviado', 'entregado', 'leido', 'cancelado'];
  event = ''; state = '';
  constructor() { this.load(); }
  load() {
    if (this.busy()) return;
    this.busy.set(true); this.error.set('');
    const params: Record<string, string> = {};
    if (this.event) params['evento'] = this.event;
    if (this.state) params['estado'] = this.state;
    forkJoin({ status: this.http.get<Readiness>(`${this.base}/comunicaciones/estado`), messages: this.http.get<OutgoingMessage[]>(`${this.base}/mensajes`, { params }), incoming: this.http.get<IncomingMessage[]>(`${this.base}/mensajes-entrantes`) }).pipe(finalize(() => this.busy.set(false))).subscribe({ next: data => { this.status.set(data.status); this.templates.set(data.status.plantillas); this.messages.set(data.messages); this.incoming.set(data.incoming); }, error: error => this.error.set(operationError(error)) });
  }
  templateLabel(event: string): string { return this.operationalFlows.find(flow => flow.event === event)?.label || ({ receta: 'Receta PDF (HU-050)', vacuna: 'Próxima vacuna (HU-056 / HU-103)', cita_cancelada: 'Cancelación de cita (HU-036)', cita_confirmada: 'Confirmación al cliente (HU-098)', cita_reprogramada: 'Reprogramación al cliente (HU-098)', veterinario_reprogramacion: 'Reprogramación al veterinario (HU-105)', veterinario_cancelacion: 'Cancelación al veterinario (HU-106)' } as Record<string, string>)[event] || event; }
  focusFlow(event: string) { if (this.busy()) return; this.event = event; this.state = ''; this.templateEvent.set(event); this.preview.set(null); this.load(); }
  setVariables(template: MessageTemplate, value: string) { template.variables = value.split(',').map(item => item.trim()).filter(Boolean); }
  save(template: MessageTemplate) {
    if (this.busy() || !this.auth.can('usuarios', 'editar')) return;
    const { evento, ...payload } = template;
    this.busy.set(true); this.error.set(''); this.message.set(''); this.preview.set(null);
    this.http.put<MessageTemplate>(`${this.base}/plantillas/${evento}`, payload).pipe(finalize(() => this.busy.set(false))).subscribe({ next: saved => { this.templates.update(rows => rows.map(row => row.evento === saved.evento ? saved : row)); this.message.set('Plantilla guardada. Comprueba su aprobación en Meta y realiza el envío real.'); }, error: error => this.error.set(operationError(error)) });
  }
  retryable(item: OutgoingMessage) { return ['pendiente', 'pendiente_configuracion', 'error'].includes(item.estado); }
  showPreview(template: MessageTemplate) {
    if (this.busy()) return;
    this.preview.set(null); this.error.set('');
    const valores = Object.fromEntries(template.variables.map(variable => [variable, this.examples[variable] || '']));
    if (Object.values(valores).some(value => !value.trim())) { this.error.set('Completa todos los ejemplos de la plantilla.'); return; }
    this.busy.set(true);
    this.http.post<TemplatePreview>(`${this.base}/plantillas/${template.evento}/vista-previa`, { valores }).pipe(finalize(() => this.busy.set(false))).subscribe({ next: result => this.preview.set(result), error: error => this.error.set(operationError(error)) });
  }
  retry(id: number) {
    if (this.busy() || !this.auth.can('usuarios', 'editar')) return;
    this.busy.set(true); this.error.set(''); this.message.set('');
    this.http.post(`${this.base}/mensajes/${id}/reintentar`, {}).subscribe({ next: () => { this.busy.set(false); this.message.set('Reintento preparado. Ejecuta el worker y actualiza para comprobar el resultado.'); this.load(); }, error: error => { this.busy.set(false); this.error.set(operationError(error)); } });
  }
}
