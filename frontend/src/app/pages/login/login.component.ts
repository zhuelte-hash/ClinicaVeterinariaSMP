import { HttpErrorResponse } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { finalize } from 'rxjs';
import { AuthService } from '../../core/auth/auth.service';
import { NoticeService } from '../../core/services/notice.service';
import { VisualSessionService } from '../../core/services/visual-session.service';
import { CartService } from '../../services/cart.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './login.component.html',
  styleUrl: './login.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class LoginComponent {
  private readonly formBuilder = inject(FormBuilder);
  private readonly auth = inject(AuthService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly notice = inject(NoticeService);
  private readonly visualSession = inject(VisualSessionService);
  private readonly cart = inject(CartService);

  readonly isSubmitting = signal(false);
  readonly errorMessage = signal('');
  readonly showPassword = signal(false);
  readonly returnUrl = this.route.snapshot.queryParamMap.get('returnUrl');
  readonly isPurchaseLogin = this.isSafePurchaseUrl(
    this.returnUrl,
  );
  readonly loginForm = this.formBuilder.nonNullable.group({
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required, Validators.minLength(6)]],
    remember: [false],
  });

  submit(): void {
    this.errorMessage.set('');

    if (this.loginForm.invalid) {
      this.loginForm.markAllAsTouched();
      return;
    }

    this.isSubmitting.set(true);
    const { email, password } = this.loginForm.getRawValue();

    this.auth
      .login({ identifier: email, password })
      .pipe(finalize(() => this.isSubmitting.set(false)))
      .subscribe({
        next: () => {
          this.visualSession.login(email, this.auth.currentUser()?.nombre ?? 'Cliente');
          if (this.cart.addPending()) this.notice.show('Producto añadido al carrito');
          const requestedUrl = this.route.snapshot.queryParamMap.get('returnUrl');
          const destination =
            this.isSafePurchaseUrl(requestedUrl)
              ? requestedUrl!
              : this.auth.isCashier() && requestedUrl?.startsWith('/caja')
                ? requestedUrl
              : this.auth.isAdmin() && requestedUrl?.startsWith('/admin')
                ? requestedUrl
                : this.auth.isAdmin()
                  ? '/admin/dashboard'
                  : this.auth.isCashier()
                    ? '/caja/dashboard'
                    : '/inicio';
          void this.router.navigateByUrl(destination);
        },
        error: (error: unknown) => this.errorMessage.set(this.getErrorMessage(error)),
      });
  }

  private isSafePurchaseUrl(url: string | null): boolean {
    const path = url?.split('?')[0];
    return Boolean(
      url
      && !url.startsWith('//')
      && ['/carrito', '/checkout', '/compra/confirmacion', '/reservar-cita'].includes(path!),
    );
  }

  showUpcomingFeature(event: Event): void {
    event.preventDefault();
    this.notice.show('Esta función estará disponible próximamente.');
  }

  private getErrorMessage(error: unknown): string {
    if (!(error instanceof HttpErrorResponse) || error.status === 0) {
      return 'No se pudo conectar con el servidor.';
    }
    if (error.status === 401) {
      return 'El correo o la contraseña son incorrectos.';
    }
    return 'No se pudo iniciar sesión. Inténtalo nuevamente.';
  }
}
