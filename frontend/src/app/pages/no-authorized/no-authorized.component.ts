import { Component, inject } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../../core/auth/auth.service';

@Component({
  selector: 'app-no-authorized',
  standalone: true,
  imports: [RouterLink],
  templateUrl: './no-authorized.component.html',
  styleUrl: './no-authorized.component.css',
})
export class NoAuthorizedComponent {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  logout(): void {
    this.auth.logout();
    void this.router.navigateByUrl('/login');
  }
}
