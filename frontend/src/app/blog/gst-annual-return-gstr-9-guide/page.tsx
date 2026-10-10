import type { Metadata } from 'next';
import Link from 'next/link';
import { ShareButtons } from '@/components/blog/share-buttons';

export const metadata: Metadata = {
  title: 'GSTR-9 Annual Return Guide 2026 — Filing & Deadlines',
  description: 'Complete GSTR-9 annual return guide for 2026. Who must file, due dates, step-by-step filling instructions, GSTR-9C reconciliation & common mistakes.',
  openGraph: {
    title: 'GSTR-9 Annual Return Guide 2026 — Filing & Deadlines',
    description: 'Complete GSTR-9 annual return guide. Who must file, due dates, step-by-step filling instructions and GSTR-9C reconciliation.',
    url: 'https://gst.doaide.com/blog/gst-annual-return-gstr-9-guide',
    type: 'article',
  },
  alternates: {
    canonical: 'https://gst.doaide.com/blog/gst-annual-return-gstr-9-guide',
  },
};

export default function GSTR9AnnualReturnGuide() {
  return (
    <article className="max-w-4xl mx-auto px-4 py-12">
      <div className="mb-8">
        <span className="text-sm font-semibold text-blue-600 bg-blue-50 px-3 py-1 rounded-full">Annual Return</span>
        <span className="text-sm text-gray-500 ml-3">Updated: 10 October 2026</span>
        <span className="text-sm text-gray-500 ml-3">17 min read</span>
      </div>

      <h1 className="text-3xl sm:text-4xl font-bold text-gray-900 dark:text-gray-100 mb-6">
        GST Annual Return (GSTR-9) Guide 2026: Who Files, Deadlines &amp; How to Fill
      </h1>

      <ShareButtons
        title="GSTR-9 Annual Return Guide 2026: Filing & Deadlines"
        url="/blog/gst-annual-return-gstr-9-guide"
        className="mb-8"
      />

      <p className="text-lg text-gray-600 dark:text-gray-400 mb-8 leading-relaxed">
        GSTR-9 is the annual return that every regular GST-registered taxpayer must file once a year. It is a comprehensive summary of all the monthly/quarterly returns (GSTR-1 and GSTR-3B) filed during the financial year. This guide covers who needs to file GSTR-9, the due date, step-by-step instructions for filling each section, the GSTR-9C reconciliation statement, and common mistakes to avoid.
      </p>

      <div className="bg-blue-50 border-l-4 border-blue-500 p-4 rounded mb-8">
        <p className="text-blue-900 font-medium">Quick Navigation</p>
        <ul className="text-blue-800 text-sm mt-2 space-y-1">
          <li>&bull; What is GSTR-9?</li>
          <li>&bull; Who Must File GSTR-9?</li>
          <li>&bull; GSTR-9 Due Date for FY 2025-26</li>
          <li>&bull; GSTR-9 Table-by-Table Breakdown</li>
          <li>&bull; How to Fill GSTR-9: Step-by-Step</li>
          <li>&bull; GSTR-9C: Reconciliation Statement</li>
          <li>&bull; Late Fees for Late Filing</li>
          <li>&bull; Common Mistakes to Avoid</li>
          <li>&bull; FAQs</li>
        </ul>
      </div>

      {/* Section 1 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">What is GSTR-9?</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        GSTR-9 is the annual return under the Goods and Services Tax law, prescribed under Section 44 of the CGST Act, 2017. It is a consolidation of all the information furnished in the monthly or quarterly returns during a particular financial year. Think of it as the annual summary that reconciles your periodic returns with your books of accounts.
      </p>

      <p className="text-gray-700 leading-relaxed mb-4">
        The return consists of six parts and 19 tables covering outward supplies, inward supplies, ITC details, tax paid, demand and refund details, and HSN-wise summary. It pulls together data from GSTR-1 (outward supplies), GSTR-3B (summary returns with tax payment), and GSTR-2B (ITC statements) for the entire financial year.
      </p>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">Types of Annual Returns Under GST</h3>

      <div className="overflow-x-auto mb-6">
        <table className="w-full border-collapse border border-gray-300 text-sm">
          <thead>
            <tr className="bg-gray-100">
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Return Form</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Who Files</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Details</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="border border-gray-300 px-4 py-3 font-medium">GSTR-9</td>
              <td className="border border-gray-300 px-4 py-3">Regular taxpayers</td>
              <td className="border border-gray-300 px-4 py-3">Annual return with outward/inward supply details, ITC, tax paid</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-3 font-medium">GSTR-9C</td>
              <td className="border border-gray-300 px-4 py-3">Turnover above ₹5 crore</td>
              <td className="border border-gray-300 px-4 py-3">Self-certified reconciliation statement (audited financials vs GST returns)</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-3 font-medium">GSTR-4 (Annual)</td>
              <td className="border border-gray-300 px-4 py-3">Composition scheme dealers</td>
              <td className="border border-gray-300 px-4 py-3">Annual return for composition taxpayers (separate from GSTR-9)</td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* Section 2 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">Who Must File GSTR-9?</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        GSTR-9 filing requirements depend on your turnover and type of registration:
      </p>

      <div className="overflow-x-auto mb-6">
        <table className="w-full border-collapse border border-gray-300 text-sm">
          <thead>
            <tr className="bg-gray-100">
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Taxpayer Category</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">GSTR-9 Required?</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">GSTR-9C Required?</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="border border-gray-300 px-4 py-3">Turnover above ₹5 crore</td>
              <td className="border border-gray-300 px-4 py-3 font-medium text-red-600">Mandatory</td>
              <td className="border border-gray-300 px-4 py-3 font-medium text-red-600">Mandatory</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-3">Turnover ₹2 crore to ₹5 crore</td>
              <td className="border border-gray-300 px-4 py-3 font-medium text-red-600">Mandatory</td>
              <td className="border border-gray-300 px-4 py-3 font-medium text-green-600">Not Required</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-3">Turnover up to ₹2 crore</td>
              <td className="border border-gray-300 px-4 py-3 font-medium text-green-600">Optional</td>
              <td className="border border-gray-300 px-4 py-3 font-medium text-green-600">Not Required</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-3">Composition scheme dealers</td>
              <td className="border border-gray-300 px-4 py-3 font-medium text-green-600">Not Applicable (file GSTR-4)</td>
              <td className="border border-gray-300 px-4 py-3 font-medium text-green-600">Not Required</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-3">Input Service Distributors (ISD)</td>
              <td className="border border-gray-300 px-4 py-3 font-medium text-green-600">Not Required</td>
              <td className="border border-gray-300 px-4 py-3 font-medium text-green-600">Not Required</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-3">Casual Taxable Persons</td>
              <td className="border border-gray-300 px-4 py-3 font-medium text-green-600">Not Required</td>
              <td className="border border-gray-300 px-4 py-3 font-medium text-green-600">Not Required</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-3">Non-Resident Taxable Persons</td>
              <td className="border border-gray-300 px-4 py-3 font-medium text-green-600">Not Required</td>
              <td className="border border-gray-300 px-4 py-3 font-medium text-green-600">Not Required</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-3">TDS / TCS Deductors</td>
              <td className="border border-gray-300 px-4 py-3 font-medium text-green-600">Not Required</td>
              <td className="border border-gray-300 px-4 py-3 font-medium text-green-600">Not Required</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div className="bg-yellow-50 border-l-4 border-yellow-500 p-4 rounded mb-6">
        <p className="text-yellow-900 font-medium">Important Note</p>
        <p className="text-yellow-800 text-sm mt-1">Even though GSTR-9 is optional for taxpayers with turnover up to ₹2 crore, it is highly recommended to file it as it helps in reconciling your annual figures and avoiding future notices from the tax department.</p>
      </div>

      {/* Section 3 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">GSTR-9 Due Date for FY 2025-26</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        The due date for filing GSTR-9 (and GSTR-9C, if applicable) for a financial year is <strong>31 December of the following year</strong>. Therefore:
      </p>

      <div className="overflow-x-auto mb-6">
        <table className="w-full border-collapse border border-gray-300 text-sm">
          <thead>
            <tr className="bg-gray-100">
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Financial Year</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">GSTR-9 / GSTR-9C Due Date</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Status</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="border border-gray-300 px-4 py-3">FY 2024-25</td>
              <td className="border border-gray-300 px-4 py-3">31 December 2025</td>
              <td className="border border-gray-300 px-4 py-3">Filed / Overdue</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-3 font-medium">FY 2025-26</td>
              <td className="border border-gray-300 px-4 py-3 font-medium">31 December 2026</td>
              <td className="border border-gray-300 px-4 py-3 font-medium text-orange-600">Upcoming</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-3">FY 2026-27</td>
              <td className="border border-gray-300 px-4 py-3">31 December 2027</td>
              <td className="border border-gray-300 px-4 py-3">Future</td>
            </tr>
          </tbody>
        </table>
      </div>

      <p className="text-gray-700 leading-relaxed mb-4">
        The GST Council or CBIC may extend the due date via notification. Always check the latest notifications on cbic.gov.in for any extensions.
      </p>

      {/* Section 4 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">GSTR-9 Table-by-Table Breakdown</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        GSTR-9 has 6 parts with 19 tables. Here is a breakdown of each part and what data goes where:
      </p>

      <div className="overflow-x-auto mb-6">
        <table className="w-full border-collapse border border-gray-300 text-sm">
          <thead>
            <tr className="bg-gray-100">
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Part</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Tables</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Description</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Source</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="border border-gray-300 px-4 py-3 font-medium">Part I</td>
              <td className="border border-gray-300 px-4 py-3">1-3</td>
              <td className="border border-gray-300 px-4 py-3">Basic details &mdash; GSTIN, legal name, trade name, FY</td>
              <td className="border border-gray-300 px-4 py-3">Auto-populated</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-3 font-medium">Part II</td>
              <td className="border border-gray-300 px-4 py-3">4-5</td>
              <td className="border border-gray-300 px-4 py-3">Details of outward and inward supplies declared during the FY</td>
              <td className="border border-gray-300 px-4 py-3">From GSTR-1 &amp; GSTR-3B</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-3 font-medium">Part III</td>
              <td className="border border-gray-300 px-4 py-3">6-8</td>
              <td className="border border-gray-300 px-4 py-3">Details of ITC &mdash; availed, reversed, ineligible</td>
              <td className="border border-gray-300 px-4 py-3">From GSTR-3B &amp; GSTR-2B</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-3 font-medium">Part IV</td>
              <td className="border border-gray-300 px-4 py-3">9</td>
              <td className="border border-gray-300 px-4 py-3">Details of tax paid (through cash and ITC)</td>
              <td className="border border-gray-300 px-4 py-3">From GSTR-3B</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-3 font-medium">Part V</td>
              <td className="border border-gray-300 px-4 py-3">10-14</td>
              <td className="border border-gray-300 px-4 py-3">Amendments, late fee, refunds, demands</td>
              <td className="border border-gray-300 px-4 py-3">Manual entry from books</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-3 font-medium">Part VI</td>
              <td className="border border-gray-300 px-4 py-3">15-19</td>
              <td className="border border-gray-300 px-4 py-3">Other information &mdash; demands, refunds, HSN summary, late fee</td>
              <td className="border border-gray-300 px-4 py-3">Manual entry + HSN from books</td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* Section 5 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">How to Fill GSTR-9: Step-by-Step</h2>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">Step 1: Download Data and Reconcile</h3>

      <p className="text-gray-700 leading-relaxed mb-4">
        Before starting the GSTR-9, download and reconcile all your periodic returns:
      </p>

      <ul className="list-disc pl-6 text-gray-700 space-y-2 mb-6">
        <li>Download all GSTR-1 data (monthly/quarterly) for the financial year</li>
        <li>Download all GSTR-3B data for the financial year</li>
        <li>Download GSTR-2B statements for ITC reconciliation</li>
        <li>Prepare a reconciliation between your books of accounts and the returns filed</li>
        <li>Identify any amendments made in subsequent periods for the FY in question</li>
      </ul>

      <div className="bg-blue-50 border-l-4 border-blue-500 p-4 rounded mb-6">
        <p className="text-blue-900 font-medium">Pro Tip</p>
        <p className="text-blue-800 text-sm mt-1">Use the <Link href="/" className="text-blue-600 underline">GSTIndia GST Calculator</Link> to cross-check your tax computations for the year. Even small calculation errors when aggregated across 12 months can result in significant mismatches.</p>
      </div>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">Step 2: Log In and Access GSTR-9</h3>

      <p className="text-gray-700 leading-relaxed mb-4">
        Log in to the GST portal (gst.gov.in). Navigate to <strong>Services &rarr; Returns &rarr; Annual Return</strong>. Select the financial year and click <strong>&quot;Prepare Online&quot;</strong>. The system auto-populates data from your filed returns into relevant tables.
      </p>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">Step 3: Verify Tables 4 &amp; 5 (Outward &amp; Inward Supplies)</h3>

      <p className="text-gray-700 leading-relaxed mb-4">
        Tables 4 and 5 contain details of all outward and inward supplies declared in GSTR-1 and GSTR-3B during the year:
      </p>

      <ul className="list-disc pl-6 text-gray-700 space-y-2 mb-6">
        <li><strong>Table 4A-4G:</strong> B2B supplies, B2C supplies, exports, SEZ supplies, deemed exports, advances received (and adjusted)</li>
        <li><strong>Table 4H-4K:</strong> Amendments to previously reported outward supplies (credit/debit notes, amendments in subsequent period returns)</li>
        <li><strong>Table 5A-5F:</strong> Inward supplies on which tax is paid on reverse charge basis, import of goods, import of services, inward supplies from ISD</li>
        <li><strong>Table 5H-5K:</strong> Amendments to inward supply details</li>
      </ul>

      <p className="text-gray-700 leading-relaxed mb-4">
        These tables are auto-populated from GSTR-1 and GSTR-3B. Verify each figure against your books. If there are differences, note them down &mdash; they will be reported in Part V (Tables 10-14).
      </p>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">Step 4: Fill Tables 6, 7, 8 (ITC Details)</h3>

      <p className="text-gray-700 leading-relaxed mb-4">
        These tables capture the complete picture of Input Tax Credit for the year:
      </p>

      <ul className="list-disc pl-6 text-gray-700 space-y-2 mb-6">
        <li><strong>Table 6A:</strong> Total ITC availed through GSTR-3B during the FY (auto-populated)</li>
        <li><strong>Table 6B-6E:</strong> Breakup of ITC &mdash; from imports, reverse charge, ISD, and all other sources</li>
        <li><strong>Table 7A-7H:</strong> ITC reversed during the year &mdash; Rule 37, Rule 39, Rule 42, Rule 43, Section 17(5), and others</li>
        <li><strong>Table 8A:</strong> ITC as per GSTR-2A (auto-populated; total ITC available in GSTR-2A for the FY)</li>
        <li><strong>Table 8B-8K:</strong> ITC claimed in GSTR-3B, difference between 2A and 3B, ITC available but not availed</li>
      </ul>

      <div className="bg-yellow-50 border-l-4 border-yellow-500 p-4 rounded mb-6">
        <p className="text-yellow-900 font-medium">Critical Point</p>
        <p className="text-yellow-800 text-sm mt-1">Table 8 is one of the most scrutinised sections. The difference between ITC in GSTR-2A/2B and what you claimed in GSTR-3B is closely monitored. Any excess claim will trigger notices. Use the <Link href="/" className="text-blue-600 underline">GSTIndia reconciliation tool</Link> to match your ITC data before filing. Also refer to our <Link href="/blog/input-tax-credit-itc-rules-2026-27" className="text-blue-600 underline">ITC Rules Guide</Link> for detailed eligibility criteria.</p>
      </div>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">Step 5: Verify Table 9 (Tax Paid)</h3>

      <p className="text-gray-700 leading-relaxed mb-4">
        Table 9 shows the total tax paid during the year through cash and ITC. It is auto-populated from your GSTR-3B filings. Verify that the IGST, CGST, SGST, and Cess figures match your cash and credit ledger statements on the portal.
      </p>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">Step 6: Fill Tables 10-14 (Amendments &amp; Adjustments)</h3>

      <p className="text-gray-700 leading-relaxed mb-4">
        These tables capture amendments and corrections made in the next financial year for transactions of the current year:
      </p>

      <ul className="list-disc pl-6 text-gray-700 space-y-2 mb-6">
        <li><strong>Table 10:</strong> Outward supplies declared in returns of April to September of the next FY that relate to the current FY</li>
        <li><strong>Table 11:</strong> ITC availed in the next FY returns relating to the current FY</li>
        <li><strong>Table 12:</strong> ITC reversed in the next FY returns relating to the current FY</li>
        <li><strong>Table 13:</strong> ITC declared as ineligible in current FY but later reclaimed in the next FY</li>
        <li><strong>Table 14:</strong> Differential tax paid on account of adjustments in Tables 10 to 13</li>
      </ul>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">Step 7: Fill Tables 15-18 (Other Information)</h3>

      <p className="text-gray-700 leading-relaxed mb-4">
        These cover additional disclosures:
      </p>

      <ul className="list-disc pl-6 text-gray-700 space-y-2 mb-6">
        <li><strong>Table 15:</strong> Demands and refunds (if any orders passed during the year)</li>
        <li><strong>Table 16:</strong> Supplies received from <Link href="/blog/gst-composition-scheme-guide" className="text-blue-600 hover:text-blue-700 underline">composition scheme</Link> taxpayers, deemed supply under Section 143, and goods sent on approval but not returned</li>
        <li><strong>Table 17:</strong> HSN-wise summary of outward supplies (mandatory for turnover above ₹5 crore at 6-digit HSN level; 4-digit for turnover between ₹1.5 to ₹5 crore)</li>
        <li><strong>Table 18:</strong> HSN-wise summary of inward supplies (mandatory for turnover above ₹5 crore)</li>
      </ul>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">Step 8: Compute Late Fee (Table 19) and File</h3>

      <p className="text-gray-700 leading-relaxed mb-4">
        Table 19 auto-calculates the late fee if you are filing after the due date. After verifying all tables, click <strong>&quot;Preview&quot;</strong> to review the complete return. Once satisfied, click <strong>&quot;File GSTR-9&quot;</strong> using DSC (for companies/LLPs) or EVC (for others). Note that GSTR-9 <strong>cannot be revised</strong> once filed, so verify everything carefully.
      </p>

      {/* Section 6 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">GSTR-9C: Reconciliation Statement</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        GSTR-9C is a reconciliation statement required for taxpayers with annual turnover above ₹5 crore. Since FY 2020-21, it is self-certified by the taxpayer (earlier it required CA certification). GSTR-9C reconciles:
      </p>

      <ul className="list-disc pl-6 text-gray-700 space-y-2 mb-6">
        <li><strong>Part A:</strong> Turnover as per audited financial statements vs turnover declared in GSTR-9</li>
        <li><strong>Part B:</strong> Tax payable as per audited financials vs tax already paid through returns</li>
        <li><strong>Part C:</strong> ITC as per audited financials vs ITC availed in returns</li>
        <li><strong>Part D:</strong> Additional liability to be discharged (if any mismatch results in under-payment)</li>
      </ul>

      <p className="text-gray-700 leading-relaxed mb-4">
        If GSTR-9C reveals additional tax payable, you must pay it through DRC-03 before filing GSTR-9C. The reconciliation statement is filed along with GSTR-9 on the same portal and has the same due date.
      </p>

      {/* Section 7 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">Late Fees for Late Filing of GSTR-9</h2>

      <div className="overflow-x-auto mb-6">
        <table className="w-full border-collapse border border-gray-300 text-sm">
          <thead>
            <tr className="bg-gray-100">
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Parameter</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Details</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="border border-gray-300 px-4 py-3 font-medium">Late fee per day</td>
              <td className="border border-gray-300 px-4 py-3">₹200 per day (₹100 CGST + ₹100 SGST)</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-3 font-medium">Maximum late fee cap</td>
              <td className="border border-gray-300 px-4 py-3">0.5% of turnover in the state/UT (0.25% CGST + 0.25% SGST)</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-3 font-medium">Example</td>
              <td className="border border-gray-300 px-4 py-3">For turnover of ₹1 crore in a state, maximum late fee = ₹50,000 (₹25,000 CGST + ₹25,000 SGST)</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-3 font-medium">Late fee for turnover up to ₹5 crore (relaxation)</td>
              <td className="border border-gray-300 px-4 py-3">Capped at ₹50 per day (₹25 CGST + ₹25 SGST), max ₹2,000 per return for FY 2022-23 onwards (as per recent notifications)</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-3 font-medium">Late fee for turnover ₹5 crore to ₹20 crore</td>
              <td className="border border-gray-300 px-4 py-3">Capped at ₹100 per day, max ₹10,000 per return</td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* Section 8 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">Common Mistakes to Avoid While Filing GSTR-9</h2>

      <div className="space-y-4 mb-6">
        <div className="bg-white border rounded-lg p-4">
          <h4 className="font-semibold text-gray-900 mb-2">1. Not Reconciling GSTR-1 with GSTR-3B</h4>
          <p className="text-gray-700 text-sm">The values auto-populated in GSTR-9 come from GSTR-1 (for Tables 4-5) and GSTR-3B (for Tables 6-9). If these returns were not reconciled during the year, mismatches will surface in the annual return.</p>
        </div>
        <div className="bg-white border rounded-lg p-4">
          <h4 className="font-semibold text-gray-900 mb-2">2. Ignoring Amendments Made in the Next Year</h4>
          <p className="text-gray-700 text-sm">Amendments, credit notes, and debit notes filed in April-September of the next FY relating to the current FY must be reported in Tables 10-14. Missing these leads to incomplete annual return data.</p>
        </div>
        <div className="bg-white border rounded-lg p-4">
          <h4 className="font-semibold text-gray-900 mb-2">3. Wrong HSN Reporting</h4>
          <p className="text-gray-700 text-sm">Tables 17 and 18 require HSN-wise summary. Using incorrect HSN codes or reporting at the wrong digit level (4-digit vs 6-digit) is a common error. Use the <Link href="/" className="text-blue-600 underline">GSTIndia HSN Code Finder</Link> to verify codes before entering.</p>
        </div>
        <div className="bg-white border rounded-lg p-4">
          <h4 className="font-semibold text-gray-900 mb-2">4. Not Paying Additional Liability Before Filing</h4>
          <p className="text-gray-700 text-sm">If your reconciliation reveals additional tax payable, you must pay it via DRC-03 before filing GSTR-9. Filing without paying results in interest liability.</p>
        </div>
        <div className="bg-white border rounded-lg p-4">
          <h4 className="font-semibold text-gray-900 mb-2">5. Filing Without Completing All Periodic Returns</h4>
          <p className="text-gray-700 text-sm">GSTR-9 cannot be filed until all GSTR-1 and GSTR-3B for the financial year have been filed. Ensure all 12 months&apos; returns are filed before attempting the annual return.</p>
        </div>
        <div className="bg-white border rounded-lg p-4">
          <h4 className="font-semibold text-gray-900 mb-2">6. Excess ITC Claimed vs GSTR-2B</h4>
          <p className="text-gray-700 text-sm">Table 8 highlights the difference between ITC available in GSTR-2A/2B and ITC claimed in GSTR-3B. Any excess must be explained or reversed. This is a major area of scrutiny during assessments.</p>
        </div>
      </div>

      <div className="bg-gradient-to-r from-blue-600 to-blue-700 rounded-xl p-6 text-white mb-8">
        <h3 className="text-xl font-bold mb-2">Prepare for GSTR-9 Filing</h3>
        <p className="text-blue-100 mb-4">Use GSTIndia&apos;s free tools to reconcile ITC, verify HSN codes, validate GSTINs of your suppliers, and compute tax accurately before filing your annual return.</p>
        <Link href="/" className="inline-block bg-white text-blue-600 font-semibold px-6 py-2 rounded-lg hover:bg-blue-50 transition-colors">
          Try Free GST Tools &rarr;
        </Link>
      </div>

      {/* FAQ Section */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-6">Frequently Asked Questions (FAQ)</h2>

      <div className="space-y-4 mb-8">
        {[
          {
            q: 'Is GSTR-9 mandatory for turnover below ₹2 crore?',
            a: 'No, GSTR-9 is optional for taxpayers with aggregate turnover up to ₹2 crore for FY 2022-23 onwards. However, it is recommended to file it for proper reconciliation and to avoid potential notices.',
          },
          {
            q: 'Can GSTR-9 be revised after filing?',
            a: 'No, GSTR-9 cannot be revised once filed. This is why it is crucial to reconcile all your data thoroughly before filing. Any errors discovered after filing will need to be addressed through other mechanisms like DRC-03 or in the next year\'s returns.',
          },
          {
            q: 'What is the due date of GSTR-9 for FY 2025-26?',
            a: 'The due date for GSTR-9 for FY 2025-26 is 31 December 2026. The CBIC may extend this date via notification — check cbic.gov.in for updates.',
          },
          {
            q: 'Do I need a CA audit for GSTR-9C?',
            a: 'No, since FY 2020-21, GSTR-9C is self-certified by the taxpayer. CA/CMA certification is no longer mandatory. However, having your CA review the reconciliation before filing is still advisable.',
          },
          {
            q: 'What happens if I don\'t file GSTR-9?',
            a: 'Late filing attracts a late fee of ₹200 per day (₹100 CGST + ₹100 SGST), capped at 0.5% of your turnover. Additionally, the tax department may issue notices for non-filing, and it can impact your compliance rating.',
          },
          {
            q: 'Can I file GSTR-9 before filing all monthly returns?',
            a: 'No, you must file all GSTR-1 and GSTR-3B returns for the financial year before GSTR-9 can be filed. The portal will not allow GSTR-9 filing if any periodic return is pending.',
          },
          {
            q: 'What turnover is considered for GSTR-9C applicability?',
            a: 'The aggregate turnover threshold of ₹5 crore for GSTR-9C is calculated PAN-wise (across all GSTINs under the same PAN). It includes all taxable, exempt, export, and inter-state supplies but excludes inward supplies on reverse charge.',
          },
          {
            q: 'How do I pay additional tax discovered during GSTR-9 preparation?',
            a: 'Any additional tax liability discovered during GSTR-9 preparation must be paid through Form DRC-03 (voluntary payment). Go to Services → User Services → My Applications → DRC-03 on the GST portal. Pay the tax with interest before filing GSTR-9.',
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
        Filing GSTR-9 is a critical annual compliance requirement that consolidates your entire year&apos;s GST data into a single return. While the process may seem complex with its 19 tables and multiple reconciliation points, proper preparation &mdash; including reconciling GSTR-1 with GSTR-3B, matching ITC with GSTR-2B, and verifying HSN codes &mdash; makes the filing smoother and helps avoid notices.
      </p>

      <p className="text-gray-700 leading-relaxed mb-4">
        Start preparing your GSTR-9 well before the due date. Use the <Link href="/" className="text-blue-600 hover:text-blue-700 underline">GSTIndia</Link> tools for GST calculations, HSN code lookups, and ITC reconciliation. For a detailed understanding of periodic returns that feed into GSTR-9, refer to our <Link href="/blog/gst-return-filing-guide-2026-27" className="text-blue-600 hover:text-blue-700 underline">GST Return Filing Guide</Link>.
      </p>

      {/* JSON-LD Structured Data */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            '@context': 'https://schema.org',
            '@type': 'Article',
            headline: 'GST Annual Return (GSTR-9) Guide 2026: Who Files, Deadlines & How to Fill',
            description: 'Complete GSTR-9 annual return guide for 2026. Who must file, due dates, step-by-step filling instructions, GSTR-9C reconciliation & common mistakes.',
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
            url: 'https://gst.doaide.com/blog/gst-annual-return-gstr-9-guide',
            mainEntityOfPage: 'https://gst.doaide.com/blog/gst-annual-return-gstr-9-guide',
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
                name: 'Is GSTR-9 mandatory for turnover below ₹2 crore?',
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: 'No, GSTR-9 is optional for taxpayers with aggregate turnover up to ₹2 crore for FY 2022-23 onwards.',
                },
              },
              {
                '@type': 'Question',
                name: 'Can GSTR-9 be revised after filing?',
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: 'No, GSTR-9 cannot be revised once filed. Reconcile all data thoroughly before filing.',
                },
              },
              {
                '@type': 'Question',
                name: 'What is the due date of GSTR-9 for FY 2025-26?',
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: 'The due date is 31 December 2026. The CBIC may extend this via notification.',
                },
              },
              {
                '@type': 'Question',
                name: 'Do I need a CA audit for GSTR-9C?',
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: 'No, since FY 2020-21, GSTR-9C is self-certified by the taxpayer. CA certification is no longer mandatory.',
                },
              },
              {
                '@type': 'Question',
                name: 'What happens if I don\'t file GSTR-9?',
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: 'Late filing attracts ₹200/day late fee (₹100 CGST + ₹100 SGST), capped at 0.5% of turnover.',
                },
              },
              {
                '@type': 'Question',
                name: 'Can I file GSTR-9 before filing all monthly returns?',
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: 'No, all GSTR-1 and GSTR-3B returns for the financial year must be filed before GSTR-9 can be filed.',
                },
              },
              {
                '@type': 'Question',
                name: 'What turnover is considered for GSTR-9C applicability?',
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: 'The ₹5 crore threshold is PAN-wise (across all GSTINs), including taxable, exempt, export, and inter-state supplies.',
                },
              },
              {
                '@type': 'Question',
                name: 'How do I pay additional tax discovered during GSTR-9 preparation?',
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: 'Pay through Form DRC-03 (voluntary payment) on the GST portal before filing GSTR-9.',
                },
              },
            ],
          }),
        }}
      />

      <div className="mt-8 pt-8 border-t dark:border-gray-800">
        <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">Found this guide helpful? Share it:</p>
        <ShareButtons
          title="GSTR-9 Annual Return Guide 2026: Filing & Deadlines"
          url="/blog/gst-annual-return-gstr-9-guide"
        />
      </div>
    </article>
  );
}
