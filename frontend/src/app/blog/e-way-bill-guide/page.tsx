import type { Metadata } from 'next';
import Link from 'next/link';
import { ShareButtons } from '@/components/blog/share-buttons';

export const metadata: Metadata = {
  title: 'E-Way Bill Guide 2026 — Rules, Generation & Validity',
  description: 'Complete e-way bill guide for 2026. Learn when e-way bill is needed, how to generate on ewaybillgst.gov.in, validity rules, penalties & exemptions.',
  openGraph: {
    title: 'E-Way Bill Guide 2026 — Rules, Generation & Validity',
    description: 'Complete e-way bill guide for 2026. Learn when e-way bill is needed, how to generate, validity and penalties.',
    url: 'https://gst.doaide.com/blog/e-way-bill-guide',
    type: 'article',
  },
  alternates: {
    canonical: 'https://gst.doaide.com/blog/e-way-bill-guide',
  },
};

export default function EWayBillGuide() {
  return (
    <article className="max-w-4xl mx-auto px-4 py-12">
      <div className="mb-8">
        <span className="text-sm font-semibold text-blue-600 bg-blue-50 px-3 py-1 rounded-full">E-Way Bill</span>
        <span className="text-sm text-gray-500 ml-3">Updated: 10 October 2026</span>
        <span className="text-sm text-gray-500 ml-3">18 min read</span>
      </div>

      <h1 className="text-3xl sm:text-4xl font-bold text-gray-900 dark:text-gray-100 mb-6">
        E-Way Bill Guide 2026: Rules, How to Generate, Validity &amp; Penalties
      </h1>

      <ShareButtons
        title="E-Way Bill Guide 2026: Rules, Generation & Validity"
        url="/blog/e-way-bill-guide"
        className="mb-8"
      />

      <p className="text-lg text-gray-600 dark:text-gray-400 mb-8 leading-relaxed">
        The Electronic Way Bill (E-Way Bill) is a mandatory document under GST for the movement of goods worth more than ₹50,000 within or across state borders. It is generated electronically on the GST E-Way Bill portal and must accompany every consignment during transit. This guide covers everything you need to know about e-way bills in 2026 &mdash; when they are required, how to generate them, their validity period, penalties for non-compliance, and common exemptions.
      </p>

      <div className="bg-blue-50 border-l-4 border-blue-500 p-4 rounded mb-8">
        <p className="text-blue-900 font-medium">Quick Navigation</p>
        <ul className="text-blue-800 text-sm mt-2 space-y-1">
          <li>&bull; What is an E-Way Bill?</li>
          <li>&bull; When is E-Way Bill Required?</li>
          <li>&bull; Who Should Generate E-Way Bill?</li>
          <li>&bull; How to Generate E-Way Bill Online</li>
          <li>&bull; E-Way Bill Validity &amp; Distance Rules</li>
          <li>&bull; E-Way Bill Part A vs Part B</li>
          <li>&bull; Consolidated E-Way Bill</li>
          <li>&bull; E-Way Bill Exemptions</li>
          <li>&bull; Penalties for Non-Compliance</li>
          <li>&bull; E-Way Bill Blocking Rules</li>
          <li>&bull; FAQs</li>
        </ul>
      </div>

      {/* Section 1 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">What is an E-Way Bill?</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        An E-Way Bill (EWB) is an electronic document generated on the E-Way Bill portal (ewaybillgst.gov.in) that is required for the movement of goods. It was introduced under GST to replace the multiple waybill systems that existed under the earlier VAT/CST regime across different states. The e-way bill system ensures that goods being transported comply with GST law and helps curb tax evasion.
      </p>

      <p className="text-gray-700 leading-relaxed mb-4">
        Every e-way bill has a unique 12-digit number called the E-Way Bill Number (EBN) and contains details of the goods, consignor, consignee, and transporter. It is valid for a specific period based on the distance to be covered. The bill can be verified at any point during transit by tax officers using the EBN or by scanning the QR code printed on the bill.
      </p>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">Key Features of the E-Way Bill System</h3>

      <ul className="list-disc pl-6 text-gray-700 space-y-2 mb-6">
        <li><strong>Electronic generation:</strong> Generated online through the portal, SMS, API, or GST Suvidha Providers</li>
        <li><strong>Unique 12-digit EBN:</strong> Each e-way bill gets a unique number for tracking</li>
        <li><strong>QR code:</strong> Contains the EBN, date, supplier GSTIN, and consignment value for quick verification</li>
        <li><strong>Real-time verification:</strong> Tax officers can verify e-way bills in real time using the GST E-Way Bill system</li>
        <li><strong>Two parts:</strong> Part A (supply details) and Part B (transport details)</li>
      </ul>

      {/* Section 2 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">When is an E-Way Bill Required?</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        An e-way bill must be generated before the commencement of movement of goods in the following situations:
      </p>

      <ul className="list-disc pl-6 text-gray-700 space-y-2 mb-6">
        <li><strong>Supply of goods:</strong> When goods valued above ₹50,000 are being supplied (sold) and need to be transported</li>
        <li><strong>Non-supply movement:</strong> When goods are moved for reasons other than supply (e.g., job work, exhibition, repair, return) and the consignment value exceeds ₹50,000</li>
        <li><strong>Inward supply from unregistered person:</strong> When a registered person receives goods from an unregistered supplier worth above ₹50,000</li>
      </ul>

      <div className="bg-yellow-50 border-l-4 border-yellow-500 p-4 rounded mb-6">
        <p className="text-yellow-900 font-medium">Important Note</p>
        <p className="text-yellow-800 text-sm mt-1">The ₹50,000 threshold is calculated per consignment (per invoice), not per vehicle load. However, some states have reduced this threshold — for example, several states require e-way bills for intra-state movement of goods worth more than ₹50,000 or even lower amounts for specific goods like tobacco and pan masala. Always check state-specific rules.</p>
      </div>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">E-Way Bill for Inter-State vs Intra-State Movement</h3>

      <div className="overflow-x-auto mb-6">
        <table className="w-full border-collapse border border-gray-300 text-sm">
          <thead>
            <tr className="bg-gray-100">
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Parameter</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Inter-State</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Intra-State</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="border border-gray-300 px-4 py-3 font-medium">Threshold</td>
              <td className="border border-gray-300 px-4 py-3">₹50,000 (mandatory)</td>
              <td className="border border-gray-300 px-4 py-3">₹50,000 (varies by state; some states have lower limits)</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-3 font-medium">Applicability</td>
              <td className="border border-gray-300 px-4 py-3">All India since 1 April 2018</td>
              <td className="border border-gray-300 px-4 py-3">All states since 25 April 2018</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-3 font-medium">Special Goods</td>
              <td className="border border-gray-300 px-4 py-3">E-way bill required for handicraft goods regardless of value (even below ₹50,000)</td>
              <td className="border border-gray-300 px-4 py-3">State-specific rules may require EWB for gold, tobacco etc. at lower thresholds</td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* Section 3 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">Who Should Generate an E-Way Bill?</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        The responsibility of generating an e-way bill depends on the nature of the transaction and the mode of transport:
      </p>

      <div className="overflow-x-auto mb-6">
        <table className="w-full border-collapse border border-gray-300 text-sm">
          <thead>
            <tr className="bg-gray-100">
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Scenario</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Who Generates EWB</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="border border-gray-300 px-4 py-3">Supplier arranges transport</td>
              <td className="border border-gray-300 px-4 py-3">Supplier (consignor)</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-3">Buyer arranges transport</td>
              <td className="border border-gray-300 px-4 py-3">Buyer (consignee)</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-3">Neither supplier nor buyer generates</td>
              <td className="border border-gray-300 px-4 py-3">Transporter can generate on behalf</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-3">Supply from unregistered person</td>
              <td className="border border-gray-300 px-4 py-3">Registered recipient</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-3">Goods sent for job work</td>
              <td className="border border-gray-300 px-4 py-3">Principal (registered person sending goods)</td>
            </tr>
          </tbody>
        </table>
      </div>

      <p className="text-gray-700 leading-relaxed mb-4">
        Unregistered persons can also generate e-way bills on the portal. If an unregistered person supplies goods to a registered person, and the registered person has not generated the e-way bill, the responsibility falls on the transporter.
      </p>

      {/* Section 4 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">How to Generate an E-Way Bill Online: Step-by-Step</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        E-way bills can be generated through the official portal at ewaybillgst.gov.in. Here is the complete step-by-step process:
      </p>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">Step 1: Register on the E-Way Bill Portal</h3>

      <p className="text-gray-700 leading-relaxed mb-4">
        Visit ewaybillgst.gov.in and click on <strong>&quot;Registration&quot;</strong> then <strong>&quot;e-Way Bill Registration&quot;</strong>. Enter your GSTIN and the OTP sent to your registered mobile number and email. Create a username and password. Once registered, you can log in and start generating e-way bills.
      </p>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">Step 2: Log In and Select &quot;Generate New&quot;</h3>

      <p className="text-gray-700 leading-relaxed mb-4">
        After logging in, go to <strong>e-Way Bill → Generate New</strong>. You will see a form with two parts &mdash; Part A and Part B.
      </p>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">Step 3: Fill Part A &mdash; Supply Details</h3>

      <p className="text-gray-700 leading-relaxed mb-4">
        Part A captures the core details of the consignment:
      </p>

      <ul className="list-disc pl-6 text-gray-700 space-y-2 mb-6">
        <li><strong>Transaction Type:</strong> Outward (supply to buyer) or Inward (supply received from supplier)</li>
        <li><strong>Sub-Type:</strong> Supply, Export, Job Work, SKD/CKD, Sales Return, Exhibition, For Own Use, etc.</li>
        <li><strong>Document Type:</strong> Invoice, Bill of Supply, Delivery Challan, or Bill of Entry</li>
        <li><strong>Document Number &amp; Date:</strong> Your invoice number and date</li>
        <li><strong>From / To:</strong> GSTIN and address of supplier and recipient</li>
        <li><strong>Item Details:</strong> Product name, description, HSN code, quantity, unit, taxable value, CGST/SGST/IGST rate</li>
        <li><strong>Consignment Value:</strong> Total value of goods being transported</li>
      </ul>

      <div className="bg-blue-50 border-l-4 border-blue-500 p-4 rounded mb-6">
        <p className="text-blue-900 font-medium">Pro Tip</p>
        <p className="text-blue-800 text-sm mt-1">Use the <Link href="/" className="text-blue-600 underline">GSTIndia HSN Code Finder</Link> to quickly look up the correct HSN code while generating your e-way bill. An incorrect HSN code can lead to issues during transit verification. Also verify the recipient&apos;s GSTIN using the <Link href="/" className="text-blue-600 underline">GSTIN Validator</Link> to avoid errors.</p>
      </div>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">Step 4: Fill Part B &mdash; Transport Details</h3>

      <p className="text-gray-700 leading-relaxed mb-4">
        Part B captures the transport details and is required for the e-way bill to be valid for movement:
      </p>

      <ul className="list-disc pl-6 text-gray-700 space-y-2 mb-6">
        <li><strong>Mode of Transport:</strong> Road, Rail, Air, or Ship/Water</li>
        <li><strong>Vehicle Number:</strong> Registration number of the vehicle (for road transport)</li>
        <li><strong>Transport Document Number:</strong> Railway receipt number, airway bill number, or bill of lading number (for non-road transport)</li>
        <li><strong>Transporter ID &amp; Name:</strong> GSTIN or Enrolment ID of the transporter</li>
      </ul>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">Step 5: Generate and Print</h3>

      <p className="text-gray-700 leading-relaxed mb-4">
        After filling both parts, click <strong>&quot;Submit&quot;</strong>. The system validates the details and generates the e-way bill with a unique 12-digit EBN. You can print the e-way bill or save it in PDF format. The EBN and QR code must accompany the goods during transit.
      </p>

      {/* Section 5 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">E-Way Bill Validity &amp; Distance Rules</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        The validity of an e-way bill depends on the distance the goods need to travel and the type of conveyance. The validity starts from the time of generation of Part B (transport details).
      </p>

      <div className="overflow-x-auto mb-6">
        <table className="w-full border-collapse border border-gray-300 text-sm">
          <thead>
            <tr className="bg-gray-100">
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Type of Conveyance</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Distance</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Validity Period</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="border border-gray-300 px-4 py-3 font-medium" rowSpan={4}>Regular Vehicle (other than over-dimensional cargo)</td>
              <td className="border border-gray-300 px-4 py-3">Up to 200 km</td>
              <td className="border border-gray-300 px-4 py-3">1 day</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-3">200 km to 400 km</td>
              <td className="border border-gray-300 px-4 py-3">3 days</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-3">400 km to 600 km</td>
              <td className="border border-gray-300 px-4 py-3">4 days</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-3">Every additional 200 km</td>
              <td className="border border-gray-300 px-4 py-3">+1 day</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-3 font-medium" rowSpan={2}>Over-Dimensional Cargo (ODC)</td>
              <td className="border border-gray-300 px-4 py-3">Up to 20 km</td>
              <td className="border border-gray-300 px-4 py-3">1 day</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-3">Every additional 20 km</td>
              <td className="border border-gray-300 px-4 py-3">+1 day</td>
            </tr>
          </tbody>
        </table>
      </div>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">Extending E-Way Bill Validity</h3>

      <p className="text-gray-700 leading-relaxed mb-4">
        If the goods cannot be delivered within the validity period due to unforeseen circumstances (vehicle breakdown, natural disaster, law and order issues, transshipment delays), the validity can be extended. The extension must be done <strong>before the expiry</strong> of the current validity or within <strong>8 hours after expiry</strong>. Extension can be done on the portal under <strong>e-Way Bill → Extend Validity</strong>. You must provide the reason for extension and the new vehicle number (if changed).
      </p>

      {/* Section 6 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">E-Way Bill Part A vs Part B</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        Understanding the distinction between Part A and Part B is important because in certain situations, only Part A needs to be filled:
      </p>

      <div className="overflow-x-auto mb-6">
        <table className="w-full border-collapse border border-gray-300 text-sm">
          <thead>
            <tr className="bg-gray-100">
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Aspect</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Part A</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Part B</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="border border-gray-300 px-4 py-3 font-medium">Contains</td>
              <td className="border border-gray-300 px-4 py-3">Supply details &mdash; GSTIN, invoice, HSN, value, tax</td>
              <td className="border border-gray-300 px-4 py-3">Transport details &mdash; vehicle number, transporter ID</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-3 font-medium">Filled by</td>
              <td className="border border-gray-300 px-4 py-3">Supplier or recipient</td>
              <td className="border border-gray-300 px-4 py-3">Supplier, recipient, or transporter</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-3 font-medium">Validity starts</td>
              <td className="border border-gray-300 px-4 py-3">No validity without Part B</td>
              <td className="border border-gray-300 px-4 py-3">Validity starts when Part B is completed</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-3 font-medium">Can be filled separately</td>
              <td className="border border-gray-300 px-4 py-3">Yes &mdash; Part A can be filled first, Part B later</td>
              <td className="border border-gray-300 px-4 py-3">Yes &mdash; Part B can be added within 15 days of Part A</td>
            </tr>
          </tbody>
        </table>
      </div>

      <p className="text-gray-700 leading-relaxed mb-4">
        Part B is not required when the goods are transported for a distance of up to 50 km from the place of business of the consignor to the transporter for further transport (i.e., movement to/from a transporter&apos;s godown within 50 km).
      </p>

      {/* Section 7 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">Consolidated E-Way Bill</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        When a transporter is carrying multiple consignments in a single vehicle, instead of carrying individual e-way bills, they can generate a <strong>Consolidated E-Way Bill (CEWB)</strong>. The CEWB is a single document that consolidates multiple EWBs. To generate one:
      </p>

      <ol className="list-decimal pl-6 text-gray-700 space-y-2 mb-6">
        <li>Each individual consignment must have its own e-way bill generated</li>
        <li>The transporter logs into the portal and selects <strong>Consolidated EWB → Generate New</strong></li>
        <li>Enters the vehicle number, the from-state, and adds the individual EBN numbers</li>
        <li>A consolidated EBN is generated covering all consignments in that vehicle</li>
      </ol>

      {/* Section 8 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">E-Way Bill Exemptions</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        E-way bills are <strong>not required</strong> in the following cases, even if the consignment value exceeds ₹50,000:
      </p>

      <ul className="list-disc pl-6 text-gray-700 space-y-2 mb-6">
        <li>Goods exempted under specific notifications (e.g., fresh fruits, vegetables, milk, eggs, bread)</li>
        <li>Goods transported by non-motorised conveyance (bullock cart, hand cart, etc.)</li>
        <li>Goods moved from port, airport, or customs station to a customs bonded warehouse or ICD under customs bond or transit</li>
        <li>Movement of goods within the notified area from the port to ICD or CFS</li>
        <li>Goods transported under customs supervision or customs seal</li>
        <li>Transit cargo from or to Nepal or Bhutan</li>
        <li>Defence or military equipment under Ministry of Defence</li>
        <li>Empty cargo containers being transported</li>
        <li>Goods transported by railways (railways exempt from generating EWB, but the consignor must generate Part A)</li>
        <li>Specified goods: used personal &amp; household effects, coral, unworked &amp; worked, LPG for household supply, kerosene under PDS</li>
        <li>Goods transported within 50 km from the place of business (only Part A required, Part B not needed)</li>
      </ul>

      {/* Section 9 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">Penalties for E-Way Bill Non-Compliance</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        Non-compliance with e-way bill provisions can attract serious penalties. If goods are found being transported without a valid e-way bill, or with an expired or incorrect e-way bill, the following consequences may arise:
      </p>

      <div className="overflow-x-auto mb-6">
        <table className="w-full border-collapse border border-gray-300 text-sm">
          <thead>
            <tr className="bg-gray-100">
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Offence</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Penalty</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Legal Section</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="border border-gray-300 px-4 py-3">Transporting goods without e-way bill</td>
              <td className="border border-gray-300 px-4 py-3">Penalty of ₹10,000 or tax sought to be evaded, whichever is higher</td>
              <td className="border border-gray-300 px-4 py-3">Section 129</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-3">Detention of goods &amp; vehicle</td>
              <td className="border border-gray-300 px-4 py-3">Goods and vehicle can be detained and released only after payment of applicable tax &amp; penalty (200% of tax for owner of goods, 50% for transporter if goods belong to someone else)</td>
              <td className="border border-gray-300 px-4 py-3">Section 129(1)</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-3">Confiscation of goods</td>
              <td className="border border-gray-300 px-4 py-3">Goods may be confiscated if penalty is not paid within 14 days of detention</td>
              <td className="border border-gray-300 px-4 py-3">Section 130</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-3">E-way bill with incorrect details</td>
              <td className="border border-gray-300 px-4 py-3">Treated as goods without valid documents; same penalty as above</td>
              <td className="border border-gray-300 px-4 py-3">Section 129</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div className="bg-yellow-50 border-l-4 border-yellow-500 p-4 rounded mb-6">
        <p className="text-yellow-900 font-medium">Critical Warning</p>
        <p className="text-yellow-800 text-sm mt-1">If an e-way bill is expired during transit, it is treated as movement without a valid e-way bill, and the goods and vehicle can be detained. Always check the validity before dispatching goods and extend it promptly if delays are expected.</p>
      </div>

      {/* Section 10 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">E-Way Bill Blocking Rules</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        The e-way bill system is linked to GST return compliance. Your ability to generate e-way bills can be <strong>blocked</strong> in the following situations:
      </p>

      <ul className="list-disc pl-6 text-gray-700 space-y-2 mb-6">
        <li><strong>Non-filing of GSTR-3B:</strong> If you have not filed GSTR-3B for two or more consecutive tax periods, your e-way bill generation will be blocked</li>
        <li><strong>Non-filing of GSTR-1:</strong> Similarly, non-filing of GSTR-1 for two or more consecutive periods can lead to blocking</li>
        <li><strong>Composition taxpayers:</strong> If CMP-08 is not filed for two consecutive quarters, e-way bill generation is blocked</li>
      </ul>

      <p className="text-gray-700 leading-relaxed mb-4">
        To unblock, you must file all pending returns. The system automatically unblocks within 24 hours of filing the overdue returns. This linking of e-way bills to return compliance ensures that businesses stay up to date with their GST filings. Learn more about GST return filing in our <Link href="/blog/gst-return-filing-guide-2026-27" className="text-blue-600 hover:text-blue-700 underline">GST Return Filing Guide</Link>.
      </p>

      {/* Section 11 - Other Methods */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">Other Methods to Generate E-Way Bills</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        Apart from the web portal, e-way bills can be generated through several other channels:
      </p>

      <div className="space-y-4 mb-6">
        <div className="bg-white border rounded-lg p-4">
          <h4 className="font-semibold text-gray-900 mb-2">SMS-Based Generation</h4>
          <p className="text-gray-700 text-sm">Send an SMS in the prescribed format to the designated number. This is useful when internet connectivity is limited, though only basic e-way bills can be generated this way.</p>
        </div>
        <div className="bg-white border rounded-lg p-4">
          <h4 className="font-semibold text-gray-900 mb-2">API Integration</h4>
          <p className="text-gray-700 text-sm">Businesses with high volumes can integrate the E-Way Bill API with their ERP or accounting software for automated generation. This is recommended for large enterprises.</p>
        </div>
        <div className="bg-white border rounded-lg p-4">
          <h4 className="font-semibold text-gray-900 mb-2">GST Suvidha Providers (GSPs)</h4>
          <p className="text-gray-700 text-sm">Authorised GSPs offer platforms for bulk e-way bill generation, management, and integration with accounting systems.</p>
        </div>
        <div className="bg-white border rounded-lg p-4">
          <h4 className="font-semibold text-gray-900 mb-2">Bulk Generation Tool</h4>
          <p className="text-gray-700 text-sm">Download the offline tool from the portal, fill in multiple e-way bills in the Excel template, and upload the JSON file for bulk generation.</p>
        </div>
      </div>

      <div className="bg-gradient-to-r from-blue-600 to-blue-700 rounded-xl p-6 text-white mb-8">
        <h3 className="text-xl font-bold mb-2">Simplify Your GST Compliance</h3>
        <p className="text-blue-100 mb-4">Use GSTIndia&apos;s free tools to calculate GST, find HSN codes for your e-way bills, validate GSTINs, and stay compliant &mdash; all in one place.</p>
        <Link href="/" className="inline-block bg-white text-blue-600 font-semibold px-6 py-2 rounded-lg hover:bg-blue-50 transition-colors">
          Try Free GST Tools &rarr;
        </Link>
      </div>

      {/* FAQ Section */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-6">Frequently Asked Questions (FAQ)</h2>

      <div className="space-y-4 mb-8">
        {[
          {
            q: 'What is the e-way bill limit for 2026?',
            a: 'The e-way bill is required for movement of goods with consignment value exceeding ₹50,000. This threshold applies to inter-state movement nationwide. For intra-state movement, most states follow the ₹50,000 limit, but some states have lower thresholds for specific goods.',
          },
          {
            q: 'Can I cancel an e-way bill?',
            a: 'Yes, an e-way bill can be cancelled within 24 hours of generation if the goods are not transported or if the bill was generated with incorrect details. However, it cannot be cancelled if it has been verified by a tax officer during transit. Cancellation is done on the portal under e-Way Bill → Cancel.',
          },
          {
            q: 'What happens if the vehicle number changes during transit?',
            a: 'If the vehicle breaks down or goods are transferred to another vehicle, the e-way bill must be updated with the new vehicle number on the portal under e-Way Bill → Update Vehicle Number. This does not change the EBN or validity — it only updates Part B.',
          },
          {
            q: 'Is e-way bill required for goods sent for job work?',
            a: 'Yes, an e-way bill is required for movement of goods for job work if the consignment value exceeds ₹50,000. The principal (person sending goods for job work) should generate the e-way bill. Use delivery challan as the document type.',
          },
          {
            q: 'Can I generate an e-way bill without a GSTIN?',
            a: 'Yes, unregistered persons can generate e-way bills by selecting "Citizen" option on the registration page and using their PAN or Aadhaar for enrolment. They can then generate e-way bills for their consignments.',
          },
          {
            q: 'What is the validity of an e-way bill for 500 km distance?',
            a: 'For regular vehicles (non-ODC), the validity would be approximately 4 days. The calculation is: up to 200 km = 1 day, 200-400 km = 3 days, 400-600 km = 4 days. So for 500 km, it is 4 days from the time Part B is entered.',
          },
          {
            q: 'Is e-way bill required for movement within the same city?',
            a: 'If the consignment value exceeds ₹50,000 (or the state-specific threshold for intra-state movement), an e-way bill is required even within the same city. However, if the movement is within 50 km, only Part A is mandatory — Part B (vehicle details) is not required.',
          },
          {
            q: 'How is e-way bill linked to e-invoice?',
            a: 'For taxpayers required to generate e-invoices (turnover above ₹5 crore), Part A of the e-way bill is auto-populated from the e-invoice data on the IRP (Invoice Registration Portal). You only need to fill Part B (transport details) on the e-way bill portal to complete the EWB.',
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
        The e-way bill system is a critical component of GST compliance for businesses involved in the movement of goods. Understanding when an e-way bill is required, how to generate one correctly, and the validity rules can save you from costly penalties and detention of goods during transit. Always ensure your GSTR-1 and GSTR-3B filings are up to date to avoid e-way bill blocking, and use the correct HSN codes on your e-way bills to prevent issues during verification.
      </p>

      <p className="text-gray-700 leading-relaxed mb-4">
        For related guides, check our <Link href="/blog/gst-invoice-format-guide" className="text-blue-600 hover:text-blue-700 underline">GST Invoice Format Guide</Link> (proper invoicing is the foundation for e-way bill generation) and the <Link href="/blog/gst-hsn-code-list" className="text-blue-600 hover:text-blue-700 underline">HSN Code List</Link> for finding the right product codes. Use the free tools on <Link href="/" className="text-blue-600 hover:text-blue-700 underline">GSTIndia</Link> to make your compliance journey smoother.
      </p>

      {/* JSON-LD Structured Data */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            '@context': 'https://schema.org',
            '@type': 'Article',
            headline: 'E-Way Bill Guide 2026: Rules, How to Generate, Validity & Penalties',
            description: 'Complete e-way bill guide for 2026. Learn when e-way bill is needed, how to generate on ewaybillgst.gov.in, validity rules, penalties & exemptions.',
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
            url: 'https://gst.doaide.com/blog/e-way-bill-guide',
            mainEntityOfPage: 'https://gst.doaide.com/blog/e-way-bill-guide',
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
                name: 'What is the e-way bill limit for 2026?',
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: 'The e-way bill is required for movement of goods with consignment value exceeding ₹50,000. Some states have lower thresholds for specific goods.',
                },
              },
              {
                '@type': 'Question',
                name: 'Can I cancel an e-way bill?',
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: 'Yes, an e-way bill can be cancelled within 24 hours of generation if the goods are not transported or the bill was generated with incorrect details.',
                },
              },
              {
                '@type': 'Question',
                name: 'What happens if the vehicle number changes during transit?',
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: 'The e-way bill must be updated with the new vehicle number on the portal under e-Way Bill → Update Vehicle Number. This does not change the EBN or validity.',
                },
              },
              {
                '@type': 'Question',
                name: 'Is e-way bill required for goods sent for job work?',
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: 'Yes, if the consignment value exceeds ₹50,000. The principal should generate the e-way bill using delivery challan as the document type.',
                },
              },
              {
                '@type': 'Question',
                name: 'Can I generate an e-way bill without a GSTIN?',
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: 'Yes, unregistered persons can generate e-way bills by enrolling on the portal using PAN or Aadhaar.',
                },
              },
              {
                '@type': 'Question',
                name: 'What is the validity of an e-way bill for 500 km distance?',
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: 'For regular vehicles, the validity for 500 km would be 4 days from the time Part B is entered.',
                },
              },
              {
                '@type': 'Question',
                name: 'Is e-way bill required for movement within the same city?',
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: 'Yes, if the consignment value exceeds ₹50,000. However, within 50 km only Part A is required — Part B (vehicle details) is not needed.',
                },
              },
              {
                '@type': 'Question',
                name: 'How is e-way bill linked to e-invoice?',
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: 'For taxpayers with turnover above ₹5 crore, Part A of the e-way bill is auto-populated from e-invoice data. Only Part B needs to be filled on the e-way bill portal.',
                },
              },
            ],
          }),
        }}
      />

      <div className="mt-8 pt-8 border-t dark:border-gray-800">
        <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">Found this guide helpful? Share it:</p>
        <ShareButtons
          title="E-Way Bill Guide 2026: Rules, Generation & Validity"
          url="/blog/e-way-bill-guide"
        />
      </div>
    </article>
  );
}
