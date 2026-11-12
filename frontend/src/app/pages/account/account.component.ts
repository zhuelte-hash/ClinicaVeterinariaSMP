import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { finalize } from 'rxjs';
import { AuthService } from '../../core/auth/auth.service';
import { LoginResponse } from '../../core/auth/auth.models';
import { environment } from '../../../environments/environment';

@Component({
  selector: 'app-account', standalone: true, imports: [FormsModule, RouterLink],
  template: `<section class="mx-auto my-10 w-full max-w-lg space-y-5 rounded-2xl border border-slate-200 bg-white p-6"><h1 class="text-2xl font-extrabold">{{ profile ? 'Mi perfil' : verify ? 'Verificar correo' : token ? 'Nueva contraseña' : 'Recuperar contraseña' }}</h1>
    @if (error()) { <p class="rounded-xl bg-rose-50 p-3 text-rose-700" role="alert">{{ error() }}</p> } @if (message()) { <p class="rounded-xl bg-emerald-50 p-3 text-emerald-800" role="status">{{ message() }}</p> }
    <form #form="ngForm" (ngSubmit)="submit()" class="grid gap-4">
      @if (profile) { <label class="grid gap-1 text-sm font-bold">Nombre<input class="site-input" name="nombre" [(ngModel)]="name" required minlength="2" maxlength="150"></label><label class="grid gap-1 text-sm font-bold">Teléfono / WhatsApp<input class="site-input" name="telefono" [(ngModel)]="phone" maxlength="30"></label><label class="grid gap-1 text-sm font-bold">Dirección<input class="site-input" name="direccion" [(ngModel)]="address" maxlength="255"></label> }
      @else { <label class="grid gap-1 text-sm font-bold">Correo electrónico<input class="site-input" type="email" name="correo" [(ngModel)]="email" required email></label>
        @if (verify) { <p class="text-sm text-slate-600">Ingresa el código de seis dígitos recibido por correo. Caduca en 15 minutos.</p><label class="grid gap-1 text-sm font-bold">Código<input class="site-input" name="codigo" [(ngModel)]="code" required pattern="[0-9]{6}" maxlength="6" autocomplete="one-time-code"></label> }
        @if (token) { <label class="grid gap-1 text-sm font-bold">Nueva contraseña<input class="site-input" type="password" name="clave" [(ngModel)]="password" required minlength="8" maxlength="72" autocomplete="new-password"></label> }
      }
      <button class="site-button" [disabled]="busy() || form.invalid">{{ busy() ? 'Procesando…' : profile ? 'Guardar perfil' : verify ? 'Verificar y entrar' : token ? 'Guardar contraseña' : 'Enviar enlace' }}</button>
    </form>
    @if (verify) { <button class="font-bold text-brand-600" (click)="resend()" [disabled]="busy() || !email">Reenviar código</button> }
    @if (profile) { <hr><h2 class="font-bold">Cambiar contraseña</h2><form #passForm="ngForm" (ngSubmit)="changePassword()" class="grid gap-3"><label>Contraseña actual<input class="site-input" type="password" name="actual" [(ngModel)]="currentPassword" required autocomplete="current-password"></label><label>Nueva contraseña<input class="site-input" type="password" name="nueva" [(ngModel)]="password" required minlength="8" maxlength="72" autocomplete="new-password"></label><button class="site-button" [disabled]="busy() || passForm.invalid">Actualizar contraseña</button></form> }
    <a routerLink="/inicio" class="inline-block text-sm font-semibold text-brand-600">Volver al inicio</a></section>`,
})
export class AccountComponent {
  private readonly http = inject(HttpClient); private readonly route = inject(ActivatedRoute); private readonly router = inject(Router); private readonly auth = inject(AuthService);
  readonly profile = this.route.snapshot.routeConfig?.path === 'mi-perfil'; readonly verify = this.route.snapshot.routeConfig?.path === 'verificar-correo'; readonly token = this.route.snapshot.queryParamMap.get('token');
  readonly busy = signal(false); readonly error = signal(''); readonly message = signal('');
  email = this.route.snapshot.queryParamMap.get('correo') || ''; code = ''; password = ''; currentPassword = ''; name = this.auth.currentUser()?.nombre || ''; phone = this.auth.currentUser()?.telefono || ''; address = this.auth.currentUser()?.direccion || '';
  submit(): void {
    if (this.busy()) return;
    const request = this.profile ? this.http.patch(`${environment.apiUrl}/auth/me`, { nombre: this.name, telefono: this.phone, direccion: this.address }) : this.http.post<LoginResponse>(`${environment.apiUrl}/auth/${this.verify ? 'verificar-correo' : this.token ? 'restablecer-clave?correo=' + encodeURIComponent(this.email) : 'recuperar-clave'}`, this.verify ? { correo: this.email, codigo: this.code } : this.token ? { token: this.token, password: this.password } : { correo: this.email });
    this.busy.set(true); this.error.set('');
    request.pipe(finalize(() => this.busy.set(false))).subscribe({ next: response => {
      if (this.verify) { this.auth.acceptSession(response as LoginResponse); void this.router.navigateByUrl('/inicio'); }
      else if (this.profile) { this.auth.getCurrentUser().subscribe(); this.message.set('Perfil actualizado.'); }
      else if (this.token) { this.message.set('Contraseña actualizada. Inicia sesión con la nueva clave.'); this.password = ''; }
      else this.message.set('Si existe una cuenta activa, recibirás el enlace en tu correo.');
    }, error: error => this.fail(error) });
  }
  resend(): void { this.busy.set(true); this.http.post(`${environment.apiUrl}/auth/reenviar-verificacion`, { correo: this.email }).pipe(finalize(() => this.busy.set(false))).subscribe({ next: () => this.message.set('Solicitamos un nuevo código. Revisa tu correo.'), error: error => this.fail(error) }); }
  changePassword(): void { this.busy.set(true); this.http.patch(`${environment.apiUrl}/auth/me/password`, { current_password: this.currentPassword, new_password: this.password }).pipe(finalize(() => this.busy.set(false))).subscribe({ next: () => { this.auth.logout(); void this.router.navigateByUrl('/login'); }, error: error => this.fail(error) }); }
  private fail(error: HttpErrorResponse): void { this.error.set(typeof error.error?.detail === 'string' ? error.error.detail : 'Revisa los datos e intenta nuevamente.'); }
}
