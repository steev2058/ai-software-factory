import fs from 'fs';
import path from 'path';

export type DemoProduct = {
  id: string;
  name: string;
  price: number;
  image: string;
  description: string;
};

export function getProducts(): DemoProduct[] {
  const p = path.join(process.cwd(), 'data', 'products.json');
  const raw = fs.readFileSync(p, 'utf-8');
  return JSON.parse(raw) as DemoProduct[];
}
