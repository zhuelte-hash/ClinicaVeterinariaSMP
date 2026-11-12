import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

@Component({
  selector: 'app-weight-evolution', standalone: true, changeDetection: ChangeDetectionStrategy.OnPush,
  template: `<section class="vet-panel"><div class="vet-panel-heading"><div><h2>Evolución del peso</h2><p>Registros de cada visita · kilogramos (kg)</p></div></div>
    @if (series().length) { <div class="p-4"><svg viewBox="0 0 620 250" class="w-full" role="img" aria-labelledby="weight-chart-title"><title id="weight-chart-title">Curva de peso por fecha. Los valores exactos aparecen en la tabla.</title><path d="M50 20V210H590" fill="none" stroke="currentColor" opacity=".3" /><text x="4" y="25" font-size="12" fill="currentColor">{{ scale().max.toFixed(2) }} kg</text><text x="4" y="205" font-size="12" fill="currentColor">{{ scale().min.toFixed(2) }} kg</text><polyline [attr.points]="points()" fill="none" stroke="#168ba1" stroke-width="3" />@for (point of series(); track point.key) { <circle [attr.cx]="x(point.date)" [attr.cy]="y(point.weight)" r="5" fill="#168ba1"><title>{{ dateLabel(point.date) }}: {{ point.weight }} kg</title></circle> }<text x="50" y="240" font-size="12" fill="currentColor">{{ dateLabel(series()[0].date) }}</text><text x="590" y="240" text-anchor="end" font-size="12" fill="currentColor">{{ dateLabel(series()[series().length - 1].date) }}</text></svg></div>
      <div class="vet-table-scroll"><table class="vet-data-table vet-data-table-compact"><caption class="sr-only">Valores de la curva de peso</caption><thead><tr><th>Fecha de visita</th><th>Peso (kg)</th></tr></thead><tbody>@for (point of series(); track point.key) { <tr><td>{{ dateLabel(point.date) }}</td><td>{{ point.weight.toFixed(2) }} kg</td></tr> }</tbody></table></div>
    } @else { <p class="vet-empty">Registra el peso en una atención para comenzar la curva de evolución.</p> }
  </section>`,
})
export class WeightEvolutionComponent {
  readonly records = input.required<{ id: number; fecha_inicio: string; peso: string | null }[]>();
  readonly series = computed(() => this.records().filter(item => item.peso !== null && Number.isFinite(Number(item.peso))).map(item => ({ key: item.id, date: item.fecha_inicio, weight: Number(item.peso) })).sort((a, b) => Date.parse(a.date) - Date.parse(b.date) || a.key - b.key));
  readonly scale = computed(() => { const weights = this.series().map(item => item.weight); return { min: Math.max(0, Math.min(...weights) - .5), max: Math.max(...weights) + .5 }; });
  readonly points = computed(() => this.series().map(item => `${this.x(item.date)},${this.y(item.weight)}`).join(' '));
  x(date: string): number { const items = this.series(); const first = Date.parse(items[0].date); const span = Date.parse(items[items.length - 1].date) - first; return span ? 50 + (Date.parse(date) - first) / span * 540 : 320; }
  y(weight: number): number { const scale = this.scale(); return 210 - (weight - scale.min) / (scale.max - scale.min) * 190; }
  dateLabel(value: string): string { return new Intl.DateTimeFormat('es-PE', { timeZone: 'America/Lima', dateStyle: 'short' }).format(new Date(value)); }
}
