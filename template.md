Document Templates
Document templates module internally uses an open source version of [docx templater] for mail merging the d(https://docxtemplater.com/docs/) for mail merging and image rendering.
##Features

Document template (.docx) file upload : Customer can upload a .docx file with the necessary structure and upload the template file for a specific application and organisation of upto 10 MB size.
Document template (.docx) file updates : Existing document can be updated with a new docx template.
Retrieve all document templates : Get all document templates metadata for a given organisation of an application.
Download a specific template given a template identifier.
Mail merge data into an existing document template and render docx/pdf.
Mail merge images/QR codes (multiple image files/base64 encoded images, upto 5) into an existing document template and returns either docx/pdf.
Multi Language Support
Document Service supports generating PDFs in Non English languages. The capability is to only render the language on the PDF and not translate the data. The below languages are supported as needed by P100 business.

Chinese
Korean
German
Romanian
French
Arabic
Spanish
Cambodian
[Supporting a language needs us to make specific changes to the pdf generation libraries to ensure that the characters of that language are correctly getting rendered. So teams should reach out to us with specific templates with exact font that needs to be rendered.]

Authentication for all APIs.
We need to send valid params in headers:

"x-api-key": "" // api key depending on the env and the product
NOTE: API keys must not be shared among services. To request a new key for a service, email cargoes-datachain-team@dpworld.com. Keys are generated and shared per service and environment. Keys must be kept confidential.

Now all the Template Service APIs will query database, as all the APIs are updated with database related changes.

Create template
POST /templates

An endpoint that supports creating template. We can upload the template and specify the metadata for it.

Attribute	Type	Required	Default	Description
file	File	Yes		Template to be uploaded to azure storage account. fieldName must be equal to either "file" or "files".
organizationId	int	Yes		Should be the unique identifier for the organisation in your application. As each organisation might have different templates , files etc. If you have some common templates which you use for any organisation , you have to fix an unique number as organisation id and use it.
templateName	String	Yes		Template Name for this record
applicationId	string	Yes		Application Id should be the name of your application. Example if template is for Cargoes datachain team then applicationId is datachain
metadata	Json	Yes		Metadata which has sample data for this template. Ensure that the metadata fits into the template.
language	String	No		This has primary language for the template.
validateTemplateTagsWithMetadata	Boolean	No	False	If true, it validates all the placeholders present in template with metadta. As of now it does not consider loop and complex structure. It only works for simple strings in the templates
Please refer this link to know more about the Template language detection: https://dev.azure.com/dpwhotfsonline/DTLP/_wiki/wikis/DTLP.wiki/8681/Template-Language-Detection-and-Storage

NOTE:

Allowed files for template creation are docx, HTML, zpl.
If the template is an HTML file, it must comply with the following standards:
All HTML tag names must be in lowercase.
Attribute names must be lowercase and must be enclosed in double quotes.
Duplicate attributes within the same tag are not allowed and Each id must be unique across the document.
The src attribute in <img>, <script>, <iframe>, etc., must not be empty.
All <script> tags are strictly prohibited. If script tags are required, please contact datachain team.
fieldName should match the following as shown in the image:
image.png
The sample response looks like this:

{
    "templateId": "b724065c03a72887",
    "templateName": "testtemplate1",
    "templateS3Path": "https://docserdevblobs.blob.core.windows.net/dtlp-templates-development/b724065c03a72887",
    "organizationId": "12345",
    "applicationId": "1234",
    "metadata": {
        "name": "Jayakrishna",
        "lastname": "Alwar",
        "employeeid": "000923973",
        "hascar": true,
        "carname": "Jaguar",
        "hasDog": false,
        "dog": null,
        "products": [
            {
                "name": "Windows",
                "price": 100
            },
            {
                "name": "Mac OSX",
                "price": 200
            },
            {
                "name": "Ubuntu",
                "price": 0
            }
        ],
        "createdAt": "2022-07-29T06:45:37.527Z"
    }
}
Error Codes

Code	Error	Description
40030	Argument Error	For invalid arguments
50090	Api Error	Internal Server Error
Error response in case validateTemplateTagsWithMetadata flag is True

{

"errorCode": "40030",

"success": false,

"data": "[40030] Missing tags in uploaded template: {RANDOM_VARIABLE}, {DRIVER_NAME}",

"message": "Missing tags in uploaded template: {RANDOM_VARIABLE}, {DRIVER_NAME}"

}
Download Document
POST /templates/:templateId/document

This endpoint takes a templateId and merges the metadata in the request body into the template and converts into a pdf as given in options.
There are 3 versions available for this api.

###Modules Supported by Document Service:

Basic Features
Table Module (Currently below functionalities are supported):
Vertical loops
Image Module
File types supported

Input File type	Output File type
docx	docx,pdf,xlsx
zpl	zpl
html	pdf
###Version 1(v1)
This is the old api where we can get only one image i.e logo image. Details for attributes and metadata are as follows

Attribute	Type	Required	Default	Description
templateId	string	Yes		TemplateId which is to be downloaded
body	Json	Yes		Metadata for template which is to be downloaded. If you want to add image to the template specify it as {%image} in your template and give details for this image in data json as shown below. Where logo_path is url of image you want to render in the template (if not provided it will take default image url present in code) and logo_path_height, logo_path_width to set height and width for this image (default values are 190 and 100 respectively),logo_center is to specify if you want to set your image in center (default values is false).
The sample data for body which contains body with metadata and options looks like this:

This body contains metadata for the template and options.

{
  "data": {
    "name": "Jayakrishna",
    "lastname": "Alwar",
    "employeeid": "000923973",
    "hascar": true,
    "carname": "Jaguar",
    "hasDog": false,
    "dog": null,
    "products": [
      {
        "name": "Windows",
        "price": 100
      },
      {
        "name": "Mac OSX",
        "price": 200
      },
      {
        "name": "Ubuntu",
        "price": 0
      }
    ],
    "logo_path": "https://images.unsplash.com/photo-1453728013993-6d66e9c9123a?ixlib=rb- 
                  1.2.1&ixid=MnwxMjA3fDB8MHxzZWFyY2h8Mnx8dmlld3xlbnwwfHwwfHw%3D&w=1000&q=80",
    "logo_path_height": "200",
    "logo_path_width": "200",
    "logo_center":"true",
  },
  "options" : { 
     "type": "docx", 
     "upload": false, 
     "responseType": "buffer", 
     "linkExpiryDuration": 8
    }
}
Options
It is a JSON which tells about the type of response we need from this api

Key	Description	Default
type	Response file types. Allowed values are docx,pdf or xlsx	docx
responseType	Values can be stream,buffer,secureDownloadLink,presignedDownloadLink	stream
linkExpiryDuration	If response type is securedownloadlink.Then this key is used to set the expiry duration of the generated link	7 days
preSignedUrlMetadata	It is a json which contains 2 fields readExpryDuration and readCount	default values is as per client
The sample response would include the respective file that is to be downloaded.
Note: If user wants to immediately generate the secureDownloadLink and is okay with file generation process to happen asynchronously, then they can give type in options as preSignedUrl.

###Version 2(v2)
This api supports multiple images as well as base 64 images also. Details for attributes and metadata are as follows.
To use version 2 api pass header X-Api-Version = v2

Attribute	Type	Required	Default	Description
templateId	string	Yes		TemplateId which is to be downloaded
body	Json	Yes		Metadata for template which is to be downloaded.
For multiple images:

If you want to add an image to the template specify it as {%image_tag_name} in your template.
image_tag_name attribute value should be unique for each of the images as it is the identifier for the image in the JSON and the template.
image_type can be "file_url" ,"base64" or "qr_code" or "barcode", default value is "file_url"
For image_type as "qr_code", "qr_code_text" should be provided. This will convert this text into Qr code and put that image in document placeholder.
image_url for "file_url" type or image_data for "base64" type is to be given according to the image_type provided.
image_height, and image_width to set height and width for this image (default values are 190 and 100 respectively).
In options you can pass the type of file you want as a response. Allowed values are docx, xlsx and pdf whereas the default value is pdf.
For image_type as "barcode", "barcode_type" and "label" should be provided. "label" will convert this text into "barcode_type" and put that image in document placeholder.
"textYOffset": The vertical offset of the label text from the barcode, in millimeters. Default is 3mm.
"textSize": The size of the label text beneath the barcode, in points. Default is 20pt.
"scale": The scaling factor for the barcode image. Default is 3. Increasing the scale enlarges the image without reducing its resolution.
For Encrypting output file:

If you want your output pdf to be encrypted with a password, you have to give the password as encryptWithPassword in the data. Note that encryption is only supported for pdf files, So encryption works only if the type of file is 'pdf' in the options.

The sample data for the body which contains metadata and options look like this:

This body contains metadata for the template and options.

{
  "data": {
    "images": [
      {
        "image_tag_name": "image1",
        "image_type": "file_url",
        "image_url": "https://images.unsplash.com/photo-1453728013993-6d66e9c9123a?ixlib=rb-1.2.1&ixid=MnwxMjA3fDB8MHxzZWFyY2h8Mnx8dmlld3xlbnwwfHwwfHw%3D&w=1000&q=80",
        "image_height": "200",
        "image_width": "200"
      },
      {
        "image_tag_name": "image2",
        "image_type": "base64",
        "image_data": "data:image/png;base64,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",
        "image_height": "250",
        "image_width": "250"
      },
      {
        "image_tag_name": "image3",
        "image_type": "file_url",
        "image_url": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRz19vsWTF44r453MYR8qgUuVJyaapu5kkxng&usqp=CAU",
        "image_height": "150",
        "image_width": "150"
      },
      {
        "image_tag_name": "image4",
        "image_type": "qr_code",
        "qr_code_text": "hello",
        "image_height": "200",
        "image_width": "200"
      },
      {
        "image_tag_name": "image4",
        "image_type": "barcode",
        "barcode_type": "code39",
        "label": "123456789ABCDE",
        "image_height": "200",
        "image_width": "400",
        "includeText": true,
        "textYOffset": "20",
        "textSize": "30"
     }
    ]
  },
  "options": {
    "type": "pdf",
    "upload": false,
    "encryptWithPassword": "password123"
  }
}
Options
It is a JSON which tells about the type of response we need from this api

Key	Description	Default
type	Response file types. Allowed values are docx,pdf or xlsx	docx
responseType	Values can be stream,buffer,secureDownloadLink,presignedDownloadLink	stream
linkExpiryDuration	If response type is securedownloadlink.Then this key is used to set the expiry duration of the generated link	7 days
preSignedUrlMetadata	It is a json which contains 2 fields readExpryDuration and readCount	default values is as per client
Note

Maximum number of images supported: 5
Image more than 1MB is not supported.
responseType in options can take values: ["attachment", "buffer", "secureDownloadLink", "presignedDownloadLink"].
linkExpiryDuration in request body comes in action with responseType="secureDownloadLink". It's default value is 7(in days).
For base64 string we have a validation which accepts string which have 'data:image/png;base64,' in prefix.
Please refer to the sample request above for complete base64 string.
Note: If user wants to immediately generate the secureDownloadLink and is okay with file generation process to happen asynchronously, then they can give type in options as preSignedUrl
The sample response would include the respective encrypted pdf file that is to be downloaded.
Sample response when responseType is "presignedDownloadLink":

{

"filename": "PROCUREMENT_PO_TEST_FINAL-b438c7d1062b77c6-whvdmc.pdf",
"fileIdentifier": "6aa6e11e-f948-4c57-8e55-8482ab83489d",
"presignedDownloadUrl": "https://staging-document-service-api.cargoes.com/file-storage/file/presignedurl?signature=b6d8332a719b20effe71b1cbf55d5c6d37e995769a5f2a2b757cfb5f52b8f50df2dc37ca387bea08c132b136dd8b77d9|395776a41ebd7bd1de6dacfe1d945c24"

}
HTML to PDF document generation

It supports html documents also which generates pdf as output file.
For html template creation check handlebar documentation. https://handlebarsjs.com/guide/
Inline css or public css link will work in the template.
display: grid is NOT supported in css. Please avoid that
Provide Metadata in the json format.
Avoid for each loop in the script tag it is not supported.
Following are the keywords we support in handlebar template.
Script tags are only allowed if you have permission from security team to use them. Also since we are using aspose fro html to pdf conversion as of now.It only supports static html templates.
As of now only web fonts, like free fonts provided by Google are supported. So if you’d like to use some specific
licenced font you would need to provide it by link in styles. Something like that:
@font-face {
        font-family: 'Arial';
        src: url('https://example.com/fonts/arial.woff2') format('woff2'),
             url('https://example.com/fonts/arial.woff') format('woff'),
             url('https://example.com/fonts/arial.ttf') format('truetype');
        font-weight: normal;
        font-style: normal;
    }
Following are the helpers that can bes used inn handlebar html template
Helper Name	Description
Calculation Helpers	
calculate(base, weight)	Multiplies base by weight and returns a fixed decimal result.
calculateTotal(items)	Iterates over an array of items, calculates the total price (basePrice * weight), and returns the sum.
Comparison Helpers	
eq(v1, v2)	Returns true if v1 is strictly equal to v2.
ifCond(v1, operator, v2, options)	Performs conditional checks using operators (===, !==, <, <=, >, >=) and executes the corresponding block.
Lookup Helpers	
lookup(obj, field)	Retrieves a nested property field from an object obj.
Iteration Helpers	
each(context, options)	Iterates over an array context and renders the block for each item. If empty, renders the {{else}} block.
Utility Helpers	
inc(value)	Increments value by 1 and returns the result.
dec(value)	Decrements value by 1 and returns the result.
formatDate(date)	Converts a date to a localized string format.
formatCurrency(value)	Formats value as a currency with two decimal places.
Comparison Helpers (Alternative Implementations)	
eq(a, b)	Returns true if a is strictly equal to b.
gt(a, b)	Returns true if a is greater than b.
lt(a, b)	Returns true if a is less than b.
gte(a, b)	Returns true if a is greater than or equal to b.
lte(a, b)	Returns true if a is less than or equal to b.
Logical Operators	
and(...args)	Returns true if all arguments are truthy.
or(...args)	Returns true if at least one argument is truthy.
not(value)	Returns the negation (!value) of the given value.
###Version 3(v3)
Version 3 of download document API supports multiple payload for a template and generate documents for each of them (or merged document if 'mergeFiles' as true). Note that, this version supports multiple images as well in payloads.

##Validations

Json Structure:
Key: 'generationDetails'[Mandatory] and Value as 'Array of payloads' is expected in request body as shown below.'
Key: 'responseType'[Mandatory] and Value can be 'presignedDownloadLink'. Only presignedDownloadLink is supported as of now
Key: 'mergeFiles' [Optional]. This key should be true if the final file is expected to be a merged File of all the generated files. In this case, type for each payload should be pdf. By default, value of mergeFiles is false.
Each payload should have data which is expected in the generated documents per wiki. All features supported in v2 API, should be supported as a part of individual payload in v3 api: https://dpwhotfsonline.visualstudio.com/DTLP/_wiki/wikis/DTLP.wiki/1922/Template-APIs?anchor=version-2(v2)
Options should contain only type or preSignedUrlMetadata keys as specified in above wiki. Default value of type should be docx and default value of presignedUrlMetadata is default values set for the client.
'type' in options, should only be one of 'pdf', 'docx', or 'xlsx'
Maximum number of payload allowed are : 20
Sample Request Body:

{
  "generationDetails": [
    {
      "data": {
        "productCode": "productCode",
        "route": "route"
      },
      "options": {
        "type": "pdf"
      }
    },
    {
      "data": {
        "productCode": "productCode",
        "route": "route"
      },
      "options": {
        "type": "xlsx"
      }
    }
  ],
  "responseType": "presignedDownloadLink",
  "mergeFiles": false
}
CURL:

curl --location 'http://staging-document-service-api.private-cargoes.com/templates/fffeea68434131e2/document' \
--header 'x-api-key: 9e0b7bc7bd666a8ac0d7f5c70d3460e0' \
--header 'x-api-version: v3' \
--header 'Content-Type: application/json' \
--data '{
  "generationDetails": [
    {
      "data": {
        "orderNo": "1",
        "depot": "depot",
        "tripSheetNumber": "12",
        "fleetNo1": "V1",
        "fleetNo2": "V2",
        "organization": "org",
        "customer": "customer",
        "productCode": "productCode",
        "route": "route",
        "unNumber": "un",
        "productName": "name",
        "quantityOrdered": "22",
        "requiredLoadingBefore": "date",
        "requiredDeliveryBefore": "date",
        "deliverToStreet": "deliverToStreet",
        "deliverToCityDetails": "deliverToCityDetails",
        "deliverToProvinceDetails": "deliverToProvinceDetails",
        "deliverToCountry": "deliverToCountry",
        "deliverToPostalCode": "deliverToPostalCode",
        "chargeToStreet": "chargeToStreet",
        "chargeToCityDetails": "chargeToCityDetails",
        "chargeToProvinceDetails": "chargeToProvinceDetails",
        "chargeToCountry": "chargeToCountry",
        "chargeToPostalCode": "chargeToPostalCode",
        "loadingPoint": "loadingPoint",
        "unloadingPoint": "unloadingPoint",
        "driverName1": "driverName1",
        "driverName2": "driverName1",
        "consignorLoadingPoint": "consignorLoadingPoint",
        "consignorLoadingCountry": "consignorLoadingCountry",
        "consigneeDeliveryPoint": "consigneeDeliveryPoint",
        "consigneeDeliveryCountry": "consigneeDeliveryCountry",
        "fleetNo1Registration": "fleetNo1Registration",
        "fleetNo2Registration": "fleetNo2Registration",
        "customerOnBehalfOf": "customerOnBehalfOf"
      },
      "options": {
        "type": "pdf"
      }
    },
    {
      "data": {
        "orderNo": "1",
        "depot": "depot",
        "tripSheetNumber": "12",
        "fleetNo1": "V1",
        "fleetNo2": "V2",
        "organization": "org",
        "customer": "customer",
        "productCode": "productCode",
        "route": "route",
        "unNumber": "un",
        "productName": "name",
        "quantityOrdered": "22",
        "requiredLoadingBefore": "date",
        "requiredDeliveryBefore": "date",
        "deliverToStreet": "deliverToStreet",
        "deliverToCityDetails": "deliverToCityDetails",
        "deliverToProvinceDetails": "deliverToProvinceDetails",
        "deliverToCountry": "deliverToCountry",
        "deliverToPostalCode": "deliverToPostalCode",
        "chargeToStreet": "chargeToStreet",
        "chargeToCityDetails": "chargeToCityDetails",
        "chargeToProvinceDetails": "chargeToProvinceDetails",
        "chargeToCountry": "chargeToCountry",
        "chargeToPostalCode": "chargeToPostalCode",
        "loadingPoint": "loadingPoint",
        "unloadingPoint": "unloadingPoint",
        "driverName1": "driverName1",
        "driverName2": "driverName1",
        "consignorLoadingPoint": "consignorLoadingPoint",
        "consignorLoadingCountry": "consignorLoadingCountry",
        "consigneeDeliveryPoint": "consigneeDeliveryPoint",
        "consigneeDeliveryCountry": "consigneeDeliveryCountry",
        "fleetNo1Registration": "fleetNo1Registration",
        "fleetNo2Registration": "fleetNo2Registration",
        "customerOnBehalfOf": "customerOnBehalfOf"
      },
      "options": {
        "type": "pdf"
      }
    },
    {
      "data": {
        "orderNo": "1",
        "depot": "depot",
        "tripSheetNumber": "12",
        "fleetNo1": "V1",
        "fleetNo2": "V2",
        "organization": "org",
        "customer": "customer",
        "productCode": "productCode",
        "route": "route",
        "unNumber": "un",
        "productName": "name",
        "quantityOrdered": "22",
        "requiredLoadingBefore": "date",
        "requiredDeliveryBefore": "date",
        "deliverToStreet": "deliverToStreet",
        "deliverToCityDetails": "deliverToCityDetails",
        "deliverToProvinceDetails": "deliverToProvinceDetails",
        "deliverToCountry": "deliverToCountry",
        "deliverToPostalCode": "deliverToPostalCode",
        "chargeToStreet": "chargeToStreet",
        "chargeToCityDetails": "chargeToCityDetails",
        "chargeToProvinceDetails": "chargeToProvinceDetails",
        "chargeToCountry": "chargeToCountry",
        "chargeToPostalCode": "chargeToPostalCode",
        "loadingPoint": "loadingPoint",
        "unloadingPoint": "unloadingPoint",
        "driverName1": "driverName1",
        "driverName2": "driverName1",
        "consignorLoadingPoint": "consignorLoadingPoint",
        "consignorLoadingCountry": "consignorLoadingCountry",
        "consigneeDeliveryPoint": "consigneeDeliveryPoint",
        "consigneeDeliveryCountry": "consigneeDeliveryCountry",
        "fleetNo1Registration": "fleetNo1Registration",
        "fleetNo2Registration": "fleetNo2Registration",
        "customerOnBehalfOf": "customerOnBehalfOf"
      },
      "options": {
        "type": "pdf"
      }
    },
    {
      "data": {
        "orderNo": "1",
        "depot": "depot",
        "tripSheetNumber": "12",
        "fleetNo1": "V1",
        "fleetNo2": "V2",
        "organization": "org",
        "customer": "customer",
        "productCode": "productCode",
        "route": "route",
        "unNumber": "un",
        "productName": "name",
        "quantityOrdered": "22",
        "requiredLoadingBefore": "date",
        "requiredDeliveryBefore": "date",
        "deliverToStreet": "deliverToStreet",
        "deliverToCityDetails": "deliverToCityDetails",
        "deliverToProvinceDetails": "deliverToProvinceDetails",
        "deliverToCountry": "deliverToCountry",
        "deliverToPostalCode": "deliverToPostalCode",
        "chargeToStreet": "chargeToStreet",
        "chargeToCityDetails": "chargeToCityDetails",
        "chargeToProvinceDetails": "chargeToProvinceDetails",
        "chargeToCountry": "chargeToCountry",
        "chargeToPostalCode": "chargeToPostalCode",
        "loadingPoint": "loadingPoint",
        "unloadingPoint": "unloadingPoint",
        "driverName1": "driverName1",
        "driverName2": "driverName1",
        "consignorLoadingPoint": "consignorLoadingPoint",
        "consignorLoadingCountry": "consignorLoadingCountry",
        "consigneeDeliveryPoint": "consigneeDeliveryPoint",
        "consigneeDeliveryCountry": "consigneeDeliveryCountry",
        "fleetNo1Registration": "fleetNo1Registration",
        "fleetNo2Registration": "fleetNo2Registration",
        "customerOnBehalfOf": "customerOnBehalfOf"
      },
      "options": {
        "type": "pdf"
      }
    },
    {
      "data": {
        "orderNo": "1",
        "depot": "depot",
        "tripSheetNumber": "12",
        "fleetNo1": "V1",
        "fleetNo2": "V2",
        "organization": "org",
        "customer": "customer",
        "productCode": "productCode",
        "route": "route",
        "unNumber": "un",
        "productName": "name",
        "quantityOrdered": "22",
        "requiredLoadingBefore": "date",
        "requiredDeliveryBefore": "date",
        "deliverToStreet": "deliverToStreet",
        "deliverToCityDetails": "deliverToCityDetails",
        "deliverToProvinceDetails": "deliverToProvinceDetails",
        "deliverToCountry": "deliverToCountry",
        "deliverToPostalCode": "deliverToPostalCode",
        "chargeToStreet": "chargeToStreet",
        "chargeToCityDetails": "chargeToCityDetails",
        "chargeToProvinceDetails": "chargeToProvinceDetails",
        "chargeToCountry": "chargeToCountry",
        "chargeToPostalCode": "chargeToPostalCode",
        "loadingPoint": "loadingPoint",
        "unloadingPoint": "unloadingPoint",
        "driverName1": "driverName1",
        "driverName2": "driverName1",
        "consignorLoadingPoint": "consignorLoadingPoint",
        "consignorLoadingCountry": "consignorLoadingCountry",
        "consigneeDeliveryPoint": "consigneeDeliveryPoint",
        "consigneeDeliveryCountry": "consigneeDeliveryCountry",
        "fleetNo1Registration": "fleetNo1Registration",
        "fleetNo2Registration": "fleetNo2Registration",
        "customerOnBehalfOf": "customerOnBehalfOf"
      },
      "options": {
        "type": "pdf"
      }
    }
  ],
  "mergeFiles": true,
  "responseType": "presignedDownloadLink"
}'
Response:

When mergeFiles is true:

[
    {
        "filename": "response.pdf",
        "fileIdentifier": "da3eb6a2-0d6f-4fc3-ac70-13f49be73077",
        "presignedDownloadUrl": "https://qa-document-service-api.cargoes.com/file-storage/file/presignedurl?signature=3afec8292e4b08dd489854f408b976f0d8bd7c47de957dcca566d4df720de93a51a88234875f21b8d8ee84f5912f5929|217bc8a0ee2ed44d118f19c905e7478e"
    }
]
When mergeFiles is false:

[
    {
        "filename": "Sea Payment Summary.docx-fffeea68434131e2-iqarin.pdf",
        "fileIdentifier": "23da60c4-2d09-497f-9f99-cb5e95df78b5",
        "presignedDownloadUrl": "https://staging-document-service-api.cargoes.com/file-storage/file/presignedurl?signature=093d7049ed91f7aea16899e5e9ec580a527fffd2e83783a7ff294a6b48fef30028799ba9a5fc255b6a9fd9ae82389ac8|2603472bdd4b536f8d0cb4af5dddf4a7"
    },
    {
        "filename": "Sea Payment Summary.docx-fffeea68434131e2-a0vpr8.pdf",
        "fileIdentifier": "be4d1229-e05a-4ff9-b743-81c6804e4678",
        "presignedDownloadUrl": "https://staging-document-service-api.cargoes.com/file-storage/file/presignedurl?signature=85e0ee3da6bfc6a947e178caca058c0a5885d80e020d8650374ffcbf9f89ce9a210b77d8aa69e7bee45afbcfc648883a|1fe66bddeb38d53a9c80dfb51ec6a91e"
    },
    {
        "filename": "Sea Payment Summary.docx-fffeea68434131e2-spj0xu.pdf",
        "fileIdentifier": "28be5100-5ba5-4dfd-a583-f0c9bd67ea17",
        "presignedDownloadUrl": "https://staging-document-service-api.cargoes.com/file-storage/file/presignedurl?signature=e21520f990de437e3a87f3ca201135449d66f6dc3e6bde1d2d14236ebc7369a05c0293b3977126fe9b5fbe876b070b5b|dd960224371f4430f1935d62f9c413f5"
    },
    {
        "filename": "Sea Payment Summary.docx-fffeea68434131e2-syltfh.pdf",
        "fileIdentifier": "12dbf710-f297-416e-85ae-5a3a82697cab",
        "presignedDownloadUrl": "https://staging-document-service-api.cargoes.com/file-storage/file/presignedurl?signature=7dba7b85c84065df8b352ef42afc33b4559f8bce112a990b05d12659adf2943582bb9ccc611388c8532ed6b38256f8cd|655bd6d0d4b3033edad8ee19f8763a3c"
    },
    {
        "filename": "Sea Payment Summary.docx-fffeea68434131e2-98vi87.pdf",
        "fileIdentifier": "90c97218-0ea5-47e0-b880-7e3d7e5a1604",
        "presignedDownloadUrl": "https://staging-document-service-api.cargoes.com/file-storage/file/presignedurl?signature=8c407f9444aca5faaf987238428e31233263fbd07bae5fb61ecd2ea1674ba98c042a6c58c6b3697c40267ee2f5cd9d4b|3c65e261dddcd1c38cf426b428e41ce2"
    }
]
Attribute	Type	Required	Default	Description
templateId	string	Yes		TemplateId which is to be downloaded
body	Json	Yes		Metadata for template which is to be downloaded. If you want to add image to the template specify it as {%image} in your template and give details for this image in data json as shown below. Where logo_path is url of image you want to render in the template (if not provided it will take default image url present in code) and logo_path_height, logo_path_width to set height and width for this image (default values are 190 and 100 respectively),logo_center is to specify if you want to set your image in center (default values is false).
The sample data for body which contains body with metadata and options looks like this:

This body contains metadata for the template and options.
Error Codes

Code	Error	Description
40030	Argument Error	For invalid arguments
50090	Api Error	Internal Server Error
40410	NotFound Error	If template id is not available
###File Size, Time Taken, and JSON Payload Comparison

File Size	Time Taken	JSON Payload Lines
5MB	< 3 sec	5k lines
13MB	12 sec	13.5k lines
30MB	24 sec	30k lines
50MB	27 sec	50k lines
Get template by template id
GET /templates/:templateId

Query attribute	Type	Required	Description
templateId	string	Yes	Template Id to get data
The sample response looks like this:

{
    "templateId": "48b744724fd6bd39",
    "templateName": "Ocean Bill of Lading",
    "templateS3Path": " https://docserstagingblobs.blob.core.windows.net/dtlp-templates-staging/48b744724fd6bd39",
    "organizationId": "1110090913",
    "applicationId": "1234215",
    "metadata": {
        "exporterName": "Honda-UK",
        "bookingNumber": "DPW897890",
        "documentNumber": "8799909",
        "consigneeName": "DP World",
        "forwardingAgent": "DP World London",
        "notifyParty": "Honda Head Office , UK",
        "notifyParty2": "Honda Head Office , India",
        "preCarriageBy": "Black Buck Trucks Ltd",
        "placeOfReceipt": "London",
        "domesticRouting": "No",
        "exportingCarrier": "Mersec",
        "portOfLoading": "London Port",
        "loadingTerminal": "Terminal 5",
        "portOfDischarge": "London Port",
        "placeOfReceiptOnCar": "Chennai",
        "typeOfMove": "Vessel",
        "table": [
            {
                "number": "X234",
                "noOfPkgs": "100",
                "hm": "HY",
                "description": "Package 1",
                "weight": "290",
                "measurement": "3*4*8"
            },
            {
                "number": "X786",
                "noOfPkgs": "100",
                "hm": "HU",
                "description": "Package 2",
                "weight": "286",
                "measurement": "3*42*8"
            },
            {
                "number": "X785",
                "noOfPkgs": "180",
                "hm": "HJ",
                "description": "Package 3",
                "weight": "286",
                "measurement": "31*42*8"
            }
        ],
        "shipRefNo": "RD89765",
        "details": "Mersec Carrier",
        "prepaid": "1000 $",
        "collect": "1300 $",
        "total": "2300 $",
        "witness": "DP World",
        "placeOfSignature": "London",
        "agentName": "DP World",
        "month": "November",
        "day": "18",
        "year": "2019",
        "blNumber": "BL457865"
    },
    "updatedAt": "2022-07-29T06:45:37.527Z",
    "createdAt": "2022-07-29T06:45:37.527Z"
}
Error Codes

Code	Error	Description
40030	Argument Error	For invalid arguments
50090	Api Error	Internal Server Error
40410	NotFound Error	If template id is not available
Get list of all the templates
GET /templates

This API will return list of all templates available and it supports filtering, sorting, pagination and text search as well.

To enable filtering/text search, the mentioned below can be passed as a query parameter while making the API call.

q:ocean bill
_organizationId:11145699
_templateName:emailTestTemplate
_applicationId:123422

Here, 'q' -> Is for text search and will query the entered text over templateId, templateName, organizationId and applicationId.

Sorting can be enable on the following fields templateId, templateName, organizationId and applicationId.

Inorder to sort, the following needs to be passed as query parameter while making the API call.

'_sort' : templateId     // Here, field Name can be any of - templateId, templateName, organizationId and applicationId
'_order' : asc           // Here, order can be 'asc' - Ascending or 'desc' - Descending. By default, it is set to 'asc'

To enable Pagination, the following needs to be passed as query parameter while making the API call.

'_limit' : 10   // This is where you can pass the number of records to be fetched. By default, it is set to '50'
'_page' : 1  // Here, you can pass the page number

The sample response looks like this:

[
    {
        "templateId": "48b744724fd6bd39",
        "templateName": "Ocean Bill of Lading",
        "templateS3Path": " https://docserstagingblobs.blob.core.windows.net/dtlp-templates-staging/48b744724fd6bd39",
        "organizationId": "1110090913",
        "applicationId": "1234215",
        "metadata": {
            "exporterName": "Honda-UK",
            "bookingNumber": "DPW897890",
            "documentNumber": "8799909",
            "consigneeName": "DP World",
            "forwardingAgent": "DP World London",
            "notifyParty": "Honda Head Office , UK",
            "notifyParty2": "Honda Head Office , India",
            "preCarriageBy": "Black Buck Trucks Ltd",
            "placeOfReceipt": "London",
            "domesticRouting": "No",
            "exportingCarrier": "Mersec",
            "portOfLoading": "London Port",
            "loadingTerminal": "Terminal 5",
            "portOfDischarge": "London Port",
            "placeOfReceiptOnCar": "Chennai",
            "typeOfMove": "Vessel",
            "table": [
                {
                    "number": "X234",
                    "noOfPkgs": "100",
                    "hm": "HY",
                    "description": "Package 1",
                    "weight": "290",
                    "measurement": "3*4*8"
                },
                {
                    "number": "X786",
                    "noOfPkgs": "100",
                    "hm": "HU",
                    "description": "Package 2",
                    "weight": "286",
                    "measurement": "3*42*8"
                },
                {
                    "number": "X785",
                    "noOfPkgs": "180",
                    "hm": "HJ",
                    "description": "Package 3",
                    "weight": "286",
                    "measurement": "31*42*8"
                }
            ],
            "shipRefNo": "RD89765",
            "details": "Mersec Carrier",
            "prepaid": "1000 $",
            "collect": "1300 $",
            "total": "2300 $",
            "witness": "DP World",
            "placeOfSignature": "London",
            "agentName": "DP World",
            "month": "November",
            "day": "18",
            "year": "2019",
            "blNumber": "BL457865"
        },
        "updatedAt": "2022-07-29T06:45:37.527Z",
        "createdAt": "2022-07-29T06:45:37.527Z"
    }
]
Error Codes

Code	Error	Description
40030	Argument Error	For invalid arguments
50090	Api Error	Internal Server Error
Get templates by organisation id
GET /templates/organization/:organizationId
This api gives the list of all the templates for this organization id.

Sorting can be enable on the following fields templateId, templateName, organizationId and applicationId.

Inorder to sort, the following needs to be passed as query parameter while making the API call.

'_sort' : templateId     // Here, field Name can be any of - templateId, templateName, organizationId and applicationId
'_order' : asc           // Here, order can be 'asc' - Ascending or 'desc' - Descending. By default, it is set to 'asc'

To enable Pagination, the following needs to be passed as query parameter while making the API call.

'_limit' : 10   // This is where you can pass the number of records to be fetched. By default, it is set to '50'
'_page' : 1  // Here, you can pass the page number

Attribute	Type	Required	Default	Description
organizationId	int	Yes		OrganizationId to fetch templates
The sample response looks like this:

[
    {
        "templateId": "48b744724fd6bd39",
        "templateName": "Ocean Bill of Lading",
        "templateS3Path": " https://docserstagingblobs.blob.core.windows.net/dtlp-templates-staging/48b744724fd6bd39",
        "organizationId": "1110090913",
        "applicationId": "1234215",
        "metadata": {
            "exporterName": "Honda-UK",
            "bookingNumber": "DPW897890",
            "documentNumber": "8799909",
            "consigneeName": "DP World",
            "forwardingAgent": "DP World London",
            "notifyParty": "Honda Head Office , UK",
            "notifyParty2": "Honda Head Office , India",
            "preCarriageBy": "Black Buck Trucks Ltd",
            "placeOfReceipt": "London",
            "domesticRouting": "No",
            "exportingCarrier": "Mersec",
            "portOfLoading": "London Port",
            "loadingTerminal": "Terminal 5",
            "portOfDischarge": "London Port",
            "placeOfReceiptOnCar": "Chennai",
            "typeOfMove": "Vessel",
            "table": [
                {
                    "number": "X234",
                    "noOfPkgs": "100",
                    "hm": "HY",
                    "description": "Package 1",
                    "weight": "290",
                    "measurement": "3*4*8"
                },
                {
                    "number": "X786",
                    "noOfPkgs": "100",
                    "hm": "HU",
                    "description": "Package 2",
                    "weight": "286",
                    "measurement": "3*42*8"
                },
                {
                    "number": "X785",
                    "noOfPkgs": "180",
                    "hm": "HJ",
                    "description": "Package 3",
                    "weight": "286",
                    "measurement": "31*42*8"
                }
            ],
            "shipRefNo": "RD89765",
            "details": "Mersec Carrier",
            "prepaid": "1000 $",
            "collect": "1300 $",
            "total": "2300 $",
            "witness": "DP World",
            "placeOfSignature": "London",
            "agentName": "DP World",
            "month": "November",
            "day": "18",
            "year": "2019",
            "blNumber": "BL457865"
        },
        "updatedAt": "2022-07-29T06:45:37.527Z",
        "createdAt": "2022-07-29T06:45:37.527Z"
    }
]
Error Codes

Code	Error	Description
40030	Argument Error	For invalid arguments
50090	Api Error	Internal Server Error
Get templates by application id
GET /templates/application/:applicationId
This api gives the list of all the templates for this application id

Sorting can be enable on the following fields templateId, templateName, organizationId and applicationId.

Inorder to sort, the following needs to be passed as query parameter while making the API call.

'_sort' : templateId     // Here, field Name can be any of - templateId, templateName, organizationId and applicationId
'_order' : asc           // Here, order can be 'asc' - Ascending or 'desc' - Descending. By default, it is set to 'asc'

To enable Pagination, the following needs to be passed as query parameter while making the API call.

'_limit' : 10   // This is where you can pass the number of records to be fetched. By default, it is set to '50'
'_page' : 1  // Here, you can pass the page number

Attribute	Type	Required	Default	Description
applicationId	string	Yes		ApplicationId to fetch templates
The sample response looks like this:

[
    {
        "templateId": "48b744724fd6bd39",
        "templateName": "Ocean Bill of Lading",
        "templateS3Path": " https://docserstagingblobs.blob.core.windows.net/dtlp-templates-staging/48b744724fd6bd39",
        "organizationId": "1110090913",
        "applicationId": "1234215",
        "metadata": {
            "exporterName": "Honda-UK",
            "bookingNumber": "DPW897890",
            "documentNumber": "8799909",
            "consigneeName": "DP World",
            "forwardingAgent": "DP World London",
            "notifyParty": "Honda Head Office , UK",
            "notifyParty2": "Honda Head Office , India",
            "preCarriageBy": "Black Buck Trucks Ltd",
            "placeOfReceipt": "London",
            "domesticRouting": "No",
            "exportingCarrier": "Mersec",
            "portOfLoading": "London Port",
            "loadingTerminal": "Terminal 5",
            "portOfDischarge": "London Port",
            "placeOfReceiptOnCar": "Chennai",
            "typeOfMove": "Vessel",
            "table": [
                {
                    "number": "X234",
                    "noOfPkgs": "100",
                    "hm": "HY",
                    "description": "Package 1",
                    "weight": "290",
                    "measurement": "3*4*8"
                },
                {
                    "number": "X786",
                    "noOfPkgs": "100",
                    "hm": "HU",
                    "description": "Package 2",
                    "weight": "286",
                    "measurement": "3*42*8"
                },
                {
                    "number": "X785",
                    "noOfPkgs": "180",
                    "hm": "HJ",
                    "description": "Package 3",
                    "weight": "286",
                    "measurement": "31*42*8"
                }
            ],
            "shipRefNo": "RD89765",
            "details": "Mersec Carrier",
            "prepaid": "1000 $",
            "collect": "1300 $",
            "total": "2300 $",
            "witness": "DP World",
            "placeOfSignature": "London",
            "agentName": "DP World",
            "month": "November",
            "day": "18",
            "year": "2019",
            "blNumber": "BL457865"
        },
        "updatedAt": "2022-07-29T06:45:37.527Z",
        "createdAt": "2022-07-29T06:45:37.527Z"
    }
]
Error Codes

Code	Error	Description
40030	Argument Error	For invalid arguments
50090	Api Error	Internal Server Error
Update template by template id
PUT /templates/:templateId
To update the template

Attribute	Type	Required	Default	Description
file	File	Yes		Template to be uploaded to azure storage account
organizationId	int	Yes		Organization Id with whom the file is associated
templateName	String	Yes		Template Name for this record
applicationId	string	Yes		Application Id with whom the file is associated
metadata	Json	Yes		Metadata which has ample data for this template
templateId	string	Yes		Template Id to update
validateTemplateTagsWithMetadata	Boolean	No	False	If true, it validates all the placeholders present in template with metadta. As of now it does not consider loop and complex structure. It only works for simple strings in the templates
The sample response looks like this:

{
    "message": "success"
}
NOTE:

The updated file must have the same extension as the existing one.
Code	Error	Description
40030	Argument Error	For invalid arguments
50090	Api Error	Internal Server Error
40410	Not Found Error	If template id is not available
Download Template
GET /templates/:templateId/download

Query attribute	Type	Required	Description
templateId	string	Yes	Template Id to download
The sample response looks like this:
Requested file

Error Codes

Code	Error	Description
40030	Argument Error	For invalid arguments
50090	Api Error	Internal Server Error
40410	NotFound Error	If template id is not available
Error response in case validateTemplateTagsWithMetadata flag is True

{

"errorCode": "40030",

"success": false,

"data": "[40030] Missing tags in uploaded template: {RANDOM_VARIABLE}, {DRIVER_NAME}",

"message": "Missing tags in uploaded template: {RANDOM_VARIABLE}, {DRIVER_NAME}"

}
Delete Template
DELETE /templates/:templateId

Query attribute	Type	Required	Description
templateId	string	Yes	Template Id to delete
The sample response looks like this:

{
    "message": "success"
}
Error Codes

Code	Error	Description
40030	Argument Error	For invalid arguments
50090	Api Error	Internal Server Error
40410	Not Found Error	If template id is not available
---,		
[[TOC]]

Modules Supported by Document Service:
###Basic Features

Different types of tags we use from docxtemplater:
This documentation helps in understanding of the working of most frequent tags we use in our templates.

Variable holding tags
Conditional tags
Loop tags
Section tags
Inverted section tags
Set Delimiter tags
Dash tags
Let's look in detail how each of these tags work

Variable tag:

Syntax :

{variable_name}
Data:

{
  variable_name : "Mike"
}
Template:

Hello {variable_name}!
With the provided data and given template, docxtemplater will produce the following:

Hello Mike!
Conditional tag:

conditions start with a pound and ends with a slash

Syntax:

{#hasCharges}
Charges:{chargesType}
{/hasCharges}
Data:

{
  "hasCharges":true,
  "charges":"delivery charges",
  "hasOffice":false,
  "Location":"chennai"
}
Template:

{#hasCharges}charges: {chargesType} {/hasCharges}
{#hasOffice}Address: {Location} {/hasOffice}
With the provided data and given template, docxtemplater will produce the following:

charges: delivery charges
condition tags works similar to an if clause, if the condition is true then docxtemplater will render the data present in that respective clause. In our example, as hasCharges is true, docxtemplater will go inside the loop and render chargesType, whereas hasOffice is false, so docxtemplater wouldn't go inside loop and render location.

Loop tag

Loops start with a pound and end with a slash

Syntax:

{#interests} {name} {/interests}
Data:

{
  "interests" : [
   { name : "biking" },
   { name : "skiing" },
   { name : "swimming" }
}
Template:

Interests:
{#interests}
-{name}
{/interests}
With the provided data and given template, docxtemplater will produce the following:

Interests:
-biking
-skiing
-swimming
Section tags

conditions and loops use the same syntax as sections.

Sections begin with a pound and ends with a slash.Condition and loop tags are subsets of section tags.We can use multiple tags and iterators inside a section tag.Sections can be used to render text one or more times based on value of key.

Syntax:

{#variables}
{first_variable}
{second_variable}
{/variables}
Data:

{
  "transport" :{
   "public" : "bus",
   "private" : "car"
  }
}
Template:

Transport preferance:
{#transport}
Public mode - {public}
Private mode - {private}
{/transport}
With the provided data and given template, docxtemplater will produce the following:

Transport preferance:

Public mode - bus
Private mode - car
Inverted Section tag

Its syntax starts with a hat and ends with a slash. It works similar to an else clause, they render text if the key doesn't exist, is false, or is an empty list. While sections can be used to render text one or more times based on the value of the key, inverted sections may render text once based on the inverse value of the key.

Syntax:

{^hasCharges} No charges {/hasCharges}
Data:

{
  “hasCharges”:false,
  “chargesType”: “delivery”,
  "repo":[]
}
Template:

{#hasCharges} {chargesType} {/hasCharges}
{^hasCharges} No charges {/hasCharges}
{#repo} {name} {/repo}
{^repo} No repos {/repo}
With the provided data and given template, docxtemplater will produce the following:

No charges
No repos
In our example, we used a conditional tag, as the value of hasCharges is false docxtemplater wouldn't render chargesType and it will go inside inverted section and produces "No charges" similarly in the next case as repo is null, inverted section is triggered and docxtemplater will go inside the inverted section and renders "No repos"

Set Delimiter tag

Set Delimiter tags start and end with an equal sign and change the tag delimiters from {} to custom strings.

Syntax:

{= [[ ]] =}
By default the delimiter used is {}, we can change it using "=" which is used as an assign operator.
Old delimiter opening tag = new delimiter opening tag,
{ = [[
New delimiter closing tag = old delimiter closing tag,
]] = }

Apart from writing this syntax in template we should also add the following line in our code:

new docxtemplater(zip,{
 delimiters : { start : “[[“,end:”]]”}
})
Data:

{
  "first_variable" : "callao",
  "second_variable" : "Peru"
}
Template:

{first_variable},
{= [[ ]]=}
[[second_variable]]
With the provided data and given template, docxtemplater will produce the following:

callao,
Peru
Dash tag

Dash tags provides some additional features.

If between the two tags {#tag}______{/tag},there is a table cell tag (<w:tc> or <a:tc>) , that means that your loop is inside a table, and it will expand the loop over the table row (<w:tr> or <a:tr>).In other cases it will not expand the loop.

Syntax:

{-w:p outer}{inner}{/outer} --> if you want to loop on paragraphs

{-w:tr outer}{-w:tc inner}{text}{/inner}{/outer} --> if you want loop over table row
Data:

{
    "outer": [
        {
            "inner":[
                {"text":"I"},
                {"text":"am"},
                {"text":"your"},
                {"text":"father"},
            ]
        },
        {
            "inner":[
                {"text":"I"},
                {"text":"am"},
                {"text":"your"},
                {"text":"son"},
            ]
        }
    ],
    "loop" :[
     { "para" : "first line"},
     { "para" : "second line"},
     { "para" : "third line"}
   ]   
}
Template:

{-w:tr outer}{-w:tc inner}{text}{/inner}{/outer}
{-w:p loop}{para}{/loop}
With the provided data and given template, docxtemplater will produce the following:

| I | am | your | father |
|--|--|--|--|--|--|
| I | am | your | son |

first line
second line
third line
Reference
https://docxtemplater.com/docs/tag-types/

Table Module (Currently below functionalities are supported):
Vertical loops
Syntax:

{:vt#users} {:vt/users}
For demo: https://docxtemplater.com/demo/#/view/vertical-table
Please follow the same syntax in template as shown in demo.

Sample request body:

{
  "data": {
    "users": [
      {
        "index": 1,
        "name": "John",
        "age": 44,
        "address": "3374 Olen Thomas Drive Frisco Texas 75034"
      },
      {
        "index": 2,
        "name": "Mary",
        "age": 31,
        "address": "352 Illinois Avenue Yamhill Oregon(OR) 97148"
      },
      {
        "index": 2,
        "name": "Leo",
        "age": 5,
        "address": "1402 Pearcy Avenue Fort Wayne  Indiana(IN) 46804"
      }
    ]
  },
  "options": {
    "type": "pdf",
    "encryptWithPassword": "",
    "watermark": {},
    "upload": false
  }
}
Table tag
Syntax:

{:table table1}
Table tag can be used as part of Table module purchased.
For demo: https://docxtemplater.com/demo/#/view/table-2

Please follow the same syntax as shown in demo.

For styling tables and other functionalities offered by Table Module, please refer :
https://docxtemplater.com/modules/table/#style

Sample request body:

{
  "data": {
    "table1": {
      "data": [
        [
          "Age",
          "44",
          "33",
          "42",
          "19"
        ],
        [
          "Address",
          "3374 Olen Thomas Drive Frisco Texas 75034",
          "352 Illinois Avenue Yamhill Oregon(OR) 97148",
          "1402 Pearcy Avenue Fort Wayne Indiana(IN) 46804",
          "3088 Terry Lane Orlando Florida(FL) 32801"
        ],
        [
          "Address",
          "3374 Olen Thomas Drive Frisco Texas 75034",
          "352 Illinois Avenue Yamhill Oregon(OR) 97148",
          "1402 Pearcy Avenue Fort Wayne Indiana(IN) 46804",
          "3088 Terry Lane Orlando Florida(FL) 32801"
        ]
      ],
      "fixedColumns": [
        null,
        null,
        null,
        null,
        null
      ],
      "widths": [
        80,
        110,
        110,
        110,
        110
      ],
      "header": [
        "Table",
        "1",
        "2",
        "3",
        "4"
      ],
      "subheader": [
        "Name",
        "John",
        "Mary",
        "Larry",
        "Tom"
      ],
      "chunkSize": {
        "type": "dynamic",
        "size": {
          "min": 9000,
          "max": 9100
        }
      },
      "border": "none"
    }
  },
  "options": {
    "type": "pdf",
    "encryptWithPassword": "",
    "watermark": {},
    "upload": false
  }
}

Image Module
Syntax:

{%image}
Sample request body:

{
  "data": {
    "images": [
      {
        "image_tag_name": "image1",
        "image_type": "file_url",
        "image_url": "https://images.unsplash.com/photo-1453728013993-6d66e9c9123a?ixlib=rb-1.2.1&ixid=MnwxMjA3fDB8MHxzZWFyY2h8Mnx8dmlld3xlbnwwfHwwfHw%3D&w=1000&q=80",
        "image_height": 200,
        "image_width": 200
      },
      {
        "image_tag_name": "image2",
        "image_type": "base64",
        "image_data": "data:image/png;base64,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",
        "image_height": 250,
        "image_width": 250
      }
    ]
  },
  "options": {
    "type": "pdf",
    "encryptWithPassword": "",
    "watermark": {},
    "upload": false
  }
}
Auto-numbering for Optional Fields in DOCX Templates
Enabling Auto-numbering in Microsoft Word
Before setting up optional fields in your DOCX template, you should enable automatic numbering in Microsoft Word instead of manually adding explicit numbers. To do this:

Open your DOCX template in Microsoft Word.

Select the section where you want numbering.

Go to the Home tab and click on the Numbering button (or use a custom numbering style).

Word will now manage numbering automatically, even when certain sections are dynamically included or omitted.

Configuring Optional Headings
When working with optional headings, use a conditional placeholder in your DOCX template to ensure that headings appear only if relevant data is provided in the request JSON.

Template Format:

{-w:p Placeholder_heading}Additional Terms{/}
How It Works:

If Placeholder_heading is present in the request JSON, then "Additional Terms" will be printed in the document.

If Placeholder_heading is absent, this heading will be omitted.

Example JSON Request
{
  "data": {
    "Placeholder_heading": "true",
    "Placeholder_AdditionalTerms": [
        "abc", "def", "ebc", "hsdish"
    ]
  },
  "options": {
    "type": "pdf",
    "upload": false
  }
}
Auto-numbering for Optional Clauses/Terms

For dynamically inserting optional clauses/terms under the heading, use the following syntax:

Template Format:

{-w:p Placeholder_AdditionalTerms}{.}{/}
How It Works:

If Placeholder_AdditionalTerms contains data, it will be auto-numbered in the document.

If the field is empty or missing, the numbering will automatically adjust to omit it.

Example JSON Request:

{
  "data": {
    "Placeholder_AdditionalTerms": [
        "abc", "def", "ebc", "hsdish"
    ]
  },
  "options": {
    "type": "pdf",
    "upload": false
  }
}

Expected Output in DOCX/PDF:

If the above JSON request is sent, the document will generate:

10.2 Additional Terms

(i) abc
(ii) def
(iii) ebc
(iv) hsdish
If Placeholder_AdditionalTerms is not present, this section will be omitted, and the numbering of other sections will remain intact.



Auto-numbering for Optional Schedules/Annexures

You can also dynamically insert optional schedules or annexures with auto-numbering. Use the following template syntax:

Template Format:

{-w:p Placeholder_OptionalSchedules}{.}{/}

How It Works:

If `Placeholder_OptionalSchedules` contains an array of schedule/annexure names or content, each will be inserted and auto-numbered in the output document.

If the field is empty or missing, the numbering will automatically adjust to omit it.

Example JSON Request:

{
  "data": {
    "Placeholder_OptionalSchedules": [
        "Schedule A: Payment Terms",
        "Schedule B: Delivery Milestones"
    ]
  },
  "options": {
    "type": "pdf",
    "upload": false
  }
}

Expected Output in DOCX/PDF:

If the above JSON request is sent, the document will generate:

Annexures

(i) Schedule A: Payment Terms
(ii) Schedule B: Delivery Milestones

If `Placeholder_OptionalSchedules` is not present, this section will be omitted, and the numbering of other sections will remain intact.

---

Auto-numbering for Optional Parties/Signatories

To dynamically insert a list of parties or signatories, use:

Template Format:

{-w:p Placeholder_Signatories}{.}{/}

Example JSON Request:

{
  "data": {
    "Placeholder_Signatories": [
        "John Doe, CEO",
        "Jane Smith, CFO"
    ]
  },
  "options": {
    "type": "pdf",
    "upload": false
  }
}

Expected Output in DOCX/PDF:

Signatories

(i) John Doe, CEO
(ii) Jane Smith, CFO

If `Placeholder_Signatories` is not present, this section will be omitted, and the numbering of other sections will remain intact.
