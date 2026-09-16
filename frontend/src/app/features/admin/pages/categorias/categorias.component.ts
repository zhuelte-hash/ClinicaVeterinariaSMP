import { Component, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { CategoryDraft } from '../../models/admin.models';
import { AdminDataService } from '../../services/admin-data.service';
import { PageHeaderComponent } from '../../shared/page-header.component';

@Component({ selector: 'app-admin-categorias', standalone: true, imports: [FormsModule, PageHeaderComponent], templateUrl: './categorias.component.html', styleUrl: '../../shared/admin-ui.css' })
export class CategoriasComponent { readonly open = signal(false); form: CategoryDraft = { name: '', description: '' }; constructor(readonly data: AdminDataService) {} save(): void { this.data.addCategory(this.form); this.form = { name: '', description: '' }; this.open.set(false); } }
