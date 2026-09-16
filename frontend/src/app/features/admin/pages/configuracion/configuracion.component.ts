import { Component, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { AdminSettings } from '../../models/admin.models';
import { AdminDataService } from '../../services/admin-data.service';
import { PageHeaderComponent } from '../../shared/page-header.component';

@Component({ selector: 'app-admin-configuracion', standalone: true, imports: [FormsModule, PageHeaderComponent], templateUrl: './configuracion.component.html', styleUrl: '../../shared/admin-ui.css' })
export class ConfiguracionComponent { readonly saved = signal(false); form: AdminSettings; constructor(readonly data: AdminDataService) { this.form = { ...data.settings() }; } save(): void { this.data.saveSettings(this.form); this.saved.set(true); window.setTimeout(() => this.saved.set(false), 2500); } }
