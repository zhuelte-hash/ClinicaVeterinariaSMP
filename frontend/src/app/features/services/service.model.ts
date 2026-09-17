export const SERVICE_CATEGORIES = [
  'Todos',
  'Consultas y prevención',
  'Diagnóstico',
  'Tratamientos y cirugía',
  'Hospitalización y cuidados',
  'Servicios especiales',
] as const;

export type ServiceCategory = (typeof SERVICE_CATEGORIES)[number];
export type ServiceCategoryFilter = ServiceCategory;

export interface VeterinaryService {
  readonly slug: string;
  readonly name: string;
  readonly summary: string;
  readonly description: string;
  readonly category: Exclude<ServiceCategory, 'Todos'>;
  readonly imageUrl: string;
  readonly imageAlt: string;
  readonly icon: string;
  readonly featured?: boolean;
  readonly emergency?: boolean;
}
