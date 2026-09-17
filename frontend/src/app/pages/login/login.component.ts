import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { NoticeService } from '../../core/services/notice.service';
import { VisualSessionService } from '../../core/services/visual-session.service';

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
  private readonly router = inject(Router);
  private readonly notice = inject(NoticeService);
  private readonly session = inject(VisualSessionService);

  readonly isSubmitting = signal(false);
  readonly showPassword = signal(false);
  readonly loginForm = this.formBuilder.nonNullable.group({
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required, Validators.minLength(6)]],
    remember: [false],
  });

  submit(): void {
    if (this.loginForm.invalid) {
      this.loginForm.markAllAsTouched();
      return;
    }

    this.isSubmitting.set(true);
    this.session.login();
    this.notice.show('Inicio de sesión simulado correctamente.');
    setTimeout(() => void this.router.navigateByUrl('/inicio'), 450);
  }

  showUpcomingFeature(event: Event): void {
    event.preventDefault();
    this.notice.show('Esta función estará disponible próximamente.');
  }
}
