export interface ProductListType {
  id: string;
  name: string;
  category: string;
  brand?: string;
  addedDate: string;
  price: string;
  price_original?: string;
  price_numeric?: number;
  currency?: string;
  description?: string;
  rating?: number;
  availability: string;
  imageSrc: string;
}
