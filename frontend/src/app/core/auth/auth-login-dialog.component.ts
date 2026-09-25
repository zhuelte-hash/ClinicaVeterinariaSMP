import { HttpErrorResponse } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { DialogRef, DIALOG_DATA } from '@angular/cdk/dialog';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { finalize } from 'rxjs';
import { CartService } from '../../services/cart.service';
import { NoticeService } from '../services/notice.service';
import { VisualSessionService } from '../services/visual-session.service';
import { AuthService } from './auth.service';

export interface AuthDialogData {
  returnUrl?: string;
}

@Component({
  selector: 'app-auth-login-dialog',
  standalone: true,
  imports: [ReactiveFormsModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section class="relative w-[calc(100vw-2rem)] max-w-md rounded-[2rem] bg-white p-6 shadow-2xl sm:p-9" aria-labelledby="dialog-login-title">
      <button type="button" (click)="dialogRef.close(false)" class="absolute right-4 top-4 grid h-9 w-9 place-items-center rounded-full text-slate-400 hover:bg-slate-100" aria-label="Cerrar">✕</button>
      <div class="text-center">
        <img src="/logo.png" alt="Clínica Veterinaria San Martín de Porres" class="mx-auto h-16 w-16 rounded-full border-2 border-[#0799AE]/25 object-cover" />
        <h2 id="dialog-login-title" class="mt-5 text-3xl font-black text-[#0B1B6D]">Iniciar sesión</h2>
        <p class="mt-2 text-sm text-slate-500">Ingresa para continuar sin salir de esta página.</p>
      </div>

      <form [formGroup]="loginForm" (ngSubmit)="submit()" class="mt-7 grid gap-4">
        <label class="grid gap-2 text-sm font-bold">Correo electrónico<input type="email" formControlName="email" autocomplete="email" placeholder="nombre@correo.com" class="rounded-xl border border-slate-300 px-4 py-3 font-normal outline-none focus:border-[#0799AE] focus:ring-2 focus:ring-[#0799AE]/10" /></label>
        <label class="grid gap-2 text-sm font-bold">Contraseña<div class="relative"><input [type]="showPassword() ? 'text' : 'password'" formControlName="password" autocomplete="current-password" placeholder="Tu contraseña" class="w-full rounded-xl border border-slate-300 px-4 py-3 pr-12 font-normal outline-none focus:border-[#0799AE] focus:ring-2 focus:ring-[#0799AE]/10" /><button type="button" (click)="showPassword.update(value => !value)" class="absolute right-3 top-1/2 -translate-y-1/2 text-xs font-bold text-[#0799AE]">{{ showPassword() ? 'Ocultar' : 'Ver' }}</button></div></label>
        @if (errorMessage()) { <p role="alert" class="rounded-xl bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-700">{{ errorMessage() }}</p> }
        <button type="submit" [disabled]="loginForm.invalid || submitting()" class="min-h-12 rounded-xl bg-[#0B1B6D] px-4 font-black text-white hover:bg-[#0799AE] disabled:opacity-45">{{ submitting() ? 'Ingresando...' : 'Iniciar sesión' }}</button>
      </form>

      <div class="mt-6 border-t border-slate-200 pt-5 text-center"><p class="mb-3 text-sm text-slate-500">¿Aún no tienes cuenta?</p><button type="button" (click)="openRegistration()" class="w-full rounded-xl border-2 border-[#0B1B6D] px-4 py-3 font-black text-[#0B1B6D] hover:border-[#0799AE] hover:text-[#0799AE]">Crear nueva cuenta</button></div>
    </section>
  `,
})
export class AuthLoginDialogComponent {
  readonly dialogRef = inject<DialogRef<boolean>>(DialogRef);
  readonly data = inject<AuthDialogData>(DIALOG_DATA);
  private readonly auth = inject(AuthService);
  private readonly formBuilder = inject(FormBuilder);
  private readonly visualSession = inject(VisualSessionService);
  private readonly cart = inject(CartService);
  private readonly notice = inject(NoticeService);
  private readonly router = inject(Router);

  readonly submitting = signal(false);
  readonly showPassword = signal(false);
  readonly errorMessage = signal('');
  readonly loginForm = this.formBuilder.nonNullable.group({
    email: ['', [Validators.required, Validators.email]],
    password: ['', Validators.required],
  });

  submit(): void {
    if (this.loginForm.invalid) {
      this.loginForm.markAllAsTouched();
      return;
    }
    this.submitting.set(true);
    this.errorMessage.set('');
    const { email, password } = this.loginForm.getRawValue();
    this.auth.login({ identifier: email, password })
      .pipe(finalize(() => this.submitting.set(false)))
      .subscribe({
        next: ({ user }) => {
          this.visualSession.login(user.correo, user.nombre);
          if (this.cart.addPending()) this.notice.show('Producto añadido al carrito');
          this.dialogRef.close(true);
        },
        error: (error: unknown) => this.errorMessage.set(this.getErrorMessage(error)),
      });
  }

  openRegistration(): void {
    this.dialogRef.close(false);
    void this.router.navigate(['/registro'], {
      queryParams: this.data.returnUrl ? { returnUrl: this.data.returnUrl } : undefined,
    });
  }

  private getErrorMessage(error: unknown): string {
    if (!(error instanceof HttpErrorResponse) || error.status === 0) {
      return 'No se pudo conectar con el servidor.';
    }
    if (error.status === 401) return 'El correo o la contraseña son incorrectos.';
    return 'No se pudo iniciar sesión. Inténtalo nuevamente.';
  }
}
