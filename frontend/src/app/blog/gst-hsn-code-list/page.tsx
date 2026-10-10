import type { Metadata } from 'next';
import Link from 'next/link';
import { ShareButtons } from '@/components/blog/share-buttons';

export const metadata: Metadata = {
  title: 'GST HSN Code List 2026: Find Your HSN/SAC Code',
  description: 'Complete HSN code list for GST with chapter-wise breakdown. Find HSN codes for goods and SAC codes for services. Updated for 2026-27 with search guide.',
  openGraph: {
    title: 'GST HSN Code List 2026: Complete Guide to HSN & SAC Codes',
    description: 'Complete HSN code list for GST with chapter-wise breakdown. Find HSN codes for goods and SAC codes for services.',
    url: 'https://gst.doaide.com/blog/gst-hsn-code-list',
    type: 'article',
  },
  alternates: {
    canonical: 'https://gst.doaide.com/blog/gst-hsn-code-list',
  },
};

export default function GSTHSNCodeListGuide() {
  return (
    <article className="max-w-4xl mx-auto px-4 py-12">
      <div className="mb-8">
        <span className="text-sm font-semibold text-blue-600 bg-blue-50 px-3 py-1 rounded-full">HSN Codes</span>
        <span className="text-sm text-gray-500 ml-3">Updated: 10 October 2026</span>
        <span className="text-sm text-gray-500 ml-3">18 min read</span>
      </div>

      <h1 className="text-3xl sm:text-4xl font-bold text-gray-900 dark:text-gray-100 mb-6">
        GST HSN Code List 2026: Complete Guide to Finding HSN &amp; SAC Codes
      </h1>

      <ShareButtons
        title="GST HSN Code List 2026: Complete Guide"
        url="/blog/gst-hsn-code-list"
        className="mb-8"
      />

      <p className="text-lg text-gray-600 dark:text-gray-400 mb-8 leading-relaxed">
        HSN codes are the backbone of product classification under GST. Every registered business in India must use the correct HSN (Harmonized System of Nomenclature) code on their invoices, GSTR-1 returns, and e-invoices. Using the wrong HSN code can lead to incorrect tax rates, ITC denial, and scrutiny notices from the tax department. This comprehensive guide covers everything about HSN codes — from the structure and classification to a complete chapter-wise list of HSN codes and SAC codes for services.
      </p>

      <div className="bg-blue-50 border-l-4 border-blue-500 p-4 rounded mb-8">
        <p className="text-blue-900 font-medium">Quick Navigation</p>
        <ul className="text-blue-800 text-sm mt-2 space-y-1">
          <li>&bull; What is HSN Code</li>
          <li>&bull; What is SAC Code</li>
          <li>&bull; HSN Code Structure</li>
          <li>&bull; HSN Requirements by Turnover</li>
          <li>&bull; Chapter-wise HSN Code List</li>
          <li>&bull; SAC Code List for Services</li>
          <li>&bull; How to Find Your HSN Code</li>
          <li>&bull; Penalties for Wrong HSN</li>
          <li>&bull; FAQs</li>
        </ul>
      </div>

      {/* Section 1 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">What is HSN Code in GST?</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        HSN stands for <strong>Harmonized System of Nomenclature</strong>. It is an internationally standardized system of names and numbers developed by the <strong>World Customs Organization (WCO)</strong> to classify traded goods across the world. The HSN system was introduced in 1988 and is used by more than 200 countries and economies for customs tariffs and international trade statistics.
      </p>

      <p className="text-gray-700 leading-relaxed mb-4">
        In India, HSN codes were adopted under the GST framework to systematically classify all goods under specific categories. Each product is assigned a unique HSN code that determines the <strong>GST rate</strong> applicable to it. This standardized classification ensures uniformity in taxation across the country and simplifies the process of identifying the correct tax rate for any product.
      </p>

      <p className="text-gray-700 leading-relaxed mb-4">
        Before GST, India used different classification systems — the Central Excise Tariff Act (CETA) for manufactured goods and the Customs Tariff Act for imported goods. Under GST, the HSN system unifies all product classification under a single framework, making it easier for businesses to determine tax rates and for the government to analyze trade data.
      </p>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">Why HSN Codes Matter for Your Business</h3>

      <ul className="list-disc pl-6 text-gray-700 space-y-2 mb-6">
        <li><strong>Correct tax rate:</strong> Each HSN code maps to a specific GST rate (0%, 5%, 12%, 18%, or 28%). Using the wrong code means applying the wrong tax rate</li>
        <li><strong>Invoice compliance:</strong> HSN codes are mandatory on <Link href="/blog/gst-invoice-format-guide" className="text-blue-600 hover:text-blue-700 underline">GST invoices</Link> and must be mentioned in GSTR-1 Table 12</li>
        <li><strong>ITC matching:</strong> The tax department uses HSN codes to match and verify <Link href="/blog/input-tax-credit-itc-rules-2026-27" className="text-blue-600 hover:text-blue-700 underline">Input Tax Credit</Link> claims</li>
        <li><strong>E-invoicing:</strong> 6-digit HSN codes are mandatory for all e-invoices regardless of turnover</li>
        <li><strong>International trade:</strong> HSN codes are the basis for customs duty classification on imports and exports</li>
      </ul>

      {/* Section 2 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">What is SAC Code in GST?</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        SAC stands for <strong>Services Accounting Code</strong>. While HSN codes classify goods, SAC codes classify services under GST. The SAC system was introduced specifically for the Indian GST framework to categorize all types of services rendered by businesses and professionals.
      </p>

      <p className="text-gray-700 leading-relaxed mb-4">
        SAC codes follow a <strong>6-digit structure</strong> and always start with <strong>99</strong>. The format is <strong>99XXYY</strong>, where:
      </p>

      <ul className="list-disc pl-6 text-gray-700 space-y-2 mb-6">
        <li><strong>99:</strong> Denotes that it is a service (not a good)</li>
        <li><strong>XX:</strong> Major service category heading (e.g., 54 for construction, 83 for IT services)</li>
        <li><strong>YY:</strong> Specific service sub-category</li>
      </ul>

      <p className="text-gray-700 leading-relaxed mb-4">
        For example, SAC code <strong>998311</strong> represents &quot;Management consulting and management services including financial, strategic, human resources, marketing, operations and supply chain management&quot;. Like HSN codes, SAC codes are mandatory on invoices and in GSTR-1 filing.
      </p>

      <div className="bg-blue-50 border-l-4 border-blue-500 p-4 rounded mb-6">
        <p className="text-blue-900 font-medium">Key Difference: HSN vs SAC</p>
        <p className="text-blue-800 text-sm mt-1">HSN codes are for <strong>goods</strong> (physical products) and can be 2, 4, 6, or 8 digits long. SAC codes are for <strong>services</strong> and are always 6 digits starting with 99. Both are required on GST invoices and in return filing.</p>
      </div>

      {/* Section 3 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">HSN Code Structure Explained</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        The HSN code follows a hierarchical structure that goes from broad categories to specific products. Understanding this structure helps you find the correct code for your products:
      </p>

      <div className="overflow-x-auto mb-6">
        <table className="w-full border-collapse border border-gray-300 text-sm">
          <thead>
            <tr className="bg-gray-100">
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Level</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Digits</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Classification</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Example</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="border border-gray-300 px-4 py-2 font-medium">Section</td>
              <td className="border border-gray-300 px-4 py-2">—</td>
              <td className="border border-gray-300 px-4 py-2">Broadest grouping (21 sections)</td>
              <td className="border border-gray-300 px-4 py-2">Section XVI: Machinery &amp; Equipment</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-2 font-medium">Chapter</td>
              <td className="border border-gray-300 px-4 py-2">2 digits</td>
              <td className="border border-gray-300 px-4 py-2">Product category (99 chapters)</td>
              <td className="border border-gray-300 px-4 py-2"><strong>84</strong> — Nuclear reactors, boilers, machinery</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-2 font-medium">Heading</td>
              <td className="border border-gray-300 px-4 py-2">4 digits</td>
              <td className="border border-gray-300 px-4 py-2">Product group within chapter</td>
              <td className="border border-gray-300 px-4 py-2"><strong>8471</strong> — Automatic data processing machines (computers)</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-2 font-medium">Sub-heading</td>
              <td className="border border-gray-300 px-4 py-2">6 digits</td>
              <td className="border border-gray-300 px-4 py-2">Specific product (international standard)</td>
              <td className="border border-gray-300 px-4 py-2"><strong>847130</strong> — Portable digital computers (laptops)</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-2 font-medium">Tariff Item</td>
              <td className="border border-gray-300 px-4 py-2">8 digits</td>
              <td className="border border-gray-300 px-4 py-2">India-specific classification</td>
              <td className="border border-gray-300 px-4 py-2"><strong>84713010</strong> — Laptop weighing up to 10 kg</td>
            </tr>
          </tbody>
        </table>
      </div>

      <p className="text-gray-700 leading-relaxed mb-4">
        The first 6 digits are internationally standardized — a laptop has the same HSN code 847130 in India, the USA, Europe, or Japan. The 7th and 8th digits are India-specific additions for customs tariff and excise purposes. For GST purposes, you typically need 4 or 6 digits depending on your turnover.
      </p>

      {/* Section 4 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">HSN Code Requirements Based on Turnover</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        The number of HSN digits required on your <Link href="/blog/gst-invoice-format-guide" className="text-blue-600 hover:text-blue-700 underline">GST invoices</Link> depends on your aggregate annual turnover in the preceding financial year:
      </p>

      <div className="overflow-x-auto mb-6">
        <table className="w-full border-collapse border border-gray-300 text-sm">
          <thead>
            <tr className="bg-gray-100">
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Annual Turnover</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">HSN Digits on Invoice</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">HSN in GSTR-1</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="border border-gray-300 px-4 py-2">Up to ₹1.5 crore (Composition)</td>
              <td className="border border-gray-300 px-4 py-2">Not mandatory</td>
              <td className="border border-gray-300 px-4 py-2">Not applicable</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-2">₹1.5 crore to ₹5 crore</td>
              <td className="border border-gray-300 px-4 py-2">4-digit HSN (B2B supplies)</td>
              <td className="border border-gray-300 px-4 py-2">4-digit mandatory in Table 12</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-2">Above ₹5 crore</td>
              <td className="border border-gray-300 px-4 py-2">6-digit HSN (all supplies)</td>
              <td className="border border-gray-300 px-4 py-2">6-digit mandatory in Table 12</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-2">E-invoicing (B2B)</td>
              <td className="border border-gray-300 px-4 py-2">6-digit HSN mandatory</td>
              <td className="border border-gray-300 px-4 py-2">Auto-populated from e-invoice</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div className="bg-yellow-50 border-l-4 border-yellow-500 p-4 rounded mb-6">
        <p className="text-yellow-900 font-medium">Important: GSTR-1 Table 12 Validation</p>
        <p className="text-yellow-800 text-sm mt-1">From April 2021, the GST portal validates HSN codes entered in GSTR-1 Table 12 (HSN-wise Summary of Outward Supplies). If you enter an invalid or non-existent HSN code, the portal will reject it. The total taxable value and tax amounts in Table 12 must also match with the invoice-level data in other tables of GSTR-1.</p>
      </div>

      {/* Section 5 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">Chapter-wise HSN Code List for Goods</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        The HSN system organizes all goods into 21 sections and 99 chapters. Below is a comprehensive list of all sections with representative HSN codes, descriptions, and applicable GST rates. Use the <Link href="/" className="text-blue-600 hover:text-blue-700 underline">GSTIndia HSN Code Finder</Link> to search for the exact code for your specific product.
      </p>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">Section I: Live Animals and Animal Products (Chapters 01-05)</h3>

      <div className="overflow-x-auto mb-6">
        <table className="w-full border-collapse border border-gray-300 text-sm">
          <thead>
            <tr className="bg-gray-100">
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">HSN Code</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Description</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">GST Rate</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="border border-gray-300 px-4 py-2">0101</td>
              <td className="border border-gray-300 px-4 py-2">Live horses, asses, mules and hinnies</td>
              <td className="border border-gray-300 px-4 py-2">Nil / 12%</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-2">0201</td>
              <td className="border border-gray-300 px-4 py-2">Meat of bovine animals, fresh or chilled</td>
              <td className="border border-gray-300 px-4 py-2">Nil</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-2">0401</td>
              <td className="border border-gray-300 px-4 py-2">Milk and cream, not concentrated</td>
              <td className="border border-gray-300 px-4 py-2">Nil</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-2">0504</td>
              <td className="border border-gray-300 px-4 py-2">Animal guts, bladders, stomachs</td>
              <td className="border border-gray-300 px-4 py-2">Nil / 5%</td>
            </tr>
          </tbody>
        </table>
      </div>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">Section II: Vegetable Products (Chapters 06-14)</h3>

      <div className="overflow-x-auto mb-6">
        <table className="w-full border-collapse border border-gray-300 text-sm">
          <thead>
            <tr className="bg-gray-100">
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">HSN Code</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Description</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">GST Rate</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="border border-gray-300 px-4 py-2">0701</td>
              <td className="border border-gray-300 px-4 py-2">Potatoes, fresh or chilled</td>
              <td className="border border-gray-300 px-4 py-2">Nil</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-2">0713</td>
              <td className="border border-gray-300 px-4 py-2">Dried leguminous vegetables (dal, pulses)</td>
              <td className="border border-gray-300 px-4 py-2">Nil / 5%</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-2">1001</td>
              <td className="border border-gray-300 px-4 py-2">Wheat and meslin</td>
              <td className="border border-gray-300 px-4 py-2">Nil / 5%</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-2">1006</td>
              <td className="border border-gray-300 px-4 py-2">Rice</td>
              <td className="border border-gray-300 px-4 py-2">Nil / 5%</td>
            </tr>
          </tbody>
        </table>
      </div>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">Sections III-IV: Fats, Oils &amp; Food Products (Chapters 15-24)</h3>

      <div className="overflow-x-auto mb-6">
        <table className="w-full border-collapse border border-gray-300 text-sm">
          <thead>
            <tr className="bg-gray-100">
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">HSN Code</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Description</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">GST Rate</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="border border-gray-300 px-4 py-2">1507</td>
              <td className="border border-gray-300 px-4 py-2">Soya-bean oil</td>
              <td className="border border-gray-300 px-4 py-2">5%</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-2">1701</td>
              <td className="border border-gray-300 px-4 py-2">Cane or beet sugar</td>
              <td className="border border-gray-300 px-4 py-2">5%</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-2">1905</td>
              <td className="border border-gray-300 px-4 py-2">Bread, pastry, cakes, biscuits</td>
              <td className="border border-gray-300 px-4 py-2">5% / 18%</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-2">2106</td>
              <td className="border border-gray-300 px-4 py-2">Food preparations not elsewhere specified</td>
              <td className="border border-gray-300 px-4 py-2">12% / 18%</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-2">2202</td>
              <td className="border border-gray-300 px-4 py-2">Waters with added sugar/sweetener (soft drinks)</td>
              <td className="border border-gray-300 px-4 py-2">28% + Cess</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-2">2402</td>
              <td className="border border-gray-300 px-4 py-2">Cigars, cigarettes, tobacco</td>
              <td className="border border-gray-300 px-4 py-2">28% + Cess</td>
            </tr>
          </tbody>
        </table>
      </div>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">Sections V-VII: Minerals, Chemicals, Plastics (Chapters 25-40)</h3>

      <div className="overflow-x-auto mb-6">
        <table className="w-full border-collapse border border-gray-300 text-sm">
          <thead>
            <tr className="bg-gray-100">
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">HSN Code</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Description</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">GST Rate</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="border border-gray-300 px-4 py-2">2523</td>
              <td className="border border-gray-300 px-4 py-2">Portland cement, aluminous cement</td>
              <td className="border border-gray-300 px-4 py-2">28%</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-2">2710</td>
              <td className="border border-gray-300 px-4 py-2">Petroleum oils (petrol, diesel, kerosene)</td>
              <td className="border border-gray-300 px-4 py-2">Outside GST</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-2">3004</td>
              <td className="border border-gray-300 px-4 py-2">Medicaments for therapeutic use (medicines)</td>
              <td className="border border-gray-300 px-4 py-2">5% / 12%</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-2">3923</td>
              <td className="border border-gray-300 px-4 py-2">Plastic articles for packing (bottles, containers)</td>
              <td className="border border-gray-300 px-4 py-2">18%</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-2">4011</td>
              <td className="border border-gray-300 px-4 py-2">New pneumatic tyres, of rubber</td>
              <td className="border border-gray-300 px-4 py-2">28%</td>
            </tr>
          </tbody>
        </table>
      </div>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">Sections VIII-XII: Leather, Wood, Paper, Textiles, Footwear (Chapters 41-67)</h3>

      <div className="overflow-x-auto mb-6">
        <table className="w-full border-collapse border border-gray-300 text-sm">
          <thead>
            <tr className="bg-gray-100">
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">HSN Code</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Description</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">GST Rate</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="border border-gray-300 px-4 py-2">4202</td>
              <td className="border border-gray-300 px-4 py-2">Trunks, suitcases, handbags (leather/plastic)</td>
              <td className="border border-gray-300 px-4 py-2">18%</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-2">4802</td>
              <td className="border border-gray-300 px-4 py-2">Uncoated paper for writing or printing</td>
              <td className="border border-gray-300 px-4 py-2">12%</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-2">5208</td>
              <td className="border border-gray-300 px-4 py-2">Woven fabrics of cotton</td>
              <td className="border border-gray-300 px-4 py-2">5%</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-2">6109</td>
              <td className="border border-gray-300 px-4 py-2">T-shirts, singlets, tank tops (knitted)</td>
              <td className="border border-gray-300 px-4 py-2">5% / 12%</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-2">6403</td>
              <td className="border border-gray-300 px-4 py-2">Footwear with leather upper</td>
              <td className="border border-gray-300 px-4 py-2">12% / 18%</td>
            </tr>
          </tbody>
        </table>
      </div>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">Sections XIII-XV: Stone, Cement, Precious Metals, Base Metals (Chapters 68-83)</h3>

      <div className="overflow-x-auto mb-6">
        <table className="w-full border-collapse border border-gray-300 text-sm">
          <thead>
            <tr className="bg-gray-100">
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">HSN Code</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Description</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">GST Rate</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="border border-gray-300 px-4 py-2">6910</td>
              <td className="border border-gray-300 px-4 py-2">Ceramic sinks, wash basins, baths, toilets</td>
              <td className="border border-gray-300 px-4 py-2">18%</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-2">7101</td>
              <td className="border border-gray-300 px-4 py-2">Pearls, natural or cultured</td>
              <td className="border border-gray-300 px-4 py-2">3%</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-2">7113</td>
              <td className="border border-gray-300 px-4 py-2">Gold and silver jewellery</td>
              <td className="border border-gray-300 px-4 py-2">3%</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-2">7308</td>
              <td className="border border-gray-300 px-4 py-2">Iron/steel structures (bridges, towers, pillars)</td>
              <td className="border border-gray-300 px-4 py-2">18%</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-2">7318</td>
              <td className="border border-gray-300 px-4 py-2">Screws, bolts, nuts, washers (iron/steel)</td>
              <td className="border border-gray-300 px-4 py-2">18%</td>
            </tr>
          </tbody>
        </table>
      </div>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">Sections XVI-XXI: Machinery, Vehicles, Instruments, Miscellaneous (Chapters 84-97)</h3>

      <div className="overflow-x-auto mb-6">
        <table className="w-full border-collapse border border-gray-300 text-sm">
          <thead>
            <tr className="bg-gray-100">
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">HSN Code</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Description</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">GST Rate</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="border border-gray-300 px-4 py-2">8415</td>
              <td className="border border-gray-300 px-4 py-2">Air conditioning machines</td>
              <td className="border border-gray-300 px-4 py-2">28%</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-2">8471</td>
              <td className="border border-gray-300 px-4 py-2">Computers, laptops, tablets</td>
              <td className="border border-gray-300 px-4 py-2">18%</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-2">8517</td>
              <td className="border border-gray-300 px-4 py-2">Telephones, smartphones</td>
              <td className="border border-gray-300 px-4 py-2">18%</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-2">8528</td>
              <td className="border border-gray-300 px-4 py-2">Monitors, TVs, projectors</td>
              <td className="border border-gray-300 px-4 py-2">18% / 28%</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-2">8703</td>
              <td className="border border-gray-300 px-4 py-2">Motor cars and vehicles for transport of persons</td>
              <td className="border border-gray-300 px-4 py-2">28% + Cess</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-2">8711</td>
              <td className="border border-gray-300 px-4 py-2">Motorcycles, scooters, mopeds</td>
              <td className="border border-gray-300 px-4 py-2">28% + Cess</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-2">9018</td>
              <td className="border border-gray-300 px-4 py-2">Medical instruments and appliances</td>
              <td className="border border-gray-300 px-4 py-2">12%</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-2">9401</td>
              <td className="border border-gray-300 px-4 py-2">Seats and chairs (office, household)</td>
              <td className="border border-gray-300 px-4 py-2">18%</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-2">9403</td>
              <td className="border border-gray-300 px-4 py-2">Other furniture (tables, desks, shelves)</td>
              <td className="border border-gray-300 px-4 py-2">18%</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-2">9503</td>
              <td className="border border-gray-300 px-4 py-2">Toys, games, sports equipment</td>
              <td className="border border-gray-300 px-4 py-2">12% / 18%</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div className="bg-blue-50 border-l-4 border-blue-500 p-4 rounded mb-6">
        <p className="text-blue-900 font-medium">Search Your Exact HSN Code</p>
        <p className="text-blue-800 text-sm mt-1">The tables above show representative codes. For the exact HSN code and GST rate for your specific product, use the <Link href="/" className="text-blue-600 underline">GSTIndia HSN Code Finder</Link> — search by product name or description to get the precise 4/6/8-digit code with the applicable rate.</p>
      </div>

      {/* Section 6 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">SAC Code List for Services</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        If your business provides services, you need to use SAC codes instead of HSN codes. Below is a comprehensive list of the most commonly used SAC codes with their GST rates:
      </p>

      <div className="overflow-x-auto mb-6">
        <table className="w-full border-collapse border border-gray-300 text-sm">
          <thead>
            <tr className="bg-gray-100">
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">SAC Code</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Service Category</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Examples</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">GST Rate</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="border border-gray-300 px-4 py-2 font-medium">9954</td>
              <td className="border border-gray-300 px-4 py-2">Construction Services</td>
              <td className="border border-gray-300 px-4 py-2">Building construction, civil engineering, renovation</td>
              <td className="border border-gray-300 px-4 py-2">12% / 18%</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-2 font-medium">9961</td>
              <td className="border border-gray-300 px-4 py-2">Transport — Goods</td>
              <td className="border border-gray-300 px-4 py-2">Freight transport, courier, logistics</td>
              <td className="border border-gray-300 px-4 py-2">5% / 12% / 18%</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-2 font-medium">9962</td>
              <td className="border border-gray-300 px-4 py-2">Transport — Passengers</td>
              <td className="border border-gray-300 px-4 py-2">Cab services, bus, air travel</td>
              <td className="border border-gray-300 px-4 py-2">5% / 12% / 18%</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-2 font-medium">9963</td>
              <td className="border border-gray-300 px-4 py-2">Accommodation Services</td>
              <td className="border border-gray-300 px-4 py-2">Hotels, guest houses, hostels, resorts</td>
              <td className="border border-gray-300 px-4 py-2">12% / 18%</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-2 font-medium">9964</td>
              <td className="border border-gray-300 px-4 py-2">Restaurant &amp; Catering</td>
              <td className="border border-gray-300 px-4 py-2">Restaurants, food delivery, outdoor catering</td>
              <td className="border border-gray-300 px-4 py-2">5% / 18%</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-2 font-medium">9971</td>
              <td className="border border-gray-300 px-4 py-2">Financial Services</td>
              <td className="border border-gray-300 px-4 py-2">Banking, insurance, stock broking</td>
              <td className="border border-gray-300 px-4 py-2">18%</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-2 font-medium">9972</td>
              <td className="border border-gray-300 px-4 py-2">Real Estate Services</td>
              <td className="border border-gray-300 px-4 py-2">Renting, leasing of property</td>
              <td className="border border-gray-300 px-4 py-2">18%</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-2 font-medium">9973</td>
              <td className="border border-gray-300 px-4 py-2">Leasing Services</td>
              <td className="border border-gray-300 px-4 py-2">Equipment leasing, vehicle leasing</td>
              <td className="border border-gray-300 px-4 py-2">18%</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-2 font-medium">9981</td>
              <td className="border border-gray-300 px-4 py-2">Research &amp; Development</td>
              <td className="border border-gray-300 px-4 py-2">Scientific research, experimental development</td>
              <td className="border border-gray-300 px-4 py-2">18%</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-2 font-medium">9983</td>
              <td className="border border-gray-300 px-4 py-2">IT &amp; Software Services</td>
              <td className="border border-gray-300 px-4 py-2">Software development, IT consulting, web development</td>
              <td className="border border-gray-300 px-4 py-2">18%</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-2 font-medium">9985</td>
              <td className="border border-gray-300 px-4 py-2">Support Services</td>
              <td className="border border-gray-300 px-4 py-2">Security, cleaning, manpower, travel agents</td>
              <td className="border border-gray-300 px-4 py-2">18%</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-2 font-medium">9986</td>
              <td className="border border-gray-300 px-4 py-2">Rental &amp; Leasing (Other)</td>
              <td className="border border-gray-300 px-4 py-2">Machinery rental, vehicle rental without operator</td>
              <td className="border border-gray-300 px-4 py-2">18%</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-2 font-medium">9988</td>
              <td className="border border-gray-300 px-4 py-2">Manufacturing Services</td>
              <td className="border border-gray-300 px-4 py-2">Job work, contract manufacturing, processing</td>
              <td className="border border-gray-300 px-4 py-2">5% / 12% / 18%</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-2 font-medium">9991</td>
              <td className="border border-gray-300 px-4 py-2">Public Admin &amp; Government</td>
              <td className="border border-gray-300 px-4 py-2">Government administrative services</td>
              <td className="border border-gray-300 px-4 py-2">18%</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-2 font-medium">9992</td>
              <td className="border border-gray-300 px-4 py-2">Education Services</td>
              <td className="border border-gray-300 px-4 py-2">Primary, secondary, higher education, coaching</td>
              <td className="border border-gray-300 px-4 py-2">Nil / 18%</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-2 font-medium">9993</td>
              <td className="border border-gray-300 px-4 py-2">Health Services</td>
              <td className="border border-gray-300 px-4 py-2">Hospitals, clinics, diagnostic, dental</td>
              <td className="border border-gray-300 px-4 py-2">Nil / 18%</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-2 font-medium">9995</td>
              <td className="border border-gray-300 px-4 py-2">Recreation &amp; Cultural</td>
              <td className="border border-gray-300 px-4 py-2">Entertainment, sports events, theme parks</td>
              <td className="border border-gray-300 px-4 py-2">18% / 28%</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-2 font-medium">9996</td>
              <td className="border border-gray-300 px-4 py-2">Personal Care Services</td>
              <td className="border border-gray-300 px-4 py-2">Beauty parlour, spa, fitness, laundry</td>
              <td className="border border-gray-300 px-4 py-2">18%</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-2 font-medium">9982</td>
              <td className="border border-gray-300 px-4 py-2">Legal &amp; Accounting</td>
              <td className="border border-gray-300 px-4 py-2">CA, CS, legal advisory, auditing</td>
              <td className="border border-gray-300 px-4 py-2">18%</td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* Section 7 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">How to Find the Correct HSN Code for Your Product</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        Finding the right HSN code is critical for correct GST compliance. Here is a step-by-step approach:
      </p>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">Method 1: Use the GSTIndia HSN Code Finder (Recommended)</h3>

      <p className="text-gray-700 leading-relaxed mb-4">
        The fastest and most accurate way to find your HSN code is to use the <Link href="/" className="text-blue-600 hover:text-blue-700 underline">GSTIndia HSN Code Finder</Link>. Simply type your product name or description, and the AI-powered search will return the correct HSN code with the applicable GST rate. This tool is regularly updated with the latest GST rate changes and notifications.
      </p>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">Method 2: Search on the GST Portal</h3>

      <ol className="list-decimal pl-6 text-gray-700 space-y-2 mb-6">
        <li>Visit <strong>services.gst.gov.in/services/searchhsnsac</strong></li>
        <li>Select &quot;Search by HSN Code&quot; or &quot;Search by Product Name&quot;</li>
        <li>Enter your product name or HSN code</li>
        <li>Review the results and select the most appropriate match</li>
        <li>Note the applicable GST rate from the notification column</li>
      </ol>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">Method 3: Check the Customs Tariff Schedule</h3>

      <p className="text-gray-700 leading-relaxed mb-4">
        The Customs Tariff Act, 1975 (First Schedule) contains the complete HSN classification used in India. The CBIC website provides a searchable version. Start with the broad section that matches your product category, then drill down through chapters, headings, and sub-headings to find the specific code.
      </p>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">Method 4: Consult Trade Associations</h3>

      <p className="text-gray-700 leading-relaxed mb-4">
        If your product is unique or falls between two categories, consult your industry trade association or a GST practitioner. You can also apply to the Authority for Advance Ruling (AAR) for a binding classification decision on your specific product.
      </p>

      <div className="bg-yellow-50 border-l-4 border-yellow-500 p-4 rounded mb-6">
        <p className="text-yellow-900 font-medium">Tip: When in Doubt</p>
        <p className="text-yellow-800 text-sm mt-1">If a product could fall under two HSN codes with different GST rates, apply the General Rules of Interpretation (GRI) given at the beginning of the Customs Tariff. Rule 3(a) says the most specific heading takes precedence over a general heading. When classification is ambiguous, use the heading that comes last in numerical order.</p>
      </div>

      {/* Section 8 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">HSN Code on GST Invoice</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        The HSN code must be mentioned on every <Link href="/blog/gst-invoice-format-guide" className="text-blue-600 hover:text-blue-700 underline">GST tax invoice</Link>. The number of digits depends on your turnover as mentioned earlier. Here are the key rules:
      </p>

      <ul className="list-disc pl-6 text-gray-700 space-y-2 mb-6">
        <li>HSN must be mentioned for each line item on the invoice, not just once</li>
        <li>If multiple products have the same HSN code, they can be clubbed under one line with the total quantity and value</li>
        <li>For e-invoices, the HSN code is validated against the master list — invalid codes will be rejected by the IRP</li>
        <li>HSN-wise summary must also be reported in GSTR-1 Table 12, matching the total from invoice-level data</li>
        <li><Link href="/blog/gst-composition-scheme-guide" className="text-blue-600 hover:text-blue-700 underline">Composition dealers</Link> with turnover up to ₹1.5 crore are exempt from mentioning HSN on their bills of supply</li>
      </ul>

      {/* Section 9 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">Penalties for Using Wrong HSN Code</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        Using incorrect HSN codes has serious consequences under GST:
      </p>

      <div className="space-y-4 mb-6">
        <div className="bg-white border rounded-lg p-4">
          <h4 className="font-semibold text-gray-900 mb-2">1. Wrong Tax Rate Application</h4>
          <p className="text-gray-700 text-sm">If the HSN code maps to a 12% rate but your product should be at 18%, you are short-paying tax. The department can issue a demand notice under Section 73 or 74 for the differential tax plus interest at 18% per annum.</p>
        </div>
        <div className="bg-white border rounded-lg p-4">
          <h4 className="font-semibold text-gray-900 mb-2">2. ITC Denial for Your Buyer</h4>
          <p className="text-gray-700 text-sm">If the HSN code on your invoice does not match the actual product, your buyer may face <Link href="/blog/input-tax-credit-itc-rules-2026-27" className="text-blue-600 underline">ITC</Link> denial during scrutiny or audit. This damages your business relationship and can lead to disputes.</p>
        </div>
        <div className="bg-white border rounded-lg p-4">
          <h4 className="font-semibold text-gray-900 mb-2">3. Penalty Under Section 122</h4>
          <p className="text-gray-700 text-sm">Issuing an invoice with incorrect particulars (including wrong HSN) attracts a penalty of ₹10,000 or the tax amount involved, whichever is higher, per invoice under Section 122(1)(ii) of the CGST Act.</p>
        </div>
        <div className="bg-white border rounded-lg p-4">
          <h4 className="font-semibold text-gray-900 mb-2">4. Scrutiny and Audit Notices</h4>
          <p className="text-gray-700 text-sm">The GST system uses automated data analytics to identify HSN mismatches. If your declared HSN does not match industry patterns or if there are discrepancies between GSTR-1 and e-way bill data, you may receive a scrutiny notice under Section 61.</p>
        </div>
        <div className="bg-white border rounded-lg p-4">
          <h4 className="font-semibold text-gray-900 mb-2">5. E-Invoice Rejection</h4>
          <p className="text-gray-700 text-sm">If you are required to generate e-invoices, the IRP validates HSN codes. An invalid or non-existent HSN code will cause the e-invoice generation to fail, preventing you from issuing a valid tax invoice.</p>
        </div>
      </div>

      {/* Section 10 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">Recent Changes in HSN Code Requirements</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        The government has progressively tightened HSN code requirements over the years. Here are the key changes businesses should be aware of:
      </p>

      <ul className="list-disc pl-6 text-gray-700 space-y-2 mb-6">
        <li><strong>Mandatory 6-digit for e-invoicing:</strong> All e-invoices must use 6-digit HSN codes regardless of the taxpayer&apos;s turnover. The IRP rejects invoices with fewer digits.</li>
        <li><strong>GSTR-1 Table 12 validation:</strong> The GST portal now validates HSN codes in the HSN-wise summary. Invalid codes are rejected, and the summary must match total values from other tables.</li>
        <li><strong>Auto-population in GSTR-2B:</strong> HSN codes from seller&apos;s GSTR-1 now auto-populate in buyer&apos;s GSTR-2B, enabling the department to cross-verify product-level details.</li>
        <li><strong>GST rate rationalization:</strong> The GST Council periodically revises rates, which means the GST rate for an HSN code can change via notification. Always verify the current rate.</li>
        <li><strong>Revised HSN chapter notes:</strong> CBIC periodically updates clarifications on HSN classification through circulars. Check the latest circulars for products where classification is disputed.</li>
      </ul>

      {/* Section 11 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">How GSTIndia Tools Can Help</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        Finding the right HSN or SAC code should not slow down your business. The <Link href="/" className="text-blue-600 hover:text-blue-700 underline">GSTIndia platform</Link> by DoAide provides free tools designed to make GST compliance effortless:
      </p>

      <ul className="list-disc pl-6 text-gray-700 space-y-2 mb-6">
        <li><strong><Link href="/" className="text-blue-600 underline">HSN Code Finder:</Link></strong> AI-powered search — type any product name and get the exact HSN/SAC code with the applicable GST rate instantly</li>
        <li><strong><Link href="/" className="text-blue-600 underline">GST Calculator:</Link></strong> Calculate CGST, SGST, and IGST for any amount once you know the correct rate from the HSN code</li>
        <li><strong><Link href="/" className="text-blue-600 underline">GSTIN Validator:</Link></strong> Verify supplier and buyer GSTINs before issuing invoices with HSN codes</li>
      </ul>

      <div className="bg-gradient-to-r from-blue-600 to-blue-700 rounded-xl p-6 text-white mb-8">
        <h3 className="text-xl font-bold mb-2">Find Your HSN Code in Seconds</h3>
        <p className="text-blue-100 mb-4">Use GSTIndia&apos;s AI-powered HSN Code Finder to search by product name and get the correct code with GST rate — free, fast, and always up to date.</p>
        <Link href="/" className="inline-block bg-white text-blue-600 font-semibold px-6 py-2 rounded-lg hover:bg-blue-50 transition-colors">
          Try HSN Code Finder Free &rarr;
        </Link>
      </div>

      {/* FAQ Section */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-6">Frequently Asked Questions (FAQ)</h2>

      <div className="space-y-4 mb-8">
        {[
          {
            q: 'What is HSN code and why is it important in GST?',
            a: 'HSN (Harmonized System of Nomenclature) is an international standard for classifying goods. In India\'s GST system, every product is assigned an HSN code that determines its GST rate. It is important because it ensures the correct tax rate is applied, enables proper ITC matching, and is mandatory on invoices and in GSTR-1 filing.',
          },
          {
            q: 'How many digits of HSN code are required on a GST invoice?',
            a: 'For businesses with turnover up to ₹5 crore, 4-digit HSN codes are required on B2B invoices. For turnover above ₹5 crore, 6-digit codes are mandatory. For e-invoices, 6-digit HSN is always required regardless of turnover. Composition dealers with turnover up to ₹1.5 crore are exempt from HSN requirements.',
          },
          {
            q: 'What is the difference between HSN code and SAC code?',
            a: 'HSN codes classify goods (physical products) and can be 2 to 8 digits long. SAC (Services Accounting Code) classifies services and is always 6 digits starting with 99. Both serve the same purpose of determining the applicable GST rate, but HSN is for goods and SAC is for services.',
          },
          {
            q: 'Is HSN code mandatory for all businesses under GST?',
            a: 'HSN codes are mandatory for all registered regular taxpayers on B2B invoices. Composition dealers with turnover up to ₹1.5 crore are exempt. The number of digits required depends on your turnover — 4 digits for turnover up to ₹5 crore and 6 digits for above ₹5 crore.',
          },
          {
            q: 'How to find the HSN code for my product?',
            a: 'The easiest way is to use the GSTIndia HSN Code Finder tool — search by product name. You can also search on the GST portal (services.gst.gov.in/services/searchhsnsac), check the Customs Tariff Act schedule, or consult your trade association or GST practitioner.',
          },
          {
            q: 'What happens if I use the wrong HSN code?',
            a: 'Using the wrong HSN code can lead to: (1) wrong tax rate application and demand notices, (2) ITC denial for your buyer, (3) penalty of ₹10,000 or tax amount per invoice under Section 122, (4) e-invoice rejection on the IRP, and (5) scrutiny notices from the tax department.',
          },
          {
            q: 'Are HSN codes the same across all countries?',
            a: 'The first 6 digits of HSN codes are internationally standardized across 200+ countries that use the WCO Harmonized System. A laptop is classified as 847130 in India, the US, and Europe. India adds 7th and 8th digits for customs tariff purposes, which are country-specific.',
          },
          {
            q: 'What is the HSN code for services?',
            a: 'Services use SAC (Services Accounting Code) instead of HSN. SAC codes always start with 99 and are 6 digits long. For example, IT services use 9983, financial services use 9971, restaurant services use 9964, and construction services use 9954.',
          },
          {
            q: 'Can the GST rate for an HSN code change?',
            a: 'Yes, the GST Council can revise rates for any HSN code through notifications. Rate changes are effective from the notified date, and businesses must update their billing systems accordingly. Always verify the current rate before invoicing — use the GSTIndia HSN Code Finder for the latest rates.',
          },
          {
            q: 'Where do I report HSN codes in GST returns?',
            a: 'HSN codes are reported in GSTR-1 Table 12 (HSN-wise Summary of Outward Supplies). This table requires HSN code, description, UQC (unit), total quantity, taxable value, and tax amounts. The totals must match with invoice-level data in other tables.',
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
        HSN and SAC codes form the classification backbone of India&apos;s GST system. Using the correct code ensures you apply the right tax rate, your buyers can claim ITC without issues, and your returns are filed accurately. With e-invoicing requirements expanding and the GST portal enforcing stricter validation, getting your HSN codes right is more important than ever.
      </p>

      <p className="text-gray-700 leading-relaxed mb-4">
        Bookmark this page for quick reference to HSN and SAC code lists. For finding the exact code for your specific product or service, use the <Link href="/" className="text-blue-600 hover:text-blue-700 underline">GSTIndia HSN Code Finder</Link>. To understand how HSN codes fit into the broader invoicing requirements, read our <Link href="/blog/gst-invoice-format-guide" className="text-blue-600 hover:text-blue-700 underline">GST Invoice Format Guide</Link>. And for filing the returns that use these HSN codes, check our <Link href="/blog/gst-return-filing-guide-2026-27" className="text-blue-600 hover:text-blue-700 underline">GST Return Filing Guide</Link>.
      </p>

      {/* JSON-LD Structured Data */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            '@context': 'https://schema.org',
            '@type': 'Article',
            headline: 'GST HSN Code List 2026: Complete Guide to Finding HSN & SAC Codes',
            description: 'Complete HSN code list for GST with chapter-wise breakdown. Find HSN codes for goods and SAC codes for services. Updated for 2026-27.',
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
            url: 'https://gst.doaide.com/blog/gst-hsn-code-list',
            mainEntityOfPage: 'https://gst.doaide.com/blog/gst-hsn-code-list',
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
                name: 'What is HSN code and why is it important in GST?',
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: 'HSN (Harmonized System of Nomenclature) classifies goods under GST. It determines the correct GST rate, is mandatory on invoices and in GSTR-1, and enables proper ITC matching.',
                },
              },
              {
                '@type': 'Question',
                name: 'How many digits of HSN code are required on a GST invoice?',
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: '4-digit for turnover up to ₹5 crore, 6-digit for turnover above ₹5 crore, and 6-digit mandatory for all e-invoices regardless of turnover.',
                },
              },
              {
                '@type': 'Question',
                name: 'What is the difference between HSN code and SAC code?',
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: 'HSN codes classify goods (2-8 digits). SAC codes classify services (always 6 digits starting with 99). Both determine the applicable GST rate.',
                },
              },
              {
                '@type': 'Question',
                name: 'Is HSN code mandatory for all businesses under GST?',
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: 'Mandatory for all regular taxpayers on B2B invoices. Composition dealers with turnover up to ₹1.5 crore are exempt. Digit requirements vary by turnover.',
                },
              },
              {
                '@type': 'Question',
                name: 'How to find the HSN code for my product?',
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: 'Use the GSTIndia HSN Code Finder, search on the GST portal, check the Customs Tariff Act schedule, or consult your trade association or GST practitioner.',
                },
              },
              {
                '@type': 'Question',
                name: 'What happens if I use the wrong HSN code?',
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: 'Consequences include wrong tax rate, ITC denial for buyer, penalty of ₹10,000 or tax amount per invoice, e-invoice rejection, and scrutiny notices.',
                },
              },
              {
                '@type': 'Question',
                name: 'Are HSN codes the same across all countries?',
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: 'The first 6 digits are internationally standardized across 200+ countries. India adds 7th and 8th digits for customs purposes, which are country-specific.',
                },
              },
              {
                '@type': 'Question',
                name: 'What is the HSN code for services?',
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: 'Services use SAC codes, always starting with 99. IT services: 9983, financial: 9971, restaurant: 9964, construction: 9954.',
                },
              },
              {
                '@type': 'Question',
                name: 'Can the GST rate for an HSN code change?',
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: 'Yes, the GST Council revises rates through notifications. Changes are effective from the notified date. Always verify current rates before invoicing.',
                },
              },
              {
                '@type': 'Question',
                name: 'Where do I report HSN codes in GST returns?',
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: 'In GSTR-1 Table 12 (HSN-wise Summary of Outward Supplies) with HSN code, description, UQC, quantity, taxable value, and tax amounts.',
                },
              },
            ],
          }),
        }}
      />
      <div className="mt-8 pt-8 border-t dark:border-gray-800">
        <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">Found this guide helpful? Share it:</p>
        <ShareButtons
          title="GST HSN Code List 2026: Complete Guide"
          url="/blog/gst-hsn-code-list"
        />
      </div>
    </article>
  );
}
