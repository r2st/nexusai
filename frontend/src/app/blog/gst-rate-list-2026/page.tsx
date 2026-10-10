import type { Metadata } from 'next';
import Link from 'next/link';
import { ShareButtons } from '@/components/blog/share-buttons';

export const metadata: Metadata = {
  title: 'GST Rate List 2026 — Complete Slab-Wise Rate Table',
  description: 'Complete GST rate list for 2026 with slab-wise breakdown at 5%, 12%, 18% & 28%. Find GST rates for all goods and services with HSN/SAC codes.',
  openGraph: {
    title: 'GST Rate List 2026 — Complete Slab-Wise Rate Table',
    description: 'Complete GST rate list for 2026 with slab-wise breakdown at 5%, 12%, 18% & 28%. Find GST rates for all goods and services.',
    url: 'https://gst.doaide.com/blog/gst-rate-list-2026',
    type: 'article',
  },
  alternates: {
    canonical: 'https://gst.doaide.com/blog/gst-rate-list-2026',
  },
};

export default function GSTRateList2026() {
  return (
    <article className="max-w-4xl mx-auto px-4 py-12">
      <div className="mb-8">
        <span className="text-sm font-semibold text-blue-600 bg-blue-50 px-3 py-1 rounded-full">GST Rates</span>
        <span className="text-sm text-gray-500 ml-3">Updated: 10 October 2026</span>
        <span className="text-sm text-gray-500 ml-3">20 min read</span>
      </div>

      <h1 className="text-3xl sm:text-4xl font-bold text-gray-900 dark:text-gray-100 mb-6">
        GST Rate List 2026: Complete Slab-Wise Rate Table for Goods &amp; Services
      </h1>

      <ShareButtons
        title="GST Rate List 2026: Complete Slab-Wise Rate Table"
        url="/blog/gst-rate-list-2026"
        className="mb-8"
      />

      <p className="text-lg text-gray-600 dark:text-gray-400 mb-8 leading-relaxed">
        The Goods and Services Tax (GST) in India follows a multi-slab rate structure with four main slabs &mdash; 5%, 12%, 18%, and 28%. Additionally, certain essential goods are exempt (0%) while specific luxury and sin goods attract a compensation cess above the 28% rate. This comprehensive guide lists the GST rates applicable to major categories of goods and services in 2026, updated after the latest GST Council recommendations.
      </p>

      <div className="bg-blue-50 border-l-4 border-blue-500 p-4 rounded mb-8">
        <p className="text-blue-900 font-medium">Quick Navigation</p>
        <ul className="text-blue-800 text-sm mt-2 space-y-1">
          <li>&bull; GST Rate Structure Overview</li>
          <li>&bull; Exempt (0% GST) Items</li>
          <li>&bull; 5% GST Rate Items</li>
          <li>&bull; 12% GST Rate Items</li>
          <li>&bull; 18% GST Rate Items</li>
          <li>&bull; 28% GST Rate Items</li>
          <li>&bull; GST Rates on Services</li>
          <li>&bull; Compensation Cess Items</li>
          <li>&bull; Recent GST Rate Changes</li>
          <li>&bull; How to Find the Correct GST Rate</li>
          <li>&bull; FAQs</li>
        </ul>
      </div>

      {/* Section 1 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">GST Rate Structure Overview</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        India adopted a four-tier GST rate structure when the tax was introduced on 1 July 2017. The GST Council, chaired by the Union Finance Minister, decides and revises rates periodically. As of 2026, the structure remains largely the same with minor changes over the years. Here is the overview:
      </p>

      <div className="overflow-x-auto mb-6">
        <table className="w-full border-collapse border border-gray-300 text-sm">
          <thead>
            <tr className="bg-gray-100">
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">GST Slab</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">CGST + SGST (Intra-State)</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">IGST (Inter-State)</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Typical Items</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="border border-gray-300 px-4 py-3 font-medium">0% (Exempt)</td>
              <td className="border border-gray-300 px-4 py-3">0%</td>
              <td className="border border-gray-300 px-4 py-3">0%</td>
              <td className="border border-gray-300 px-4 py-3">Fresh food, milk, education, healthcare</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-3 font-medium">5%</td>
              <td className="border border-gray-300 px-4 py-3">2.5% + 2.5%</td>
              <td className="border border-gray-300 px-4 py-3">5%</td>
              <td className="border border-gray-300 px-4 py-3">Packaged food, economy transport, fertilisers</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-3 font-medium">12%</td>
              <td className="border border-gray-300 px-4 py-3">6% + 6%</td>
              <td className="border border-gray-300 px-4 py-3">12%</td>
              <td className="border border-gray-300 px-4 py-3">Processed food, business-class air travel, medicines</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-3 font-medium">18%</td>
              <td className="border border-gray-300 px-4 py-3">9% + 9%</td>
              <td className="border border-gray-300 px-4 py-3">18%</td>
              <td className="border border-gray-300 px-4 py-3">Most goods &amp; services, electronics, financial services</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-3 font-medium">28%</td>
              <td className="border border-gray-300 px-4 py-3">14% + 14%</td>
              <td className="border border-gray-300 px-4 py-3">28%</td>
              <td className="border border-gray-300 px-4 py-3">Luxury goods, cars, tobacco, aerated drinks</td>
            </tr>
          </tbody>
        </table>
      </div>

      <p className="text-gray-700 leading-relaxed mb-4">
        Use the <Link href="/" className="text-blue-600 hover:text-blue-700 underline">GSTIndia GST Calculator</Link> to compute the exact tax for any rate slab instantly. Enter the amount, select the rate, and get the CGST, SGST, and IGST breakup.
      </p>

      {/* Section 2 - Exempt */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">Exempt (0% GST) Items</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        Certain goods and services are fully exempt from GST. These are mostly essential commodities and basic services that impact daily life. No tax is charged and no Input Tax Credit (ITC) is available on exempt supplies.
      </p>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">Exempt Goods</h3>

      <div className="overflow-x-auto mb-6">
        <table className="w-full border-collapse border border-gray-300 text-sm">
          <thead>
            <tr className="bg-gray-100">
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Category</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Items</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="border border-gray-300 px-4 py-3 font-medium">Fresh Food</td>
              <td className="border border-gray-300 px-4 py-3">Fresh fruits, fresh vegetables, fresh milk, eggs, bread (non-branded), natural honey, fresh meat &amp; fish, curd, lassi, buttermilk</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-3 font-medium">Grains &amp; Cereals</td>
              <td className="border border-gray-300 px-4 py-3">Rice, wheat, flour (atta), maize, bajra, jowar, ragi, oats (unbranded &amp; unpackaged)</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-3 font-medium">Other Essentials</td>
              <td className="border border-gray-300 px-4 py-3">Salt, puja samagri, bangles (non-precious metal), kumkum, bindi, sindoor, stamps, judicial papers, printed books, newspapers</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-3 font-medium">Agriculture</td>
              <td className="border border-gray-300 px-4 py-3">Seeds, live plants, live trees, unprocessed tea leaves, raw jute, raw cotton, raw silk, firewood, charcoal</td>
            </tr>
          </tbody>
        </table>
      </div>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">Exempt Services</h3>

      <ul className="list-disc pl-6 text-gray-700 space-y-2 mb-6">
        <li><strong>Education:</strong> Services by educational institutions (up to higher secondary) and services by IIMs leading to MBA degree</li>
        <li><strong>Healthcare:</strong> Services by clinical establishments, hospitals, doctors, paramedics</li>
        <li><strong>Public Transport:</strong> Metro, local train, non-AC bus, auto-rickshaw</li>
        <li><strong>Agriculture:</strong> Services related to cultivation, harvesting, renting of agri-machinery</li>
        <li><strong>Financial:</strong> Services by RBI, interest on deposits, Pradhan Mantri Jan Dhan Yojana accounts</li>
        <li><strong>Government:</strong> Services by government or local authority (excluding specific notified services)</li>
      </ul>

      <div className="bg-yellow-50 border-l-4 border-yellow-500 p-4 rounded mb-6">
        <p className="text-yellow-900 font-medium">Important Note</p>
        <p className="text-yellow-800 text-sm mt-1">Branded and packaged food items that were previously exempt became taxable at 5% from July 2022. This includes pre-packaged and labelled items like rice, wheat, atta, pulses, curd, paneer, and honey when sold in packages up to 25 kg/litre.</p>
      </div>

      {/* Section 3 - 5% */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">5% GST Rate &mdash; Items List</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        The 5% slab covers essential goods that are not exempt but require a lower tax burden. This slab was designed to keep commonly used items affordable for the average consumer.
      </p>

      <div className="overflow-x-auto mb-6">
        <table className="w-full border-collapse border border-gray-300 text-sm">
          <thead>
            <tr className="bg-gray-100">
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Category</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Items (5% GST)</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">HSN Chapter</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="border border-gray-300 px-4 py-3 font-medium">Packaged Food</td>
              <td className="border border-gray-300 px-4 py-3">Pre-packaged rice, wheat, atta, pulses, curd, paneer, honey, jaggery, spices (branded &amp; packed), sugar</td>
              <td className="border border-gray-300 px-4 py-3">Ch. 04-17</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-3 font-medium">Edible Oil</td>
              <td className="border border-gray-300 px-4 py-3">Mustard oil, groundnut oil, coconut oil, sunflower oil, rice bran oil</td>
              <td className="border border-gray-300 px-4 py-3">Ch. 15</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-3 font-medium">Fertilisers</td>
              <td className="border border-gray-300 px-4 py-3">All fertilisers other than those already exempt</td>
              <td className="border border-gray-300 px-4 py-3">Ch. 31</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-3 font-medium">Clothing &amp; Footwear</td>
              <td className="border border-gray-300 px-4 py-3">Apparel &amp; clothing below ₹1,000 per piece, footwear below ₹1,000 per pair</td>
              <td className="border border-gray-300 px-4 py-3">Ch. 61-64</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-3 font-medium">Fuel &amp; Energy</td>
              <td className="border border-gray-300 px-4 py-3">Coal, lignite, peat, LPG for domestic use, kerosene (PDS)</td>
              <td className="border border-gray-300 px-4 py-3">Ch. 27</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-3 font-medium">Transport</td>
              <td className="border border-gray-300 px-4 py-3">Economy class air travel (domestic), cab aggregator services (Ola, Uber)</td>
              <td className="border border-gray-300 px-4 py-3">SAC 9964</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-3 font-medium">Others</td>
              <td className="border border-gray-300 px-4 py-3">Agarbatti, hand-made carpets, life-saving drugs, small restaurants (non-AC, no ITC), newsprint</td>
              <td className="border border-gray-300 px-4 py-3">Various</td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* Section 4 - 12% */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">12% GST Rate &mdash; Items List</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        The 12% slab is the second-lowest standard rate and covers processed goods, some industrial inputs, and mid-tier services.
      </p>

      <div className="overflow-x-auto mb-6">
        <table className="w-full border-collapse border border-gray-300 text-sm">
          <thead>
            <tr className="bg-gray-100">
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Category</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Items (12% GST)</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">HSN Chapter</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="border border-gray-300 px-4 py-3 font-medium">Processed Food</td>
              <td className="border border-gray-300 px-4 py-3">Butter, ghee, cheese, dry fruits, fruit juices (with added sugar), namkeen, bakery items, pickles, sauces</td>
              <td className="border border-gray-300 px-4 py-3">Ch. 04-21</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-3 font-medium">Apparel &amp; Footwear</td>
              <td className="border border-gray-300 px-4 py-3">Clothing above ₹1,000 per piece, footwear above ₹1,000 per pair</td>
              <td className="border border-gray-300 px-4 py-3">Ch. 61-64</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-3 font-medium">Pharma &amp; Medical</td>
              <td className="border border-gray-300 px-4 py-3">Ayurvedic medicines, diagnostic kits, medical-grade oxygen, orthopaedic appliances</td>
              <td className="border border-gray-300 px-4 py-3">Ch. 30, 90</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-3 font-medium">Industrial Goods</td>
              <td className="border border-gray-300 px-4 py-3">Sewing machines, cell phone (value up to ₹10,000), bicycles, umbrellas, spectacle lenses</td>
              <td className="border border-gray-300 px-4 py-3">Ch. 84-90</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-3 font-medium">Construction</td>
              <td className="border border-gray-300 px-4 py-3">Works contract for affordable housing (PMAY &amp; similar), marble &amp; granite blocks</td>
              <td className="border border-gray-300 px-4 py-3">Ch. 25, 68</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-3 font-medium">Services</td>
              <td className="border border-gray-300 px-4 py-3">Business class air travel, rail freight, hotel rooms ₹1,000&ndash;₹7,500 per night, works contract for government</td>
              <td className="border border-gray-300 px-4 py-3">SAC 9964-9972</td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* Section 5 - 18% */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">18% GST Rate &mdash; Items List</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        The 18% slab is the standard rate and covers the largest number of goods and services under GST. Most manufactured products, IT services, and financial services fall in this bracket.
      </p>

      <div className="overflow-x-auto mb-6">
        <table className="w-full border-collapse border border-gray-300 text-sm">
          <thead>
            <tr className="bg-gray-100">
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Category</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Items (18% GST)</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">HSN Chapter</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="border border-gray-300 px-4 py-3 font-medium">Electronics</td>
              <td className="border border-gray-300 px-4 py-3">Mobile phones, laptops, tablets, monitors, printers, cameras, computer accessories, CCTV cameras</td>
              <td className="border border-gray-300 px-4 py-3">Ch. 84-85</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-3 font-medium">Household Items</td>
              <td className="border border-gray-300 px-4 py-3">Refrigerators, washing machines, water heaters, iron, fan, mixer-grinder, vacuum cleaners, kitchen appliances</td>
              <td className="border border-gray-300 px-4 py-3">Ch. 84-85</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-3 font-medium">Food &amp; Beverages</td>
              <td className="border border-gray-300 px-4 py-3">Chocolates, ice cream, pasta, cornflakes, instant food mixes, mineral water, soft drinks (non-aerated)</td>
              <td className="border border-gray-300 px-4 py-3">Ch. 17-22</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-3 font-medium">Personal Care</td>
              <td className="border border-gray-300 px-4 py-3">Soaps, shampoos, hair oil, toothpaste, deodorants, cosmetics, perfumes, razors</td>
              <td className="border border-gray-300 px-4 py-3">Ch. 33-34</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-3 font-medium">Construction Materials</td>
              <td className="border border-gray-300 px-4 py-3">Cement, TMT bars, iron &amp; steel, aluminium, copper, tiles, plywood, paints, varnishes</td>
              <td className="border border-gray-300 px-4 py-3">Ch. 25-32, 68-76</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-3 font-medium">Stationery &amp; Paper</td>
              <td className="border border-gray-300 px-4 py-3">Notebooks, exercise books, printing paper, envelopes, registers, pens, pencils</td>
              <td className="border border-gray-300 px-4 py-3">Ch. 48-49</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-3 font-medium">Services (Major)</td>
              <td className="border border-gray-300 px-4 py-3">IT/ITES, consulting, legal, accounting, restaurants with ITC, hotel rooms above ₹7,500, telecom, insurance, banking, outdoor catering</td>
              <td className="border border-gray-300 px-4 py-3">SAC 9971-9997</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div className="bg-blue-50 border-l-4 border-blue-500 p-4 rounded mb-6">
        <p className="text-blue-900 font-medium">Pro Tip</p>
        <p className="text-blue-800 text-sm mt-1">Not sure about the GST rate for a specific item? Use the <Link href="/" className="text-blue-600 underline">GSTIndia HSN Code Finder</Link> to search by product name and get the applicable HSN code along with the exact GST rate.</p>
      </div>

      {/* Section 6 - 28% */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">28% GST Rate &mdash; Items List</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        The highest slab at 28% is reserved for luxury goods, demerit goods (sin goods), and items considered non-essential. Over the years, the GST Council has significantly reduced the number of items in this bracket.
      </p>

      <div className="overflow-x-auto mb-6">
        <table className="w-full border-collapse border border-gray-300 text-sm">
          <thead>
            <tr className="bg-gray-100">
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Category</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Items (28% GST)</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">HSN Chapter</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="border border-gray-300 px-4 py-3 font-medium">Automobiles</td>
              <td className="border border-gray-300 px-4 py-3">Motor cars, SUVs, motor vehicles for transport of persons (all engine capacities)</td>
              <td className="border border-gray-300 px-4 py-3">Ch. 87</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-3 font-medium">Tobacco &amp; Pan Masala</td>
              <td className="border border-gray-300 px-4 py-3">Cigarettes, cigars, chewing tobacco, pan masala, gutkha</td>
              <td className="border border-gray-300 px-4 py-3">Ch. 24</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-3 font-medium">Aerated Drinks</td>
              <td className="border border-gray-300 px-4 py-3">Aerated water, caffeinated beverages, energy drinks</td>
              <td className="border border-gray-300 px-4 py-3">Ch. 22</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-3 font-medium">Luxury Items</td>
              <td className="border border-gray-300 px-4 py-3">Air conditioners, dishwashers, yachts, private aircraft, race horses, sunscreen, weighing machines</td>
              <td className="border border-gray-300 px-4 py-3">Various</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-3 font-medium">Entertainment</td>
              <td className="border border-gray-300 px-4 py-3">Cinema tickets above ₹100, gambling, betting, horse racing, casinos, online gaming (on full face value)</td>
              <td className="border border-gray-300 px-4 py-3">SAC 9996</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-3 font-medium">Services</td>
              <td className="border border-gray-300 px-4 py-3">5-star hotel accommodation (room tariff above ₹7,500 effective rate), race club services</td>
              <td className="border border-gray-300 px-4 py-3">SAC 9963</td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* Section 7 - Services */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">GST Rates on Common Services</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        Services are classified under the Services Accounting Code (SAC) system. Here is a consolidated view of GST rates applicable to the most commonly used services in India:
      </p>

      <div className="overflow-x-auto mb-6">
        <table className="w-full border-collapse border border-gray-300 text-sm">
          <thead>
            <tr className="bg-gray-100">
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Service</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">GST Rate</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">SAC Code</th>
            </tr>
          </thead>
          <tbody>
            {[
              ['Restaurants (non-AC, no ITC)', '5%', '9963'],
              ['Restaurants (with AC / ITC claim)', '18%', '9963'],
              ['Outdoor catering', '18%', '9963'],
              ['Hotel rooms (up to ₹1,000/night)', 'Exempt', '9963'],
              ['Hotel rooms (₹1,001 to ₹7,500/night)', '12%', '9963'],
              ['Hotel rooms (above ₹7,500/night)', '18%', '9963'],
              ['Cab aggregator services (Ola, Uber)', '5%', '9964'],
              ['Economy air travel (domestic)', '5%', '9964'],
              ['Business class air travel', '12%', '9964'],
              ['Rail transport (AC classes)', '5%', '9964'],
              ['Goods transport by road (GTA)', '5% / 12%', '9965'],
              ['Courier services', '18%', '9968'],
              ['Telecom services', '18%', '9984'],
              ['Banking &amp; financial services', '18%', '9971'],
              ['Insurance (life &amp; general)', '18%', '9971'],
              ['IT &amp; software services', '18%', '9983'],
              ['Legal services', '18%', '9982'],
              ['CA / audit / accounting services', '18%', '9982'],
              ['Construction (residential — affordable)', '1% / 5%', '9954'],
              ['Construction (commercial / non-affordable)', '12% / 18%', '9954'],
              ['Renting of commercial property', '18%', '9972'],
              ['Renting of residential property (by registered person)', '18%', '9972'],
              ['Cinema tickets (up to ₹100)', '12%', '9996'],
              ['Cinema tickets (above ₹100)', '28%', '9996'],
              ['Online gaming, betting, gambling', '28%', '9996'],
            ].map(([service, rate, sac], i) => (
              <tr key={i} className={i % 2 === 1 ? 'bg-gray-50' : ''}>
                <td className="border border-gray-300 px-4 py-2">{service}</td>
                <td className="border border-gray-300 px-4 py-2 font-medium">{rate}</td>
                <td className="border border-gray-300 px-4 py-2">{sac}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Section 8 - Compensation Cess */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">Compensation Cess &mdash; Items Attracting Additional Cess</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        Apart from the 28% GST, certain goods attract an additional Compensation Cess. This cess was introduced to compensate states for revenue loss during the GST transition (initially for 5 years, extended through June 2025 for loan repayment, and further extended to March 2026). The cess applies on top of the 28% GST rate.
      </p>

      <div className="overflow-x-auto mb-6">
        <table className="w-full border-collapse border border-gray-300 text-sm">
          <thead>
            <tr className="bg-gray-100">
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Item</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Compensation Cess Rate</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Total Tax (28% + Cess)</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="border border-gray-300 px-4 py-3">Small cars (petrol, &le;1200cc)</td>
              <td className="border border-gray-300 px-4 py-3">1%</td>
              <td className="border border-gray-300 px-4 py-3">29%</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-3">Small cars (diesel, &le;1500cc)</td>
              <td className="border border-gray-300 px-4 py-3">3%</td>
              <td className="border border-gray-300 px-4 py-3">31%</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-3">Mid-size cars (&gt;1500cc, &le;4m length)</td>
              <td className="border border-gray-300 px-4 py-3">17%</td>
              <td className="border border-gray-300 px-4 py-3">45%</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-3">Large cars, SUVs (&gt;4m, &gt;1500cc)</td>
              <td className="border border-gray-300 px-4 py-3">20% / 22%</td>
              <td className="border border-gray-300 px-4 py-3">48% / 50%</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-3">Aerated waters (sugar-sweetened)</td>
              <td className="border border-gray-300 px-4 py-3">12%</td>
              <td className="border border-gray-300 px-4 py-3">40%</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-3">Pan masala</td>
              <td className="border border-gray-300 px-4 py-3">Specific rate (ad valorem)</td>
              <td className="border border-gray-300 px-4 py-3">28% + specific cess</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-3">Cigarettes, tobacco products</td>
              <td className="border border-gray-300 px-4 py-3">Specific rate per unit/length</td>
              <td className="border border-gray-300 px-4 py-3">28% + specific cess</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-3">Coal, lignite, peat</td>
              <td className="border border-gray-300 px-4 py-3">₹400 per tonne</td>
              <td className="border border-gray-300 px-4 py-3">5% + ₹400/tonne</td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* Section 9 - Recent Changes */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">Recent GST Rate Changes (2025&ndash;2026)</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        The GST Council meets periodically to review and rationalise rates. Here are some notable rate changes from recent council meetings that are relevant in 2026:
      </p>

      <div className="space-y-4 mb-6">
        <div className="bg-white border rounded-lg p-4">
          <h4 className="font-semibold text-gray-900 mb-2">Online Gaming, Casinos &amp; Horse Racing</h4>
          <p className="text-gray-700 text-sm">Taxed at 28% on the full face value of bets placed (not just the platform fee). This applies to both skill-based and chance-based games as clarified in the 50th and 51st GST Council meetings. Foreign online gaming companies must also register under GST in India.</p>
        </div>
        <div className="bg-white border rounded-lg p-4">
          <h4 className="font-semibold text-gray-900 mb-2">Pre-Packaged &amp; Labelled Goods</h4>
          <p className="text-gray-700 text-sm">Items like rice, wheat, atta, pulses, curd, paneer, and honey are taxed at 5% when sold in pre-packaged and labelled form (packages up to 25 kg/litre). Loose/unbranded remains exempt.</p>
        </div>
        <div className="bg-white border rounded-lg p-4">
          <h4 className="font-semibold text-gray-900 mb-2">Corporate Guarantees</h4>
          <p className="text-gray-700 text-sm">GST at 18% applies on corporate guarantees provided by a holding company to its subsidiary, even without consideration. The taxable value is 1% of the guarantee amount or the actual consideration, whichever is higher.</p>
        </div>
        <div className="bg-white border rounded-lg p-4">
          <h4 className="font-semibold text-gray-900 mb-2">EV &amp; Green Energy</h4>
          <p className="text-gray-700 text-sm">Electric vehicles continue at the concessional rate of 5%. EV charging stations are taxed at 18%. Solar panels and related components remain at 12%.</p>
        </div>
      </div>

      {/* Section 10 - How to Find */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">How to Find the Correct GST Rate for Any Product</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        Finding the right GST rate requires identifying the correct HSN code (for goods) or SAC code (for services). Here is a step-by-step approach:
      </p>

      <ol className="list-decimal pl-6 text-gray-700 space-y-3 mb-6">
        <li><strong>Identify the HSN/SAC Code:</strong> Use the <Link href="/" className="text-blue-600 hover:text-blue-700 underline">GSTIndia HSN Code Finder</Link> tool. Enter your product or service name and get the matching HSN/SAC code with the applicable rate.</li>
        <li><strong>Check the GST Rate Schedule:</strong> Cross-verify with the official GST rate schedule available in Schedule I (5%), Schedule II (12%), Schedule III (18%), and Schedule IV (28%) of Notification No. 1/2017-CT (Rate).</li>
        <li><strong>Verify with the CBIC GST Rate Finder App:</strong> Download the official GST Rate Finder app from the CBIC or use the GST portal.</li>
        <li><strong>Check for Notifications:</strong> The rate may have been changed by a subsequent notification. Check the latest CBIC notifications on cbic.gov.in.</li>
        <li><strong>Consider Conditions:</strong> Some items have conditional rates (e.g., restaurants with/without ITC, clothing below/above ₹1,000). Make sure the conditions are met.</li>
      </ol>

      <div className="bg-gradient-to-r from-blue-600 to-blue-700 rounded-xl p-6 text-white mb-8">
        <h3 className="text-xl font-bold mb-2">Find GST Rates Instantly</h3>
        <p className="text-blue-100 mb-4">Use GSTIndia&apos;s free GST Calculator and HSN Code Finder to look up GST rates, compute tax, and validate your GSTIN &mdash; all in one place.</p>
        <Link href="/" className="inline-block bg-white text-blue-600 font-semibold px-6 py-2 rounded-lg hover:bg-blue-50 transition-colors">
          Try Free GST Tools &rarr;
        </Link>
      </div>

      {/* FAQ Section */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-6">Frequently Asked Questions (FAQ)</h2>

      <div className="space-y-4 mb-8">
        {[
          {
            q: 'How many GST slabs are there in India in 2026?',
            a: 'There are four main GST slabs in India: 5%, 12%, 18%, and 28%. Additionally, some essential goods are exempt (0% GST), and certain luxury and demerit goods attract a Compensation Cess above the 28% rate. There is also a special rate of 0.25% for rough diamonds and 3% for gold and silver.',
          },
          {
            q: 'What is the GST rate on mobile phones?',
            a: 'Mobile phones are taxed at 18% GST (HSN 8517). This rate has been in effect since April 2020 when it was increased from 12%. Accessories like chargers, cases, and earphones are also at 18%.',
          },
          {
            q: 'What is the GST rate on food items?',
            a: 'Fresh food (fruits, vegetables, milk, eggs) is exempt (0%). Pre-packaged and labelled food items like rice, wheat, atta are at 5%. Processed food like ghee, butter, dry fruits are at 12%. Chocolates, ice cream are at 18%. Restaurant food is either 5% (no ITC) or 18% (with ITC).',
          },
          {
            q: 'Is GST charged on gold and jewellery?',
            a: 'Yes, gold, silver, and platinum are taxed at 3% GST. Making charges for jewellery are taxed at 5%. This is a special rate separate from the four main slabs.',
          },
          {
            q: 'What is the GST rate on rent?',
            a: 'Renting of commercial property is taxed at 18% GST. Renting of residential property by a registered person to another registered person is also at 18%. However, renting of residential property for personal use by an unregistered individual is exempt.',
          },
          {
            q: 'What is the GST rate on insurance premiums?',
            a: 'All insurance premiums (life, health, motor, travel) are taxed at 18% GST. The GST Council has discussed reducing health insurance GST rates, but as of 2026, it remains at 18%.',
          },
          {
            q: 'How do I know if my product falls in the 12% or 18% slab?',
            a: 'The GST rate depends on the HSN code classification, not just the product description. Use the GSTIndia HSN Code Finder to identify the correct code and rate. When in doubt, consult the official notification or seek advice from a tax professional.',
          },
          {
            q: 'What is Compensation Cess under GST?',
            a: 'Compensation Cess is an additional tax levied on top of GST (typically 28%) on certain luxury and sin goods like tobacco, aerated drinks, and motor vehicles. It was introduced to compensate states for revenue loss during GST transition and has been extended beyond the initial 5-year period.',
          },
        ].map(({ q, a }, i) => (
          <details key={i} className="border rounded-lg">
            <summary className="px-6 py-4 cursor-pointer font-semibold text-gray-900 hover:text-blue-600">
              {q}
            </summary>
            <p className="px-6 pb-4 text-gray-700 text-sm leading-relaxed">{a}</p>
          </details>
        ))}
      </div>

      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">Conclusion</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        Understanding the correct GST rate for your goods and services is fundamental to GST compliance. Whether you are a business owner issuing invoices, a consumer wanting to verify the tax charged, or a tax professional advising clients, having access to an accurate and updated rate list is essential. The GST Council continues to rationalise rates, so stay informed about the latest changes through official CBIC notifications.
      </p>

      <p className="text-gray-700 leading-relaxed mb-4">
        For quick GST calculations, HSN code lookups, and GSTIN validation, use the free tools available on <Link href="/" className="text-blue-600 hover:text-blue-700 underline">GSTIndia by DoAide</Link>. Bookmark this page for a handy reference to GST rates across all categories, and check our <Link href="/blog/gst-hsn-code-list" className="text-blue-600 hover:text-blue-700 underline">HSN Code List guide</Link> for a detailed chapter-wise breakdown of HSN codes.
      </p>

      {/* JSON-LD Structured Data */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            '@context': 'https://schema.org',
            '@type': 'Article',
            headline: 'GST Rate List 2026: Complete Slab-Wise Rate Table for Goods & Services',
            description: 'Complete GST rate list for 2026 with slab-wise breakdown at 5%, 12%, 18% & 28%. Find GST rates for all goods and services with HSN/SAC codes.',
            author: {
              '@type': 'Organization',
              name: 'DoAide Technologies',
              url: 'https://gst.doaide.com',
            },
            publisher: {
              '@type': 'Organization',
              name: 'DoAide Technologies',
              url: 'https://gst.doaide.com',
            },
            datePublished: '2026-10-10',
            dateModified: '2026-10-10',
            url: 'https://gst.doaide.com/blog/gst-rate-list-2026',
            mainEntityOfPage: 'https://gst.doaide.com/blog/gst-rate-list-2026',
          }),
        }}
      />

      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            '@context': 'https://schema.org',
            '@type': 'FAQPage',
            mainEntity: [
              {
                '@type': 'Question',
                name: 'How many GST slabs are there in India in 2026?',
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: 'There are four main GST slabs in India: 5%, 12%, 18%, and 28%. Additionally, some essential goods are exempt (0% GST), and certain goods attract a Compensation Cess above 28%.',
                },
              },
              {
                '@type': 'Question',
                name: 'What is the GST rate on mobile phones?',
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: 'Mobile phones are taxed at 18% GST (HSN 8517), effective since April 2020.',
                },
              },
              {
                '@type': 'Question',
                name: 'What is the GST rate on food items?',
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: 'Fresh food is exempt (0%). Pre-packaged items are at 5%. Processed food like ghee, butter are at 12%. Chocolates, ice cream are at 18%.',
                },
              },
              {
                '@type': 'Question',
                name: 'Is GST charged on gold and jewellery?',
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: 'Gold, silver, and platinum are taxed at 3% GST. Making charges for jewellery are taxed at 5%.',
                },
              },
              {
                '@type': 'Question',
                name: 'What is the GST rate on rent?',
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: 'Commercial property rent is at 18%. Residential property rent by a registered person to another registered person is also 18%. Residential rent for personal use by unregistered individuals is exempt.',
                },
              },
              {
                '@type': 'Question',
                name: 'What is the GST rate on insurance premiums?',
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: 'All insurance premiums (life, health, motor, travel) are taxed at 18% GST.',
                },
              },
              {
                '@type': 'Question',
                name: 'How do I know if my product falls in the 12% or 18% slab?',
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: 'The GST rate depends on the HSN code classification. Use the GSTIndia HSN Code Finder to identify the correct code and rate.',
                },
              },
              {
                '@type': 'Question',
                name: 'What is Compensation Cess under GST?',
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: 'Compensation Cess is an additional tax on top of 28% GST on luxury and sin goods like tobacco, aerated drinks, and motor vehicles to compensate states for revenue loss.',
                },
              },
            ],
          }),
        }}
      />

      <div className="mt-8 pt-8 border-t dark:border-gray-800">
        <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">Found this guide helpful? Share it:</p>
        <ShareButtons
          title="GST Rate List 2026: Complete Slab-Wise Rate Table"
          url="/blog/gst-rate-list-2026"
        />
      </div>
    </article>
  );
}
