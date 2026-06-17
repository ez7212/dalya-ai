export interface Listing {
  id: string
  title: string
  developer: string
  location: string
  bedrooms: number
  bathrooms: number
  buaSqft: number
  priceAed: number
  paymentPercent: number
  nocStatus: 'ready' | 'at40' | 'pending'
  handoverQuarter: string
  imageUrl: string
  imageAlt: string
}
