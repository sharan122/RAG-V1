# Template Service - Extended FAQ (Comprehensive Guide)

This document provides a **comprehensive deep-dive** into the Template Service, its supported features, configurations, and best practices. It expands on the initial FAQ and is designed as a **reference manual** for developers, system integrators, and operational teams.

---

## 1. Conversion Strategies for DOCX → PDF

(Existing sections 1–12 remain unchanged for brevity)

---

## 13. Can I use images in templates?

Yes. Images can be embedded in both **DOCX** and **HTML** templates.

* **DOCX** → Insert image placeholders using Docxtemplator syntax.
* **HTML** → Use `<img>` tags with either absolute URLs or base64 encoded strings.

**Tip:** For consistent rendering in PDF, ensure images are optimized and not overly large.

---

## 14. How are fonts handled?

* **DOCX** → Fonts are embedded in the document if configured in Word.
* **HTML** → Web fonts must be hosted or embedded (Google Fonts, self-hosted, or base64 encoded).
* **ZPL** → Fonts are printer-dependent, usually limited to built-in Zebra fonts.

**Recommendation:** Always test PDFs with required fonts to avoid fallback issues.

---

## 15. Is multilingual support available?

Yes ✅. Templates support **UTF-8** encoding.

* Supported languages include **English, Chinese, Japanese, Korean, Arabic, Cyrillic**, and more.
* RTL (Right-to-Left) languages like Arabic and Hebrew are supported, though formatting may need adjustments.

---

## 16. How can I debug template issues?

1. Validate placeholders against your JSON payload.
2. Render a sample document with test data.
3. Switch between Aspose and Apryse for comparison.
4. Use the API response logs for error details.

---

## 17. Can I secure generated documents?

Yes.

* PDF password protection is supported.
* Watermarks can be added for compliance.
* Documents can be stored temporarily and auto-expired.

---

## 18. Does the service support versioning?

Yes. Templates can be version-controlled manually.

* Always upload a new template when making significant changes.
* Maintain a changelog.
* Rollback by switching to the older template ID.

---

## 19. Can I generate non-PDF outputs?

Yes.

* **DOCX output** is supported.
* **ZPL output** is supported.
* **HTML output** is supported.
* **PDF output** remains the most common for final distribution.

---

## 20. What limits should I be aware of?

* File size limit: **25 MB per template**.
* Batch generation: Up to **500 documents per request** (configurable).
* API rate limit: Depends on tenant-level configuration.

---

## 21. Can I schedule document generation?

The service itself does not provide scheduling. However:

* Use an **external scheduler** (e.g., cron jobs, Airflow, AWS Lambda).
* Call the API at scheduled intervals.

---

## 22. Can I customize error handling?

Yes. API responses return detailed error codes.

* Developers can build retry mechanisms.
* Use webhooks to notify failures.
* Store failed payloads for reprocessing.

---

## 23. Does the service integrate with cloud storage?

Yes.

* Generated documents can be uploaded to **AWS S3**, **Azure Blob**, or **Google Cloud Storage**.
* Direct integration may require middleware.

---

## 24. How do I handle large-scale bulk jobs?

* Use **batch API v3** for efficiency.
* Split extremely large jobs into chunks.
* Consider asynchronous job processing with callbacks.

---

## 25. Can templates include dynamic tables?

Yes.

* **DOCX** → Docxtemplator supports looping rows.
* **HTML** → Handlebars supports array iteration.
* Useful for invoices, reports, and multi-line receipts.

---

## 26. Can I test templates without real data?

Yes.

* Use mock JSON payloads.
* Sandbox environments are available for safe testing.

---

## 27. How long are generated documents stored?

* Default retention: **24 hours**.
* Configurable retention may be available depending on tenant.
* Always download or store documents in your own storage for long-term use.

---

## 28. What file formats are planned for future support?

Upcoming roadmap includes:

* XLSX (Excel templates).
* PPTX (PowerPoint templates).
* ZPL → PDF support.

---

## 29. Can I restrict template access?

Yes.

* Access control can be managed at the tenant level.
* Use IAM policies and role-based permissions.
* Only authorized users should update or download sensitive templates.

---

## 30. Can I embed links in generated documents?

Yes.

* **HTML** → Standard `<a>` tags.
* **DOCX** → Hyperlinks added in Word remain intact.
* Works seamlessly when converted to PDF.

---

## 31. Does the service support digital signatures?

Currently:

* Native **digital signatures** are not supported directly.
* Generated PDFs can be post-processed with a signing service.
* Integration with e-signature platforms (DocuSign, Adobe Sign) is common.

---

## 32. What monitoring options are available?

* API logs track request/response details.
* Metrics include request count, error rate, and processing time.
* Integrate logs with observability tools (Datadog, Splunk, CloudWatch).

---

## 33. Can I use conditional formatting?

Yes.

* **Handlebars** → Supports conditional rendering.
* **Docxtemplator** → If/else conditions can be applied.
* Useful for scenarios like invoice discounts or approval messages.

---

## 34. Does the service provide a UI editor?

* Currently templates are managed via API and external tools (Word, IDEs).
* A WYSIWYG editor is in roadmap.

---

## 35. How do I migrate templates between environments?

* Export template files from **Dev/QA**.
* Import into **Production** using API.
* Ensure environment-specific variables are adjusted.

---

## 36. Can I include charts or graphs?

Yes, but with limitations.

* **DOCX** → Supports embedded charts created in Word.
* **HTML** → Can render charts via libraries (e.g., Chart.js) before conversion.
* **PDF** fidelity depends on chart complexity.

---

## 37. How do I manage template lifecycle?

* Draft → Upload new version.
* Test → Validate with sample data.
* Publish → Move to production.
* Archive → Retain old versions for rollback.

---

## 38. Can I encrypt generated documents?

Yes, with certain limitations.

* Password protection supported.
* For advanced encryption, use post-processing tools.

---

## 39. Is offline generation supported?

Yes, in hybrid setups.

* On-prem installations can use local rendering engines.
* Useful for air-gapped or high-security environments.

---

## 40. Can I generate images (JPG/PNG) instead of PDFs?

Currently not natively supported.

* Workaround: Convert generated PDF into images via external libraries.

---

## 41. Does the Template Service support integration with Weaviate DB?

Yes. The Template Service is designed to use Weaviate DB for storing and searching template metadata and related vector data. This enables advanced semantic search and efficient retrieval of templates based on content, tags, or metadata.

* **Note:** FAISS or other vector DBs are not used or supported as a fallback. All vector operations are handled exclusively via Weaviate.

---

## 42. Can I use custom metadata fields for templates?

Yes. You can attach custom metadata (as JSON) to each template during upload. This metadata can include tags, categories, business context, or any other relevant information. The metadata is indexed in Weaviate for fast search and filtering.

---

## 43. How do I search for templates by content or tags?

The Template Service leverages Weaviate’s vector search capabilities. You can:

* Search by keywords, tags, or semantic meaning.
* Filter by organization, application, or custom metadata fields.
* Use the API endpoint `/templates/search` with your query parameters.



