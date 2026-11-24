import { environment } from '../../../environments/environment';

/** Las fotos subidas pertenecen a la API; los recursos del catálogo, a Angular. */
export function publicImageUrl(url: string | null | undefined): string {
  if (!url) return '/catalogo/producto-sin-foto.svg';
  return url.startsWith('/uploads/') ? `${environment.apiUrl}${url}` : url;
}
