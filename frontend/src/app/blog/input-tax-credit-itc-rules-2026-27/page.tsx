import type { Metadata } from 'next';
import Link from 'next/link';
import { ShareButtons } from '@/components/blog/share-buttons';

export const metadata: Metadata = {
  title: 'Input Tax Credit (ITC) Rules 2026-27 | Guide',
  description: 'Complete guide to Input Tax Credit under GST — eligibility, conditions, blocked credits, reversal rules, time limits, and common mistakes to avoid in 2026-27.',
  openGraph: {
    title: 'Input Tax Credit (ITC) Rules 2026-27 | Complete Guide',
    description: 'Everything about ITC under GST — eligibility, conditions, blocked credits, reversal rules, and how to claim ITC correctly.',
    url: 'https://gst.doaide.com/blog/input-tax-credit-itc-rules-2026-27',
    type: 'article',
  },
  alternates: {
    canonical: 'https://gst.doaide.com/blog/input-tax-credit-itc-rules-2026-27',
  },
};

export default function ITCRulesGuide() {
  return (
    <article className="max-w-4xl mx-auto px-4 py-12">
      <div className="mb-8">
        <span className="text-sm font-semibold text-blue-600 bg-blue-50 px-3 py-1 rounded-full">ITC &amp; Credits</span>
        <span className="text-sm text-gray-500 ml-3">Updated: 10 October 2026</span>
        <span className="text-sm text-gray-500 ml-3">14 min read</span>
      </div>

      <h1 className="text-3xl sm:text-4xl font-bold text-gray-900 dark:text-gray-100 mb-6">
        Input Tax Credit (ITC) Rules 2026-27: Complete Guide to Claiming ITC Under GST
      </h1>

      <ShareButtons
        title="Input Tax Credit (ITC) Rules 2026-27: Complete Guide"
        url="/blog/input-tax-credit-itc-rules-2026-27"
        className="mb-8"
      />

      <p className="text-lg text-gray-600 dark:text-gray-400 mb-8 leading-relaxed">
        Input Tax Credit (ITC) is one of the most important features of India&apos;s GST system. It allows businesses to reduce their tax liability by claiming credit for the tax paid on purchases and expenses used in the course of business. Understanding ITC rules correctly is essential to maximise your legitimate credit claims, avoid compliance issues, and reduce your overall tax burden. This comprehensive guide covers everything about ITC under GST for the financial year 2026-27.
      </p>

      <div className="bg-blue-50 border-l-4 border-blue-500 p-4 rounded mb-8">
        <p className="text-blue-900 font-medium">In This Guide</p>
        <ul className="text-blue-800 text-sm mt-2 space-y-1">
          <li>• What is ITC and how it works</li>
          <li>• Eligibility conditions under Section 16</li>
          <li>• Blocked credits under Section 17(5)</li>
          <li>• ITC reversal rules (Rule 42 &amp; 43)</li>
          <li>• Time limits for claiming ITC</li>
          <li>• How to claim ITC in GSTR-3B</li>
          <li>• Common mistakes to avoid</li>
        </ul>
      </div>

      {/* Section 1 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">What is Input Tax Credit (ITC) Under GST?</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        Input Tax Credit is the credit that a registered taxpayer can claim for the GST paid on purchases of goods and services that are used for business purposes. In simple terms, it is the mechanism through which businesses can set off the tax paid on inputs (purchases) against the tax collected on outputs (sales).
      </p>

      <div className="bg-purple-50 border-l-4 border-purple-500 p-4 rounded mb-6">
        <p className="text-purple-900 font-medium">Example: How ITC Works</p>
        <div className="text-purple-800 text-sm mt-2 space-y-2">
          <p>A manufacturer buys raw materials worth ₹1,00,000 and pays 18% GST = ₹18,000 (this is the <strong>input tax</strong>).</p>
          <p>The manufacturer sells the finished product for ₹1,50,000 and collects 18% GST = ₹27,000 (this is the <strong>output tax</strong>).</p>
          <p>The manufacturer can claim ITC of ₹18,000 and only pay the difference:</p>
          <p className="font-semibold">Net GST Payable = ₹27,000 (output) − ₹18,000 (input) = ₹9,000</p>
        </div>
      </div>

      <p className="text-gray-700 leading-relaxed mb-4">
        This mechanism eliminates the cascading effect of tax (tax on tax) that existed in the pre-GST era. ITC ensures that tax is levied only on the value added at each stage of the supply chain, making the tax system more efficient and reducing the overall cost of goods and services for consumers.
      </p>

      <p className="text-gray-700 leading-relaxed mb-4">
        You can use the <Link href="/" className="text-blue-600 hover:text-blue-700 underline">GSTIndia GST Calculator</Link> to quickly compute the tax on your inputs and outputs, and determine your net ITC position before filing returns.
      </p>

      {/* Section 2 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">Who Can Claim Input Tax Credit?</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        Only persons registered under GST can claim ITC. The following categories of registered persons can claim ITC:
      </p>

      <ul className="list-disc pl-6 text-gray-700 space-y-2 mb-6">
        <li><strong>Regular taxpayers:</strong> Businesses registered under the regular GST scheme</li>
        <li><strong>Input Service Distributors (ISD):</strong> Can receive and distribute ITC to branches</li>
        <li><strong>Casual taxable persons:</strong> Can claim ITC on goods and services used for taxable supplies</li>
        <li><strong>Non-resident taxable persons:</strong> Can claim ITC on imported goods and services used for taxable supplies</li>
      </ul>

      <div className="bg-yellow-50 border-l-4 border-yellow-500 p-4 rounded mb-6">
        <p className="text-yellow-900 font-medium">Who Cannot Claim ITC?</p>
        <ul className="text-yellow-800 text-sm mt-2 space-y-1">
          <li>• <strong>Composition scheme dealers:</strong> They pay tax at a flat rate and cannot claim ITC</li>
          <li>• <strong>Unregistered persons:</strong> Must register under GST before claiming ITC</li>
          <li>• Persons making only exempt or nil-rated supplies</li>
          <li>• Persons exclusively engaged in non-taxable supplies</li>
        </ul>
      </div>

      {/* Section 3 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">Conditions for Claiming ITC (Section 16)</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        Section 16 of the CGST Act lays down four essential conditions that must be fulfilled simultaneously for a registered person to claim ITC. If even one condition is not met, ITC cannot be claimed:
      </p>

      <div className="space-y-6 mb-8">
        <div className="border-l-4 border-blue-500 pl-4">
          <h3 className="text-xl font-semibold text-gray-800 mb-2">Condition 1: Possession of Tax Invoice or Debit Note</h3>
          <p className="text-gray-700 text-sm leading-relaxed">
            You must possess a valid tax invoice or debit note issued by the supplier. The invoice must contain all mandatory details — GSTIN of supplier and recipient, invoice number, date, HSN/SAC code, description, quantity, value, and tax amount with breakup of CGST, SGST/UTGST, or IGST. Self-invoices are acceptable for supplies under reverse charge.
          </p>
        </div>

        <div className="border-l-4 border-green-500 pl-4">
          <h3 className="text-xl font-semibold text-gray-800 mb-2">Condition 2: Receipt of Goods or Services</h3>
          <p className="text-gray-700 text-sm leading-relaxed">
            You must have actually received the goods or services. For goods, this means the goods have been delivered to you or to a person directed by you. For services, this means the services have been rendered. In case of goods received in lots or installments, ITC can be claimed only upon receipt of the last lot or installment.
          </p>
        </div>

        <div className="border-l-4 border-orange-500 pl-4">
          <h3 className="text-xl font-semibold text-gray-800 mb-2">Condition 3: Tax Must Be Paid by the Supplier</h3>
          <p className="text-gray-700 text-sm leading-relaxed">
            The tax charged on the invoice must actually be paid to the government by the supplier. This is verified through the GSTR-2B statement — if a supplier has not filed their GSTR-1 or has not paid the tax, the corresponding ITC may not be available in your GSTR-2B. From FY 2022-23 onwards, ITC is restricted to the amount reflected in GSTR-2B.
          </p>
        </div>

        <div className="border-l-4 border-red-500 pl-4">
          <h3 className="text-xl font-semibold text-gray-800 mb-2">Condition 4: Filing of Return</h3>
          <p className="text-gray-700 text-sm leading-relaxed">
            You must file your GST return (GSTR-3B) for the relevant period in which you claim the ITC. Without filing the return, ITC cannot be utilized to offset the output tax liability. Additionally, if you fail to pay the supplier within 180 days from the date of invoice, the ITC claimed must be reversed along with interest.
          </p>
        </div>
      </div>

      <div className="bg-gray-100 border border-gray-300 p-4 rounded mb-6 font-mono text-sm">
        <p className="text-gray-800 font-semibold mb-2">180-Day Payment Rule:</p>
        <p className="text-gray-700">If payment to supplier is not made within 180 days of invoice date:</p>
        <p className="text-gray-700">→ ITC claimed must be REVERSED</p>
        <p className="text-gray-700">→ Interest at 18% per annum must be paid</p>
        <p className="text-gray-700">→ ITC can be re-claimed when payment is eventually made</p>
      </div>

      {/* Section 4 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">ITC on Capital Goods</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        Input Tax Credit on capital goods (machinery, equipment, plant, etc.) can be claimed in full in the tax period in which the capital goods are received. Unlike the pre-GST regime where credit was spread over two years, under GST you can claim the entire ITC on capital goods immediately.
      </p>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">Key Rules for ITC on Capital Goods</h3>

      <ul className="list-disc pl-6 text-gray-700 space-y-2 mb-6">
        <li>Full ITC is available in the period of receipt — no installment claiming required</li>
        <li>If capital goods are used partly for business and partly for personal purposes, ITC is available only on the business-use portion</li>
        <li>If capital goods are used for both taxable and exempt supplies, proportional ITC reversal under Rule 43 applies</li>
        <li>If you have claimed depreciation on the tax component of a capital good under Income Tax Act, you <strong>cannot</strong> claim ITC on the same amount</li>
        <li>When capital goods are sold, you must pay GST on the higher of: (a) the GST on transaction value, or (b) the ITC attributable minus 5% per quarter (or part thereof) from the date of invoice</li>
      </ul>

      <div className="bg-purple-50 border-l-4 border-purple-500 p-4 rounded mb-6">
        <p className="text-purple-900 font-medium">Example: ITC on Capital Goods</p>
        <div className="text-purple-800 text-sm mt-2">
          <p>A company purchases machinery for ₹10,00,000 + 18% GST (₹1,80,000) in April 2026.</p>
          <p className="mt-1">→ Full ITC of ₹1,80,000 can be claimed in the GSTR-3B for April 2026.</p>
          <p className="mt-1">→ If the machinery is sold after 2 years (8 quarters), the remaining ITC = ₹1,80,000 - (5% × 8 × ₹1,80,000) = ₹1,80,000 - ₹72,000 = ₹1,08,000. GST must be paid on the higher of this amount or the GST on sale value.</p>
        </div>
      </div>

      {/* Section 5 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">Documents Required for Claiming ITC</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        ITC can be claimed on the basis of the following documents:
      </p>

      <div className="overflow-x-auto mb-6">
        <table className="w-full border-collapse border border-gray-300 text-sm">
          <thead>
            <tr className="bg-gray-100">
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Document</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">When Applicable</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="border border-gray-300 px-4 py-3 font-medium">Tax Invoice (issued by supplier)</td>
              <td className="border border-gray-300 px-4 py-3">Regular purchases from registered suppliers</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-3 font-medium">Debit Note (issued by supplier)</td>
              <td className="border border-gray-300 px-4 py-3">When original invoice value increases</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-3 font-medium">Bill of Entry</td>
              <td className="border border-gray-300 px-4 py-3">Import of goods (IGST paid at customs)</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-3 font-medium">ISD Invoice (issued by ISD)</td>
              <td className="border border-gray-300 px-4 py-3">Credit distributed by Input Service Distributor to branches</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-3 font-medium">Self-Invoice (under reverse charge)</td>
              <td className="border border-gray-300 px-4 py-3">Purchases from unregistered persons or import of services</td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* Section 6 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">Blocked ITC — Items Where ITC Cannot Be Claimed (Section 17(5))</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        Section 17(5) of the CGST Act lists specific goods and services on which ITC is blocked, meaning you cannot claim credit even if you have a valid tax invoice and use them for business. Here is the complete list:
      </p>

      <div className="space-y-4 mb-6">
        <div className="bg-red-50 border rounded-lg p-4">
          <h4 className="font-semibold text-red-900 mb-2">1. Motor Vehicles and Conveyances</h4>
          <p className="text-red-800 text-sm">ITC is blocked on purchase, lease, or hire of motor vehicles (including cars, SUVs, two-wheelers). <strong>Exceptions:</strong> Vehicles used for transportation of goods, passenger transport services (bus, taxi), driving schools, vehicle dealers, and vehicles used for authorized purposes.</p>
        </div>

        <div className="bg-red-50 border rounded-lg p-4">
          <h4 className="font-semibold text-red-900 mb-2">2. Food &amp; Beverages, Outdoor Catering, Beauty Treatment, Health Services, Cosmetic &amp; Plastic Surgery</h4>
          <p className="text-red-800 text-sm">No ITC on food, catering, salon services, gym memberships, spa services, and cosmetic procedures. <strong>Exception:</strong> When the same category of goods/services is used for making outward taxable supplies of the same category, or where it is obligatory for an employer to provide it to employees under any law.</p>
        </div>

        <div className="bg-red-50 border rounded-lg p-4">
          <h4 className="font-semibold text-red-900 mb-2">3. Membership of Club, Health &amp; Fitness Centre</h4>
          <p className="text-red-800 text-sm">No ITC on membership fees for clubs, gyms, or fitness centres.</p>
        </div>

        <div className="bg-red-50 border rounded-lg p-4">
          <h4 className="font-semibold text-red-900 mb-2">4. Rent-a-Cab, Life Insurance, Health Insurance</h4>
          <p className="text-red-800 text-sm">ITC is blocked on cab rentals, life insurance premiums, and health insurance premiums. <strong>Exception:</strong> When the government makes it obligatory for the employer to provide these to employees, or when used for making outward taxable supplies of the same category.</p>
        </div>

        <div className="bg-red-50 border rounded-lg p-4">
          <h4 className="font-semibold text-red-900 mb-2">5. Travel Benefits to Employees (LTC/LTA)</h4>
          <p className="text-red-800 text-sm">No ITC on leave travel concession or leave travel assistance provided to employees on vacation.</p>
        </div>

        <div className="bg-red-50 border rounded-lg p-4">
          <h4 className="font-semibold text-red-900 mb-2">6. Works Contract Services (for Construction of Immovable Property)</h4>
          <p className="text-red-800 text-sm">No ITC on works contract services when used for construction of immovable property (other than plant and machinery). This includes construction of buildings, offices, factories (structure), etc. <strong>Exception:</strong> Works contract for further supply of works contract service is allowed.</p>
        </div>

        <div className="bg-red-50 border rounded-lg p-4">
          <h4 className="font-semibold text-red-900 mb-2">7. Construction of Immovable Property (on Own Account)</h4>
          <p className="text-red-800 text-sm">ITC is blocked on goods/services used for construction of immovable property on own account, including materials, cement, steel, etc. used for building construction. <strong>&quot;Plant and machinery&quot; is excluded from this block</strong> — so ITC on plant and machinery installed in a factory is available.</p>
        </div>

        <div className="bg-red-50 border rounded-lg p-4">
          <h4 className="font-semibold text-red-900 mb-2">8. Goods or Services for Personal Consumption</h4>
          <p className="text-red-800 text-sm">No ITC on any goods or services used for personal consumption by the proprietor, partners, or directors.</p>
        </div>

        <div className="bg-red-50 border rounded-lg p-4">
          <h4 className="font-semibold text-red-900 mb-2">9. Goods Lost, Stolen, Destroyed, Written Off, or Given as Free Samples/Gifts</h4>
          <p className="text-red-800 text-sm">If goods on which ITC was claimed are subsequently lost, stolen, destroyed, written off, or disposed of as free samples or gifts, the ITC must be reversed.</p>
        </div>

        <div className="bg-red-50 border rounded-lg p-4">
          <h4 className="font-semibold text-red-900 mb-2">10. Tax Paid Under Composition Scheme or Section 10</h4>
          <p className="text-red-800 text-sm">No ITC on tax paid under the composition scheme. Also, ITC is not available on tax paid due to fraud or suppression (Section 74).</p>
        </div>
      </div>

      {/* Section 7 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">ITC Reversal Rules (Rule 42 and Rule 43)</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        When inputs or capital goods are used for both taxable and exempt supplies, or partly for business and partly for non-business purposes, a proportional reversal of ITC is required. This ensures that ITC is claimed only on the portion used for taxable business supplies.
      </p>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">Rule 42: ITC Reversal for Inputs and Input Services</h3>

      <p className="text-gray-700 leading-relaxed mb-4">
        Rule 42 applies when common inputs or input services are used for both taxable and exempt supplies. The formula for proportional reversal is:
      </p>

      <div className="bg-gray-100 border border-gray-300 p-4 rounded mb-6 font-mono text-sm">
        <p className="text-gray-800 font-semibold mb-2">Rule 42 Formula:</p>
        <p className="text-gray-700">Common Credit (C) = Total ITC - ITC exclusively for taxable supplies - ITC exclusively for exempt supplies - Blocked ITC</p>
        <p className="text-gray-700 mt-2">ITC attributable to exempt supplies (D1) = (Exempt Turnover / Total Turnover) × C</p>
        <p className="text-gray-700 mt-1">ITC attributable to non-business use (D2) = 5% × C (if no records maintained)</p>
        <p className="text-gray-700 mt-2 font-semibold">ITC to be reversed = D1 + D2</p>
        <p className="text-gray-700 mt-2 font-semibold">Eligible Common Credit = C - D1 - D2</p>
      </div>

      <div className="bg-purple-50 border-l-4 border-purple-500 p-4 rounded mb-6">
        <p className="text-purple-900 font-medium">Example: Rule 42 Reversal</p>
        <div className="text-purple-800 text-sm mt-2">
          <p>Total ITC in a month: ₹1,00,000</p>
          <p>ITC exclusively for taxable supplies: ₹60,000</p>
          <p>ITC exclusively for exempt supplies: ₹10,000 (not claimable)</p>
          <p>Common Credit (C): ₹1,00,000 - ₹60,000 - ₹10,000 = ₹30,000</p>
          <p className="mt-1">Exempt turnover: ₹5,00,000; Total turnover: ₹25,00,000</p>
          <p>D1 = (5,00,000 / 25,00,000) × ₹30,000 = ₹6,000</p>
          <p>D2 = 5% × ₹30,000 = ₹1,500 (assuming non-business use)</p>
          <p className="font-semibold mt-1">ITC to reverse = ₹6,000 + ₹1,500 = ₹7,500</p>
          <p className="font-semibold">Eligible ITC = ₹60,000 + (₹30,000 - ₹7,500) = ₹82,500</p>
        </div>
      </div>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">Rule 43: ITC Reversal for Capital Goods</h3>

      <p className="text-gray-700 leading-relaxed mb-4">
        Rule 43 applies to capital goods used for both taxable and exempt supplies. The reversal is done on a monthly basis over the useful life of the capital goods (60 months, or 20 quarters). Each month, a portion of ITC attributable to exempt supplies is reversed.
      </p>

      <div className="bg-gray-100 border border-gray-300 p-4 rounded mb-6 font-mono text-sm">
        <p className="text-gray-800 font-semibold mb-2">Rule 43 Formula (Monthly Reversal):</p>
        <p className="text-gray-700">ITC on common capital goods (A)</p>
        <p className="text-gray-700">Useful life: 60 months (5 years)</p>
        <p className="text-gray-700 mt-1">Monthly common credit = A / 60</p>
        <p className="text-gray-700 mt-1">Monthly reversal = (Exempt Turnover / Total Turnover) × (A / 60)</p>
      </div>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">Annual Reconciliation of ITC Reversal</h3>

      <p className="text-gray-700 leading-relaxed mb-4">
        The monthly ITC reversals under Rule 42 are provisional. At the end of the financial year, a final calculation based on actual annual turnover figures must be done. Any difference between the provisional monthly reversals and the final annual calculation must be adjusted in the return for the month of September following the end of the financial year (or at the time of filing the annual return, whichever is earlier).
      </p>

      {/* Section 8 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">Time Limit for Claiming ITC</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        There is a strict time limit for claiming ITC under Section 16(4) of the CGST Act. ITC for any invoice or debit note relating to a financial year must be claimed by the earlier of:
      </p>

      <div className="bg-yellow-50 border-l-4 border-yellow-500 p-4 rounded mb-6">
        <p className="text-yellow-900 font-medium">Deadline for ITC Claim (Section 16(4))</p>
        <ul className="text-yellow-800 text-sm mt-2 space-y-2">
          <li><strong>Option A:</strong> The due date of filing GSTR-3B for the month of September following the end of the financial year</li>
          <li><strong>Option B:</strong> The date of filing the annual return (GSTR-9)</li>
          <li className="font-semibold">Whichever is earlier</li>
        </ul>
      </div>

      <div className="bg-purple-50 border-l-4 border-purple-500 p-4 rounded mb-6">
        <p className="text-purple-900 font-medium">Example: Time Limit for FY 2026-27</p>
        <div className="text-purple-800 text-sm mt-2">
          <p>For invoices received during FY 2026-27 (April 2026 to March 2027):</p>
          <p className="mt-1">→ GSTR-3B for September 2027 due date: <strong>20 October 2027</strong></p>
          <p>→ GSTR-9 for FY 2026-27 due date: <strong>31 December 2027</strong></p>
          <p className="mt-1 font-semibold">Last date to claim ITC: 20 October 2027 (earlier of the two)</p>
        </div>
      </div>

      <p className="text-gray-700 leading-relaxed mb-4">
        Any ITC not claimed by this deadline is permanently lost. There is no mechanism to claim it after the due date. This makes regular reconciliation of your purchases with GSTR-2B extremely important.
      </p>

      {/* Section 9 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">How to Claim ITC in GSTR-3B</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        ITC is claimed through the GSTR-3B return. Here is the step-by-step process:
      </p>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">Step 1: Download and Review GSTR-2B</h3>

      <p className="text-gray-700 leading-relaxed mb-4">
        GSTR-2B is an auto-generated statement based on the GSTR-1 and GSTR-5 filed by your suppliers, GSTR-6 filed by ISDs, and ICEGATE data for imports. It is generated on the 14th of each month. Download it from the GST portal and review all invoices.
      </p>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">Step 2: Reconcile with Purchase Register</h3>

      <p className="text-gray-700 leading-relaxed mb-4">
        Match the invoices in GSTR-2B with your purchase register. Identify:
      </p>

      <ul className="list-disc pl-6 text-gray-700 space-y-2 mb-6">
        <li><strong>Matched invoices:</strong> Present in both your records and GSTR-2B — ITC can be claimed</li>
        <li><strong>Missing in GSTR-2B:</strong> Invoices in your records but not in GSTR-2B — follow up with supplier to file their GSTR-1</li>
        <li><strong>Extra in GSTR-2B:</strong> Invoices in GSTR-2B but not in your records — verify if these are genuine purchases</li>
        <li><strong>Value mismatches:</strong> Invoice values differ between your records and GSTR-2B — resolve with supplier</li>
      </ul>

      <div className="bg-blue-50 border-l-4 border-blue-500 p-4 rounded mb-6">
        <p className="text-blue-900 font-medium">Simplify Reconciliation</p>
        <p className="text-blue-800 text-sm mt-1">Use the <Link href="/" className="text-blue-600 underline">GSTIndia reconciliation tool</Link> to automatically match your purchase data with GSTR-2B. It highlights mismatches and missing invoices so you can resolve them before filing.</p>
      </div>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">Step 3: Fill Table 4 of GSTR-3B</h3>

      <p className="text-gray-700 leading-relaxed mb-4">
        In GSTR-3B, Table 4 is where you declare ITC. The system auto-populates values from GSTR-2B. Enter:
      </p>

      <ul className="list-disc pl-6 text-gray-700 space-y-2 mb-6">
        <li><strong>4(A)(1):</strong> ITC on import of goods (from bill of entry data via ICEGATE)</li>
        <li><strong>4(A)(2):</strong> ITC on import of services (self-assessed)</li>
        <li><strong>4(A)(3):</strong> ITC on inward supplies liable to reverse charge</li>
        <li><strong>4(A)(4):</strong> ITC received from Input Service Distributor</li>
        <li><strong>4(A)(5):</strong> All other ITC (auto-populated from GSTR-2B)</li>
      </ul>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">Step 4: Report ITC Reversals</h3>

      <p className="text-gray-700 leading-relaxed mb-4">
        In Table 4(B), report any ITC that needs to be reversed:
      </p>

      <ul className="list-disc pl-6 text-gray-700 space-y-2 mb-6">
        <li><strong>4(B)(1):</strong> As per Rule 42 &amp; 43 (proportional reversal for exempt/non-business use)</li>
        <li><strong>4(B)(2):</strong> Others — ITC reversed for non-payment within 180 days, ITC on goods lost/stolen/destroyed, etc.</li>
      </ul>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">Step 5: Net ITC and Set Off</h3>

      <p className="text-gray-700 leading-relaxed mb-4">
        The system calculates Net ITC = 4(A) - 4(B). This net ITC is credited to your Electronic Credit Ledger and can be used to offset your output tax liability. The order of utilization is:
      </p>

      <ol className="list-decimal pl-6 text-gray-700 space-y-2 mb-6">
        <li>IGST credit → First against IGST liability, then CGST, then SGST</li>
        <li>CGST credit → First against CGST liability, then IGST (not against SGST)</li>
        <li>SGST credit → First against SGST liability, then IGST (not against CGST)</li>
      </ol>

      {/* Section 10 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">ITC Matching and Reconciliation</h2>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">GSTR-2A vs GSTR-2B: Which One to Use?</h3>

      <p className="text-gray-700 leading-relaxed mb-4">
        Both GSTR-2A and GSTR-2B show your inward supplies based on your suppliers&apos; filings, but they serve different purposes:
      </p>

      <div className="overflow-x-auto mb-6">
        <table className="w-full border-collapse border border-gray-300 text-sm">
          <thead>
            <tr className="bg-gray-100">
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Feature</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">GSTR-2A</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">GSTR-2B</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="border border-gray-300 px-4 py-3">Nature</td>
              <td className="border border-gray-300 px-4 py-3">Dynamic (changes as suppliers file/amend)</td>
              <td className="border border-gray-300 px-4 py-3">Static (generated once per month on 14th)</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-3">Cut-off Date</td>
              <td className="border border-gray-300 px-4 py-3">No fixed cut-off</td>
              <td className="border border-gray-300 px-4 py-3">GSTR-1 filed by 11th/13th of following month</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-3">Use for ITC</td>
              <td className="border border-gray-300 px-4 py-3">Reference only</td>
              <td className="border border-gray-300 px-4 py-3">Basis for ITC claim in GSTR-3B</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-3">ITC Advisory</td>
              <td className="border border-gray-300 px-4 py-3">No</td>
              <td className="border border-gray-300 px-4 py-3">Yes (eligible, ineligible, reverse charge)</td>
            </tr>
          </tbody>
        </table>
      </div>

      <p className="text-gray-700 leading-relaxed mb-4">
        <strong>Always use GSTR-2B as the basis for claiming ITC in GSTR-3B.</strong> GSTR-2B gives a clear advisory on which ITC is eligible and which is not. The auto-populated values in GSTR-3B Table 4 are derived from GSTR-2B.
      </p>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">Current ITC Matching Rules</h3>

      <p className="text-gray-700 leading-relaxed mb-4">
        The earlier 10% provisional ITC rule (which allowed claiming 10% over GSTR-2A) was replaced. The current rules from FY 2022-23 onwards are:
      </p>

      <ul className="list-disc pl-6 text-gray-700 space-y-2 mb-6">
        <li>ITC claimed in GSTR-3B must not exceed the amount of ITC available in GSTR-2B</li>
        <li>For invoices not reflected in GSTR-2B, ITC cannot be claimed until the supplier files their return</li>
        <li>The system auto-populates ITC in GSTR-3B based on GSTR-2B — any manual upward revision beyond this amount may trigger notices</li>
        <li>ITC on reverse charge supplies (self-assessed) can be claimed even if not in GSTR-2B</li>
      </ul>

      {/* Section 11 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">Common Mistakes in ITC Claims and How to Avoid Them</h2>

      <div className="space-y-4 mb-6">
        <div className="bg-white border rounded-lg p-4">
          <h4 className="font-semibold text-gray-900 mb-2">1. Claiming ITC on Blocked Items</h4>
          <p className="text-gray-700 text-sm">Many businesses inadvertently claim ITC on items blocked under Section 17(5) — like motor vehicles, food and beverages, or personal consumption. Review your ITC claims against the blocked list before filing.</p>
        </div>
        <div className="bg-white border rounded-lg p-4">
          <h4 className="font-semibold text-gray-900 mb-2">2. Not Reconciling with GSTR-2B</h4>
          <p className="text-gray-700 text-sm">Claiming ITC based solely on your purchase register without checking GSTR-2B is the most common mistake. Always reconcile before filing. Use the <Link href="/" className="text-blue-600 underline">GSTIndia reconciliation tool</Link> for automated matching.</p>
        </div>
        <div className="bg-white border rounded-lg p-4">
          <h4 className="font-semibold text-gray-900 mb-2">3. Missing the Deadline</h4>
          <p className="text-gray-700 text-sm">ITC for a financial year must be claimed by the GSTR-3B filing date for September of the following year. Missing this deadline means the ITC is lost forever. Maintain a tracker for pending ITC claims.</p>
        </div>
        <div className="bg-white border rounded-lg p-4">
          <h4 className="font-semibold text-gray-900 mb-2">4. Not Reversing ITC for Non-Payment Within 180 Days</h4>
          <p className="text-gray-700 text-sm">If you have not paid your supplier within 180 days of the invoice date, ITC must be reversed. Many businesses overlook this and face penalties during audits.</p>
        </div>
        <div className="bg-white border rounded-lg p-4">
          <h4 className="font-semibold text-gray-900 mb-2">5. Claiming ITC on Invoices from Cancelled GSTINs</h4>
          <p className="text-gray-700 text-sm">If a supplier&apos;s registration has been cancelled, invoices issued after the cancellation date do not qualify for ITC. Verify supplier GSTINs regularly using the <Link href="/" className="text-blue-600 underline">GSTIndia GSTIN Validator</Link>.</p>
        </div>
        <div className="bg-white border rounded-lg p-4">
          <h4 className="font-semibold text-gray-900 mb-2">6. Double Claiming ITC</h4>
          <p className="text-gray-700 text-sm">Claiming ITC on the same invoice in multiple months, or claiming both in GSTR-3B and ITC-04 for job work, leads to excess credit. The department&apos;s automated systems flag such duplicates.</p>
        </div>
        <div className="bg-white border rounded-lg p-4">
          <h4 className="font-semibold text-gray-900 mb-2">7. Ignoring Rule 42/43 Reversals</h4>
          <p className="text-gray-700 text-sm">Businesses with both taxable and exempt supplies often forget to do the proportional ITC reversal. This is a major audit finding. Set up a system to calculate reversals monthly.</p>
        </div>
      </div>

      {/* Section 12 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">How GSTIndia Tools Help with ITC Management</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        Managing ITC effectively requires accurate calculations, regular reconciliation, and proper documentation. The <Link href="/" className="text-blue-600 hover:text-blue-700 underline">GSTIndia platform</Link> offers free tools to help:
      </p>

      <ul className="list-disc pl-6 text-gray-700 space-y-2 mb-6">
        <li><strong><Link href="/" className="text-blue-600 underline">GST Calculator:</Link></strong> Calculate the exact GST on inputs and outputs to determine your net ITC position</li>
        <li><strong><Link href="/" className="text-blue-600 underline">GSTIN Validator:</Link></strong> Verify supplier GSTINs to ensure they are active and valid before claiming ITC on their invoices</li>
        <li><strong><Link href="/" className="text-blue-600 underline">HSN Code Finder:</Link></strong> Confirm correct HSN codes to ensure invoices are valid for ITC claims</li>
        <li><strong><Link href="/" className="text-blue-600 underline">ITC Reconciliation:</Link></strong> Automatically match your purchase register with GSTR-2B to identify discrepancies</li>
      </ul>

      <div className="bg-gradient-to-r from-blue-600 to-blue-700 rounded-xl p-6 text-white mb-8">
        <h3 className="text-xl font-bold mb-2">Maximise Your ITC Claims</h3>
        <p className="text-blue-100 mb-4">Use GSTIndia&apos;s free tools to calculate GST, validate supplier GSTINs, and reconcile ITC with GSTR-2B — ensure you never miss a legitimate credit.</p>
        <Link href="/" className="inline-block bg-white text-blue-600 font-semibold px-6 py-2 rounded-lg hover:bg-blue-50 transition-colors">
          Start Using Free GST Tools →
        </Link>
      </div>

      {/* FAQ Section */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-6">Frequently Asked Questions (FAQ)</h2>

      <div className="space-y-4 mb-8">
        {[
          {
            q: 'What is Input Tax Credit in GST with example?',
            a: 'Input Tax Credit (ITC) is the credit a registered business claims for GST paid on purchases. For example, if you buy goods for ₹1,00,000 + 18% GST (₹18,000) and sell them for ₹1,50,000 + 18% GST (₹27,000), you pay only ₹9,000 (₹27,000 - ₹18,000) as GST. The ₹18,000 is your ITC.',
          },
          {
            q: 'Can I claim ITC on purchases from unregistered dealers?',
            a: 'Generally, no. ITC is available only on purchases from registered suppliers backed by a valid tax invoice. However, for specified goods/services under reverse charge mechanism (Section 9(3)), you can pay GST on reverse charge basis and claim ITC by issuing a self-invoice.',
          },
          {
            q: 'What is the time limit for claiming ITC?',
            a: 'ITC for a financial year must be claimed by the due date of filing GSTR-3B for September of the following year, or the date of filing annual return — whichever is earlier. For FY 2026-27, the deadline is 20 October 2027.',
          },
          {
            q: 'Can ITC be claimed on GST paid under reverse charge?',
            a: 'Yes, ITC can be claimed on GST paid under reverse charge mechanism, provided all conditions under Section 16 are met. The ITC is available in the same month in which the reverse charge tax is paid.',
          },
          {
            q: 'Is ITC available on rent paid for office premises?',
            a: 'Yes, ITC is available on rent paid for commercial office premises used for business purposes. However, ITC is blocked on rent for residential property (regardless of whether it is used for business). The 2024 amendment clarified that ITC on renting residential property is blocked under Section 17(5).',
          },
          {
            q: 'What happens if my supplier does not file their GSTR-1?',
            a: 'If your supplier does not file GSTR-1, the invoice will not appear in your GSTR-2B, and you cannot claim ITC on that invoice. You should follow up with the supplier to file their return. Once they file, the ITC will be available in a subsequent GSTR-2B.',
          },
          {
            q: 'Can ITC be claimed on mobile phone purchased for business use?',
            a: 'Yes, ITC can be claimed on mobile phones purchased for business use. Unlike motor vehicles, mobile phones are not in the blocked ITC list under Section 17(5). Ensure you have a tax invoice and the phone is used for business purposes.',
          },
          {
            q: 'How is ITC reversed when a credit note is issued?',
            a: 'When a supplier issues a credit note (for returns, discounts, etc.), the corresponding ITC claimed by the buyer must be reversed. The credit note reflects in GSTR-2B as a reduction in ITC. The buyer must reverse the ITC in the GSTR-3B of the period in which the credit note appears in GSTR-2B.',
          },
          {
            q: 'Can a composition dealer claim Input Tax Credit?',
            a: 'No, composition scheme dealers cannot claim ITC. This is one of the major restrictions of the composition scheme. If you need to claim ITC on your inputs, you should register as a regular taxpayer instead of opting for composition scheme.',
          },
          {
            q: 'What is the difference between eligible and ineligible ITC?',
            a: 'Eligible ITC is the credit you can legally claim and use to offset output tax — it appears as eligible in GSTR-2B. Ineligible ITC includes blocked credits under Section 17(5), ITC on exempt supplies, ITC on supplies from cancelled GSTINs, and credits that fail the conditions under Section 16.',
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
        Input Tax Credit is the backbone of the GST system, and claiming it correctly is vital for maintaining healthy cash flow and avoiding compliance issues. By understanding the eligibility conditions, blocked credits, reversal rules, and time limits outlined in this guide, you can maximise your legitimate ITC claims while staying fully compliant.
      </p>

      <p className="text-gray-700 leading-relaxed mb-4">
        Regular reconciliation of your purchase data with GSTR-2B, timely follow-ups with suppliers who have not filed their returns, and proper documentation are the three pillars of effective ITC management. Leverage tools like the <Link href="/" className="text-blue-600 hover:text-blue-700 underline">GSTIndia platform</Link> to automate reconciliation and validate supplier GSTINs, so you can focus on growing your business while staying compliant with GST regulations.
      </p>

      <p className="text-gray-700 leading-relaxed mb-4">
        Also read our <Link href="/blog/gst-return-filing-guide-2026-27" className="text-blue-600 underline">GST Return Filing Guide 2026-27</Link> and <Link href="/blog/gst-registration-online-guide" className="text-blue-600 underline">GST Registration Guide</Link> for complete GST compliance coverage.
      </p>

      {/* JSON-LD Structured Data */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            '@context': 'https://schema.org',
            '@type': 'Article',
            headline: 'Input Tax Credit (ITC) Rules 2026-27: Complete Guide to Claiming ITC Under GST',
            description: 'Complete guide to Input Tax Credit under GST — eligibility, conditions, blocked credits, reversal rules, time limits, and common mistakes to avoid.',
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
            url: 'https://gst.doaide.com/blog/input-tax-credit-itc-rules-2026-27',
            mainEntityOfPage: 'https://gst.doaide.com/blog/input-tax-credit-itc-rules-2026-27',
            image: 'https://gst.doaide.com/og-itc-rules.png',
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
                name: 'What is Input Tax Credit in GST with example?',
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: 'ITC is the credit a registered business claims for GST paid on purchases. For example, if you buy goods for ₹1,00,000 + 18% GST (₹18,000) and sell for ₹1,50,000 + 18% GST (₹27,000), you pay only ₹9,000 as GST.',
                },
              },
              {
                '@type': 'Question',
                name: 'Can I claim ITC on purchases from unregistered dealers?',
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: 'Generally no. ITC is available only on purchases from registered suppliers backed by a valid tax invoice. For specified goods/services under reverse charge, you can pay GST and claim ITC by issuing a self-invoice.',
                },
              },
              {
                '@type': 'Question',
                name: 'What is the time limit for claiming ITC?',
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: 'ITC must be claimed by the due date of filing GSTR-3B for September of the following year, or the date of filing annual return — whichever is earlier. For FY 2026-27, the deadline is 20 October 2027.',
                },
              },
              {
                '@type': 'Question',
                name: 'Can ITC be claimed on GST paid under reverse charge?',
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: 'Yes, ITC can be claimed on GST paid under reverse charge mechanism, provided all conditions under Section 16 are met.',
                },
              },
              {
                '@type': 'Question',
                name: 'Is ITC available on rent paid for office premises?',
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: 'Yes, ITC is available on rent for commercial office premises used for business. However, ITC is blocked on rent for residential property regardless of use.',
                },
              },
              {
                '@type': 'Question',
                name: 'What happens if my supplier does not file their GSTR-1?',
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: 'The invoice will not appear in your GSTR-2B, and you cannot claim ITC. Follow up with the supplier to file their return.',
                },
              },
              {
                '@type': 'Question',
                name: 'Can ITC be claimed on mobile phone purchased for business use?',
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: 'Yes, ITC can be claimed on mobile phones for business use. Mobile phones are not in the blocked ITC list under Section 17(5).',
                },
              },
              {
                '@type': 'Question',
                name: 'How is ITC reversed when a credit note is issued?',
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: 'When a supplier issues a credit note, the corresponding ITC must be reversed by the buyer in the GSTR-3B of the period in which the credit note appears in GSTR-2B.',
                },
              },
              {
                '@type': 'Question',
                name: 'Can a composition dealer claim Input Tax Credit?',
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: 'No, composition scheme dealers cannot claim ITC. To claim ITC, you must register as a regular taxpayer.',
                },
              },
              {
                '@type': 'Question',
                name: 'What is the difference between eligible and ineligible ITC?',
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: 'Eligible ITC can be claimed and used to offset output tax. Ineligible ITC includes blocked credits under Section 17(5), ITC on exempt supplies, and credits from cancelled GSTINs.',
                },
              },
            ],
          }),
        }}
      />
      <div className="mt-8 pt-8 border-t dark:border-gray-800">
        <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">Found this guide helpful? Share it:</p>
        <ShareButtons
          title="Input Tax Credit (ITC) Rules 2026-27: Complete Guide"
          url="/blog/input-tax-credit-itc-rules-2026-27"
        />
      </div>
    </article>
  );
}
