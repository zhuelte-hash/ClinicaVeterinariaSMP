import { HttpErrorResponse } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { finalize } from 'rxjs';
import { AuthService } from '../../core/auth/auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './login.component.html',
  styleUrl: './login.component.css',
})
export class LoginComponent {
  private readonly formBuilder = inject(FormBuilder);
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  readonly isSubmitting = signal(false);
  readonly errorMessage = signal('');
  readonly loginForm = this.formBuilder.nonNullable.group({
    identifier: ['', [Validators.required]],
    password: ['', [Validators.required, Validators.minLength(6)]],
  });

  submit(): void {
    this.errorMessage.set('');

    if (this.loginForm.invalid) {
      this.loginForm.markAllAsTouched();
      return;
    }

    this.isSubmitting.set(true);
    this.auth
      .login(this.loginForm.getRawValue())
      .pipe(finalize(() => this.isSubmitting.set(false)))
      .subscribe({
        next: () => {
          const destination = this.auth.isAdmin()
            ? '/admin/dashboard'
            : '/no-autorizado';
          void this.router.navigateByUrl(destination);
        },
        error: (error: unknown) => this.errorMessage.set(this.getErrorMessage(error)),
      });
  }

  private getErrorMessage(error: unknown): string {
    if (!(error instanceof HttpErrorResponse)) {
      return 'No pudimos iniciar sesión. Inténtalo nuevamente.';
    }

    if (error.status === 0) {
      return 'No se pudo conectar con el servidor. Inténtalo nuevamente';
    }

    if (error.status === 401 || error.status === 400) {
      return 'El usuario o la contraseña son incorrectos.';
    }

    if (error.status === 429) {
      return 'Demasiados intentos. Espera unos minutos antes de volver a intentarlo.';
    }

    return 'No se pudo conectar con el servidor. Inténtalo nuevamente';
  }
}
