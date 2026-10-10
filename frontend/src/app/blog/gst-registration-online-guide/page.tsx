import type { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'GST Registration Online: Complete Guide 2026',
  description: 'Step-by-step guide to GST registration online. Documents required, eligibility, fees, and how to get your GST number on the GST portal in 2026.',
  openGraph: {
    title: 'GST Registration Online: Complete Guide 2026',
    description: 'Step-by-step guide to GST registration online. Documents required, eligibility, and how to get your GSTIN.',
    url: 'https://gst.doaide.com/blog/gst-registration-online-guide',
    type: 'article',
  },
  alternates: {
    canonical: 'https://gst.doaide.com/blog/gst-registration-online-guide',
  },
};

export default function GSTRegistrationGuide() {
  return (
    <article className="max-w-4xl mx-auto px-4 py-12">
      <div className="mb-8">
        <span className="text-sm font-semibold text-blue-600 bg-blue-50 px-3 py-1 rounded-full">Registration</span>
        <span className="text-sm text-gray-500 ml-3">Updated: 10 October 2026</span>
        <span className="text-sm text-gray-500 ml-3">12 min read</span>
      </div>

      <h1 className="text-4xl font-bold text-gray-900 mb-6">
        GST Registration Online: Complete Guide to Getting Your GST Number in 2026
      </h1>

      <p className="text-lg text-gray-600 mb-8 leading-relaxed">
        GST registration is the first step for any business to become a part of India&apos;s Goods and Services Tax system. Whether you are starting a new business, crossing the turnover threshold, or selling online, obtaining a GSTIN (GST Identification Number) is mandatory. This guide walks you through the complete GST registration process online — from eligibility and documents to step-by-step application on the GST portal.
      </p>

      <div className="bg-blue-50 border-l-4 border-blue-500 p-4 rounded mb-8">
        <p className="text-blue-900 font-medium">Key Highlights</p>
        <ul className="text-blue-800 text-sm mt-2 space-y-1">
          <li>• GST registration is completely <strong>free of cost</strong> on the official portal</li>
          <li>• Processing takes 3-7 working days after application</li>
          <li>• GSTIN is a 15-digit unique identification number</li>
          <li>• Can be done entirely online at gst.gov.in</li>
        </ul>
      </div>

      {/* Section 1 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">What is GST Registration?</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        GST registration is the process by which a business or individual gets registered under the Goods and Services Tax law. Upon successful registration, a unique 15-digit GSTIN (GST Identification Number) is allotted. This number serves as your identity for all GST-related activities — filing returns, collecting tax, claiming Input Tax Credit, and issuing tax invoices.
      </p>

      <p className="text-gray-700 leading-relaxed mb-4">
        The GSTIN follows a specific format: the first two digits represent the state code, the next ten digits are the PAN of the business, the thirteenth digit indicates the number of registrations within the state, the fourteenth is &quot;Z&quot; by default, and the last digit is a check digit. For example, <strong>27AADCB2230M1ZP</strong> — where 27 is Maharashtra&apos;s state code.
      </p>

      <p className="text-gray-700 leading-relaxed mb-4">
        You can verify any GSTIN instantly using the <Link href="/" className="text-blue-600 hover:text-blue-700 underline">GSTIndia GSTIN Validator</Link> tool to check whether a supplier or buyer is genuinely registered and their registration status is active.
      </p>

      {/* Section 2 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">Who Needs GST Registration?</h2>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">Mandatory Registration</h3>

      <p className="text-gray-700 leading-relaxed mb-4">
        GST registration is mandatory for the following categories of persons and businesses:
      </p>

      <div className="overflow-x-auto mb-6">
        <table className="w-full border-collapse border border-gray-300 text-sm">
          <thead>
            <tr className="bg-gray-100">
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Category</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Threshold Limit</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="border border-gray-300 px-4 py-3">Suppliers of goods (Normal states)</td>
              <td className="border border-gray-300 px-4 py-3">Annual turnover exceeds ₹40 lakh</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-3">Suppliers of goods (Special category states*)</td>
              <td className="border border-gray-300 px-4 py-3">Annual turnover exceeds ₹20 lakh</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-3">Suppliers of services (All states)</td>
              <td className="border border-gray-300 px-4 py-3">Annual turnover exceeds ₹20 lakh</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-3">Suppliers of services (Special category states*)</td>
              <td className="border border-gray-300 px-4 py-3">Annual turnover exceeds ₹10 lakh</td>
            </tr>
          </tbody>
        </table>
      </div>

      <p className="text-gray-500 text-sm mb-4">
        *Special category states: Arunachal Pradesh, Manipur, Meghalaya, Mizoram, Nagaland, Puducherry, Sikkim, Telangana, Tripura, and Uttarakhand.
      </p>

      <p className="text-gray-700 leading-relaxed mb-4">
        Additionally, registration is mandatory regardless of turnover for:
      </p>

      <ul className="list-disc pl-6 text-gray-700 space-y-2 mb-6">
        <li><strong>Inter-state suppliers:</strong> Any person making inter-state taxable supplies (selling goods/services to another state)</li>
        <li><strong>E-commerce sellers:</strong> Persons selling through e-commerce platforms like Amazon, Flipkart, Meesho</li>
        <li><strong>E-commerce operators:</strong> Platforms that facilitate sales and are required to collect TCS</li>
        <li><strong>Casual taxable persons:</strong> Those who occasionally supply goods/services in a state where they have no fixed place of business</li>
        <li><strong>Non-resident taxable persons:</strong> Foreign entities supplying goods/services in India</li>
        <li><strong>Persons liable to pay tax under reverse charge</strong></li>
        <li><strong>Input Service Distributors (ISD)</strong></li>
        <li><strong>Agents of suppliers</strong></li>
        <li><strong>TDS/TCS deductors/collectors</strong></li>
        <li><strong>Online information and database access or retrieval (OIDAR) services</strong> providers from outside India</li>
      </ul>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">Voluntary Registration</h3>

      <p className="text-gray-700 leading-relaxed mb-4">
        Even if your turnover is below the threshold, you can voluntarily register for GST. Voluntary registration is beneficial if:
      </p>

      <ul className="list-disc pl-6 text-gray-700 space-y-2 mb-6">
        <li>You want to claim Input Tax Credit on your purchases</li>
        <li>You deal with registered businesses that prefer GST-registered suppliers</li>
        <li>You plan to sell on e-commerce platforms</li>
        <li>You want to build credibility and trust with B2B clients</li>
        <li>You anticipate crossing the threshold soon and want to be prepared</li>
      </ul>

      <div className="bg-green-50 border-l-4 border-green-500 p-4 rounded mb-6">
        <p className="text-green-900 font-medium">Pro Tip</p>
        <p className="text-green-800 text-sm mt-1">If you are a freelancer or small business providing services worth less than ₹20 lakh per year and dealing only within your state, GST registration is not mandatory. However, if your clients are large companies, they may prefer dealing with GST-registered vendors for ITC purposes.</p>
      </div>

      {/* Section 3 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">Types of GST Registration</h2>

      <div className="overflow-x-auto mb-6">
        <table className="w-full border-collapse border border-gray-300 text-sm">
          <thead>
            <tr className="bg-gray-100">
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Type</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Who is it For</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Tax Rate</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="border border-gray-300 px-4 py-3 font-medium">Regular Taxpayer</td>
              <td className="border border-gray-300 px-4 py-3">Businesses above threshold, inter-state suppliers</td>
              <td className="border border-gray-300 px-4 py-3">Normal GST rates (5%, 12%, 18%, 28%)</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-3 font-medium">Composition Dealer</td>
              <td className="border border-gray-300 px-4 py-3">Small businesses with turnover up to ₹1.5 crore (₹75 lakh for special states)</td>
              <td className="border border-gray-300 px-4 py-3">1% (traders), 2% (manufacturers), 5% (restaurants)</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-3 font-medium">Casual Taxable Person</td>
              <td className="border border-gray-300 px-4 py-3">Temporary/seasonal businesses, exhibition sellers</td>
              <td className="border border-gray-300 px-4 py-3">Normal GST rates, advance tax deposit required</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-3 font-medium">Non-Resident Taxable Person</td>
              <td className="border border-gray-300 px-4 py-3">Foreign businesses supplying in India</td>
              <td className="border border-gray-300 px-4 py-3">Normal GST rates, advance tax deposit required</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-3 font-medium">Input Service Distributor</td>
              <td className="border border-gray-300 px-4 py-3">Head office distributing ITC to branches</td>
              <td className="border border-gray-300 px-4 py-3">N/A — only distributes credit</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-3 font-medium">TDS/TCS Registration</td>
              <td className="border border-gray-300 px-4 py-3">Government bodies, e-commerce operators</td>
              <td className="border border-gray-300 px-4 py-3">TDS: 2% (1% CGST + 1% SGST), TCS: 1%</td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* Section 4 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">Documents Required for GST Registration</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        The documents required depend on the type of business entity. Keep these documents ready before starting your application to ensure a smooth registration process.
      </p>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">For Proprietorship Firm</h3>

      <ul className="list-disc pl-6 text-gray-700 space-y-2 mb-6">
        <li>PAN card of the proprietor</li>
        <li>Aadhaar card of the proprietor</li>
        <li>Photograph of the proprietor (passport size, JPEG format, max 100 KB)</li>
        <li>Bank account details — cancelled cheque or first page of passbook or bank statement</li>
        <li>Address proof of business premises:
          <ul className="list-disc pl-6 mt-2 space-y-1">
            <li>Own premises: Electricity bill, property tax receipt, or municipal khata copy</li>
            <li>Rented premises: Rent agreement + NOC from owner + any utility bill of premises</li>
          </ul>
        </li>
      </ul>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">For Partnership Firm / LLP</h3>

      <ul className="list-disc pl-6 text-gray-700 space-y-2 mb-6">
        <li>PAN card of the firm/LLP</li>
        <li>Partnership deed (for partnership firm) or LLP agreement</li>
        <li>PAN card and Aadhaar card of all partners</li>
        <li>Photographs of all partners</li>
        <li>Address proof of business premises</li>
        <li>Bank account details of the firm</li>
        <li>Authorization letter nominating the authorized signatory</li>
        <li>LLP registration certificate (for LLP)</li>
      </ul>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">For Private Limited Company / Public Company</h3>

      <ul className="list-disc pl-6 text-gray-700 space-y-2 mb-6">
        <li>PAN card of the company</li>
        <li>Certificate of Incorporation issued by MCA</li>
        <li>Memorandum and Articles of Association (MOA/AOA)</li>
        <li>PAN card and Aadhaar card of all directors</li>
        <li>Photographs of all directors</li>
        <li>Board resolution appointing authorized signatory</li>
        <li>Address proof of registered office</li>
        <li>Bank account details of the company</li>
        <li>Digital Signature Certificate (DSC) of the authorized signatory</li>
      </ul>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">For HUF (Hindu Undivided Family)</h3>

      <ul className="list-disc pl-6 text-gray-700 space-y-2 mb-6">
        <li>PAN card of HUF</li>
        <li>PAN card and Aadhaar card of Karta</li>
        <li>Photograph of Karta</li>
        <li>Address proof of business premises</li>
        <li>Bank account details</li>
      </ul>

      <div className="bg-yellow-50 border-l-4 border-yellow-500 p-4 rounded mb-6">
        <p className="text-yellow-900 font-medium">Document Specifications</p>
        <ul className="text-yellow-800 text-sm mt-2 space-y-1">
          <li>• Photographs: JPEG format, max 100 KB</li>
          <li>• All documents: PDF or JPEG format, max 1 MB each</li>
          <li>• Address proof should not be older than 2 months (for utility bills)</li>
          <li>• PAN and Aadhaar must be linked</li>
        </ul>
      </div>

      {/* Section 5 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">Step-by-Step GST Registration Process Online</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        GST registration is done entirely online through the GST portal (gst.gov.in). The process is divided into two parts: Part A (generating TRN) and Part B (filling the detailed application). Here is the complete step-by-step process:
      </p>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">Part A: Generate Temporary Reference Number (TRN)</h3>

      <div className="space-y-6 mb-8">
        <div className="flex gap-4">
          <div className="flex-shrink-0 w-10 h-10 bg-blue-600 text-white rounded-full flex items-center justify-center font-bold">1</div>
          <div>
            <h4 className="font-semibold text-gray-900 mb-1">Visit the GST Portal</h4>
            <p className="text-gray-700 text-sm">Go to <strong>gst.gov.in</strong> and click on <strong>&quot;Services&quot; → &quot;Registration&quot; → &quot;New Registration&quot;</strong>.</p>
            <div className="bg-gray-100 border border-gray-300 p-3 rounded mt-2 text-center text-gray-500 italic text-sm">
              [Screenshot: GST Portal homepage with Registration menu]
            </div>
          </div>
        </div>

        <div className="flex gap-4">
          <div className="flex-shrink-0 w-10 h-10 bg-blue-600 text-white rounded-full flex items-center justify-center font-bold">2</div>
          <div>
            <h4 className="font-semibold text-gray-900 mb-1">Select &quot;New Registration&quot;</h4>
            <p className="text-gray-700 text-sm">On the registration page, select <strong>&quot;New Registration&quot;</strong> radio button. Choose whether you are a taxpayer, TDS deductor, TCS collector, GST practitioner, or non-resident taxable person.</p>
          </div>
        </div>

        <div className="flex gap-4">
          <div className="flex-shrink-0 w-10 h-10 bg-blue-600 text-white rounded-full flex items-center justify-center font-bold">3</div>
          <div>
            <h4 className="font-semibold text-gray-900 mb-1">Fill Basic Details</h4>
            <p className="text-gray-700 text-sm">Enter your state, district, legal name of business (as on PAN), PAN number, email address, and mobile number. The email and mobile must belong to the authorized signatory — OTPs will be sent to verify them.</p>
          </div>
        </div>

        <div className="flex gap-4">
          <div className="flex-shrink-0 w-10 h-10 bg-blue-600 text-white rounded-full flex items-center justify-center font-bold">4</div>
          <div>
            <h4 className="font-semibold text-gray-900 mb-1">Verify OTPs</h4>
            <p className="text-gray-700 text-sm">Enter the OTP received on your email and mobile number separately. Both must be verified within 10 minutes. After successful verification, a <strong>Temporary Reference Number (TRN)</strong> is generated and sent to your email and mobile.</p>
          </div>
        </div>
      </div>

      <div className="bg-blue-50 border-l-4 border-blue-500 p-4 rounded mb-6">
        <p className="text-blue-900 font-medium">Save Your TRN</p>
        <p className="text-blue-800 text-sm mt-1">The TRN is valid for 15 days. Note it down immediately. You will need it to log in and complete Part B of the registration. If the TRN expires, you will need to start the process again.</p>
      </div>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">Part B: Complete the Registration Application</h3>

      <div className="space-y-6 mb-8">
        <div className="flex gap-4">
          <div className="flex-shrink-0 w-10 h-10 bg-green-600 text-white rounded-full flex items-center justify-center font-bold">5</div>
          <div>
            <h4 className="font-semibold text-gray-900 mb-1">Log in with TRN</h4>
            <p className="text-gray-700 text-sm">Go to <strong>gst.gov.in → Services → Registration → New Registration</strong>. Select the <strong>&quot;Temporary Reference Number (TRN)&quot;</strong> radio button and enter your TRN. Verify with OTP sent to your registered email/mobile.</p>
          </div>
        </div>

        <div className="flex gap-4">
          <div className="flex-shrink-0 w-10 h-10 bg-green-600 text-white rounded-full flex items-center justify-center font-bold">6</div>
          <div>
            <h4 className="font-semibold text-gray-900 mb-1">Fill Business Details (Tab 1)</h4>
            <p className="text-gray-700 text-sm">Provide details including trade name, constitution of business (proprietorship, partnership, company, etc.), district, sector, commissionerate, division, and range. Also indicate if you have opted for composition scheme.</p>
          </div>
        </div>

        <div className="flex gap-4">
          <div className="flex-shrink-0 w-10 h-10 bg-green-600 text-white rounded-full flex items-center justify-center font-bold">7</div>
          <div>
            <h4 className="font-semibold text-gray-900 mb-1">Fill Promoter/Partner Details (Tab 2)</h4>
            <p className="text-gray-700 text-sm">Add details of all partners, directors, or the proprietor — name, date of birth, PAN, Aadhaar, mobile, email, residential address, designation, and photograph. For companies, add all directors.</p>
          </div>
        </div>

        <div className="flex gap-4">
          <div className="flex-shrink-0 w-10 h-10 bg-green-600 text-white rounded-full flex items-center justify-center font-bold">8</div>
          <div>
            <h4 className="font-semibold text-gray-900 mb-1">Add Authorized Signatory (Tab 3)</h4>
            <p className="text-gray-700 text-sm">Nominate the person who will sign and file GST returns. This person&apos;s PAN and Aadhaar must be linked. They will receive all communications from the GST department.</p>
          </div>
        </div>

        <div className="flex gap-4">
          <div className="flex-shrink-0 w-10 h-10 bg-green-600 text-white rounded-full flex items-center justify-center font-bold">9</div>
          <div>
            <h4 className="font-semibold text-gray-900 mb-1">Fill Principal Place of Business (Tab 4)</h4>
            <p className="text-gray-700 text-sm">Enter the complete address of your main business location. Upload proof of address (electricity bill, rent agreement, property tax receipt). If you have additional places of business, add them too.</p>
          </div>
        </div>

        <div className="flex gap-4">
          <div className="flex-shrink-0 w-10 h-10 bg-green-600 text-white rounded-full flex items-center justify-center font-bold">10</div>
          <div>
            <h4 className="font-semibold text-gray-900 mb-1">Add Goods and Services Details (Tab 5)</h4>
            <p className="text-gray-700 text-sm">Select the top 5 goods and/or services that you deal in. Enter the corresponding HSN code (for goods) or SAC code (for services). Use the <Link href="/" className="text-blue-600 underline">GSTIndia HSN Code Finder</Link> to identify the correct codes.</p>
          </div>
        </div>

        <div className="flex gap-4">
          <div className="flex-shrink-0 w-10 h-10 bg-green-600 text-white rounded-full flex items-center justify-center font-bold">11</div>
          <div>
            <h4 className="font-semibold text-gray-900 mb-1">Add Bank Account Details (Tab 6)</h4>
            <p className="text-gray-700 text-sm">Enter your business bank account details — account number, IFSC code, bank name, branch, and account type. Upload a cancelled cheque or bank statement as proof. You can add up to 10 bank accounts.</p>
          </div>
        </div>

        <div className="flex gap-4">
          <div className="flex-shrink-0 w-10 h-10 bg-green-600 text-white rounded-full flex items-center justify-center font-bold">12</div>
          <div>
            <h4 className="font-semibold text-gray-900 mb-1">Verification and Submission</h4>
            <p className="text-gray-700 text-sm">Review all details on the verification tab. Select the authorized signatory, check the declaration box, and submit. Choose verification method:</p>
            <ul className="list-disc pl-6 text-gray-700 text-sm mt-2 space-y-1">
              <li><strong>DSC (Digital Signature Certificate):</strong> Mandatory for companies and LLPs</li>
              <li><strong>EVC (Electronic Verification Code):</strong> OTP-based, available for proprietorship, partnership, and HUF</li>
              <li><strong>E-sign (Aadhaar-based):</strong> OTP sent to Aadhaar-linked mobile number</li>
            </ul>
          </div>
        </div>
      </div>

      <p className="text-gray-700 leading-relaxed mb-4">
        After successful submission, an <strong>Application Reference Number (ARN)</strong> is generated. You can track the status of your application using this ARN on the GST portal. The application is then sent to the concerned GST officer for verification.
      </p>

      {/* Section 6 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">GST Registration Fees</h2>

      <div className="bg-green-50 border-l-4 border-green-500 p-4 rounded mb-6">
        <p className="text-green-900 font-medium text-lg">GST Registration is Completely Free!</p>
        <p className="text-green-800 text-sm mt-1">The Government of India does not charge any fee for GST registration. The entire process is online and free of cost on the GST portal (gst.gov.in). Be wary of any agent or website charging exorbitant fees for &quot;GST registration assistance.&quot; While you may choose to hire a CA or tax professional for convenience, the government registration itself costs nothing.</p>
      </div>

      {/* Section 7 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">Time Taken for GST Registration</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        The typical timeline for GST registration is:
      </p>

      <div className="overflow-x-auto mb-6">
        <table className="w-full border-collapse border border-gray-300 text-sm">
          <thead>
            <tr className="bg-gray-100">
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Stage</th>
              <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-gray-900">Timeline</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="border border-gray-300 px-4 py-3">Part A (TRN generation)</td>
              <td className="border border-gray-300 px-4 py-3">Immediate (10-15 minutes)</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-3">Part B (Application completion)</td>
              <td className="border border-gray-300 px-4 py-3">1-2 hours (if documents are ready)</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-3">Aadhaar authentication (if applicable)</td>
              <td className="border border-gray-300 px-4 py-3">Immediate to 1 day</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-3">Officer verification</td>
              <td className="border border-gray-300 px-4 py-3">3-7 working days</td>
            </tr>
            <tr>
              <td className="border border-gray-300 px-4 py-3">GSTIN issuance</td>
              <td className="border border-gray-300 px-4 py-3">Within 7 working days of filing (if no clarification needed)</td>
            </tr>
            <tr className="bg-gray-50">
              <td className="border border-gray-300 px-4 py-3">If clarification sought by officer</td>
              <td className="border border-gray-300 px-4 py-3">7 days to respond + 7 days for officer decision</td>
            </tr>
          </tbody>
        </table>
      </div>

      <p className="text-gray-700 leading-relaxed mb-4">
        If Aadhaar authentication is completed successfully, registration can be granted within 3 working days. For applications where Aadhaar authentication fails or is not opted, the officer may schedule a physical verification of the business premises, which extends the timeline.
      </p>

      {/* Section 8 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">GST Registration Certificate</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        Once your application is approved, the GST Registration Certificate (Form REG-06) is issued electronically. Here&apos;s what you need to know:
      </p>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">How to Download GST Registration Certificate</h3>

      <ol className="list-decimal pl-6 text-gray-700 space-y-2 mb-6">
        <li>Log in to the GST portal with your GSTIN and password</li>
        <li>Go to <strong>Services → User Services → View/Download Certificates</strong></li>
        <li>Click on <strong>&quot;Download&quot;</strong> next to the Registration Certificate</li>
        <li>The certificate is downloaded as a PDF file</li>
      </ol>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">What Does the Certificate Contain?</h3>

      <ul className="list-disc pl-6 text-gray-700 space-y-2 mb-6">
        <li>GSTIN (15-digit identification number)</li>
        <li>Legal name and trade name of the business</li>
        <li>Constitution of the business</li>
        <li>Address of principal place of business</li>
        <li>Date of liability and date of registration</li>
        <li>Type of registration (regular or composition)</li>
        <li>Particulars of approving authority</li>
        <li>Date of issuance of certificate</li>
      </ul>

      <p className="text-gray-700 leading-relaxed mb-4">
        You must display the GST Registration Certificate prominently at your principal place of business and at every additional place of business. The GSTIN must also be mentioned on all tax invoices, delivery challans, and other prescribed documents.
      </p>

      {/* Section 9 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">Amendment and Cancellation of GST Registration</h2>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">How to Amend GST Registration</h3>

      <p className="text-gray-700 leading-relaxed mb-4">
        If any details in your GST registration change (address, contact details, business activity, partners, etc.), you must apply for amendment within 15 days of the change. Go to <strong>Services → Registration → Amendment of Registration Core Fields / Non-Core Fields</strong>.
      </p>

      <ul className="list-disc pl-6 text-gray-700 space-y-2 mb-6">
        <li><strong>Core fields</strong> (require officer approval): Legal name, address of principal place of business, addition/deletion of partners/directors, mobile/email of authorized signatory</li>
        <li><strong>Non-core fields</strong> (auto-approved): Trade name, additional places of business, goods/services details, bank accounts, authorized signatory details</li>
      </ul>

      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3">How to Cancel GST Registration</h3>

      <p className="text-gray-700 leading-relaxed mb-4">
        You can apply for cancellation of GST registration if you close your business, transfer the business, or your turnover falls below the threshold. Go to <strong>Services → Registration → Application for Cancellation of Registration</strong> and file Form REG-16. The effective date of cancellation can be a future date or the date of application.
      </p>

      <div className="bg-yellow-50 border-l-4 border-yellow-500 p-4 rounded mb-6">
        <p className="text-yellow-900 font-medium">Before Cancellation</p>
        <p className="text-yellow-800 text-sm mt-1">You must file all pending GST returns up to the date of cancellation. You also need to pay tax on the stock of inputs, semi-finished goods, finished goods, and capital goods held on the date of cancellation. This is reported in the final return (GSTR-10), which must be filed within 3 months of cancellation.</p>
      </div>

      {/* Section 10 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">Common Reasons for GST Registration Rejection</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        Understanding why applications get rejected can help you avoid the same pitfalls:
      </p>

      <div className="space-y-4 mb-6">
        <div className="bg-white border rounded-lg p-4">
          <h4 className="font-semibold text-gray-900 mb-2">1. Incomplete or Incorrect Documents</h4>
          <p className="text-gray-700 text-sm">Uploading blurry documents, documents with incorrect names, or expired documents is the most common reason. Ensure all documents are clear, legible, and match the details entered in the form.</p>
        </div>
        <div className="bg-white border rounded-lg p-4">
          <h4 className="font-semibold text-gray-900 mb-2">2. PAN-Aadhaar Mismatch</h4>
          <p className="text-gray-700 text-sm">The name and date of birth on PAN and Aadhaar must match exactly. If there is a discrepancy, update either document before applying. PAN and Aadhaar must also be linked.</p>
        </div>
        <div className="bg-white border rounded-lg p-4">
          <h4 className="font-semibold text-gray-900 mb-2">3. Invalid Address Proof</h4>
          <p className="text-gray-700 text-sm">The address on the utility bill or rent agreement must match the address entered in the application. For rented premises, a NOC from the landlord is mandatory along with the rent agreement.</p>
        </div>
        <div className="bg-white border rounded-lg p-4">
          <h4 className="font-semibold text-gray-900 mb-2">4. Failed Aadhaar Authentication</h4>
          <p className="text-gray-700 text-sm">Aadhaar authentication may fail if the mobile number linked to Aadhaar is not active. Update your Aadhaar with the correct mobile number at the nearest Aadhaar centre before applying.</p>
        </div>
        <div className="bg-white border rounded-lg p-4">
          <h4 className="font-semibold text-gray-900 mb-2">5. Not Responding to Clarification Notices</h4>
          <p className="text-gray-700 text-sm">If the GST officer seeks clarification (Form REG-03), you must respond within 7 working days through Form REG-04 with supporting documents. Failure to respond leads to automatic rejection.</p>
        </div>
      </div>

      {/* Section 11 */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-4">How GSTIndia Tools Help with Registration</h2>

      <p className="text-gray-700 leading-relaxed mb-4">
        The <Link href="/" className="text-blue-600 hover:text-blue-700 underline">GSTIndia platform</Link> offers free tools that complement your GST registration journey:
      </p>

      <ul className="list-disc pl-6 text-gray-700 space-y-2 mb-6">
        <li><strong><Link href="/" className="text-blue-600 underline">GSTIN Validator:</Link></strong> After registration, verify your GSTIN details and check any GSTIN&apos;s validity before doing business with suppliers</li>
        <li><strong><Link href="/" className="text-blue-600 underline">HSN Code Finder:</Link></strong> Find the correct HSN/SAC codes needed during the registration process and for invoicing</li>
        <li><strong><Link href="/" className="text-blue-600 underline">GST Calculator:</Link></strong> Calculate your GST liability accurately to understand if registration is beneficial for your business</li>
      </ul>

      <div className="bg-gradient-to-r from-blue-600 to-blue-700 rounded-xl p-6 text-white mb-8">
        <h3 className="text-xl font-bold mb-2">Get Your GST Tools Ready</h3>
        <p className="text-blue-100 mb-4">Registered for GST? Use GSTIndia&apos;s free tools to calculate tax, find HSN codes, and validate GSTINs — everything you need to start your GST compliance journey.</p>
        <Link href="/" className="inline-block bg-white text-blue-600 font-semibold px-6 py-2 rounded-lg hover:bg-blue-50 transition-colors">
          Explore Free GST Tools →
        </Link>
      </div>

      {/* FAQ Section */}
      <h2 className="text-2xl font-bold text-gray-900 mt-12 mb-6">Frequently Asked Questions (FAQ)</h2>

      <div className="space-y-4 mb-8">
        {[
          {
            q: 'How long does it take to get a GST number?',
            a: 'GST registration typically takes 3-7 working days after submitting the complete application. If Aadhaar authentication is successful, it can be processed within 3 working days. If the officer seeks clarification, it may take up to 30 days.',
          },
          {
            q: 'Is there any fee for GST registration?',
            a: 'No, GST registration is completely free on the official GST portal (gst.gov.in). The government does not charge any fee. You may choose to hire a CA or tax professional for assistance, but the registration itself is free.',
          },
          {
            q: 'What is the turnover limit for GST registration?',
            a: 'For suppliers of goods, the limit is ₹40 lakh (₹20 lakh for special category states). For service providers, it is ₹20 lakh (₹10 lakh for special category states). However, registration is mandatory regardless of turnover for inter-state suppliers and e-commerce sellers.',
          },
          {
            q: 'Can I register for GST without a shop or office?',
            a: 'Yes, you can register for GST with your residential address as the principal place of business. You need to provide proof of the residential address (electricity bill, rent agreement, or ownership document). Many freelancers and home-based businesses use their home address.',
          },
          {
            q: 'What is the difference between GSTIN and GST registration number?',
            a: 'GSTIN (GST Identification Number) and GST registration number are the same thing. It is a unique 15-digit alphanumeric number allotted to every registered taxpayer. The first two digits are the state code, the next ten are the PAN, and the remaining are system-generated.',
          },
          {
            q: 'Can I have multiple GST registrations?',
            a: 'Yes, you can have multiple GST registrations. You need a separate registration for each state where you have a place of business. Additionally, within the same state, you can obtain multiple registrations for different business verticals (from FY 2020-21 onwards).',
          },
          {
            q: 'What happens if I do not register for GST when required?',
            a: 'Operating without GST registration when required attracts a penalty of 10% of the tax due or ₹10,000, whichever is higher. In case of deliberate evasion, the penalty can be 100% of the tax due. You also cannot issue tax invoices or claim ITC.',
          },
          {
            q: 'How to check GST registration status with ARN?',
            a: 'Go to gst.gov.in → Services → Registration → Track Application Status. Enter your ARN (Application Reference Number) and click Search. The status will show as Pending, Approved, or Rejected along with the officer\'s remarks if any.',
          },
          {
            q: 'Can a salaried person get GST registration?',
            a: 'Yes, a salaried person who also runs a business or provides freelance services can get GST registration for their business activity. Salary income itself is not subject to GST, but any independent business or professional services above the threshold require registration.',
          },
          {
            q: 'How to add a new place of business to existing GST registration?',
            a: 'Log in to the GST portal, go to Services → Registration → Amendment of Registration Core Fields. Add the new address under "Additional Places of Business" tab, upload the address proof, and submit. This is a core field amendment and requires officer approval.',
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
        GST registration is a straightforward process that can be completed entirely online within a few hours, with approval typically within a week. The key to a smooth registration is having all your documents ready and ensuring consistency across PAN, Aadhaar, and business details. Once registered, make sure to comply with all filing requirements — use the <Link href="/blog/gst-return-filing-guide-2026-27" className="text-blue-600 underline">GST Return Filing Guide</Link> to understand your ongoing obligations.
      </p>

      <p className="text-gray-700 leading-relaxed mb-4">
        Remember, GST registration is free and the portal is designed for self-service. However, if you need assistance, consult a qualified Chartered Accountant or GST practitioner. And for all your GST calculations, HSN code lookups, and GSTIN verification, the <Link href="/" className="text-blue-600 hover:text-blue-700 underline">GSTIndia tools</Link> are always available to help — completely free.
      </p>

      {/* JSON-LD Structured Data */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            '@context': 'https://schema.org',
            '@type': 'Article',
            headline: 'GST Registration Online: Complete Guide to Getting Your GST Number in 2026',
            description: 'Step-by-step guide to GST registration online. Documents required, eligibility, fees, and how to get your GST number on the GST portal.',
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
            url: 'https://gst.doaide.com/blog/gst-registration-online-guide',
            mainEntityOfPage: 'https://gst.doaide.com/blog/gst-registration-online-guide',
            image: 'https://gst.doaide.com/og-gst-registration.png',
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
                name: 'How long does it take to get a GST number?',
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: 'GST registration typically takes 3-7 working days after submitting the complete application. If Aadhaar authentication is successful, it can be processed within 3 working days.',
                },
              },
              {
                '@type': 'Question',
                name: 'Is there any fee for GST registration?',
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: 'No, GST registration is completely free on the official GST portal (gst.gov.in). The government does not charge any fee.',
                },
              },
              {
                '@type': 'Question',
                name: 'What is the turnover limit for GST registration?',
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: 'For suppliers of goods, the limit is ₹40 lakh (₹20 lakh for special category states). For service providers, it is ₹20 lakh (₹10 lakh for special category states).',
                },
              },
              {
                '@type': 'Question',
                name: 'Can I register for GST without a shop or office?',
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: 'Yes, you can register for GST with your residential address as the principal place of business.',
                },
              },
              {
                '@type': 'Question',
                name: 'What is the difference between GSTIN and GST registration number?',
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: 'GSTIN and GST registration number are the same thing — a unique 15-digit alphanumeric number allotted to every registered taxpayer.',
                },
              },
              {
                '@type': 'Question',
                name: 'Can I have multiple GST registrations?',
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: 'Yes, you need a separate registration for each state where you have a place of business. Within the same state, you can obtain multiple registrations for different business verticals.',
                },
              },
              {
                '@type': 'Question',
                name: 'What happens if I do not register for GST when required?',
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: 'Operating without GST registration when required attracts a penalty of 10% of the tax due or ₹10,000, whichever is higher.',
                },
              },
              {
                '@type': 'Question',
                name: 'How to check GST registration status with ARN?',
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: 'Go to gst.gov.in → Services → Registration → Track Application Status. Enter your ARN and click Search.',
                },
              },
              {
                '@type': 'Question',
                name: 'Can a salaried person get GST registration?',
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: 'Yes, a salaried person who also runs a business or provides freelance services can get GST registration for their business activity.',
                },
              },
              {
                '@type': 'Question',
                name: 'How to add a new place of business to existing GST registration?',
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: 'Log in to the GST portal, go to Services → Registration → Amendment of Registration Core Fields, and add the new address under Additional Places of Business tab.',
                },
              },
            ],
          }),
        }}
      />
    </article>
  );
}
