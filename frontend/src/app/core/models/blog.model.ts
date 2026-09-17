export type BlogCategory = 'Alimentación' | 'Consejos' | 'Educación' | 'Salud';

export interface BlogArticle {
  slug: string;
  category: BlogCategory;
  title: string;
  date: string;
  excerpt: string;
  image: string;
  imageAlt: string;
  content: string[];
}
