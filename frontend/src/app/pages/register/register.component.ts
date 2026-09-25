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
  selector: 'app-register',
  standalone: true,
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './register.component.html',
  styleUrl: '../login/login.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RegisterComponent {
  private readonly formBuilder = inject(FormBuilder);
  private readonly auth = inject(AuthService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly visualSession = inject(VisualSessionService);
  private readonly cart = inject(CartService);
  private readonly notice = inject(NoticeService);

  readonly isSubmitting = signal(false);
  readonly errorMessage = signal('');
  readonly showPassword = signal(false);
  readonly returnUrl = this.route.snapshot.queryParamMap.get('returnUrl');
  readonly registerForm = this.formBuilder.nonNullable.group({
    nombre: ['', [Validators.required, Validators.minLength(2), Validators.maxLength(150)]],
    correo: ['', [Validators.required, Validators.email]],
    telefono: ['', [Validators.pattern(/^\d{9,15}$/)]],
    password: ['', [Validators.required, Validators.minLength(8), Validators.maxLength(72)]],
    confirmPassword: ['', [Validators.required]],
  });

  submit(): void {
    this.errorMessage.set('');
    this.registerForm.markAllAsTouched();
    if (this.registerForm.invalid) return;

    const values = this.registerForm.getRawValue();
    if (values.password !== values.confirmPassword) {
      this.errorMessage.set('Las contraseñas no coinciden.');
      return;
    }

    this.isSubmitting.set(true);
    this.auth.register({
      nombre: values.nombre,
      correo: values.correo,
      password: values.password,
      telefono: values.telefono || undefined,
    }).pipe(finalize(() => this.isSubmitting.set(false))).subscribe({
      next: ({ user }) => {
        this.visualSession.login(user.correo, user.nombre);
        if (this.cart.addPending()) this.notice.show('Producto añadido al carrito');
        const destination = this.isSafePurchaseUrl(this.returnUrl) ? this.returnUrl! : '/inicio';
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

  private getErrorMessage(error: unknown): string {
    if (!(error instanceof HttpErrorResponse) || error.status === 0) {
      return 'No se pudo conectar con el servidor.';
    }
    if (error.status === 409) return 'Este correo ya tiene una cuenta registrada.';
    if (error.status === 422) return 'Revisa los datos ingresados.';
    return 'No se pudo crear la cuenta. Inténtalo nuevamente.';
  }
}
