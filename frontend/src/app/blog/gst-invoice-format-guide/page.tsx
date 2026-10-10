import type { Metadata } from 'next';
import Link from 'next/link';
import { ShareButtons } from '@/components/blog/share-buttons';

export const metadata: Metadata = {
  title: 'GST Invoice Format 2026: Rules & Templates',
  description: 'Complete guide to GST invoice format with mandatory fields, templates, e-invoicing rules, and bill of supply format for Indian businesses in 2026-27.',
  openGraph: {
    title: 'GST Invoice Format 2026: Rules, Mandatory Fields & Templates',
    description: 'Complete guide to GST invoice format with mandatory fields, templates, e-invoicing rules, and bill of supply format for Indian businesses.',
    url: 'https://gst.doaide.com/blog/gst-invoice-format-guide',
    type: 'article',
  },
  alternates: {
    canonical: 'https://gst.doaide.com/blog/gst-invoice-format-guide',
  },
};

export default function GSTInvoiceFormatGuide() {
  return (
    <article className="max-w-4xl mx-auto px-4 py-12">
      <div className="mb-8">
        <span className="text-sm font-semibold text-blue-600 bg-blue-50 px-3 py-1 rounded-full">Invoicing</span>
        <span className="text-sm text-gray-500 ml-3">Updated: 10 October 2026</span>
        <span className="text-sm text-gray-500 ml-3">16 min read</span>
      </div>

      <h1 className="text-3xl sm:text-4xl font-bold text-gray-900 dark:text-gray-100 mb-6">
        GST Invoice Format 2026: Mandatory Fields, Templates &amp; E-Invoicing Rules
      </h1>

      <ShareButtons
        title="GST Invoice Format 2026: Rules, Mandatory Fields & Templates"
        url="/blog/gst-invoice-format-guide"
        className="mb-8"
      />

      <p className="text-lg text-gray-600 dark:text-gray-400 mb-8 leading-relaxed">
        A GST invoice is the most important document in the Goods and Services Tax framework. Every registered business must issue a properly formatted tax invoice for every taxable supply of goods or services. Getting your invoice format wrong can lead to ITC denial for your buyers, penalties from the tax department, and compliance headaches. This guide covers every aspect of GST invoice format, mandatory fields, templates, and the latest e-invoicing rules for 2026-27.
      </p>

      <div className="bg-blue-50 border-l-4 border-blue-500 p-4 rounded mb-8">
        <p className="text-blue-900 font-medium">Quick Navigation</p>
        <ul className="text-blue-800 text-sm mt-2 space-y-1">
          <li>&bull; What is a GST Invoice</li>
          <li>&bull; Mandatory Fields (Rule 46)</li>
          <li>&bull; Types of GST Invoices</li>
          <li>&bull; Invoice Format Template</li>
          <li>&bull; Bill of Supply Format</li>
          <li>&bull; E-Invoicing Rules</li>
          <li>&bull; HSN Code Requirements</li>
          <li>&bull; Common Mistakes &amp; Penalties</li>
          <li>&bull; FAQs</li>
        </ul>
      </div>

      {/* Section 1 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">What is a GST Invoice?</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        A GST invoice (also called a tax invoice) is a document issued by a registered supplier to the buyer at the time of supply of goods or services. It serves as the primary evidence of a transaction under GST and is the basis on which the buyer can claim <Link href="/blog/input-tax-credit-itc-rules-2026-27" className="text-blue-600 hover:text-blue-700 underline">Input Tax Credit (ITC)</Link>. Without a valid tax invoice, ITC cannot be claimed, making it the most critical commercial document in the GST ecosystem.
      </p>

      <p className="text-gray-700 leading-relaxed mb-4">
        The legal requirement for issuing a GST invoice is laid down under <strong>Section 31 of the CGST Act, 2017</strong>. According to this section, a registered person supplying taxable goods must issue a tax invoice before or at the time of removal of goods (in case of movable goods) or delivery (in case of immovable goods). For services, the invoice must be issued before or after the provision of service, but within 30 days from the date of supply of service (45 days for banks and financial institutions).
      </p>

      <p className="text-gray-700 leading-relaxed mb-4">
        The format and content of a GST invoice are prescribed under <strong>Rule 46 of the CGST Rules, 2017</strong>. The government does not mandate a specific visual layout or design — you can use any format as long as it contains all the mandatory fields prescribed under the rules. This gives businesses flexibility to design invoices that match their branding while remaining compliant.
      </p>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">Why Proper Invoice Format Matters</h3>

      <ul className="list-disc pl-6 text-gray-700 space-y-2 mb-6">
        <li><strong>ITC for buyers:</strong> Your customer can claim Input Tax Credit only if they have a valid tax invoice from you</li>
        <li><strong>GSTR-1 reporting:</strong> Invoice details must be reported in your <Link href="/blog/gst-return-filing-guide-2026-27" className="text-blue-600 hover:text-blue-700 underline">GSTR-1 return</Link></li>
        <li><strong>E-invoicing compliance:</strong> Invoices must conform to the e-invoice schema if your turnover exceeds the threshold</li>
        <li><strong>Audit trail:</strong> Proper invoices create a clear audit trail for GST audits and assessments</li>
        <li><strong>Legal validity:</strong> A valid tax invoice is required as proof in case of disputes, refund claims, or assessment proceedings</li>
      </ul>

      {/* Section 2 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">Who Must Issue a GST Invoice?</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        Every registered person under GST must issue a tax invoice for every supply of goods or services. This includes:
      </p>

      <ul className="list-disc pl-6 text-gray-700 space-y-2 mb-6">
        <li>Regular taxpayers making taxable supplies</li>
        <li>E-commerce operators collecting TCS</li>
        <li>Input Service Distributors</li>
        <li>Persons liable to pay tax under reverse charge</li>
        <li>Casual and non-resident taxable persons</li>
      </ul>

      <p className="text-gray-700 leading-relaxed mb-4">
        <Link href="/blog/gst-composition-scheme-guide" className="text-blue-600 hover:text-blue-700 underline">Composition scheme dealers</Link> cannot issue a tax invoice because they are not allowed to collect GST from buyers. Instead, they must issue a <strong>Bill of Supply</strong>. Similarly, for exempt supplies and nil-rated supplies, a bill of supply is issued instead of a tax invoice.
      </p>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">Time Limits for Issuing Invoice</h3>

      <div className="overflow-x-auto mb-6">
        <table className="w-full border-collapse border border-gray-300 text-sm">
          <thead>
            <tr className="bg-gray-100">
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Type of Supply</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Time Limit</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="border border-gray-300 px-4 py-2">Goods — movement involved</td>
              <td className="border border-gray-300 px-4 py-2">Before or at the time of removal</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-2">Goods — no movement (e.g., property transfer)</td>
              <td className="border border-gray-300 px-4 py-2">Before or at the time of delivery</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-2">Services — general</td>
              <td className="border border-gray-300 px-4 py-2">Within 30 days from the date of supply</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-2">Services — banks &amp; financial institutions</td>
              <td className="border border-gray-300 px-4 py-2">Within 45 days from the date of supply</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-2">Continuous supply of goods</td>
              <td className="border border-gray-300 px-4 py-2">Before or at the time of each statement of account or payment</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-2">Continuous supply of services</td>
              <td className="border border-gray-300 px-4 py-2">On or before the due date of payment</td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* Section 3 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">Mandatory Fields in a GST Invoice (Rule 46)</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        Rule 46 of the CGST Rules prescribes 16 mandatory fields that every tax invoice must contain. Missing any of these fields can make your invoice non-compliant, potentially leading to ITC denial for your buyer and penalties for you.
      </p>

      <div className="overflow-x-auto mb-6">
        <table className="w-full border-collapse border border-gray-300 text-sm">
          <thead>
            <tr className="bg-gray-100">
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">S.No.</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Field</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Details</th>
            </tr>
          </thead>
          <tbody>
            {[
              ['1', 'Supplier Name', 'Legal name of the business as registered under GST'],
              ['2', 'Supplier Address', 'Complete address of the place of business'],
              ['3', 'Supplier GSTIN', '15-digit GST Identification Number of the supplier'],
              ['4', 'Invoice Serial Number', 'Consecutive serial number, max 16 characters, unique for each financial year'],
              ['5', 'Date of Issue', 'Date on which the invoice is issued'],
              ['6', 'Recipient Name', 'Name of the buyer (if registered or invoice value exceeds ₹50,000)'],
              ['7', 'Recipient Address', 'Address of the buyer (for registered buyers or value above ₹50,000)'],
              ['8', 'Recipient GSTIN/UIN', 'Buyer\'s GSTIN or UIN if they are registered under GST'],
              ['9', 'HSN/SAC Code', 'Harmonized System of Nomenclature code for goods or Services Accounting Code for services'],
              ['10', 'Description', 'Clear description of the goods or services supplied'],
              ['11', 'Quantity & Unit', 'Quantity of goods in the applicable unit of measurement'],
              ['12', 'Total Value', 'Total value of the supply of goods or services'],
              ['13', 'Taxable Value', 'Value after deducting discounts (on which tax is calculated)'],
              ['14', 'Tax Rate & Amount', 'CGST, SGST/UTGST, or IGST rate and amount separately'],
              ['15', 'Place of Supply', 'State name and code where the supply is delivered (for inter-state)'],
              ['16', 'Reverse Charge', 'Whether tax is payable on reverse charge basis (Yes/No)'],
            ].map(([num, field, details], i) => (
              <tr key={num} className={i % 2 === 1 ? 'bg-gray-50' : ''}>
                <td className="border border-gray-300 px-4 py-2 text-center">{num}</td>
                <td className="border border-gray-300 px-4 py-2 font-medium">{field}</td>
                <td className="border border-gray-300 px-4 py-2">{details}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="text-gray-700 leading-relaxed mb-4">
        Additionally, the invoice must bear the signature or digital signature of the supplier or an authorized representative. For goods, the invoice must also mention whether the supply is on approval, ex-works, FOB, or CIF basis. The invoice value must include all applicable taxes, duties, and charges.
      </p>

      <div className="bg-yellow-50 border-l-4 border-yellow-500 p-4 rounded mb-6">
        <p className="text-yellow-900 font-medium">Important: Invoice Serial Number Rules</p>
        <p className="text-yellow-800 text-sm mt-1">The invoice serial number must be consecutive, contain only alphanumeric characters with special characters like dash (-) and slash (/), and cannot exceed 16 characters. It must be unique for each financial year. Businesses with multiple branches can use different series for each branch (e.g., DEL/26-27/001 for Delhi branch, MUM/26-27/001 for Mumbai branch).</p>
      </div>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">Additional Fields for Specific Cases</h3>

      <ul className="list-disc pl-6 text-gray-700 space-y-2 mb-6">
        <li><strong>Export invoices:</strong> Must mention &quot;Supply meant for export on payment of IGST&quot; or &quot;Supply meant for export under bond or Letter of Undertaking without payment of IGST&quot;</li>
        <li><strong>SEZ supplies:</strong> Must mention &quot;Supply meant for SEZ developer/unit on payment of IGST&quot; or &quot;under bond/LUT&quot;</li>
        <li><strong>E-commerce:</strong> Must include the e-commerce operator&apos;s GSTIN if supply is made through an e-commerce platform</li>
        <li><strong>Reverse charge:</strong> Must contain a declaration that tax is payable on reverse charge</li>
      </ul>

      {/* Section 4 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">Types of GST Invoices and Documents</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        The GST framework prescribes different types of invoices and documents for different scenarios. Here is a comparison of all document types:
      </p>

      <div className="overflow-x-auto mb-6">
        <table className="w-full border-collapse border border-gray-300 text-sm">
          <thead>
            <tr className="bg-gray-100">
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Document Type</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">When to Issue</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Key Feature</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="border border-gray-300 px-4 py-2 font-medium">Tax Invoice</td>
              <td className="border border-gray-300 px-4 py-2">Regular taxable supplies by registered persons</td>
              <td className="border border-gray-300 px-4 py-2">Contains tax breakup; enables ITC for buyer</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-2 font-medium">Bill of Supply</td>
              <td className="border border-gray-300 px-4 py-2">Composition dealers, exempt/nil-rated supplies</td>
              <td className="border border-gray-300 px-4 py-2">No tax charged; no ITC available to buyer</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-2 font-medium">Receipt Voucher</td>
              <td className="border border-gray-300 px-4 py-2">Advance payment received before supply</td>
              <td className="border border-gray-300 px-4 py-2">Tax paid on advance; adjusted against final invoice</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-2 font-medium">Refund Voucher</td>
              <td className="border border-gray-300 px-4 py-2">When advance is refunded and supply is not made</td>
              <td className="border border-gray-300 px-4 py-2">References original receipt voucher</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-2 font-medium">Payment Voucher</td>
              <td className="border border-gray-300 px-4 py-2">Paying tax under reverse charge mechanism</td>
              <td className="border border-gray-300 px-4 py-2">Issued by the recipient (buyer) instead of supplier</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-2 font-medium">Delivery Challan</td>
              <td className="border border-gray-300 px-4 py-2">Goods sent on approval, job work, or without supply</td>
              <td className="border border-gray-300 px-4 py-2">Not a tax document; used for transport purposes</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-2 font-medium">Credit Note</td>
              <td className="border border-gray-300 px-4 py-2">Sales return, post-sale discount, excess tax charged</td>
              <td className="border border-gray-300 px-4 py-2">Reduces tax liability; must reference original invoice</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-2 font-medium">Debit Note</td>
              <td className="border border-gray-300 px-4 py-2">Additional tax charged, price increase</td>
              <td className="border border-gray-300 px-4 py-2">Increases tax liability; must reference original invoice</td>
            </tr>
          </tbody>
        </table>
      </div>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">Number of Copies Required</h3>

      <p className="text-gray-700 leading-relaxed mb-4">
        For <strong>supply of goods</strong>, a tax invoice must be prepared in triplicate: the original for the recipient, the duplicate for the transporter, and the triplicate for the supplier. For <strong>supply of services</strong>, the invoice is prepared in duplicate: the original for the recipient and the duplicate for the supplier.
      </p>

      {/* Section 5 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">GST Invoice Format Template</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        Below is a sample GST tax invoice template showing all mandatory fields filled with example data. You can use this as a reference when designing your invoice format. Remember, the government does not prescribe a fixed visual layout — your invoice can look different as long as it includes all required fields.
      </p>

      <div className="border-2 border-gray-400 rounded-lg p-6 mb-8 bg-white font-mono text-sm">
        <div className="text-center border-b border-gray-300 pb-4 mb-4">
          <p className="text-lg font-bold">TAX INVOICE</p>
          <p className="text-xs text-gray-500">(Original for Recipient)</p>
        </div>

        <div className="grid grid-cols-2 gap-4 mb-4">
          <div>
            <p className="font-bold text-xs text-gray-500 mb-1">SUPPLIER DETAILS</p>
            <p className="font-bold">ABC Trading Company</p>
            <p>123, MG Road, Bengaluru</p>
            <p>Karnataka - 560001</p>
            <p><strong>GSTIN:</strong> 29ABCDE1234F1Z5</p>
            <p><strong>PAN:</strong> ABCDE1234F</p>
          </div>
          <div className="text-right">
            <p><strong>Invoice No:</strong> ABC/26-27/0042</p>
            <p><strong>Date:</strong> 15-Oct-2026</p>
            <p><strong>Place of Supply:</strong> Karnataka (29)</p>
            <p><strong>Reverse Charge:</strong> No</p>
          </div>
        </div>

        <div className="border-t border-gray-300 pt-4 mb-4">
          <p className="font-bold text-xs text-gray-500 mb-1">BILL TO</p>
          <p className="font-bold">XYZ Enterprises Pvt Ltd</p>
          <p>456, 100 Feet Road, Bengaluru</p>
          <p>Karnataka - 560034</p>
          <p><strong>GSTIN:</strong> 29XYZAB5678C1D3</p>
        </div>

        <div className="border-t border-b border-gray-300 py-2 mb-2">
          <div className="grid grid-cols-8 gap-1 text-xs font-bold text-gray-600">
            <span>S.No</span>
            <span className="col-span-2">Description</span>
            <span>HSN</span>
            <span>Qty</span>
            <span>Rate</span>
            <span>Taxable Amt</span>
            <span>GST</span>
          </div>
        </div>

        <div className="border-b border-gray-200 py-2 mb-2">
          <div className="grid grid-cols-8 gap-1 text-xs">
            <span>1</span>
            <span className="col-span-2">Laptop Computer</span>
            <span>8471</span>
            <span>2 Nos</span>
            <span>45,000</span>
            <span>90,000</span>
            <span>18%</span>
          </div>
        </div>
        <div className="border-b border-gray-200 py-2 mb-2">
          <div className="grid grid-cols-8 gap-1 text-xs">
            <span>2</span>
            <span className="col-span-2">Wireless Mouse</span>
            <span>8471</span>
            <span>2 Nos</span>
            <span>800</span>
            <span>1,600</span>
            <span>18%</span>
          </div>
        </div>

        <div className="border-t border-gray-300 pt-4 mt-4">
          <div className="flex justify-between text-xs mb-1">
            <span>Total Taxable Value</span>
            <span className="font-bold">&#8377;91,600.00</span>
          </div>
          <div className="flex justify-between text-xs mb-1">
            <span>CGST @ 9%</span>
            <span>&#8377;8,244.00</span>
          </div>
          <div className="flex justify-between text-xs mb-1">
            <span>SGST @ 9%</span>
            <span>&#8377;8,244.00</span>
          </div>
          <div className="flex justify-between text-xs font-bold border-t border-gray-300 pt-2 mt-2">
            <span>TOTAL INVOICE VALUE</span>
            <span>&#8377;1,08,088.00</span>
          </div>
          <p className="text-xs mt-2 text-gray-600">Amount in words: Rupees One Lakh Eight Thousand Eighty-Eight Only</p>
        </div>

        <div className="border-t border-gray-300 mt-4 pt-4 flex justify-between text-xs">
          <div>
            <p className="text-gray-500">Bank Details:</p>
            <p>A/C: 1234567890 | IFSC: SBIN0001234</p>
            <p>State Bank of India, MG Road Branch</p>
          </div>
          <div className="text-right">
            <p className="text-gray-500 mb-8">For ABC Trading Company</p>
            <p>Authorised Signatory</p>
          </div>
        </div>
      </div>

      <div className="bg-blue-50 border-l-4 border-blue-500 p-4 rounded mb-6">
        <p className="text-blue-900 font-medium">Pro Tip</p>
        <p className="text-blue-800 text-sm mt-1">Use the <Link href="/" className="text-blue-600 underline">GSTIndia GST Calculator</Link> to verify your tax calculations before finalizing invoices. Even a small error in CGST/SGST/IGST calculation can cause mismatches during return filing and ITC reconciliation.</p>
      </div>

      {/* Section 6 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">Bill of Supply Format</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        A Bill of Supply is issued instead of a tax invoice in the following cases:
      </p>

      <ul className="list-disc pl-6 text-gray-700 space-y-2 mb-6">
        <li><strong>Composition dealers:</strong> Businesses registered under the <Link href="/blog/gst-composition-scheme-guide" className="text-blue-600 hover:text-blue-700 underline">GST Composition Scheme</Link> cannot charge GST, so they issue a bill of supply</li>
        <li><strong>Exempt supplies:</strong> Goods or services that are exempt from GST</li>
        <li><strong>Nil-rated supplies:</strong> Supplies taxed at 0% GST rate</li>
      </ul>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">Mandatory Fields in Bill of Supply</h3>

      <p className="text-gray-700 leading-relaxed mb-4">
        A bill of supply under Rule 49 must contain:
      </p>

      <ul className="list-disc pl-6 text-gray-700 space-y-2 mb-6">
        <li>Supplier&apos;s name, address, and GSTIN</li>
        <li>Consecutive serial number (max 16 characters)</li>
        <li>Date of issue</li>
        <li>Recipient&apos;s name and address (if value exceeds ₹50,000)</li>
        <li>HSN/SAC code</li>
        <li>Description of goods or services</li>
        <li>Value of supply</li>
        <li>Signature or digital signature</li>
      </ul>

      <div className="bg-yellow-50 border-l-4 border-yellow-500 p-4 rounded mb-6">
        <p className="text-yellow-900 font-medium">Mandatory Declaration for Composition Dealers</p>
        <p className="text-yellow-800 text-sm mt-1">Every bill of supply issued by a composition dealer must prominently display: <strong>&quot;Composition taxable person, not eligible to collect tax on supplies&quot;</strong>. Failure to include this declaration attracts a penalty.</p>
      </div>

      <p className="text-gray-700 leading-relaxed mb-4">
        The key difference from a tax invoice is that a bill of supply does <strong>not</strong> contain any tax breakup (no CGST, SGST, or IGST columns). Since no tax is charged, the buyer cannot claim ITC on purchases made against a bill of supply.
      </p>

      {/* Section 7 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">E-Invoicing Under GST</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        E-invoicing (electronic invoicing) is a system where B2B invoices are authenticated electronically by the GST Network (GSTN) through the Invoice Registration Portal (IRP). It was introduced to curb tax evasion, enable real-time tracking of invoices, and reduce data entry errors through auto-population of return forms.
      </p>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">What is an E-Invoice?</h3>

      <p className="text-gray-700 leading-relaxed mb-4">
        An e-invoice is not an invoice generated on a government portal. Rather, it is a regular invoice generated by your billing software that is reported to the IRP (Invoice Registration Portal) in a standardized JSON format. The IRP validates the invoice data, generates a unique <strong>Invoice Reference Number (IRN)</strong>, digitally signs the invoice, and returns a <strong>QR code</strong> that must be printed on the invoice.
      </p>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">Who Must Generate E-Invoices?</h3>

      <p className="text-gray-700 leading-relaxed mb-4">
        E-invoicing applies to businesses based on their aggregate annual turnover in any preceding financial year from 2017-18 onwards. The threshold has been progressively reduced:
      </p>

      <div className="overflow-x-auto mb-6">
        <table className="w-full border-collapse border border-gray-300 text-sm">
          <thead>
            <tr className="bg-gray-100">
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Effective Date</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Turnover Threshold</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="border border-gray-300 px-4 py-2">1 October 2020</td>
              <td className="border border-gray-300 px-4 py-2">&#8377;500 crore and above</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-2">1 January 2021</td>
              <td className="border border-gray-300 px-4 py-2">&#8377;100 crore and above</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-2">1 April 2021</td>
              <td className="border border-gray-300 px-4 py-2">&#8377;50 crore and above</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-2">1 April 2022</td>
              <td className="border border-gray-300 px-4 py-2">&#8377;20 crore and above</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-2">1 October 2022</td>
              <td className="border border-gray-300 px-4 py-2">&#8377;10 crore and above</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-2">1 August 2023</td>
              <td className="border border-gray-300 px-4 py-2">&#8377;5 crore and above</td>
            </tr>
          </tbody>
        </table>
      </div>

      <p className="text-gray-700 leading-relaxed mb-4">
        Certain categories are exempt from e-invoicing even if their turnover exceeds the threshold: Special Economic Zone (SEZ) units, insurers, banking companies, financial institutions, NBFCs, GTA (Goods Transport Agencies), and passenger transport service suppliers.
      </p>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">How to Generate an E-Invoice</h3>

      <ol className="list-decimal pl-6 text-gray-700 space-y-2 mb-6">
        <li>Generate a regular invoice using your billing/ERP software</li>
        <li>Prepare the invoice data in the prescribed JSON schema (as per e-invoice schema v1.03 or later)</li>
        <li>Upload the JSON to the IRP portal (einvoice1.gst.gov.in) via API or the web portal</li>
        <li>The IRP validates the data, checks for duplicates (based on supplier GSTIN + invoice number + FY)</li>
        <li>On successful validation, the IRP generates a unique IRN (Invoice Reference Number) and a signed QR code</li>
        <li>Print the IRN and QR code on the invoice before issuing to the buyer</li>
        <li>The IRP auto-populates the data into your GSTR-1 and the buyer&apos;s GSTR-2A/2B</li>
      </ol>

      <div className="bg-yellow-50 border-l-4 border-yellow-500 p-4 rounded mb-6">
        <p className="text-yellow-900 font-medium">Penalty for E-Invoice Non-Compliance</p>
        <p className="text-yellow-800 text-sm mt-1">If you are required to generate e-invoices but fail to do so, the invoice is treated as if it was never issued. This means your buyer cannot claim ITC, and you face a penalty of &#8377;10,000 or 100% of the tax due, whichever is higher, per invoice under Section 122 of the CGST Act.</p>
      </div>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">E-Invoice Cancellation</h3>

      <p className="text-gray-700 leading-relaxed mb-4">
        An e-invoice can be cancelled on the IRP portal within 24 hours of generation. After 24 hours, you must cancel it on the GST portal by issuing a credit note. The IRN of a cancelled invoice cannot be reused. When cancelling, you must provide a reason (duplicate, data entry error, order cancelled, etc.).
      </p>

      {/* Section 8 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">HSN Code Requirements on GST Invoices</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        Every GST invoice must mention the <Link href="/blog/gst-hsn-code-list" className="text-blue-600 hover:text-blue-700 underline">HSN (Harmonized System of Nomenclature) code</Link> for goods or SAC (Services Accounting Code) for services. The number of digits required depends on your turnover:
      </p>

      <div className="overflow-x-auto mb-6">
        <table className="w-full border-collapse border border-gray-300 text-sm">
          <thead>
            <tr className="bg-gray-100">
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Annual Turnover</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">HSN Digits Required</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Note</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="border border-gray-300 px-4 py-2">Up to &#8377;5 crore</td>
              <td className="border border-gray-300 px-4 py-2">4-digit HSN code</td>
              <td className="border border-gray-300 px-4 py-2">For B2B supplies on invoices</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-2">Above &#8377;5 crore</td>
              <td className="border border-gray-300 px-4 py-2">6-digit HSN code</td>
              <td className="border border-gray-300 px-4 py-2">Mandatory on all invoices</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-2">E-invoices (B2B)</td>
              <td className="border border-gray-300 px-4 py-2">6-digit HSN code</td>
              <td className="border border-gray-300 px-4 py-2">Regardless of turnover</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div className="bg-blue-50 border-l-4 border-blue-500 p-4 rounded mb-6">
        <p className="text-blue-900 font-medium">Find Your HSN Code</p>
        <p className="text-blue-800 text-sm mt-1">Use the <Link href="/" className="text-blue-600 underline">GSTIndia HSN Code Finder</Link> to search and find the correct HSN or SAC code for your products and services. For a complete chapter-wise list, see our <Link href="/blog/gst-hsn-code-list" className="text-blue-600 underline">HSN Code List guide</Link>.</p>
      </div>

      {/* Section 9 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">Common Invoice Mistakes and Penalties</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        Invoice errors are among the most common reasons for GST notices and ITC denials. Here are the mistakes you must avoid:
      </p>

      <div className="space-y-4 mb-6">
        <div className="bg-white border rounded-lg p-4">
          <h4 className="font-semibold text-gray-900 mb-2">1. Wrong or Missing GSTIN</h4>
          <p className="text-gray-700 text-sm">Entering an incorrect GSTIN for the buyer or supplier leads to ITC mismatch. The buyer&apos;s GSTR-2B will not reflect the invoice, and they cannot claim ITC. Always verify GSTINs using the <Link href="/" className="text-blue-600 underline">GSTIndia GSTIN Validator</Link> before issuing invoices.</p>
        </div>
        <div className="bg-white border rounded-lg p-4">
          <h4 className="font-semibold text-gray-900 mb-2">2. Missing or Incorrect HSN/SAC Code</h4>
          <p className="text-gray-700 text-sm">Wrong HSN codes can result in incorrect tax rate application. If the applicable rate is 18% but you charge 12% due to a wrong HSN code, you will receive a demand notice for the differential tax plus interest.</p>
        </div>
        <div className="bg-white border rounded-lg p-4">
          <h4 className="font-semibold text-gray-900 mb-2">3. Incorrect Tax Calculation</h4>
          <p className="text-gray-700 text-sm">Charging IGST on an intra-state supply (or CGST+SGST on an inter-state supply) is a common error. The place of supply determines which tax applies. Getting this wrong creates complications for both parties.</p>
        </div>
        <div className="bg-white border rounded-lg p-4">
          <h4 className="font-semibold text-gray-900 mb-2">4. Non-sequential Invoice Numbers</h4>
          <p className="text-gray-700 text-sm">Invoice numbers must be consecutive and sequential. Gaps in invoice numbering raise red flags during audits and can lead to scrutiny proceedings.</p>
        </div>
        <div className="bg-white border rounded-lg p-4">
          <h4 className="font-semibold text-gray-900 mb-2">5. Missing Place of Supply</h4>
          <p className="text-gray-700 text-sm">For inter-state supplies, the place of supply must be mentioned on the invoice. Missing this field makes the invoice non-compliant and can lead to disputes about the applicable tax (IGST vs CGST+SGST).</p>
        </div>
        <div className="bg-white border rounded-lg p-4">
          <h4 className="font-semibold text-gray-900 mb-2">6. Not Generating E-Invoice When Required</h4>
          <p className="text-gray-700 text-sm">If your turnover exceeds &#8377;5 crore, every B2B invoice must be registered on the IRP. An unregistered invoice is treated as invalid — your buyer cannot claim ITC on it.</p>
        </div>
      </div>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">Penalties Under Section 122</h3>

      <p className="text-gray-700 leading-relaxed mb-4">
        The CGST Act prescribes the following penalties for invoice-related offences:
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
              <td className="border border-gray-300 px-4 py-2">Not issuing invoice or issuing incorrect invoice</td>
              <td className="border border-gray-300 px-4 py-2">&#8377;10,000 or tax amount involved, whichever is higher</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-2">Issuing invoice without actual supply (fake invoice)</td>
              <td className="border border-gray-300 px-4 py-2">&#8377;10,000 or tax amount involved, whichever is higher</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-2">Not registering invoice on IRP (e-invoicing)</td>
              <td className="border border-gray-300 px-4 py-2">&#8377;10,000 or 100% of tax due, whichever is higher</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-2">Issuing invoice with wrong GSTIN to enable fraudulent ITC</td>
              <td className="border border-gray-300 px-4 py-2">100% of tax amount + prosecution for amounts above &#8377;5 crore</td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* Section 10 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">GST Invoice for Different Business Types</h2>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">Freelancers and Consultants</h3>

      <p className="text-gray-700 leading-relaxed mb-4">
        If you are a freelancer or consultant registered under GST, you must issue a tax invoice for every service engagement. Use the appropriate <Link href="/blog/gst-hsn-code-list" className="text-blue-600 hover:text-blue-700 underline">SAC code</Link> for your service category (e.g., 998311 for management consulting, 998314 for IT consulting). Your invoice must clearly describe the services rendered, the period of service, and the agreed fee. For services provided to clients outside India, mention the LUT number and state &quot;Export of services — supply without payment of IGST under LUT&quot;.
      </p>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">E-Commerce Sellers</h3>

      <p className="text-gray-700 leading-relaxed mb-4">
        If you sell through e-commerce platforms like Amazon, Flipkart, or Meesho, you must issue a tax invoice for every order. The invoice must mention the e-commerce operator&apos;s GSTIN in addition to the buyer&apos;s details. Since e-commerce supplies are inter-state in nature, IGST applies. Note that sellers on e-commerce platforms cannot opt for the <Link href="/blog/gst-composition-scheme-guide" className="text-blue-600 hover:text-blue-700 underline">composition scheme</Link>.
      </p>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">Exporters</h3>

      <p className="text-gray-700 leading-relaxed mb-4">
        Export invoices have additional requirements. You must include the buyer&apos;s name and address, the destination country, and the shipping bill number and date. Exporters can either pay IGST and claim a refund, or export under a Letter of Undertaking (LUT) without paying IGST. The invoice must clearly state which option is being used. Export invoices must be in a convertible foreign exchange or Indian rupees.
      </p>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">Composition Dealers</h3>

      <p className="text-gray-700 leading-relaxed mb-4">
        <Link href="/blog/gst-composition-scheme-guide" className="text-blue-600 hover:text-blue-700 underline">Composition dealers</Link> issue a Bill of Supply instead of a tax invoice. They cannot charge GST to customers and cannot issue tax invoices. The bill of supply must contain the mandatory declaration: &quot;Composition taxable person, not eligible to collect tax on supplies.&quot; Since composition dealers do not charge tax, their buyers cannot claim ITC on such purchases.
      </p>

      {/* Section 11 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">How GSTIndia Tools Can Help</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        Creating compliant GST invoices becomes easier with the right tools. The <Link href="/" className="text-blue-600 hover:text-blue-700 underline">GSTIndia platform</Link> by DoAide offers free tools to streamline your invoicing process:
      </p>

      <ul className="list-disc pl-6 text-gray-700 space-y-2 mb-6">
        <li><strong><Link href="/" className="text-blue-600 underline">GST Calculator:</Link></strong> Calculate CGST, SGST, and IGST accurately for any amount and tax rate before adding to invoices</li>
        <li><strong><Link href="/" className="text-blue-600 underline">HSN Code Finder:</Link></strong> Search and find the correct HSN/SAC code for your products and services instantly</li>
        <li><strong><Link href="/" className="text-blue-600 underline">GSTIN Validator:</Link></strong> Verify your buyer&apos;s GSTIN before issuing invoices to avoid ITC mismatches</li>
      </ul>

      <div className="bg-gradient-to-r from-blue-600 to-blue-700 rounded-xl p-6 text-white mb-8">
        <h3 className="text-xl font-bold mb-2">Create Error-Free GST Invoices</h3>
        <p className="text-blue-100 mb-4">Use GSTIndia&apos;s free tools to calculate GST, find HSN codes, and validate GSTINs — ensure every invoice you issue is compliant.</p>
        <Link href="/" className="inline-block bg-white text-blue-600 font-semibold px-6 py-2 rounded-lg hover:bg-blue-50 transition-colors">
          Try Free GST Tools &rarr;
        </Link>
      </div>

      {/* FAQ Section */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-6">Frequently Asked Questions (FAQ)</h2>

      <div className="space-y-4 mb-8">
        {[
          {
            q: 'Is GST invoice mandatory for all businesses?',
            a: 'A GST tax invoice is mandatory for every registered person making taxable supplies. However, composition dealers issue a Bill of Supply instead. Businesses below the registration threshold (₹40 lakh for goods, ₹20 lakh for services) who have not voluntarily registered are not required to issue GST invoices.',
          },
          {
            q: 'What is the time limit for issuing a GST invoice?',
            a: 'For goods involving movement, the invoice must be issued before or at the time of removal. For goods without movement, before or at the time of delivery. For services, within 30 days from the date of supply (45 days for banks and financial institutions). For continuous supply contracts, before or at the time of each payment due date.',
          },
          {
            q: 'Can I issue a GST invoice without HSN code?',
            a: 'HSN codes are mandatory on B2B invoices for all registered taxpayers. The number of digits required depends on your turnover — 4-digit for turnover up to ₹5 crore and 6-digit for turnover above ₹5 crore. For e-invoices, 6-digit HSN is always required. Omitting HSN codes can lead to penalties and issues during return filing.',
          },
          {
            q: 'What is the difference between tax invoice and bill of supply?',
            a: 'A tax invoice is issued for taxable supplies and contains the tax breakup (CGST, SGST, IGST amounts). It enables the buyer to claim ITC. A bill of supply is issued by composition dealers or for exempt/nil-rated supplies and does not contain any tax amounts. The buyer cannot claim ITC on a bill of supply.',
          },
          {
            q: 'Is digital signature mandatory on a GST invoice?',
            a: 'A physical or digital signature of the supplier or an authorized representative is required on the invoice. For e-invoices, the IRP digitally signs the invoice with a QR code, which is considered sufficient. Many businesses use scanned signature images or digital signatures on computer-generated invoices, which is accepted.',
          },
          {
            q: 'What is the penalty for not issuing a GST invoice?',
            a: 'Under Section 122 of the CGST Act, not issuing an invoice or issuing an incorrect invoice attracts a penalty of ₹10,000 or the tax amount involved, whichever is higher. For fake invoices (invoices without actual supply), the penalty is the same plus potential prosecution for amounts exceeding ₹5 crore.',
          },
          {
            q: 'How many copies of a GST invoice are required?',
            a: 'For supply of goods, three copies are required: Original for the recipient, Duplicate for the transporter, and Triplicate for the supplier. For supply of services, two copies: Original for the recipient and Duplicate for the supplier. These can be in physical or electronic form.',
          },
          {
            q: 'What is e-invoicing and who needs to generate e-invoices?',
            a: 'E-invoicing is a system where B2B invoices are reported to the Invoice Registration Portal (IRP) to get a unique IRN and QR code. It is mandatory for businesses with aggregate annual turnover exceeding ₹5 crore (from August 2023). E-invoicing does not mean generating invoices on a government portal — you generate them on your own software and register them on the IRP.',
          },
          {
            q: 'Can I cancel or amend a GST invoice after issuing?',
            a: 'You cannot amend a GST invoice directly. For corrections, you must issue a credit note (to reduce the value/tax) or debit note (to increase the value/tax) referencing the original invoice. For e-invoices, cancellation is possible on the IRP within 24 hours. After 24 hours, you must issue a credit note instead.',
          },
          {
            q: 'What is the maximum length of a GST invoice number?',
            a: 'The invoice serial number cannot exceed 16 characters. It must be consecutive, contain only alphanumeric characters and special characters like dash (-) and slash (/), and be unique for each financial year. Businesses with multiple branches typically use a branch code prefix (e.g., DEL/26-27/001).',
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
        A properly formatted GST invoice is the foundation of GST compliance. It determines whether your buyer can claim ITC, whether your GSTR-1 filing will be smooth, and whether you stay on the right side of the tax department. By ensuring your invoices contain all 16 mandatory fields under Rule 46, using the correct HSN/SAC codes, and complying with e-invoicing requirements, you can avoid penalties and build trust with your business partners.
      </p>

      <p className="text-gray-700 leading-relaxed mb-4">
        Whether you are a small trader issuing manual invoices or a large manufacturer using ERP-integrated e-invoicing, the fundamentals remain the same. Use the <Link href="/" className="text-blue-600 hover:text-blue-700 underline">GSTIndia tools</Link> to verify your calculations, find HSN codes, and validate GSTINs before every invoice. For more details on filing the returns that rely on your invoices, see our <Link href="/blog/gst-return-filing-guide-2026-27" className="text-blue-600 hover:text-blue-700 underline">GST Return Filing Guide</Link>. For getting registered under GST, visit our <Link href="/blog/gst-registration-online-guide" className="text-blue-600 hover:text-blue-700 underline">GST Registration Guide</Link>.
      </p>

      {/* JSON-LD Structured Data */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            '@context': 'https://schema.org',
            '@type': 'Article',
            headline: 'GST Invoice Format 2026: Mandatory Fields, Templates & E-Invoicing Rules',
            description: 'Complete guide to GST invoice format with mandatory fields, templates, e-invoicing rules, and bill of supply format for Indian businesses in 2026-27.',
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
            url: 'https://gst.doaide.com/blog/gst-invoice-format-guide',
            mainEntityOfPage: 'https://gst.doaide.com/blog/gst-invoice-format-guide',
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
                name: 'Is GST invoice mandatory for all businesses?',
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: 'A GST tax invoice is mandatory for every registered person making taxable supplies. Composition dealers issue a Bill of Supply instead. Businesses below the registration threshold are not required to issue GST invoices.',
                },
              },
              {
                '@type': 'Question',
                name: 'What is the time limit for issuing a GST invoice?',
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: 'For goods involving movement, before or at the time of removal. For services, within 30 days from the date of supply (45 days for banks). For continuous supply, before or at each payment due date.',
                },
              },
              {
                '@type': 'Question',
                name: 'Can I issue a GST invoice without HSN code?',
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: 'HSN codes are mandatory on B2B invoices. 4-digit for turnover up to ₹5 crore and 6-digit for turnover above ₹5 crore. For e-invoices, 6-digit HSN is always required.',
                },
              },
              {
                '@type': 'Question',
                name: 'What is the difference between tax invoice and bill of supply?',
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: 'A tax invoice contains tax breakup and enables ITC claim. A bill of supply is for composition dealers or exempt supplies and has no tax amounts — the buyer cannot claim ITC on it.',
                },
              },
              {
                '@type': 'Question',
                name: 'Is digital signature mandatory on a GST invoice?',
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: 'A physical or digital signature is required. For e-invoices, the IRP digital signature via QR code is sufficient. Scanned signature images on computer-generated invoices are accepted.',
                },
              },
              {
                '@type': 'Question',
                name: 'What is the penalty for not issuing a GST invoice?',
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: 'Under Section 122, the penalty is ₹10,000 or the tax amount involved, whichever is higher. For fake invoices, prosecution is possible for amounts exceeding ₹5 crore.',
                },
              },
              {
                '@type': 'Question',
                name: 'How many copies of a GST invoice are required?',
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: 'For goods: three copies (recipient, transporter, supplier). For services: two copies (recipient, supplier). These can be physical or electronic.',
                },
              },
              {
                '@type': 'Question',
                name: 'What is e-invoicing and who needs to generate e-invoices?',
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: 'E-invoicing requires B2B invoices to be reported to the IRP for a unique IRN and QR code. Mandatory for businesses with turnover exceeding ₹5 crore from August 2023.',
                },
              },
              {
                '@type': 'Question',
                name: 'Can I cancel or amend a GST invoice after issuing?',
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: 'Invoices cannot be amended directly. Issue credit/debit notes referencing the original. E-invoices can be cancelled on IRP within 24 hours; after that, use a credit note.',
                },
              },
              {
                '@type': 'Question',
                name: 'What is the maximum length of a GST invoice number?',
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: 'Maximum 16 characters. Must be consecutive, alphanumeric with dash/slash allowed, unique per financial year.',
                },
              },
            ],
          }),
        }}
      />
      <div className="mt-8 pt-8 border-t dark:border-gray-800">
        <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">Found this guide helpful? Share it:</p>
        <ShareButtons
          title="GST Invoice Format 2026: Rules, Mandatory Fields & Templates"
          url="/blog/gst-invoice-format-guide"
        />
      </div>
    </article>
  );
}
