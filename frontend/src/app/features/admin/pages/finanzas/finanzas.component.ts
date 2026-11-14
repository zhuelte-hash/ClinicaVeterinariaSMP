import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { forkJoin } from 'rxjs';
import { Expense, OperationsApiService, OperationsDashboard, operationError } from '../../services/operations-api.service';
import { PageHeaderComponent } from '../../shared/page-header.component';
import { AuthService } from '../../../../core/auth/auth.service';

@Component({ standalone: true, imports: [FormsModule, PageHeaderComponent], styleUrl: '../../shared/admin-ui.css', template: `
  <admin-page-header title="Indicadores financieros" description="Compara cobros efectivos y egresos registrados por período. Importes en soles." />
  @if (error()) { <p class="mb-4 rounded-xl bg-rose-50 p-4 text-rose-700" role="alert">{{ error() }}</p> }
  @if (message()) { <p class="mb-4 rounded-xl bg-teal-50 p-4 text-teal-800" role="status">{{ message() }}</p> }
  <form class="admin-card mb-5 flex flex-wrap items-end gap-3 p-4" #filters="ngForm" (ngSubmit)="load()"><label>Desde<input required class="admin-input" type="date" name="from" [(ngModel)]="from"></label><label>Hasta<input required class="admin-input" type="date" name="to" [(ngModel)]="to"></label><button class="admin-primary" [disabled]="busy() || filters.invalid">Consultar período</button></form>
  @if (loading()) { <p role="status">Consultando finanzas…</p> }
  @if (overview(); as data) {
    <div class="mb-5 grid gap-4 sm:grid-cols-3"><article class="admin-card p-5"><h2>Cobros efectivos</h2><b class="text-2xl text-teal-700">{{ money(data.finanzas.cobros) }}</b></article><article class="admin-card p-5"><h2>Egresos registrados</h2><b class="text-2xl text-rose-700">{{ money(data.finanzas.egresos) }}</b></article><article class="admin-card p-5"><h2>Resultado estimado</h2><b class="text-2xl">{{ money(data.finanzas.resultado) }}</b></article></div>
    <p class="mb-5 text-sm text-slate-500">Período consultado: {{ data.desde }} al {{ data.hasta }}. {{ data.finanzas.criterio }}. Incluye compras de mercadería como egreso; no es utilidad contable ni incluye gastos que no se hayan registrado.</p>
  }
  @if (auth.can('ventas', 'crear')) {
  <form class="admin-card mb-5 grid gap-4 p-5 sm:grid-cols-2" #expenseForm="ngForm" (ngSubmit)="save()"><h2 class="text-xl font-bold sm:col-span-2">Registrar egreso</h2>
    <label>Categoría<input required minlength="2" maxlength="80" class="admin-input" name="category" [(ngModel)]="expense.categoria" placeholder="Alquiler, servicios, insumos…"></label>
    <label>Concepto<input required minlength="3" maxlength="500" class="admin-input" name="concept" [(ngModel)]="expense.concepto"></label>
    <label>Monto (S/)<input required type="number" min="0.01" step="0.01" class="admin-input" name="amount" [(ngModel)]="expense.monto"></label>
    <label>Fecha<input required type="date" class="admin-input" name="date" [(ngModel)]="expense.fecha"></label><button class="admin-primary" [disabled]="busy() || expenseForm.invalid">Registrar egreso</button>
  </form>
  } @else { <p class="mb-5 text-sm text-slate-600">Acceso de consulta: necesitas permiso de creación en Ventas para registrar egresos.</p> }
  <section class="admin-card overflow-x-auto p-5"><h2 class="text-xl font-bold">Egresos del período consultado</h2><table class="admin-table"><thead><tr><th>Fecha</th><th>Categoría</th><th>Concepto</th><th>Monto</th></tr></thead><tbody>@for (item of expenses(); track item.id) { <tr><td>{{ item.fecha }}</td><td>{{ item.categoria }}</td><td>{{ item.concepto }}</td><td>{{ money(item.monto) }}</td></tr> } @empty { <tr><td colspan="4">Sin egresos registrados para este período.</td></tr> }</tbody></table></section>
` })
export class FinanzasComponent {
  readonly auth = inject(AuthService);
  private readonly api = inject(OperationsApiService);
  readonly error = signal(''); readonly message = signal(''); readonly busy = signal(false); readonly loading = signal(false);
  readonly overview = signal<OperationsDashboard | null>(null); readonly expenses = signal<Expense[]>([]);
  readonly today = new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Lima' }).format(new Date());
  from = this.today.slice(0, 8) + '01'; to = this.today;
  expense = { categoria: '', concepto: '', monto: 0, fecha: this.today };
  private version = 0;
  constructor() { this.load(); }
  load() { const version = ++this.version; this.error.set(''); this.loading.set(true); this.overview.set(null); this.expenses.set([]); forkJoin({ overview: this.api.dashboard(this.from, this.to), expenses: this.api.expenses(this.from, this.to) }).subscribe({ next: data => { if (version !== this.version) return; this.overview.set(data.overview); this.expenses.set(data.expenses); this.loading.set(false); }, error: error => { if (version === this.version) { this.error.set(operationError(error)); this.loading.set(false); } } }); }
  save() { if (this.busy() || !this.auth.can('ventas', 'crear')) return; this.busy.set(true); this.error.set(''); this.message.set(''); this.api.recordExpense(this.expense).subscribe({ next: () => { this.busy.set(false); this.expense = { categoria: '', concepto: '', monto: 0, fecha: this.today }; this.message.set('Egreso registrado.'); this.load(); }, error: error => { this.busy.set(false); this.error.set(operationError(error)); } }); }
  money(value: number | string) { return Number(value).toLocaleString('es-PE', { style: 'currency', currency: 'PEN' }); }
}
