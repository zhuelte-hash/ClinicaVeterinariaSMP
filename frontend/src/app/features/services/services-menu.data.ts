import { VETERINARY_SERVICES } from './services.data';

export type ServicesMenuCategoryId = 'veterinary' | 'grooming';
export type ServiceMenuLinkType = 'veterinary' | 'grooming' | 'related-product';

export interface ServiceMenuLink {
  readonly name: string;
  readonly icon: string;
  readonly route: string;
  readonly fragment?: string;
  readonly description?: string;
  readonly type: ServiceMenuLinkType;
}

export interface ServiceMenuGroup {
  readonly label: string;
  readonly links: readonly ServiceMenuLink[];
}

export interface ServiceMenuCategory {
  readonly id: ServicesMenuCategoryId;
  readonly name: string;
  readonly icon: string;
  readonly description: string;
  readonly groups: readonly ServiceMenuGroup[];
}

export interface EstheticService extends ServiceMenuLink {
  readonly fragment: string;
  readonly type: 'grooming';
  readonly group: 'Cuidado e higiene' | 'Cortes y arreglo';
}

const veterinaryLink = (slug: string): ServiceMenuLink => {
  const service = VETERINARY_SERVICES.find((item) => item.slug === slug);
  if (!service) throw new Error(`Servicio veterinario no encontrado: ${slug}`);
  return { name: service.name, icon: service.icon, route: '/servicios', fragment: service.slug, type: 'veterinary' };
};

export const ESTHETIC_SERVICES: readonly EstheticService[] = [
  { name: 'Baños medicados', icon: 'medical_bath', route: '/servicios', fragment: 'banos-medicados', description: 'Higiene especializada con productos adecuados para pieles sensibles.', type: 'grooming', group: 'Cuidado e higiene' },
  { name: 'Baño estético', icon: 'bath', route: '/servicios', fragment: 'bano-estetico', description: 'Limpieza, secado y cuidado del pelaje para una apariencia saludable.', type: 'grooming', group: 'Cuidado e higiene' },
  { name: 'Cepillado', icon: 'brush', route: '/servicios', fragment: 'cepillado', description: 'Retiro cuidadoso de pelo suelto y nudos para mantener el manto.', type: 'grooming', group: 'Cuidado e higiene' },
  { name: 'Limpieza de oídos', icon: 'ear', route: '/servicios', fragment: 'limpieza-de-oidos', description: 'Higiene externa delicada para favorecer el bienestar diario.', type: 'grooming', group: 'Cuidado e higiene' },
  { name: 'Limpieza de glándulas anales', icon: 'hygiene', route: '/servicios', fragment: 'limpieza-de-glandulas-anales', description: 'Procedimiento higiénico realizado con manejo profesional y cuidadoso.', type: 'grooming', group: 'Cuidado e higiene' },
  { name: 'Aplicación de antipulgas', icon: 'shield', route: '/servicios', fragment: 'aplicacion-de-antipulgas', description: 'Aplicación externa responsable según las características de la mascota.', type: 'grooming', group: 'Cuidado e higiene' },
  { name: 'Cortes estéticos', icon: 'content_cut', route: '/servicios', fragment: 'cortes-esteticos', description: 'Estilos pensados para realzar su apariencia sin descuidar la comodidad.', type: 'grooming', group: 'Cortes y arreglo' },
  { name: 'Corte de pelo', icon: 'pet_grooming', route: '/servicios', fragment: 'corte-de-pelo', description: 'Recorte funcional adaptado al tipo de pelaje y necesidades de tu mascota.', type: 'grooming', group: 'Cortes y arreglo' },
  { name: 'Corte de uñas', icon: 'nail', route: '/servicios', fragment: 'corte-de-unas', description: 'Corte seguro para mejorar su comodidad al caminar y jugar.', type: 'grooming', group: 'Cortes y arreglo' },
];

const estheticGroup = (label: EstheticService['group']): ServiceMenuGroup => ({
  label,
  links: ESTHETIC_SERVICES.filter((service) => service.group === label),
});

export const RELATED_PRODUCT_LINKS: readonly ServiceMenuLink[] = [
  { name: 'Alimento balanceado', icon: 'nutrition', route: '/productos', type: 'related-product' },
  { name: 'Alimento medicado', icon: 'medication', route: '/farmacia', type: 'related-product' },
  { name: 'Tienda veterinaria', icon: 'storefront', route: '/productos', type: 'related-product' },
];

export const SERVICES_MENU_CATEGORIES: readonly ServiceMenuCategory[] = [
  {
    id: 'veterinary', name: 'Servicios Veterinarios', icon: 'medical_services', description: 'Prevención, diagnóstico y atención integral.',
    groups: [
      { label: 'Consultas y prevención', links: ['consultas-veterinarias', 'desparasitacion', 'vacunacion', 'profilaxis-dental'].map(veterinaryLink) },
      { label: 'Diagnóstico', links: ['laboratorio-clinico', 'ecografia', 'rayos-x'].map(veterinaryLink) },
      { label: 'Tratamientos y cirugía', links: ['tratamientos', 'cirugia-general', 'cirugia-dental', 'traumatologia'].map(veterinaryLink) },
      { label: 'Cuidados y servicios especiales', links: ['internamientos', 'farmacia-veterinaria', 'servicio-a-domicilio', 'hospedaje', 'microchips', 'urgencias-24-horas'].map(veterinaryLink) },
    ],
  },
  {
    id: 'grooming', name: 'Estética Canina y Felina', icon: 'content_cut', description: 'Cuidado, higiene y bienestar para perros y gatos.',
    groups: [estheticGroup('Cuidado e higiene'), estheticGroup('Cortes y arreglo')],
  },
];
