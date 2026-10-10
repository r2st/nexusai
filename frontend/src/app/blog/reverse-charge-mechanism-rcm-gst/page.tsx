import type { Metadata } from 'next';
import Link from 'next/link';
import { ShareButtons } from '@/components/blog/share-buttons';

export const metadata: Metadata = {
  title: 'Reverse Charge Mechanism (RCM) Under GST — Guide',
  description: 'Complete guide to Reverse Charge Mechanism (RCM) under GST. What is RCM, when it applies, list of goods & services under RCM, ITC rules & compliance.',
  openGraph: {
    title: 'Reverse Charge Mechanism (RCM) Under GST — Complete Guide',
    description: 'Complete guide to Reverse Charge Mechanism under GST. When RCM applies, list of goods & services, ITC rules and compliance.',
    url: 'https://gst.doaide.com/blog/reverse-charge-mechanism-rcm-gst',
    type: 'article',
  },
  alternates: {
    canonical: 'https://gst.doaide.com/blog/reverse-charge-mechanism-rcm-gst',
  },
};

export default function ReverseChargeMechanismGuide() {
  return (
    <article className="max-w-4xl mx-auto px-4 py-12">
      <div className="mb-8">
        <span className="text-sm font-semibold text-blue-600 bg-blue-50 px-3 py-1 rounded-full">RCM / Tax</span>
        <span className="text-sm text-gray-500 ml-3">Updated: 10 October 2026</span>
        <span className="text-sm text-gray-500 ml-3">16 min read</span>
      </div>

      <h1 className="text-3xl sm:text-4xl font-bold text-gray-900 dark:text-gray-100 mb-6">
        Reverse Charge Mechanism (RCM) Under GST: Complete Guide with List of Goods &amp; Services
      </h1>

      <ShareButtons
        title="Reverse Charge Mechanism (RCM) Under GST — Complete Guide"
        url="/blog/reverse-charge-mechanism-rcm-gst"
        className="mb-8"
      />

      <p className="text-lg text-gray-600 dark:text-gray-400 mb-8 leading-relaxed">
        Under the normal GST mechanism, the supplier of goods or services collects and pays the tax to the government. However, under the <strong>Reverse Charge Mechanism (RCM)</strong>, the liability to pay GST shifts from the supplier to the recipient of the goods or services. This guide explains what RCM is, when it applies, the complete list of goods and services covered under RCM, how to claim Input Tax Credit on RCM payments, and the compliance requirements involved.
      </p>

      <div className="bg-blue-50 border-l-4 border-blue-500 p-4 rounded mb-8">
        <p className="text-blue-900 font-medium">Quick Navigation</p>
        <ul className="text-blue-800 text-sm mt-2 space-y-1">
          <li>&bull; What is Reverse Charge Mechanism?</li>
          <li>&bull; When Does RCM Apply?</li>
          <li>&bull; Section 9(3) &mdash; Notified Goods &amp; Services</li>
          <li>&bull; Section 9(4) &mdash; Supply from Unregistered Person</li>
          <li>&bull; Complete List of Services Under RCM</li>
          <li>&bull; Complete List of Goods Under RCM</li>
          <li>&bull; ITC on RCM Payments</li>
          <li>&bull; How to Report RCM in GST Returns</li>
          <li>&bull; RCM on Import of Services</li>
          <li>&bull; Common Mistakes &amp; Compliance Tips</li>
          <li>&bull; FAQs</li>
        </ul>
      </div>

      {/* Section 1 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">What is Reverse Charge Mechanism (RCM)?</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        In a normal GST transaction, the <strong>supplier</strong> collects GST from the buyer and pays it to the government. Under the Reverse Charge Mechanism, this responsibility is reversed &mdash; the <strong>recipient</strong> (buyer) of the goods or services is liable to pay the GST directly to the government instead of the supplier. The supplier, in this case, either does not charge GST on the invoice or charges it with a note that tax is payable under reverse charge.
      </p>

      <p className="text-gray-700 leading-relaxed mb-4">
        RCM is governed by <strong>Section 9(3) and Section 9(4)</strong> of the CGST Act, 2017 (and corresponding sections in SGST/UTGST/IGST Acts):
      </p>

      <ul className="list-disc pl-6 text-gray-700 space-y-2 mb-6">
        <li><strong>Section 9(3):</strong> The government can notify specific categories of goods or services where RCM applies. In these cases, irrespective of whether the supplier is registered or unregistered, the recipient must pay GST under RCM.</li>
        <li><strong>Section 9(4):</strong> When a registered person receives goods or services from an <strong>unregistered supplier</strong>, and the supply falls under a notified category, the registered recipient must pay GST under RCM.</li>
      </ul>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">Why Does RCM Exist?</h3>

      <p className="text-gray-700 leading-relaxed mb-4">
        The reverse charge mechanism serves several purposes in the GST framework:
      </p>

      <ul className="list-disc pl-6 text-gray-700 space-y-2 mb-6">
        <li><strong>Widening the tax base:</strong> It brings unregistered and informal sector suppliers into the tax net indirectly</li>
        <li><strong>Ensuring tax compliance:</strong> For services like legal, sponsorship, or transport where the supplier may be small or unorganised, RCM ensures the government receives the tax</li>
        <li><strong>Import taxation:</strong> All imports of services are taxed under RCM because the foreign supplier is not registered under Indian GST</li>
        <li><strong>Reducing evasion:</strong> When the recipient pays the tax, it reduces the scope for the supplier to evade tax</li>
      </ul>

      {/* Section 2 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">When Does RCM Apply?</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        RCM applies in three broad scenarios:
      </p>

      <div className="overflow-x-auto mb-6">
        <table className="w-full border-collapse border border-gray-300 text-sm">
          <thead>
            <tr className="bg-gray-100">
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Scenario</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Legal Basis</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Example</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="border border-gray-300 px-4 py-3 font-medium">Notified goods/services from any supplier</td>
              <td className="border border-gray-300 px-4 py-3">Section 9(3)</td>
              <td className="border border-gray-300 px-4 py-3">A company hires a lawyer &mdash; legal fees are under RCM regardless of whether the lawyer is registered</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-3 font-medium">Supply from an unregistered person (notified categories)</td>
              <td className="border border-gray-300 px-4 py-3">Section 9(4)</td>
              <td className="border border-gray-300 px-4 py-3">A registered dealer buys raw cashew nuts from an unregistered farmer</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-3 font-medium">Import of services</td>
              <td className="border border-gray-300 px-4 py-3">Section 5(3) IGST Act</td>
              <td className="border border-gray-300 px-4 py-3">An Indian company uses cloud hosting from a US-based provider &mdash; IGST payable under RCM</td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* Section 3 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">Complete List of Services Under RCM (Section 9(3))</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        The following services are notified under Section 9(3) where the recipient must pay GST under reverse charge. This list is based on Notification No. 13/2017-CT(Rate) as amended:
      </p>

      <div className="overflow-x-auto mb-6">
        <table className="w-full border-collapse border border-gray-300 text-sm">
          <thead>
            <tr className="bg-gray-100">
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">S.No.</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Service Description</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Supplier</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Recipient (Pays GST)</th>
            </tr>
          </thead>
          <tbody>
            {[
              ['1', 'Services by an insurance agent to an insurance company', 'Insurance agent', 'Insurance company'],
              ['2', 'Services by a recovery agent to a banking company or financial institution', 'Recovery agent', 'Banking company / NBFC'],
              ['3', 'Services by a director of a company (not being salary)', 'Director (individual)', 'Company or body corporate'],
              ['4', 'Services by an author, music composer, photographer, or artist to a publisher, music company, or producer', 'Author / artist (individual)', 'Publisher / music company / producer'],
              ['5', 'Services by members of overseeing committee to RBI', 'Committee members', 'RBI'],
              ['6', 'Supply of services by any individual advocate (including senior advocate) to any business entity', 'Individual advocate', 'Business entity (registered)'],
              ['7', 'Services by an arbitral tribunal to a business entity', 'Arbitral tribunal', 'Business entity'],
              ['8', 'Sponsorship services to any body corporate or partnership firm', 'Any person', 'Body corporate / firm receiving sponsorship'],
              ['9', 'Services by the Central Government, State Government, UT, or local authority (excluding specified services)', 'Government / local authority', 'Business entity'],
              ['10', 'Services by a goods transport agency (GTA) in respect of transportation of goods by road — where GTA has not opted to pay tax forward charge', 'GTA (unregistered or not opting forward charge)', 'Factory, company, registered person, cooperative, society, body corporate, partnership, casual taxable person'],
              ['11', 'Services by way of renting of residential dwelling to a registered person', 'Any person (landlord)', 'Registered person (tenant)'],
              ['12', 'Services by way of renting of a motor vehicle to a body corporate where the cost of fuel is included in the consideration', 'Any person providing vehicle rental', 'Body corporate'],
              ['13', 'Security services (supply of security personnel) by any person other than a body corporate to a registered person', 'Individual / partnership firm providing security guards', 'Registered person'],
              ['14', 'Services by way of supply of manpower for any purpose (including security) by any individual to a body corporate', 'Individual', 'Body corporate'],
              ['15', 'Services of lending of securities under SEBI (SLBM) regulations', 'Lender', 'Borrower'],
              ['16', 'Corporate guarantee by a holding company to a subsidiary', 'Holding company', 'Subsidiary (or the bank/financial institution)'],
            ].map(([sno, service, supplier, recipient], i) => (
              <tr key={i} className={i % 2 === 1 ? 'bg-gray-50' : ''}>
                <td className="border border-gray-300 px-4 py-2">{sno}</td>
                <td className="border border-gray-300 px-4 py-2">{service}</td>
                <td className="border border-gray-300 px-4 py-2">{supplier}</td>
                <td className="border border-gray-300 px-4 py-2">{recipient}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Section 4 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">Complete List of Goods Under RCM (Section 9(3))</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        The following goods are notified under Section 9(3) where the recipient must pay GST under reverse charge. This list is based on Notification No. 4/2017-CT(Rate) as amended:
      </p>

      <div className="overflow-x-auto mb-6">
        <table className="w-full border-collapse border border-gray-300 text-sm">
          <thead>
            <tr className="bg-gray-100">
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">S.No.</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Goods Description</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Supplier</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Recipient (Pays GST)</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">GST Rate</th>
            </tr>
          </thead>
          <tbody>
            {[
              ['1', 'Cashew nuts (not shelled or peeled)', 'Agriculturist', 'Registered person', '5%'],
              ['2', 'Bidi wrapper leaves (tendu leaves)', 'Agriculturist', 'Registered person', '18%'],
              ['3', 'Tobacco leaves', 'Agriculturist', 'Registered person', '28%'],
              ['4', 'Silk yarn', 'Any person who manufactures silk yarn from raw silk or cocoons', 'Registered person', '5%'],
              ['5', 'Raw cotton', 'Agriculturist', 'Registered person', '5%'],
              ['6', 'Supply of lottery', 'State Government, UT, or local authority', 'Lottery distributor or selling agent', '28%'],
              ['7', 'Used vehicles, seized and confiscated goods, old and used goods, waste and scrap', 'Central/State Government', 'Registered person', 'Applicable rate'],
              ['8', 'Priority sector lending certificates', 'Any person', 'Registered person', '12%'],
              ['9', 'Metal scrap', 'Unregistered person', 'Registered person', '18%'],
            ].map(([sno, goods, supplier, recipient, rate], i) => (
              <tr key={i} className={i % 2 === 1 ? 'bg-gray-50' : ''}>
                <td className="border border-gray-300 px-4 py-2">{sno}</td>
                <td className="border border-gray-300 px-4 py-2">{goods}</td>
                <td className="border border-gray-300 px-4 py-2">{supplier}</td>
                <td className="border border-gray-300 px-4 py-2">{recipient}</td>
                <td className="border border-gray-300 px-4 py-2 font-medium">{rate}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="bg-blue-50 border-l-4 border-blue-500 p-4 rounded mb-6">
        <p className="text-blue-900 font-medium">Pro Tip</p>
        <p className="text-blue-800 text-sm mt-1">Use the <Link href="/" className="text-blue-600 underline">GSTIndia GST Calculator</Link> to compute the exact RCM tax liability on your purchases. Select the applicable rate and enter the invoice value to get the CGST/SGST/IGST breakup that you need to pay under reverse charge.</p>
      </div>

      {/* Section 5 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">Section 9(4) &mdash; Supply from Unregistered Person</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        Section 9(4) of the CGST Act provides that when specified categories of registered persons receive supply of specified goods or services from an unregistered supplier, the registered person must pay GST under reverse charge. The scope has been narrowed over the years:
      </p>

      <ul className="list-disc pl-6 text-gray-700 space-y-2 mb-6">
        <li><strong>Initially (July 2017):</strong> All purchases from unregistered dealers by registered persons were under RCM. This was suspended from 13 October 2017 due to implementation difficulties.</li>
        <li><strong>Current position:</strong> RCM under Section 9(4) now applies only to specified categories of registered persons receiving specified services from unregistered suppliers &mdash; primarily promoters/builders in the real estate sector for cement purchases from unregistered dealers, and certain other notified categories.</li>
        <li><strong>Metal scrap:</strong> From 2024, purchase of metal scrap from unregistered persons by registered persons is under RCM at 18%.</li>
      </ul>

      <div className="bg-yellow-50 border-l-4 border-yellow-500 p-4 rounded mb-6">
        <p className="text-yellow-900 font-medium">Important Note</p>
        <p className="text-yellow-800 text-sm mt-1">Unlike Section 9(3) RCM (which applies regardless of supplier registration), Section 9(4) RCM applies only when the supplier is unregistered. If the supplier obtains GST registration, RCM under 9(4) no longer applies and normal forward charge takes over.</p>
      </div>

      {/* Section 6 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">ITC on RCM Payments</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        One of the most important aspects of RCM is the treatment of Input Tax Credit. The GST paid under reverse charge can be claimed as ITC, subject to the following conditions:
      </p>

      <div className="overflow-x-auto mb-6">
        <table className="w-full border-collapse border border-gray-300 text-sm">
          <thead>
            <tr className="bg-gray-100">
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Condition</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Details</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="border border-gray-300 px-4 py-3 font-medium">Payment of tax</td>
              <td className="border border-gray-300 px-4 py-3">GST under RCM must be paid in cash only (through the Electronic Cash Ledger). ITC from the credit ledger cannot be used to pay RCM liability.</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-3 font-medium">ITC eligibility</td>
              <td className="border border-gray-300 px-4 py-3">Once the RCM tax is paid in cash, the same amount is available as ITC in the credit ledger (subject to normal ITC eligibility conditions under Section 16).</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-3 font-medium">Self-invoice</td>
              <td className="border border-gray-300 px-4 py-3">For purchases from unregistered persons under RCM, the recipient must issue a self-invoice (payment voucher) and report it in GSTR-1 and GSTR-3B.</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-3 font-medium">Time of ITC claim</td>
              <td className="border border-gray-300 px-4 py-3">ITC on RCM can be claimed in the same month the tax is paid. No need to wait for supplier&apos;s return filing.</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-3 font-medium">Blocked ITC exclusion</td>
              <td className="border border-gray-300 px-4 py-3">If the supply itself is blocked under Section 17(5) (e.g., food &amp; beverages, health club), ITC on RCM payment is also blocked.</td>
            </tr>
          </tbody>
        </table>
      </div>

      <p className="text-gray-700 leading-relaxed mb-4">
        For a detailed understanding of ITC eligibility, conditions, and reversal rules, refer to our comprehensive <Link href="/blog/input-tax-credit-itc-rules-2026-27" className="text-blue-600 hover:text-blue-700 underline">Input Tax Credit (ITC) Rules Guide</Link>.
      </p>

      {/* Section 7 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">How to Report RCM in GST Returns</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        RCM transactions must be reported in multiple places across your GST returns:
      </p>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">In GSTR-1 (Outward Supply Return)</h3>

      <ul className="list-disc pl-6 text-gray-700 space-y-2 mb-6">
        <li>Self-invoices issued for purchases from unregistered persons under RCM should not be reported in GSTR-1 (they are reported in GSTR-3B only)</li>
        <li>If you are the supplier of goods/services notified under RCM, you should still report the supply in GSTR-1 with the &quot;Reverse Charge&quot; flag set to &quot;Yes&quot;</li>
      </ul>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">In GSTR-3B (Summary Return)</h3>

      <ul className="list-disc pl-6 text-gray-700 space-y-2 mb-6">
        <li><strong>Table 3.1(d):</strong> Report the value of inward supplies on which tax is payable under reverse charge. This creates your RCM tax liability.</li>
        <li><strong>Table 4(A)(3):</strong> Claim the ITC on the RCM tax paid (inward supplies liable to reverse charge). This ITC goes into your credit ledger.</li>
        <li><strong>Table 6.1:</strong> The RCM liability must be paid through the Electronic Cash Ledger (not ITC).</li>
      </ul>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">In GSTR-9 (Annual Return)</h3>

      <ul className="list-disc pl-6 text-gray-700 space-y-2 mb-6">
        <li><strong>Table 5:</strong> All inward supplies on which tax is paid under reverse charge are reported here</li>
        <li><strong>Table 6:</strong> ITC availed on reverse charge supplies is reported separately</li>
      </ul>

      <p className="text-gray-700 leading-relaxed mb-4">
        For detailed return filing instructions, see our <Link href="/blog/gst-return-filing-guide-2026-27" className="text-blue-600 hover:text-blue-700 underline">GST Return Filing Guide</Link> and the <Link href="/blog/gst-annual-return-gstr-9-guide" className="text-blue-600 hover:text-blue-700 underline">GSTR-9 Annual Return Guide</Link>.
      </p>

      {/* Section 8 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">RCM on Import of Services</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        All imports of services are subject to GST under the reverse charge mechanism under Section 5(3) of the IGST Act. When an Indian business receives services from a supplier located outside India, the Indian recipient must pay IGST under reverse charge, provided:
      </p>

      <ul className="list-disc pl-6 text-gray-700 space-y-2 mb-6">
        <li>The supplier of the service is located outside India</li>
        <li>The recipient of the service is located in India</li>
        <li>The place of supply is in India</li>
      </ul>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">Common Examples of Import of Services Under RCM</h3>

      <div className="overflow-x-auto mb-6">
        <table className="w-full border-collapse border border-gray-300 text-sm">
          <thead>
            <tr className="bg-gray-100">
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Service</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Example</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">IGST Rate</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="border border-gray-300 px-4 py-3">Cloud hosting / SaaS</td>
              <td className="border border-gray-300 px-4 py-3">AWS, Google Cloud, Azure subscriptions</td>
              <td className="border border-gray-300 px-4 py-3">18%</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-3">Software licensing</td>
              <td className="border border-gray-300 px-4 py-3">Licensing fees paid to foreign software companies</td>
              <td className="border border-gray-300 px-4 py-3">18%</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-3">Consulting &amp; professional services</td>
              <td className="border border-gray-300 px-4 py-3">Management consulting, legal advice from foreign firms</td>
              <td className="border border-gray-300 px-4 py-3">18%</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-3">Advertising services</td>
              <td className="border border-gray-300 px-4 py-3">Google Ads, Meta Ads, LinkedIn Ads (paid to foreign entity)</td>
              <td className="border border-gray-300 px-4 py-3">18%</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-3">Technical testing &amp; analysis</td>
              <td className="border border-gray-300 px-4 py-3">Testing services performed by foreign labs</td>
              <td className="border border-gray-300 px-4 py-3">18%</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-3">Design services</td>
              <td className="border border-gray-300 px-4 py-3">UI/UX design, architectural design from foreign agencies</td>
              <td className="border border-gray-300 px-4 py-3">18%</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div className="bg-yellow-50 border-l-4 border-yellow-500 p-4 rounded mb-6">
        <p className="text-yellow-900 font-medium">Important Note</p>
        <p className="text-yellow-800 text-sm mt-1">For import of services, the GST must be paid under RCM even if the foreign service provider has obtained GST registration under the Online Information and Database Access or Retrieval (OIDAR) provisions. If the foreign provider is already paying GST (such as Netflix or Spotify for B2C services), the Indian business recipient need not pay RCM again.</p>
      </div>

      {/* Section 9 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">Common Mistakes &amp; Compliance Tips</h2>

      <div className="space-y-4 mb-6">
        <div className="bg-white border rounded-lg p-4">
          <h4 className="font-semibold text-gray-900 mb-2">1. Trying to Pay RCM Liability Using ITC</h4>
          <p className="text-gray-700 text-sm">RCM liability must be paid only through cash (Electronic Cash Ledger). You cannot use your ITC balance to discharge RCM obligations. After paying in cash, the equivalent ITC becomes available in your credit ledger.</p>
        </div>
        <div className="bg-white border rounded-lg p-4">
          <h4 className="font-semibold text-gray-900 mb-2">2. Not Issuing Self-Invoice for Purchases from Unregistered Persons</h4>
          <p className="text-gray-700 text-sm">When you pay GST under RCM for purchases from unregistered suppliers, you must issue a self-invoice (payment voucher). Without this document, you cannot claim ITC on the RCM tax paid.</p>
        </div>
        <div className="bg-white border rounded-lg p-4">
          <h4 className="font-semibold text-gray-900 mb-2">3. Forgetting RCM on Director Remuneration</h4>
          <p className="text-gray-700 text-sm">Fees and commission (not salary) paid to company directors are subject to RCM. Many companies miss this, especially for sitting fees and commission payments to independent directors.</p>
        </div>
        <div className="bg-white border rounded-lg p-4">
          <h4 className="font-semibold text-gray-900 mb-2">4. Not Paying RCM on Legal Services</h4>
          <p className="text-gray-700 text-sm">Legal services from individual advocates or law firms (partnership of advocates) to any business entity are under RCM. Businesses often pay the lawyer&apos;s bill without adding the RCM component.</p>
        </div>
        <div className="bg-white border rounded-lg p-4">
          <h4 className="font-semibold text-gray-900 mb-2">5. Missing RCM on Renting of Residential Property</h4>
          <p className="text-gray-700 text-sm">If a registered person (company) rents a residential dwelling for employees, GST at 18% is payable under RCM by the company. This applies even when the landlord is unregistered. Many businesses overlook this.</p>
        </div>
        <div className="bg-white border rounded-lg p-4">
          <h4 className="font-semibold text-gray-900 mb-2">6. Ignoring RCM on Import of Services</h4>
          <p className="text-gray-700 text-sm">Every payment to a foreign service provider (cloud hosting, SaaS, consulting) triggers RCM. With the growing use of international digital services, this is a common area of non-compliance.</p>
        </div>
        <div className="bg-white border rounded-lg p-4">
          <h4 className="font-semibold text-gray-900 mb-2">7. Not Reporting RCM in E-Way Bill</h4>
          <p className="text-gray-700 text-sm">When generating an <Link href="/blog/e-way-bill-guide" className="text-blue-600 underline">e-way bill</Link> for goods purchased under RCM, the &quot;reverse charge&quot; flag must be set to &quot;Yes&quot;. Failing to do so can cause issues during transit verification.</p>
        </div>
      </div>

      <div className="bg-gradient-to-r from-blue-600 to-blue-700 rounded-xl p-6 text-white mb-8">
        <h3 className="text-xl font-bold mb-2">Calculate Your RCM Liability</h3>
        <p className="text-blue-100 mb-4">Use GSTIndia&apos;s free GST Calculator to compute reverse charge tax liability, find the correct HSN/SAC codes, and validate supplier GSTINs &mdash; all in one place.</p>
        <Link href="/" className="inline-block bg-white text-blue-600 font-semibold px-6 py-2 rounded-lg hover:bg-blue-50 transition-colors">
          Try Free GST Tools &rarr;
        </Link>
      </div>

      {/* FAQ Section */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-6">Frequently Asked Questions (FAQ)</h2>

      <div className="space-y-4 mb-8">
        {[
          {
            q: 'What is Reverse Charge Mechanism (RCM) in GST?',
            a: 'Reverse Charge Mechanism is a provision under GST where the liability to pay tax shifts from the supplier to the recipient. Instead of the supplier collecting and paying GST, the buyer/recipient pays GST directly to the government. It applies to specified goods and services notified under Sections 9(3) and 9(4) of the CGST Act.',
          },
          {
            q: 'Can ITC be claimed on RCM payments?',
            a: 'Yes, ITC can be claimed on GST paid under reverse charge, provided the goods or services are used for business purposes and are not blocked under Section 17(5). The RCM tax must be paid in cash first, and then the equivalent ITC becomes available in the credit ledger.',
          },
          {
            q: 'Do I need to register for GST if I only make purchases under RCM?',
            a: 'If your only GST liability arises from RCM and your turnover is below the threshold limit, you are still required to register if you receive supplies notified under Section 9(3). However, for Section 9(4), only already-registered persons are affected.',
          },
          {
            q: 'Is RCM applicable on rent paid for residential property?',
            a: 'Yes, if a registered person (such as a company) takes a residential dwelling on rent, GST at 18% is payable under reverse charge by the tenant (registered person). The landlord does not need to be registered. This applies even when the rent is for employee accommodation.',
          },
          {
            q: 'How is RCM shown on a tax invoice?',
            a: 'When a registered supplier makes a supply under RCM, the invoice should mention "Tax is payable on Reverse Charge Basis" or similar wording. The supplier does not charge GST on the invoice amount. For purchases from unregistered persons, the recipient issues a self-invoice or payment voucher.',
          },
          {
            q: 'Is there a threshold limit for RCM applicability?',
            a: 'For services notified under Section 9(3), there is generally no threshold — RCM applies regardless of the transaction value. For Section 9(4), it applies to notified categories when purchasing from unregistered suppliers. For GTA services, the exemption threshold is ₹750 per consignment or ₹1,500 per consignor/consignee per invoice.',
          },
          {
            q: 'Does RCM apply to composition scheme dealers?',
            a: 'Yes, composition scheme dealers are also liable to pay tax under RCM on notified inward supplies. However, composition dealers cannot claim ITC on the RCM tax paid. The tax paid under RCM becomes a cost for them.',
          },
          {
            q: 'What is the time of supply for RCM?',
            a: 'For goods under RCM, the time of supply is the earlier of: (a) date of receipt of goods, or (b) date of payment, or (c) 30 days from the date of issue of invoice by the supplier. For services under RCM, it is the earlier of: (a) date of payment, or (b) 60 days from the date of issue of invoice by the supplier.',
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
        The Reverse Charge Mechanism is a critical aspect of GST compliance that many businesses overlook or misunderstand. Whether it is paying GST on legal services from advocates, director fees, security services, renting of residential property, or import of services from foreign providers, missing RCM obligations can lead to interest, penalties, and adverse assessment orders.
      </p>

      <p className="text-gray-700 leading-relaxed mb-4">
        The key takeaways are: always identify if a transaction attracts RCM, pay the RCM tax in cash (not from ITC), issue self-invoices for purchases from unregistered persons, and report RCM correctly in GSTR-3B and GSTR-9. For computing your RCM liability accurately, use the <Link href="/" className="text-blue-600 hover:text-blue-700 underline">GSTIndia GST Calculator</Link>, and verify HSN/SAC codes using the <Link href="/" className="text-blue-600 hover:text-blue-700 underline">HSN Code Finder</Link>.
      </p>

      {/* JSON-LD Structured Data */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            '@context': 'https://schema.org',
            '@type': 'Article',
            headline: 'Reverse Charge Mechanism (RCM) Under GST: Complete Guide with List of Goods & Services',
            description: 'Complete guide to Reverse Charge Mechanism (RCM) under GST. What is RCM, when it applies, list of goods & services under RCM, ITC rules & compliance.',
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
            url: 'https://gst.doaide.com/blog/reverse-charge-mechanism-rcm-gst',
            mainEntityOfPage: 'https://gst.doaide.com/blog/reverse-charge-mechanism-rcm-gst',
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
                name: 'What is Reverse Charge Mechanism (RCM) in GST?',
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: 'RCM is a provision where the liability to pay GST shifts from the supplier to the recipient. The buyer pays GST directly to the government instead of the supplier collecting and remitting it.',
                },
              },
              {
                '@type': 'Question',
                name: 'Can ITC be claimed on RCM payments?',
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: 'Yes, ITC can be claimed on RCM payments. The tax must be paid in cash first, and then the equivalent ITC becomes available in the credit ledger, subject to normal ITC eligibility.',
                },
              },
              {
                '@type': 'Question',
                name: 'Is RCM applicable on rent paid for residential property?',
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: 'Yes, if a registered person rents a residential dwelling, GST at 18% is payable under reverse charge by the tenant, even when the landlord is unregistered.',
                },
              },
              {
                '@type': 'Question',
                name: 'How is RCM shown on a tax invoice?',
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: 'The supplier\'s invoice should mention "Tax is payable on Reverse Charge Basis." For purchases from unregistered persons, the recipient issues a self-invoice or payment voucher.',
                },
              },
              {
                '@type': 'Question',
                name: 'Does RCM apply to composition scheme dealers?',
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: 'Yes, composition dealers must pay tax under RCM on notified inward supplies, but they cannot claim ITC on the RCM tax paid.',
                },
              },
              {
                '@type': 'Question',
                name: 'What is the time of supply for RCM?',
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: 'For goods: the earlier of receipt of goods, payment date, or 30 days from invoice. For services: the earlier of payment date or 60 days from invoice.',
                },
              },
            ],
          }),
        }}
      />

      <div className="mt-8 pt-8 border-t dark:border-gray-800">
        <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">Found this guide helpful? Share it:</p>
        <ShareButtons
          title="Reverse Charge Mechanism (RCM) Under GST — Complete Guide"
          url="/blog/reverse-charge-mechanism-rcm-gst"
        />
      </div>
    </article>
  );
}
