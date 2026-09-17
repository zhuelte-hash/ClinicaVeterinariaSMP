export type ProductCategory = 'Alimentos' | 'Accesorios' | 'Ropa' | 'Descanso y dormitorio';

export interface Product {
  id: string;
  name: string;
  category: ProductCategory;
  price: number;
  previousPrice?: number;
  image: string;
  imageAlt: string;
  featured?: boolean;
}

export type PharmacyCategory = 'Medicamentos veterinarios' | 'Alimento medicado' | 'Higiene y cuidado' | 'Suplementos';
export type PharmacyPresentation = 'Tableta' | 'Gotas' | 'Jarabe' | 'Crema' | 'Lata' | 'Polvo';
export type PharmacySpecies = 'Perros' | 'Gatos' | 'Uso general';

export interface PharmacyProduct {
  id: string;
  name: string;
  category: PharmacyCategory;
  presentation: PharmacyPresentation;
  species: PharmacySpecies;
  price: number;
  image: string;
  imageAlt: string;
  badge?: 'Disponible' | 'Recomendado' | 'Nuevo';
}
