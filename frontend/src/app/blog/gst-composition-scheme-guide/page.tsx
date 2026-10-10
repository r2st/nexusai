import type { Metadata } from 'next';
import Link from 'next/link';
import { ShareButtons } from '@/components/blog/share-buttons';

export const metadata: Metadata = {
  title: 'GST Composition Scheme 2026: Rules & Benefits',
  description: 'Complete guide to GST Composition Scheme — eligibility, tax rates, GSTR-4 filing, benefits vs regular scheme. Updated for 2026-27 with practical examples.',
  openGraph: {
    title: 'GST Composition Scheme 2026: Eligibility, Tax Rates & Filing Guide',
    description: 'Complete guide to GST Composition Scheme — eligibility, tax rates, GSTR-4 filing, benefits vs regular scheme.',
    url: 'https://gst.doaide.com/blog/gst-composition-scheme-guide',
    type: 'article',
  },
  alternates: {
    canonical: 'https://gst.doaide.com/blog/gst-composition-scheme-guide',
  },
};

export default function GSTCompositionSchemeGuide() {
  return (
    <article className="max-w-4xl mx-auto px-4 py-12">
      <div className="mb-8">
        <span className="text-sm font-semibold text-blue-600 bg-blue-50 px-3 py-1 rounded-full">Composition Scheme</span>
        <span className="text-sm text-gray-500 ml-3">Updated: 10 October 2026</span>
        <span className="text-sm text-gray-500 ml-3">15 min read</span>
      </div>

      <h1 className="text-3xl sm:text-4xl font-bold text-gray-900 dark:text-gray-100 mb-6">
        GST Composition Scheme 2026: Eligibility, Tax Rates &amp; Filing Guide
      </h1>

      <ShareButtons
        title="GST Composition Scheme 2026: Eligibility, Tax Rates & Filing Guide"
        url="/blog/gst-composition-scheme-guide"
        className="mb-8"
      />

      <p className="text-lg text-gray-600 dark:text-gray-400 mb-8 leading-relaxed">
        The GST Composition Scheme is a simplified tax scheme designed for small businesses in India. Instead of charging GST on each sale and filing monthly returns, composition dealers pay a flat percentage of tax on their total turnover and file only quarterly and annual returns. This guide explains who can opt for the scheme, the tax rates, how to file returns, and whether the composition scheme is right for your business in 2026-27.
      </p>

      <div className="bg-blue-50 border-l-4 border-blue-500 p-4 rounded mb-8">
        <p className="text-blue-900 font-medium">Quick Navigation</p>
        <ul className="text-blue-800 text-sm mt-2 space-y-1">
          <li>&bull; What is the Composition Scheme</li>
          <li>&bull; Eligibility Criteria</li>
          <li>&bull; Tax Rates</li>
          <li>&bull; Composition vs Regular Scheme</li>
          <li>&bull; How to Opt In / Switch Out</li>
          <li>&bull; Filing Returns (CMP-08 &amp; GSTR-4)</li>
          <li>&bull; Restrictions &amp; Limitations</li>
          <li>&bull; Practical Examples</li>
          <li>&bull; Penalties</li>
          <li>&bull; FAQs</li>
        </ul>
      </div>

      {/* Section 1 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">What is the GST Composition Scheme?</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        The GST Composition Scheme is a simplified taxation option under <strong>Section 10 of the CGST Act, 2017</strong> meant for small taxpayers. It allows eligible businesses to pay GST at a flat rate on their total turnover instead of collecting and paying tax on each individual transaction. The scheme significantly reduces compliance burden — instead of filing 12-25 returns per year under the regular scheme, composition dealers file only 5 returns (4 quarterly CMP-08 statements and 1 annual GSTR-4).
      </p>

      <p className="text-gray-700 leading-relaxed mb-4">
        The key idea behind the composition scheme is simplicity. Small businesses — kirana stores, local manufacturers, neighbourhood restaurants — often lack the resources for complex tax compliance. The composition scheme lets them operate with minimal paperwork while still contributing to the tax system. However, this simplicity comes with trade-offs: composition dealers cannot collect GST from their customers, cannot claim <Link href="/blog/input-tax-credit-itc-rules-2026-27" className="text-blue-600 hover:text-blue-700 underline">Input Tax Credit (ITC)</Link>, and cannot make inter-state supplies.
      </p>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">Key Features at a Glance</h3>

      <ul className="list-disc pl-6 text-gray-700 space-y-2 mb-6">
        <li><strong>Flat tax rate:</strong> 1% to 6% on turnover (varies by business type)</li>
        <li><strong>No ITC claim:</strong> Cannot claim credit on purchases</li>
        <li><strong>No GST collection:</strong> Cannot charge GST to customers</li>
        <li><strong>Bill of Supply:</strong> Issues bill of supply instead of <Link href="/blog/gst-invoice-format-guide" className="text-blue-600 hover:text-blue-700 underline">tax invoice</Link></li>
        <li><strong>Fewer returns:</strong> Quarterly CMP-08 + annual GSTR-4 (only 5 per year)</li>
        <li><strong>No inter-state supply:</strong> Can only sell within the state</li>
        <li><strong>No e-commerce:</strong> Cannot supply through e-commerce platforms</li>
      </ul>

      {/* Section 2 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">Eligibility for GST Composition Scheme</h2>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">Turnover Limits</h3>

      <div className="overflow-x-auto mb-6">
        <table className="w-full border-collapse border border-gray-300 text-sm">
          <thead>
            <tr className="bg-gray-100">
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Business Type</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Turnover Limit (General)</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Special Category States*</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="border border-gray-300 px-4 py-2">Manufacturers and Traders</td>
              <td className="border border-gray-300 px-4 py-2 font-medium">₹1.5 crore</td>
              <td className="border border-gray-300 px-4 py-2">₹75 lakh</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-2">Service Providers (under Notification 2/2019)</td>
              <td className="border border-gray-300 px-4 py-2 font-medium">₹50 lakh</td>
              <td className="border border-gray-300 px-4 py-2">₹50 lakh</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-2">Restaurants (not serving alcohol)</td>
              <td className="border border-gray-300 px-4 py-2 font-medium">₹1.5 crore</td>
              <td className="border border-gray-300 px-4 py-2">₹75 lakh</td>
            </tr>
          </tbody>
        </table>
      </div>

      <p className="text-gray-500 text-sm mb-6">
        *Special Category States: Arunachal Pradesh, Manipur, Meghalaya, Mizoram, Nagaland, Sikkim, Tripura, and Uttarakhand.
      </p>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">Who CAN Opt for Composition Scheme</h3>

      <ul className="list-disc pl-6 text-gray-700 space-y-2 mb-6">
        <li><strong>Manufacturers:</strong> Small-scale manufacturers of goods (except notified goods)</li>
        <li><strong>Traders:</strong> Businesses engaged in buying and selling goods</li>
        <li><strong>Restaurants:</strong> Restaurants and eateries that do not serve alcohol (as part of their liquor license)</li>
        <li><strong>Service providers:</strong> Businesses providing services with turnover up to ₹50 lakh (under Notification 2/2019-CT(Rate), effective from 1 April 2019)</li>
        <li><strong>Mixed suppliers:</strong> Businesses supplying both goods and services, provided the total supply of services does not exceed 10% of turnover in the preceding year (or ₹5 lakh, whichever is higher) — except for service providers under Notification 2/2019</li>
      </ul>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">Who CANNOT Opt for Composition Scheme</h3>

      <div className="bg-yellow-50 border-l-4 border-yellow-500 p-4 rounded mb-6">
        <p className="text-yellow-900 font-medium">The following persons are NOT eligible</p>
        <ul className="text-yellow-800 text-sm mt-2 space-y-1">
          <li>&bull; Persons making inter-state outward supplies of goods (selling to other states)</li>
          <li>&bull; Persons making supplies through e-commerce operators (Amazon, Flipkart, etc.)</li>
          <li>&bull; Manufacturers of ice cream, pan masala, or tobacco products</li>
          <li>&bull; Casual taxable persons and non-resident taxable persons</li>
          <li>&bull; Persons supplying goods through e-commerce operators required to collect TCS</li>
          <li>&bull; Persons who are not registered under GST or have multiple GSTINs in different states (must opt uniformly)</li>
        </ul>
      </div>

      <p className="text-gray-700 leading-relaxed mb-4">
        If you have <Link href="/blog/gst-registration-online-guide" className="text-blue-600 hover:text-blue-700 underline">GST registrations</Link> in multiple states, you must opt for the composition scheme under all registrations or none. You cannot be a composition dealer in one state and a regular dealer in another.
      </p>

      {/* Section 3 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">Tax Rates Under Composition Scheme</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        One of the biggest advantages of the composition scheme is the lower tax rate. Instead of charging GST at standard rates (5%, 12%, 18%, or 28%) on each product, you pay a flat rate on your <strong>total turnover</strong>:
      </p>

      <div className="overflow-x-auto mb-6">
        <table className="w-full border-collapse border border-gray-300 text-sm">
          <thead>
            <tr className="bg-gray-100">
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Business Category</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">CGST Rate</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">SGST Rate</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Total Rate</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="border border-gray-300 px-4 py-2">Manufacturers (other than specified goods)</td>
              <td className="border border-gray-300 px-4 py-2 text-center">0.5%</td>
              <td className="border border-gray-300 px-4 py-2 text-center">0.5%</td>
              <td className="border border-gray-300 px-4 py-2 text-center font-bold">1%</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-2">Traders (suppliers of goods)</td>
              <td className="border border-gray-300 px-4 py-2 text-center">0.5%</td>
              <td className="border border-gray-300 px-4 py-2 text-center">0.5%</td>
              <td className="border border-gray-300 px-4 py-2 text-center font-bold">1%</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-2">Restaurants (not serving alcohol)</td>
              <td className="border border-gray-300 px-4 py-2 text-center">2.5%</td>
              <td className="border border-gray-300 px-4 py-2 text-center">2.5%</td>
              <td className="border border-gray-300 px-4 py-2 text-center font-bold">5%</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-2">Service Providers (Notification 2/2019)</td>
              <td className="border border-gray-300 px-4 py-2 text-center">3%</td>
              <td className="border border-gray-300 px-4 py-2 text-center">3%</td>
              <td className="border border-gray-300 px-4 py-2 text-center font-bold">6%</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div className="bg-blue-50 border-l-4 border-blue-500 p-4 rounded mb-6">
        <p className="text-blue-900 font-medium">Key Point: Tax is on Turnover, Not Value Addition</p>
        <p className="text-blue-800 text-sm mt-1">Unlike regular GST where you pay tax on each sale and claim ITC on purchases, composition tax is levied on your <strong>total turnover</strong> (total sales). There is no ITC offset. This means the effective tax cost depends on your profit margin — lower margins mean composition tax can be higher than regular GST after ITC.</p>
      </div>

      {/* Section 4 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">Composition Scheme vs Regular Scheme: Detailed Comparison</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        Choosing between composition and regular scheme requires understanding the trade-offs. Here is a comprehensive comparison:
      </p>

      <div className="overflow-x-auto mb-6">
        <table className="w-full border-collapse border border-gray-300 text-sm">
          <thead>
            <tr className="bg-gray-100">
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Parameter</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Composition Scheme</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Regular Scheme</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="border border-gray-300 px-4 py-2 font-medium">Tax Rate</td>
              <td className="border border-gray-300 px-4 py-2">1% / 5% / 6% flat on turnover</td>
              <td className="border border-gray-300 px-4 py-2">5% / 12% / 18% / 28% per product</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-2 font-medium">Input Tax Credit</td>
              <td className="border border-gray-300 px-4 py-2">Cannot claim ITC</td>
              <td className="border border-gray-300 px-4 py-2">Full ITC on purchases</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-2 font-medium">Invoice Type</td>
              <td className="border border-gray-300 px-4 py-2">Bill of Supply (no tax breakup)</td>
              <td className="border border-gray-300 px-4 py-2">Tax Invoice (with CGST/SGST/IGST)</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-2 font-medium">GST Collection</td>
              <td className="border border-gray-300 px-4 py-2">Cannot charge GST to customers</td>
              <td className="border border-gray-300 px-4 py-2">Must charge GST on each sale</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-2 font-medium">Returns per Year</td>
              <td className="border border-gray-300 px-4 py-2">5 (4 CMP-08 + 1 GSTR-4)</td>
              <td className="border border-gray-300 px-4 py-2">12-25 (GSTR-1, GSTR-3B + GSTR-9)</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-2 font-medium">Inter-state Supply</td>
              <td className="border border-gray-300 px-4 py-2">Not allowed</td>
              <td className="border border-gray-300 px-4 py-2">Allowed</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-2 font-medium">E-commerce Supply</td>
              <td className="border border-gray-300 px-4 py-2">Not allowed</td>
              <td className="border border-gray-300 px-4 py-2">Allowed</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-2 font-medium">Compliance Burden</td>
              <td className="border border-gray-300 px-4 py-2">Very low</td>
              <td className="border border-gray-300 px-4 py-2">High</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-2 font-medium">ITC for Buyers</td>
              <td className="border border-gray-300 px-4 py-2">Buyers cannot claim ITC</td>
              <td className="border border-gray-300 px-4 py-2">Buyers can claim full ITC</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-2 font-medium">HSN Requirement</td>
              <td className="border border-gray-300 px-4 py-2">Not mandatory (up to ₹1.5 crore)</td>
              <td className="border border-gray-300 px-4 py-2">4 or 6 digit based on turnover</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-2 font-medium">Reverse Charge</td>
              <td className="border border-gray-300 px-4 py-2">Must pay on applicable supplies</td>
              <td className="border border-gray-300 px-4 py-2">Must pay, but can claim ITC on it</td>
            </tr>
          </tbody>
        </table>
      </div>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">Cost Comparison Example: When is Composition Better?</h3>

      <p className="text-gray-700 leading-relaxed mb-4">
        Let&apos;s compare the tax cost for a trader with ₹80 lakh annual turnover and a 20% profit margin (₹64 lakh purchases, ₹80 lakh sales). Assume all goods attract 18% GST:
      </p>

      <div className="overflow-x-auto mb-6">
        <table className="w-full border-collapse border border-gray-300 text-sm">
          <thead>
            <tr className="bg-gray-100">
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Particulars</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Composition Scheme</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Regular Scheme</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="border border-gray-300 px-4 py-2">Annual Turnover</td>
              <td className="border border-gray-300 px-4 py-2">₹80,00,000</td>
              <td className="border border-gray-300 px-4 py-2">₹80,00,000</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-2">Annual Purchases</td>
              <td className="border border-gray-300 px-4 py-2">₹64,00,000</td>
              <td className="border border-gray-300 px-4 py-2">₹64,00,000</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-2">GST on Sales (Output Tax)</td>
              <td className="border border-gray-300 px-4 py-2">Not applicable</td>
              <td className="border border-gray-300 px-4 py-2">₹14,40,000 (18%)</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-2">GST on Purchases (ITC)</td>
              <td className="border border-gray-300 px-4 py-2">₹11,52,000 (paid, no credit)</td>
              <td className="border border-gray-300 px-4 py-2">₹11,52,000 (claimed as ITC)</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-2">Composition Tax (1%)</td>
              <td className="border border-gray-300 px-4 py-2 font-bold">₹80,000</td>
              <td className="border border-gray-300 px-4 py-2">Not applicable</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-2 font-bold">Net Tax Payable</td>
              <td className="border border-gray-300 px-4 py-2 font-bold text-green-700">₹80,000</td>
              <td className="border border-gray-300 px-4 py-2 font-bold">₹2,88,000 (₹14.4L − ₹11.52L)</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-2 font-bold">Total Cost (GST paid on purchases + net tax)</td>
              <td className="border border-gray-300 px-4 py-2 font-bold text-green-700">₹12,32,000</td>
              <td className="border border-gray-300 px-4 py-2 font-bold">₹2,88,000</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div className="bg-yellow-50 border-l-4 border-yellow-500 p-4 rounded mb-6">
        <p className="text-yellow-900 font-medium">Important Nuance</p>
        <p className="text-yellow-800 text-sm mt-1">While the composition tax itself (₹80,000) is lower than regular net tax (₹2,88,000), composition dealers also bear the hidden cost of GST paid on purchases (₹11,52,000) which they cannot claim as ITC. Under the regular scheme, this ₹11,52,000 is fully offset via ITC. The composition scheme is beneficial only when the composition tax + unrecoverable purchase GST is less than the regular scheme&apos;s net tax — which typically happens when the margin is very high or when purchases are from unregistered suppliers (no ITC anyway). Use the <Link href="/" className="text-blue-600 underline">GSTIndia GST Calculator</Link> to work out your specific scenario.</p>
      </div>

      {/* Section 5 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">How to Opt for the Composition Scheme</h2>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">For New GST Registrations</h3>

      <p className="text-gray-700 leading-relaxed mb-4">
        If you are applying for <Link href="/blog/gst-registration-online-guide" className="text-blue-600 hover:text-blue-700 underline">new GST registration</Link>, you can opt for the composition scheme at the time of registration itself. In Part B of the registration application (Form GST REG-01), there is an option to select &quot;Composition&quot; as your taxpayer type. The scheme becomes effective from the date of registration.
      </p>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">For Existing Regular Taxpayers</h3>

      <p className="text-gray-700 leading-relaxed mb-4">
        If you are already registered as a regular taxpayer and want to switch to the composition scheme, follow these steps:
      </p>

      <ol className="list-decimal pl-6 text-gray-700 space-y-2 mb-6">
        <li><strong>File GST CMP-02</strong> (intimation for composition levy) on the GST portal before <strong>31 March</strong> of the year preceding the year from which you want to opt for composition</li>
        <li>The scheme becomes effective from <strong>1 April</strong> of the next financial year</li>
        <li>You must have filed all pending returns (GSTR-1, GSTR-3B) before opting</li>
        <li>File <strong>ITC-03</strong> within 60 days of opting in — this reverses all ITC on closing stock, semi-finished goods, finished goods, and capital goods</li>
        <li>Start issuing <strong>bills of supply</strong> instead of tax invoices from the effective date</li>
      </ol>

      <div className="bg-blue-50 border-l-4 border-blue-500 p-4 rounded mb-6">
        <p className="text-blue-900 font-medium">Online Process on GST Portal</p>
        <p className="text-blue-800 text-sm mt-1">Log in to gst.gov.in &rarr; Services &rarr; Registration &rarr; Application for Composition Levy (GST CMP-02). Fill in the form, declare your stock details, and submit with DSC or EVC. You will receive an acknowledgement, and the composition option will reflect on your registration certificate from the next financial year.</p>
      </div>

      {/* Section 6 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">How to Switch from Composition to Regular Scheme</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        You may need to switch from composition to the regular scheme if you cross the turnover limit, start making inter-state sales, or want to sell through e-commerce. Here is the process:
      </p>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">Voluntary Withdrawal</h3>

      <ol className="list-decimal pl-6 text-gray-700 space-y-2 mb-6">
        <li>File <strong>GST CMP-04</strong> (intimation for withdrawal from composition levy) on the GST portal</li>
        <li>The withdrawal is effective from the date of filing CMP-04 or the date of the contravention, whichever is earlier</li>
        <li>File <strong>ITC-01</strong> within 30 days of the withdrawal — this allows you to claim ITC on closing stock, semi-finished goods, finished goods, and capital goods</li>
        <li>Start issuing <strong>tax invoices</strong> and filing <strong>GSTR-1 and GSTR-3B</strong> from the effective date</li>
      </ol>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">Mandatory Withdrawal (Contravention)</h3>

      <p className="text-gray-700 leading-relaxed mb-4">
        You must mandatorily switch to the regular scheme if:
      </p>

      <ul className="list-disc pl-6 text-gray-700 space-y-2 mb-6">
        <li>Your turnover exceeds the threshold (₹1.5 crore / ₹75 lakh / ₹50 lakh)</li>
        <li>You start making inter-state supplies</li>
        <li>You begin supplying goods through e-commerce operators</li>
        <li>You start manufacturing ice cream, pan masala, or tobacco products</li>
      </ul>

      <p className="text-gray-700 leading-relaxed mb-4">
        In case of contravention, you must file CMP-04 within 7 days of the date of contravention. The regular scheme applies from the date of contravention, not from the next quarter or year.
      </p>

      {/* Section 7 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">Returns Under the Composition Scheme</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        Composition dealers have a simplified return filing requirement compared to the regular scheme. Instead of monthly GSTR-1 and GSTR-3B, they file quarterly CMP-08 and annual GSTR-4.
      </p>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">CMP-08: Quarterly Statement-cum-Challan</h3>

      <p className="text-gray-700 leading-relaxed mb-4">
        CMP-08 is a self-assessed statement-cum-challan that composition dealers file every quarter. It is a simple form where you declare your total turnover for the quarter and pay the applicable tax. The due date is the <strong>18th of the month following the quarter</strong>.
      </p>

      <div className="overflow-x-auto mb-6">
        <table className="w-full border-collapse border border-gray-300 text-sm">
          <thead>
            <tr className="bg-gray-100">
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Quarter (FY 2026-27)</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Period</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">CMP-08 Due Date</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="border border-gray-300 px-4 py-2">Q1</td>
              <td className="border border-gray-300 px-4 py-2">April - June 2026</td>
              <td className="border border-gray-300 px-4 py-2">18 July 2026</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-2">Q2</td>
              <td className="border border-gray-300 px-4 py-2">July - September 2026</td>
              <td className="border border-gray-300 px-4 py-2">18 October 2026</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-2">Q3</td>
              <td className="border border-gray-300 px-4 py-2">October - December 2026</td>
              <td className="border border-gray-300 px-4 py-2">18 January 2027</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-2">Q4</td>
              <td className="border border-gray-300 px-4 py-2">January - March 2027</td>
              <td className="border border-gray-300 px-4 py-2">18 April 2027</td>
            </tr>
          </tbody>
        </table>
      </div>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">How to File CMP-08</h3>

      <ol className="list-decimal pl-6 text-gray-700 space-y-2 mb-6">
        <li>Log in to the GST portal (gst.gov.in)</li>
        <li>Go to <strong>Services &rarr; Returns &rarr; Returns Dashboard</strong></li>
        <li>Select the financial year and the quarter</li>
        <li>Click on <strong>CMP-08</strong> tile</li>
        <li>Enter the total outward supplies (taxable, exempt, nil-rated, and non-GST)</li>
        <li>Enter inward supplies liable to reverse charge</li>
        <li>The system calculates the tax payable automatically</li>
        <li>Create a challan and make the payment</li>
        <li>File using DSC or EVC</li>
      </ol>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">GSTR-4: Annual Return for Composition Dealers</h3>

      <p className="text-gray-700 leading-relaxed mb-4">
        GSTR-4 is the annual return that composition dealers must file. It contains a consolidated summary of all supplies made and received during the entire financial year. The due date for GSTR-4 is <strong>30 April of the following financial year</strong> (GSTR-4 for FY 2026-27 is due on 30 April 2028).
      </p>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">How to File GSTR-4</h3>

      <ol className="list-decimal pl-6 text-gray-700 space-y-2 mb-6">
        <li>Log in and navigate to <strong>Services &rarr; Returns &rarr; Annual Return</strong></li>
        <li>Select the financial year and click on <strong>GSTR-4</strong></li>
        <li>Fill in the details:
          <ul className="list-disc pl-6 mt-2 space-y-1">
            <li><strong>Table 4:</strong> Inward supplies from registered persons (auto-populated from sellers&apos; GSTR-1)</li>
            <li><strong>Table 5:</strong> Inward supplies from unregistered persons</li>
            <li><strong>Table 6:</strong> Summary of self-assessed tax in CMP-08 filed during the year</li>
            <li><strong>Table 7:</strong> Amendment to inward supplies from previous years</li>
            <li><strong>Table 8:</strong> Outward supplies during the year (taxable, exempt, nil-rated)</li>
            <li><strong>Table 9:</strong> Tax payable and paid</li>
            <li><strong>Table 10:</strong> TDS/TCS credit received</li>
          </ul>
        </li>
        <li>Verify the auto-populated data against your records</li>
        <li>Pay any differential tax if the annual figure differs from quarterly payments</li>
        <li>File with DSC or EVC</li>
      </ol>

      <p className="text-gray-700 leading-relaxed mb-4">
        For detailed guidance on GST return filing processes, see our <Link href="/blog/gst-return-filing-guide-2026-27" className="text-blue-600 hover:text-blue-700 underline">GST Return Filing Guide</Link>.
      </p>

      {/* Section 8 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">Bill of Supply Under Composition Scheme</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        Composition dealers must issue a <strong>Bill of Supply</strong> instead of a tax invoice. Since they cannot collect GST from customers, a bill of supply does not contain any tax breakup (no CGST, SGST, or IGST columns). For detailed invoice format requirements, see our <Link href="/blog/gst-invoice-format-guide" className="text-blue-600 hover:text-blue-700 underline">GST Invoice Format Guide</Link>.
      </p>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">Mandatory Declaration</h3>

      <p className="text-gray-700 leading-relaxed mb-4">
        Every bill of supply issued by a composition dealer must prominently display the following declaration at the top:
      </p>

      <div className="bg-gray-100 border border-gray-300 p-4 rounded mb-6 text-center">
        <p className="font-bold text-gray-800 italic">&quot;Composition taxable person, not eligible to collect tax on supplies&quot;</p>
      </div>

      <p className="text-gray-700 leading-relaxed mb-4">
        This informs the buyer that no GST is being charged and they cannot claim ITC on this purchase. The bill of supply must contain: supplier&apos;s name, address, and GSTIN; serial number; date; recipient&apos;s details (if value exceeds ₹50,000); description of goods/services; value of supply; and the supplier&apos;s signature.
      </p>

      <p className="text-gray-700 leading-relaxed mb-4">
        <Link href="/blog/gst-hsn-code-list" className="text-blue-600 hover:text-blue-700 underline">HSN codes</Link> are not mandatory on bills of supply for composition dealers with turnover up to ₹1.5 crore.
      </p>

      {/* Section 9 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">Restrictions and Limitations of the Composition Scheme</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        While the composition scheme simplifies compliance, it comes with significant restrictions that you must understand before opting in:
      </p>

      <div className="space-y-4 mb-6">
        <div className="bg-white border rounded-lg p-4">
          <h4 className="font-semibold text-gray-900 mb-2">1. Cannot Collect GST from Customers</h4>
          <p className="text-gray-700 text-sm">You cannot mention GST on your bill of supply or charge GST separately to your customers. The composition tax comes out of your revenue. This means your selling price must absorb the 1% / 5% / 6% tax.</p>
        </div>
        <div className="bg-white border rounded-lg p-4">
          <h4 className="font-semibold text-gray-900 mb-2">2. Cannot Claim Input Tax Credit</h4>
          <p className="text-gray-700 text-sm">All GST paid on your purchases (raw materials, stock, services, capital goods) is a cost to your business. You cannot offset it against your tax liability. This is the biggest hidden cost of the composition scheme.</p>
        </div>
        <div className="bg-white border rounded-lg p-4">
          <h4 className="font-semibold text-gray-900 mb-2">3. No Inter-state Supplies</h4>
          <p className="text-gray-700 text-sm">You can only sell within your state. If a customer from another state wants to buy from you, you cannot fulfil that order as a composition dealer. This limits your market to intra-state transactions only.</p>
        </div>
        <div className="bg-white border rounded-lg p-4">
          <h4 className="font-semibold text-gray-900 mb-2">4. No E-commerce Sales</h4>
          <p className="text-gray-700 text-sm">You cannot supply goods through e-commerce platforms like Amazon, Flipkart, or Meesho. This is a significant limitation in today&apos;s digital marketplace. If you want to sell online, you must be under the regular scheme.</p>
        </div>
        <div className="bg-white border rounded-lg p-4">
          <h4 className="font-semibold text-gray-900 mb-2">5. Buyers Cannot Claim ITC</h4>
          <p className="text-gray-700 text-sm">Since you issue a bill of supply (not a tax invoice), your B2B customers cannot claim <Link href="/blog/input-tax-credit-itc-rules-2026-27" className="text-blue-600 underline">ITC</Link> on purchases from you. This can make you uncompetitive for B2B sales where buyers prefer vendors who can provide tax invoices.</p>
        </div>
        <div className="bg-white border rounded-lg p-4">
          <h4 className="font-semibold text-gray-900 mb-2">6. Reverse Charge Still Applies</h4>
          <p className="text-gray-700 text-sm">Composition dealers must still pay GST under the reverse charge mechanism on applicable supplies (e.g., purchases from unregistered dealers above threshold, import of services, legal services, GTA services). This tax is paid in cash and cannot be claimed as ITC.</p>
        </div>
        <div className="bg-white border rounded-lg p-4">
          <h4 className="font-semibold text-gray-900 mb-2">7. Prohibited Goods</h4>
          <p className="text-gray-700 text-sm">Manufacturers of ice cream (whether or not containing cocoa), pan masala, and all tobacco products are specifically excluded from the composition scheme regardless of their turnover.</p>
        </div>
      </div>

      {/* Section 10 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">Practical Examples and Calculations</h2>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">Example 1: Kirana Store (Trader)</h3>

      <p className="text-gray-700 leading-relaxed mb-4">
        Rajesh runs a grocery store in Pune with annual sales of ₹1 crore. Most of his purchases (₹80 lakh) are from registered wholesalers at 5% and 12% GST.
      </p>

      <div className="overflow-x-auto mb-6">
        <table className="w-full border-collapse border border-gray-300 text-sm">
          <thead>
            <tr className="bg-gray-100">
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Particulars</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Composition</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Regular</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="border border-gray-300 px-4 py-2">Turnover</td>
              <td className="border border-gray-300 px-4 py-2">₹1,00,00,000</td>
              <td className="border border-gray-300 px-4 py-2">₹1,00,00,000</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-2">GST on Purchases (avg ~7%)</td>
              <td className="border border-gray-300 px-4 py-2">₹5,60,000 (sunk cost)</td>
              <td className="border border-gray-300 px-4 py-2">₹5,60,000 (claimed as ITC)</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-2">Output Tax (avg ~7%)</td>
              <td className="border border-gray-300 px-4 py-2">N/A</td>
              <td className="border border-gray-300 px-4 py-2">₹7,00,000</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-2">Composition Tax (1%)</td>
              <td className="border border-gray-300 px-4 py-2">₹1,00,000</td>
              <td className="border border-gray-300 px-4 py-2">N/A</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-2 font-bold">Total GST Cost</td>
              <td className="border border-gray-300 px-4 py-2 font-bold">₹6,60,000</td>
              <td className="border border-gray-300 px-4 py-2 font-bold">₹1,40,000</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-2 font-bold">Returns per Year</td>
              <td className="border border-gray-300 px-4 py-2 font-bold text-green-700">5</td>
              <td className="border border-gray-300 px-4 py-2 font-bold">~25</td>
            </tr>
          </tbody>
        </table>
      </div>

      <p className="text-gray-700 leading-relaxed mb-4">
        <strong>Verdict:</strong> For Rajesh, the regular scheme saves ₹5,20,000 per year in total GST cost. However, the composition scheme saves him from hiring an accountant for monthly return filing. If his accountant costs ₹2-3 lakh/year, composition is still costlier. The composition scheme works better for businesses with very few registered purchases (where ITC benefit is minimal anyway).
      </p>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">Example 2: Small Manufacturer</h3>

      <p className="text-gray-700 leading-relaxed mb-4">
        Priya manufactures handmade soaps in Jaipur with ₹80 lakh annual sales. Her raw material purchases are ₹30 lakh (from registered suppliers at 18% GST), and she sells at 18% GST.
      </p>

      <div className="overflow-x-auto mb-6">
        <table className="w-full border-collapse border border-gray-300 text-sm">
          <thead>
            <tr className="bg-gray-100">
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Particulars</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Composition</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Regular</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="border border-gray-300 px-4 py-2">GST on Raw Materials (ITC)</td>
              <td className="border border-gray-300 px-4 py-2">₹5,40,000 (sunk cost)</td>
              <td className="border border-gray-300 px-4 py-2">₹5,40,000 (claimed)</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-2">Output Tax / Composition Tax</td>
              <td className="border border-gray-300 px-4 py-2">₹80,000 (1%)</td>
              <td className="border border-gray-300 px-4 py-2">₹14,40,000 (18%)</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-2 font-bold">Total GST Cost</td>
              <td className="border border-gray-300 px-4 py-2 font-bold">₹6,20,000</td>
              <td className="border border-gray-300 px-4 py-2 font-bold">₹9,00,000</td>
            </tr>
          </tbody>
        </table>
      </div>

      <p className="text-gray-700 leading-relaxed mb-4">
        <strong>Verdict:</strong> For Priya, composition saves ₹2,80,000 per year because her purchase-to-sale ratio is low (high value addition). Manufacturers with high margins benefit most from the composition scheme.
      </p>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">Example 3: Restaurant</h3>

      <p className="text-gray-700 leading-relaxed mb-4">
        Vikram runs a small restaurant in Chennai with ₹40 lakh annual turnover. Food purchases are ₹16 lakh (from registered suppliers at 5% GST).
      </p>

      <div className="overflow-x-auto mb-6">
        <table className="w-full border-collapse border border-gray-300 text-sm">
          <thead>
            <tr className="bg-gray-100">
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Particulars</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Composition (5%)</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Regular (5% without ITC)</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="border border-gray-300 px-4 py-2">GST on Food Purchases</td>
              <td className="border border-gray-300 px-4 py-2">₹80,000 (sunk cost)</td>
              <td className="border border-gray-300 px-4 py-2">₹80,000 (no ITC for restaurants at 5%)</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-2">Tax on Sales</td>
              <td className="border border-gray-300 px-4 py-2">₹2,00,000 (5% on turnover)</td>
              <td className="border border-gray-300 px-4 py-2">₹2,00,000 (5% on sales)</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-2 font-bold">Total Cost</td>
              <td className="border border-gray-300 px-4 py-2 font-bold">₹2,80,000</td>
              <td className="border border-gray-300 px-4 py-2 font-bold">₹2,80,000</td>
            </tr>
          </tbody>
        </table>
      </div>

      <p className="text-gray-700 leading-relaxed mb-4">
        <strong>Verdict:</strong> For restaurants, the tax cost is similar since restaurants under the regular scheme at 5% also do not get ITC. The composition scheme wins on compliance simplicity — 5 returns vs 25+ returns per year.
      </p>

      {/* Section 11 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">Penalties Under the Composition Scheme</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        Composition dealers face the following penalties for non-compliance:
      </p>

      <div className="overflow-x-auto mb-6">
        <table className="w-full border-collapse border border-gray-300 text-sm">
          <thead>
            <tr className="bg-gray-100">
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Offence</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Penalty</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="border border-gray-300 px-4 py-2">Wrongly opting for composition (ineligible person)</td>
              <td className="border border-gray-300 px-4 py-2">₹10,000 or tax due, whichever is higher + tax with interest</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-2">Late filing of CMP-08</td>
              <td className="border border-gray-300 px-4 py-2">₹50/day (₹25 CGST + ₹25 SGST), max ₹10,000</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-2">Late filing of GSTR-4</td>
              <td className="border border-gray-300 px-4 py-2">₹200/day (₹100 CGST + ₹100 SGST), max 0.5% of turnover</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-2">Issuing tax invoice instead of bill of supply</td>
              <td className="border border-gray-300 px-4 py-2">₹10,000 or tax amount involved, whichever is higher</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-2">Collecting GST from customers</td>
              <td className="border border-gray-300 px-4 py-2">₹10,000 or tax amount collected, whichever is higher + must deposit collected amount</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-2">Making inter-state supply</td>
              <td className="border border-gray-300 px-4 py-2">Automatic withdrawal from composition + tax with interest on the transaction</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-2">Not displaying &quot;composition taxable person&quot; on bill</td>
              <td className="border border-gray-300 px-4 py-2">₹10,000 per instance</td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* Section 12 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">How GSTIndia Tools Can Help</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        Whether you are a composition dealer or thinking of opting in, the <Link href="/" className="text-blue-600 hover:text-blue-700 underline">GSTIndia platform</Link> by DoAide offers free tools to simplify your GST compliance:
      </p>

      <ul className="list-disc pl-6 text-gray-700 space-y-2 mb-6">
        <li><strong><Link href="/" className="text-blue-600 underline">GST Calculator:</Link></strong> Calculate your composition tax liability instantly — enter your turnover and get the exact CGST and SGST amounts</li>
        <li><strong><Link href="/" className="text-blue-600 underline">GSTIN Validator:</Link></strong> Verify whether your suppliers are registered (and whether they are composition or regular dealers) before making purchases</li>
        <li><strong><Link href="/" className="text-blue-600 underline">HSN Code Finder:</Link></strong> While HSN is not mandatory for composition dealers, knowing your <Link href="/blog/gst-hsn-code-list" className="text-blue-600 underline">HSN codes</Link> helps if you switch to the regular scheme</li>
      </ul>

      <div className="bg-gradient-to-r from-blue-600 to-blue-700 rounded-xl p-6 text-white mb-8">
        <h3 className="text-xl font-bold mb-2">Simplify Your Composition Scheme Compliance</h3>
        <p className="text-blue-100 mb-4">Use GSTIndia&apos;s free tools to calculate composition tax, verify GSTINs, and stay compliant — whether you are a kirana store, manufacturer, or restaurant.</p>
        <Link href="/" className="inline-block bg-white text-blue-600 font-semibold px-6 py-2 rounded-lg hover:bg-blue-50 transition-colors">
          Try Free GST Tools &rarr;
        </Link>
      </div>

      {/* FAQ Section */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-6">Frequently Asked Questions (FAQ)</h2>

      <div className="space-y-4 mb-8">
        {[
          {
            q: 'What is the turnover limit for GST composition scheme?',
            a: 'The turnover limit is ₹1.5 crore for manufacturers and traders (₹75 lakh for special category states like NE states and Uttarakhand). For service providers under Notification 2/2019, the limit is ₹50 lakh. The turnover is the aggregate turnover in the preceding financial year.',
          },
          {
            q: 'Can a service provider opt for the composition scheme?',
            a: 'Yes, since April 2019, service providers with aggregate turnover up to ₹50 lakh can opt for composition under Notification 2/2019-CT(Rate). They pay GST at 6% (3% CGST + 3% SGST) on turnover. Restaurants (not serving alcohol) were always eligible and pay 5%. Other service providers above ₹50 lakh turnover cannot opt for composition.',
          },
          {
            q: 'Can a composition dealer make inter-state sales?',
            a: 'No, composition dealers cannot make inter-state outward supplies of goods. This means they can only sell within their state. If they make any inter-state supply, they are automatically disqualified from the composition scheme and must switch to the regular scheme.',
          },
          {
            q: 'What returns does a composition dealer file?',
            a: 'Composition dealers file CMP-08 (statement-cum-challan) quarterly — due on the 18th of the month following each quarter. They also file GSTR-4 (annual return) once a year — due on 30 April of the next financial year. Total 5 returns per year, compared to 12-25 for regular dealers.',
          },
          {
            q: 'Can a composition dealer claim Input Tax Credit?',
            a: 'No, composition dealers cannot claim ITC on any purchases — whether goods, services, or capital goods. All GST paid on purchases is a sunk cost. This is one of the biggest trade-offs of the composition scheme. However, if you switch to the regular scheme, you can claim ITC on closing stock by filing ITC-01.',
          },
          {
            q: 'How to switch from composition to regular scheme?',
            a: 'File GST CMP-04 on the GST portal to intimate withdrawal from the composition scheme. Then file ITC-01 within 30 days to claim ITC on closing stock. Start issuing tax invoices and filing GSTR-1 and GSTR-3B from the effective date. You can switch voluntarily at any time, or must switch mandatorily if you cross the turnover limit.',
          },
          {
            q: 'What is the tax rate under composition scheme?',
            a: 'Manufacturers and traders pay 1% (0.5% CGST + 0.5% SGST) on total turnover. Restaurants (not serving alcohol) pay 5% (2.5% CGST + 2.5% SGST). Service providers under Notification 2/2019 pay 6% (3% CGST + 3% SGST). No IGST applies since inter-state supply is not allowed.',
          },
          {
            q: 'Can a composition dealer supply through e-commerce?',
            a: 'No, composition dealers cannot supply goods or services through e-commerce operators like Amazon, Flipkart, Swiggy, or Zomato. If you want to sell through e-commerce platforms, you must be registered under the regular scheme. This is a significant limitation for businesses looking to expand online.',
          },
          {
            q: 'Can a composition dealer issue a tax invoice?',
            a: 'No, composition dealers must issue a "Bill of Supply" instead of a tax invoice. The bill must display "Composition taxable person, not eligible to collect tax on supplies". Issuing a tax invoice or collecting GST from customers attracts a penalty of ₹10,000 or the tax amount, whichever is higher.',
          },
          {
            q: 'Is the composition scheme beneficial for my business?',
            a: 'It depends on your business type, profit margin, and customer profile. Composition is beneficial when: (1) your customers are mostly end consumers (not businesses needing ITC), (2) your purchases are mostly from unregistered suppliers (no ITC anyway), (3) you value simplicity over tax savings. Use the GSTIndia GST Calculator to compare your costs under both schemes.',
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
        The GST Composition Scheme is a valuable option for small businesses that prioritize simplicity over tax optimization. With flat rates of 1% to 6% on turnover and only 5 returns per year, it removes the complexity of monthly compliance, ITC reconciliation, and invoice-level reporting. However, the inability to claim ITC, collect GST, make inter-state sales, or sell through e-commerce makes it unsuitable for businesses with growth ambitions or significant B2B sales.
      </p>

      <p className="text-gray-700 leading-relaxed mb-4">
        Before opting for the composition scheme, carefully evaluate your business model using the practical examples above. Consider your purchase patterns, customer profile, and growth plans. Use the <Link href="/" className="text-blue-600 hover:text-blue-700 underline">GSTIndia tools</Link> to calculate your tax under both schemes and make an informed decision. If you need to register for GST first, see our <Link href="/blog/gst-registration-online-guide" className="text-blue-600 hover:text-blue-700 underline">GST Registration Guide</Link>. For understanding ITC rules that apply to the regular scheme, read our <Link href="/blog/input-tax-credit-itc-rules-2026-27" className="text-blue-600 hover:text-blue-700 underline">ITC Rules Guide</Link>.
      </p>

      {/* JSON-LD Structured Data */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            '@context': 'https://schema.org',
            '@type': 'Article',
            headline: 'GST Composition Scheme 2026: Eligibility, Tax Rates & Filing Guide',
            description: 'Complete guide to GST Composition Scheme — eligibility, tax rates, GSTR-4 filing, benefits vs regular scheme. Updated for 2026-27 with practical examples.',
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
            url: 'https://gst.doaide.com/blog/gst-composition-scheme-guide',
            mainEntityOfPage: 'https://gst.doaide.com/blog/gst-composition-scheme-guide',
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
                name: 'What is the turnover limit for GST composition scheme?',
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: '₹1.5 crore for manufacturers and traders (₹75 lakh for special category states). ₹50 lakh for service providers under Notification 2/2019.',
                },
              },
              {
                '@type': 'Question',
                name: 'Can a service provider opt for the composition scheme?',
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: 'Yes, since April 2019, service providers with turnover up to ₹50 lakh can opt for composition at 6% rate. Restaurants (not serving alcohol) pay 5%.',
                },
              },
              {
                '@type': 'Question',
                name: 'Can a composition dealer make inter-state sales?',
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: 'No, composition dealers cannot make inter-state outward supplies. They can only sell within their state.',
                },
              },
              {
                '@type': 'Question',
                name: 'What returns does a composition dealer file?',
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: 'CMP-08 quarterly (due 18th of month after quarter) and GSTR-4 annually (due 30 April). Total 5 returns per year.',
                },
              },
              {
                '@type': 'Question',
                name: 'Can a composition dealer claim Input Tax Credit?',
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: 'No, composition dealers cannot claim ITC on any purchases. All GST paid on purchases is a sunk cost.',
                },
              },
              {
                '@type': 'Question',
                name: 'How to switch from composition to regular scheme?',
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: 'File GST CMP-04 for withdrawal, then ITC-01 within 30 days to claim ITC on closing stock. Start filing GSTR-1 and GSTR-3B.',
                },
              },
              {
                '@type': 'Question',
                name: 'What is the tax rate under composition scheme?',
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: 'Manufacturers and traders: 1%. Restaurants: 5%. Service providers (Notification 2/2019): 6%. All rates are on total turnover.',
                },
              },
              {
                '@type': 'Question',
                name: 'Can a composition dealer supply through e-commerce?',
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: 'No, composition dealers cannot supply through e-commerce platforms like Amazon, Flipkart, Swiggy, or Zomato.',
                },
              },
              {
                '@type': 'Question',
                name: 'Can a composition dealer issue a tax invoice?',
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: 'No, they must issue a Bill of Supply with the declaration "Composition taxable person, not eligible to collect tax on supplies". Issuing a tax invoice attracts penalty.',
                },
              },
              {
                '@type': 'Question',
                name: 'Is the composition scheme beneficial for my business?',
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: 'It depends on customer profile, purchase patterns, and profit margins. Best for B2C businesses with end consumers, purchases from unregistered suppliers, and those valuing simplicity.',
                },
              },
            ],
          }),
        }}
      />
      <div className="mt-8 pt-8 border-t dark:border-gray-800">
        <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">Found this guide helpful? Share it:</p>
        <ShareButtons
          title="GST Composition Scheme 2026: Eligibility, Tax Rates & Filing Guide"
          url="/blog/gst-composition-scheme-guide"
        />
      </div>
    </article>
  );
}
