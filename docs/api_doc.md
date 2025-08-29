
## Table of Contents

- Authentication
- General Constraints
- File Storage Notes
- Non-Functional Requirements (NFRs)
- API Documentation


## Authentication

### Headers Required for All Requests

- `"X-DPW-ApplicationId": "" // The client Id, such as 'targaryen', the
  application Id should not change for a given application. Document
  Service Team will let the teams know which application id to use when
  onboarding.

- "x-api-key": "" // api key depending on the env.

### Security Notes

- API keys must not be shared among services. To request a new key for a
  service, email "cargoes-datachain-team@dpworld.com". Keys are generated and
  shared per service and environment. Keys must be kept confidential.

## General Constraints

- Combined length of `applicationId`, `organizationId`, and `file path` ≤ 1024 characters
- File names must not contain: `/ \ : * ? " < > |`

## File Storage Notes

- Upload File Api now supports Versioning for files. You can upload
  multiple files with same path, and a new version will be created.
- Users can download a specific version of a file as discussed in
  downloadFile api.
- Please note that, moveFiles and copyFiles api, doesn't support
  restoration of older versions of a file. i.e, If you try to move or copy a
  file with multiple versions, only the latest version will be present at
  destination path and older versions will be depricated.

## Non-Functional Requirements (NFRs)

See [NFRs for Document Service
](https://dev.azure.com/dpwhotfsonline/DTLP/wiki/wikis/DTLP.wiki/7434/NFRs-for-Document-Service)


 

# Upload File API

## Meta Data

**Purpose**
The `Upload File API` allows clients to upload files to Azure Blob Storage with rich capabilities including folder organization, version control, and secure access. It supports multiple configurations such as overwriting existing files, generating secure download links, and tagging uploads with metadata.

**Key Features**

- Uploads a single file per request with a size limit of 400MB.
- Allows assigning files to an organization via `organizationId`.
- Supports renaming files on upload using `newFileName`.
- Supports folder pathing using `path` with nested directories.
- Optional overwrite control with `overwriteFileOnDuplicate`.
- Allows setting SAS link expiry with `linkExpiryDuration`.
- Supports both deprecated `enableDownloadLink` and preferred `enablePresignedDownloadUrl`.
- Enables attaching metadata to the URL using `urlMetaData`.
- Supports version tracking and retrieval via `fileIdentifier`.

**Typical Use Cases**

- Upload employee documents to a structured storage path like `company/employees/`.
- Replace an existing file in Azure Blob using overwrite or versioning options.
- Generate time-limited presigned download links for secure sharing.
- Update previously uploaded documents using `fileIdentifier` without needing path/org again.
- Enable frontend or third-party systems to upload files securely by generating presigned URLs.

## Endpoint

```http
POST /file-storage
```

This API uploads one or more files to storage.

---


## Versions

- **v1 (default):** Overwrites files unless specified.
- **v2:** Prevents overwriting; adds unique suffix/UUID for duplicate paths.

---

## Upload File API Version 1

### Endpoint of Upload File

```http
POST /file-storage
```

### Request Parameters

**`file`**

- **Type:** `File`
- **Required:** Yes
- **Default:** –
- **Description:** File to be uploaded to azure storage account. Max file Size allowed is 400 MB.

---

**`organizationId`**

- **Type:** `Integer`
- **Required:** Yes
- **Default:** –
- **Description:** Organization I with whom the file is associated.

---

**`newFileName`**

- **Type:** `String`
- **Required:** No
- **Default:** –
- **Description:** Rename the file to this (including
  extension) before
  storing it. Please note
  that the file extension
  provided in the new file
  name should be the same as the one in the original file name.Only alphanumeric characters are allowed with hyphen and underscore.

---

**`path`**

- **Type:** `String`
- **Required:** No
- **Default:** –
- **Description:** If the file should be stored inside a folder/s, the path can be provided, where the directories are separated by a slash (e.g.: "company/ employees") . It should follow the regex pattern: '[a-zAZ0-9-"#./_ ] +$'.

---

**`overwriteFileOnDuplicate`**

- **Type:** `Boolean | String`
- **Required:** No
- **Default:** `false`
- **Description:** When the file already  exists in  azure  storage  account, if the user  wants to  overwrite  the file, they  can pass  true for this  field.

---

**`linkExpiryDuration`**

- **Type:** `Integer`
- **Required:** No
- **Default:** `7`
- **Description:** User is allowed to  set expiry  duration for  the SAS  token, default value  is 7 days.  Max expiry duration is  3650 days.  Only valid for enableDownloadLink

---

**`enableDownloadLink`**

- **Type:** `Boolean | String`
- **Required:** No
- **Default:** `false`
- **Description:** If a secured  download  link is  required for  this file , this  flag can be set to true.  Currently  the  download  link would  expire in 7  days from  the time of  creation of  the link [It is  recommended to go with a pre-signed  url based approach,  enableDownl  oadLink will  eventually  be  deprecated.]

---

**`enablePresignedDownloadUrl`**

- **Type:** `Boolean | String`
- **Required:** No
- **Default:** `false`
- **Description:** This flag if  set to true,  returns a download  url. The  download  link would  expire in 60  minutes by  default(or  the client's  read expiry  limit, if  available).  This expiry  duration can  be increased  on security  team's  approval.

---

**`urlMetaData`**

- **Type:** `JSON String`
- **Required:** No
- **Default:** `null`
- **Description:** Array of json  objects as  key-value  pair. These  key value  pairs would  be sent as query  params in  final  response  URL (in case  of presigned  download  URL).

---

**`fileIdentifier`**

- **Type:** `UUID`
- **Required:** No
- **Default:** `null`
- **Description:** fileIdentifier  mapped to  the  uploaded  file. This is  used to  update the  file mapped to this fileIdentifier.

---

### Notes

- Please note that only one of the param 'enableDownloadLink' or
  'enablePresignedDownloadUrl' can be enabled.
- If a file already exists with the same name and path (if provided), latest
  file would be overwritten. All previous uploaded version of files can be
  fetched using the getAllVersions Api. The same can be used to get
  version number for downloading a specific version of a file.
- currentVersion in response shows how many times the file has been
  updated.
- Presigned download URL 's expiry is configurable at a client level.
- Uploaded file name or new filename provided should not have
  following character
  Backslash (): \
  Forward Slash (/): /
  Colon ( : ): :
  Asterisk (_): _
  Question Mark (?): ?
  Double Quote ("): "
  Less Than (<): <
  Greater Than (>): >
  Pipe (|): |

---

### Sample JSON Requests Body & Responses from API

**Case 1: Using (organizationId + path + overwriteFileOnDuplicate)**
In this case, a new DB row will be created for the file uploaded and a unique
fileIdentifier will be associated with the uploaded file.

**Request Body**

```json
{
  "organizationId": 12345,
  "path": "testFile",
  "overwriteFileOnDuplicate": true,
  "newFileName": "test.pdf",
  "files": "<file to be uploaded>"
}
```

**Response**

```json
{
  "path": "testFile/test.pdf",
  "fileIdentifier": "64032d17-bfdc-4d3f-a078-72224d86ebd7",
  "currentVersion": 30
}
```

**Case 2: Using (organizationId + path + overwriteFileOnDuplicate) and
enableDownloadLink as true**

For this case, sas token based secure download link will be generated.

**JSON Request Body and Response**

**Request**

```json
{
  "organizationId": 12345,
  "path": "testFile",
  "overwriteFileOnDuplicate": true,
  "newFileName": "test.pdf",
  "files": "<file>",
  "linkExpiryDuration": 8,
  "enableDownloadLink": true
}
```

**Response**

```json
{
    "path": "testFile/test.pdf",
    "secureDownloadLink": "https://docserqablobs.blob.core.windows.net/dtlp
file-storage-qa/datachain/12345/testFile/test.pdf?
 st=2024-07-29T00%3A56%3A38Z&se=2024-08-06T00%3A56%3A38Z&sp=r
 &spr=https&sv=2018-03-28&sr=b&sig=K5Uavk5Hd9rxhvYFKUSFHBgqLqXgcZ
 %2F7GOxb05EXm%2FM%3D","fileIdentifier": "64032d17-bfdc-4d3f-a078-72224d86ebd7","currentVersion": 31
  }
```

**Case 3: Using (organizationId + path + overwriteFileOnDuplicate) and
enablePresignedDownloadUrl as 'true'**

For this case, presigned download link will be generated

**JSON Request Body and Responses**

**Request**

```json
{
  "organizationId": 12345,
  "path": "testFile",
  "overwriteFileOnDuplicate": true,
  "newFileName": "test.pdf",
  "files": "<file to be uploaded>",
  "enablePresignedDownloadUrl": true
}
```

**Response**

```json
{
    "path": "testFile/test.pdf",
    "presignedDownloadUrl": "https://qa-document-service-api.cargoes.com/
 file-storage/file/presignedurl?
 signature=36653cec3a9e3aebe7f9e561e9fc3674db2f6be4d9dc96b85b8ea41
 26cc92f4dce9ae77d136b246d0e839f3fbc0c0aee|
 8ac5412c4743d21bd4071e6b8c191d24","fileIdentifier": "64032d17-bfdc-4d3f-a078-72224d86ebd7","currentVersion": 31
  }
```

**Case 4: Using (organizationId + path + overwriteFileOnDuplicate) and
enablePresignedDownloadUrl as 'true' with urlMetaData
For this case, presigned download link will be generated.**

**JSON Request Body And Response**

**Request**

```json
{
  "organizationId": 12345,
  "path": "testFile",
  "overwriteFileOnDuplicate": true,
  "newFileName": "test.pdf",
  "files": "<file>",
  "enablePresignedDownloadUrl": true,
  "urlMetaData": {
    "key": "value"
  }
}
```

**Response**

```json
{
    "path": "testFile/test.pdf",
    "presignedDownloadUrl":  "https://qa-document-service-api.cargoes.com/
 file-storage/file/presignedurl?
 key=value&signature=36653cec3a9e3aebe7f9e561e9fc3674db2f6be4d9dc96
 b85b8ea4126cc92f4dce9ae77d136b246d0e839f3fbc0c0aee|
 8ac5412c4743d21bd4071e6b8c191d24",
    "fileIdentifier": "64032d17-bfdc-4d3f-a078-72224d86ebd7",
    "currentVersion": 31
  }
```

**Case 5: Using fileIdentifier to update a file already uploaded. In this case, organizationId and path should not be provided.**

**JSON Request Body and Response**

**Request**

```json
{
  "fileIdentifier": "64032d17-bfdc-4d3f-a078-72224d86ebd7",
  "newFileName": "test.pdf",
  "files": "<file>"
}
```

**Response**

```json
{
  "path": "testFile/test.pdf",
  "fileIdentifier": "64032d17-bfdc-4d3f-a078-72224d86ebd7",
  "currentVersion": 32
}
```

---

### Error Codes

- `40030`: Argument Error – Invalid input parameters
- `50090`: API Error – Internal Server Error
- `42210`: FileUpload Error – Unable to upload file

---

## Upload File API Version 2 (v2)

### Notes

- Please refer to the version 1 (v1) API for the base structure,
  validations, and overall workflow.
- The primary enhancement in version 2 (v2) is support for duplicate
  file path handling. Unlike v1, which overwrites existing files if the
  same file path is used, v2 ensures each file upload is uniquely
  stored, even if the file path or filename is identical.
- When a duplicate file path is detected, v2 automatically appends a
  UUID or suffix to the file name or path to avoid conflicts, ensuring
  that no files are overwritten unintentionally.
- It consistently returns the resolved storage path, the unique
  fileIdentifier, and the current version number as part of the
  response.

### Sample curl Requests & Responses

**Sample cURL Request Example**

```bash
curl --location 'http: //localhost:3300/file-storage' \
--header 'X-DPW-ApplicationId: datachain'\
--header 'x-api-key: YOUR_API_KEY' \
--header 'X-Api-Version: v2' \
--form 'files=@"/Users/deepali/Downloads/test (3).pdf"' \
--form  'newFileName="testfile1.xlsx"' \
--form 'path=testfolder2' \
--form 'fileIdentifier="1a295f61-3b87-4de8-98db-c2fcbd59068b"'
```

**Sample cURL Response**

```json
{
  "path": "testfolder2/1a295f61-3b87-4de8-98db-c2fcbd59068b/testfile1.xlsx",
  "fileIdentifier": "1a295f61-3b87-4de8-98db-c2fcbd59068b",
  "currentVersion": 2,
  "etag": "SowWISeub9IFYUncU0I9WA=="
}
```

---

### Error Codes

- `40030`: Argument Error – Invalid input parameters
- `50090`: API Error – Internal Server Error
- `42210`: FileUpload Error – Unable to upload file

---

# Bulk-File Upload API

## Endpoint

```http
POST /bulk-file-storage
```

An endpoint that supports bulk file upload (single / multiple files). This endpoint
does not specifically put the files under an organisation, rather it takes a
storagePath variable, and puts the files there.
There are 2 versions available for this api. By default it takes version1

---

## Meta Data

**Purpose**
The `Bulk Upload File API` allows uploading multiple files in a single API call to a designated Azure Blob Storage path. It enables efficient file transfer with options to overwrite existing files, set download link generation preferences, and manage metadata.

**Key Features**

- Uploads multiple files simultaneously with total size capped at 100 MB.
- Supports two modes:
  - **v1:** Pass individual file keys and values separately.
  - **v2:** Pass all files as an array using a unified `files` key.
- Allows uploading to a specific path using `storagePath`.
- Optional file renaming through `newFileNames` array.
- Overwrite control using `overwriteFileOnDuplicateAllowed`.
- Generates secure download links per file or as a ZIP:
  - `enableDownloadLinkForEachFile` for individual file links.
  - `enableDownloadLinkForBulkDownload` for a ZIP with all files.
- Link expiry configurable with `linkExpiryDuration`.
- Supports updating existing files using `fileIdentifier`.

**Typical Use Cases**

- Upload a batch of invoices, reports, or templates for a client.
- Share documents as a downloadable ZIP via secure link.
- Rename and organize documents during upload into folders.
- Replace previously uploaded documents based on `fileIdentifier`.
- Automate large file syncs without per-file API calls.

## Versions

- **v1 (default):** Requires each file to be passed with a unique `fileKey`.

---

## Version 1 Bulk Upload File API

This is old version where we have to pass multiple files with their fileNames.

### Request Parameters

---

**`fileKey`**

- **Type:** `File[]`
- **Required:** Yes
- **Description:** File to be  uploaded to  azure  storage. To  add multiple  files add  more rows  with fileKey  as key and  your file.  This fileKey  is not used  in azure  storage  account it is  only for  reference  purposes in  response to this API and filekey  should  always be unique in case of  multiple  files. The file  size allowed for each  individual  file is 10 Mb  and the  combined  size of all  files should  be less than 100 Mb.

---

**`storagePath`**

- **Type:** `String`
- **Required:** No
- **Description:**  
 If the file  should be  stored inside  folder/s, the  path can be  provided,  where the  directories  are  separated  by a slash  (e.g.:  "company/  employees")  . The path  will begin  from under  the azure  storage  account. It  should  follow the  regex  pattern: '^[a-zA  Z0-9-"#./_ ]  +$'.

---

**`overwriteFileOnDuplicateAllowed`**

- **Type:** `Boolean | String`
- **Required:** No
- **Default:** `false`
- **Description:**  
   When the  file already exists in the  azure storage  account, if  the user  wants to  overwrite  the file, they  can pass  true for this  field. This  applies to all  the files  being sent.

---

**`linkExpiryDuration`**

- **Type:** `Integer`
- **Required:** No
- **Default:** `7`
- **Description:**  
   User is
  allowed to
  set the
  expiry
  duration for
  the SAS
  token, the
  default value
  is 7 days

---

**`enableDownloadLinkForEachFile`**

- **Type:** `Boolean | String`
- **Required:** No
- **Default:** `false`
- **Description:**  
  Secure Download Link is a direct download link that points to a location within the Internet where the user can download a file and anyone can access this link. If a secured download link is required for the uploaded files, this flag can be set to true. Link expiry is set by the linkExpiryDuration attribute. With this flag as true, the response contains a secure download link for each file.

---

**`enableDownloadLinkForBulkDownload`**

- **Type:** `Boolean | String`
- **Required:** No
- **Default:** `false`
- **Description:**  
   With this
  flag as true
  response will
  be a zip
  folder with
  all files in it

---

**`fileIdentifier`**

- **Type:** `UUID`
- **Required:** No
- **Default:** `null`
- **Description:**  
   fileIdentifier
  mapped to
  the
  uploaded
  file, this
  parameter is
  only needed
  when user is
  trying to
  update an
  existing file

---

**`newFileNames`**

- **Type:** `String`
- **Required:** No
- **Default:** By default urfile will be stored with the same name as original file
- **Description:**  
   If you want to store your file with newName.Please provide names with extension and it allows only alphanumeric character and hyphen and underscore.

---

### Notes

- If a file already exists with the same name and path (if provided):
  If overwriteFileOnDuplicate is true, then files will be overwritten.
  Else, the service will throw a 422 (Unprocessable Entity) status code.
- Uploaded file name or new filename provided should not have following character:
  Backslash (): \
  Forward Slash (/): /
  Colon ( : ): :
  Asterisk (_): _
  Question Mark (?): ?
  Double Quote ("): "
  Less Than (<): <
  Greater Than (>): >
  Pipe (|): |

---

### Sample cURL Request

```bash
curl --location --request POST 'http://localhost:3300/bulk-file-storage' \
--header 'X-DPW-ApplicationId: datachain' \
--header 'x-api-key: 0fec68342d502b603f7bd43b66ad2ee9' \
--form 'overwriteFileOnDuplicateAllowed="true"' \
--form 'storagePath="12345/test/1"' \
--form 'invoice2=@"/Users/deepali/Downloads/3.pdf"' \
--form 'invoice1=@"/Users/deepali/Downloads/2.pdf"'

```

---

### Sample JSON Request Body And Responses

**Case 1: Using `storagePath` and `overwriteFileOnDuplicateAllowed`**

```json
{
      "overwriteFileOnDuplicateAllowed": true,
      "storagePath": "12345/test",
      "file1": <file to be uploaded>,
      "file2": <file to be uploaded>,
      "linkExpiryDuration": 8,
      "enableDownloadLink": true
    }
```

**Case 2: Using `fileIdentifier`**

Here, the user need not explicitly pass "overwriteFileOnDuplicateAllowed".
In this case if "fileIdentifier" is provided then by default
"overwriteFileOnDuplicateAllowed" is considered to be "true"

```json
{
      "fileIdentifier": "<UUID>",
      "file1": <file to be uploaded>,
      "file2": <file to be uploaded>,
      "linkExpiryDuration": 8,
      "enableDownloadLink": true
    }
```

---

**The sample response looks like this**

**With Secure Download Link (SDL) per Folder**

Here, there will be no change in the response. In this case, the user is just interested in the secure downloadable link and doesn't even require paths/locations. So in DB, there will be no entry for the bulk upload file request where the user opted for "enableDownloadLinkForBulkDownload": true.

```json
{
  "path": "testFile/test.pdf",
  "secureDownloadLink": "<LINK>"
}
```

---

**With Secure Download Link (SDL) per File**
In this case, a new DB row will be created for each file uploaded and a unique file identifier will be associated with each uploaded file.

```json
[
  {
    "fileIdentifier": "<UUID of length 32>",
    "currentVersion": 1,
    "key": "file1",
    "fileName": "1a16a8509c3406ed.html",
    "path": "12345/test/1a16a8509c3406ed.html",
    "location": "https://docserstagingblobs.blob.core.windows.net/dtlp-file-storage-staging/zms/12345/test/1a16a8509c3406ed.html",
    "secureDownloadLink": "<LINK>"
  },
  {
    "fileIdentifier": "<UUID of length 32>",
    "currentVersion": 1,
    "key": "file2",
    "fileName": "test1.xlsx",
    "path": "12345/test/test1.xlsx",
    "location": "https://docserstagingblobs.blob.core.windows.net/dtlp-file-storage-staging/zms/12345/test/test1.xlsx",
    "secureDownloadLink": "<LINK>"
  }
]
```

---

**Without SDL**
In this case, a new DB row will be created for each file uploaded and a unique fileIdentifier will be associated with each uploaded file.

```json
[
  {
    "fileIdentifier": "<UUID of length 32>",
    "currentVersion": 1,
    "key": "file1",
    "fileName": "1a16a8509c3406ed.html",
    "path": "12345/test/1a16a8509c3406ed.html",
    "location": "https://docserstagingblobs.blob.core.windows.net/dtlp-file-storage-staging/zms/12345/test/1a16a8509c3406ed.html"
  },
  {
    "fileIdentifier": "<UUID of length 32>",
    "currentVersion": 1,
    "key": "file2",
    "fileName": "test1.xlsx",
    "path": "12345/test/test1.xlsx",
    "location": "https://docserstagingblobs.blob.core.windows.net/dtlp-file-storage-staging/zms/12345/test/test1.xlsx"
  }
]
```

---

**If enableDownloadLinkForEachFile is true, a secure download link will be provided for each file in the response:**

```json
[
  {
    "key": "invoice1",
    "fileName": "2.pdf",
    "path": "12345/test/1/2.pdf",
    "location": "https://docserdevblobs.blob.core.windows.net/dtlp-file-storage-development/datachain/12345/test/1/2.pdf",
    "secureDownloadLink": "https://docserdevblobs.blob.core.windows.net/dtlp-file-storage-development/datachain/12345/test/1/2.pdf?st=2023-03-27T05%3A50%3A34Z&se=2023-04-03T05%3A50%3A34Z&sp=r&spr=https&sv=2018-03-28&sr=b&sig=dlmdH6rVWs327RzTPhgUZs9i1RY5DTGcuSFN6YGA0aE%3D"
  },
  {
    "key": "invoice2",
    "fileName": "3.pdf",
    "path": "12345/test/1/3.pdf",
    "location": "https://docserdevblobs.blob.core.windows.net/dtlp-file-storage-development/datachain/12345/test/1/3.pdf",
    "secureDownloadLink": "https://docserdevblobs.blob.core.windows.net/dtlp-file-storage-development/datachain/12345/test/1/3.pdf?st=2023-03-27T05%3A50%3A34Z&se=2023-04-03T05%3A50%3A34Z&sp=r&spr=https&sv=2018-03-28&sr=b&sig=dlmdH6rVWs327RzTPhgUZs9i1RY5DTGcuSFN6YGA0aE%3D"
  }
]
```

**If enableDownloadLinkForBulkDownload is true, the secure download link in the response will point to a ZIP folder containing all files:**

```json
{
  "filename": "response.zip",
  "secureDownloadLink": "https://docserstagingblobs.blob.core.windows.net/dtlp-file-storage-development/datachain/bulkUploadZipFiles/19debe16f2f0-45a5-bbb6-6572b42b3898.zip?st=2023-03-14T06%3A12%3A19Z&se=2033-03-11T06%3A12%3A19Z&sp=r&spr=https&sv=2018-03-28&sr=b&sig=Keh39m%2FjgegUN15h3zknusrGSfjIa6b4BEQ6w85Do%2F8%3D"
}
```

## Bulk Upload File API (Version 2)

### Endpoint

```http
POST /bulk-file-storage
```

This is new version where we have to pass multiple files together with key as files.

### Header Requirement

To use this version add following header in your request

```
X-Api-Version:v2
```

---

### Request Parameters

---

**`files`**

- **Type:** `File[]`
- **Required:** Yes
- **Description:**  
   Multiple or
  single Files
  to be
  uploaded to
  azure
  storage. File
  size allowed
  for each
  individual
  file is 10 Mb
  and
  combined
  size of all
  files should
  be less than
  100 Mb.

---

**`storagePath`**

- **Type:** `String`
- **Required:** No
- **Description:**  
   If the fileshould be stored inside folder/s, the path can be provided, where the directories are separated by a slash (e.g.: "company/ employees") . The path will begin from under the azure storage account.

---

**`overwriteFileOnDuplicateAllowed`**

- **Type:** `Boolean | String`
- **Required:** No
- **Default:** `false`
- **Description:**  
  When the file already exists in azure storage account, if the user wants to overwrite the file, they can pass true for this field. This applies to all the files being sent.

---

**`linkExpiryDuration`**

- **Type:** `Integer`
- **Required:** No
- **Default:** `7`
- **Description:**  
  User is allowed to set the expiry duration for the SAS token, the default value is 7 day

---

**`enableDownloadLinkForEachFile`**

- **Type:** `Boolean | String`
- **Required:** No
- **Default:** `false`
- **Description:**  
   Secure Download Link is a direct download link. It points to a location within the Internet where the user can download a file and anyone can access this link. If a secured download link is required for the uploaded files, this flag can be set to true. Link expiry is set by the 'linkExpiryDu ration' attribute. With this flag as true response contains the secure download link for each file.

---

**`enableDownloadLinkForBulkDownload`**

- **Type:** `Boolean | String`
- **Required:** No
- **Default:** `false`
- **Description:** With this flag as true response will be a zip folder with all files in it.

---

**`fileIdentifier`**

- **Type:** `UUID`
- **Required:** No
- **Default:** `null`
- **Description:**  
   fileIdentifier mapped to the uploaded file

---

**`newFileNames`**

- **Type:** `Array`
- **Required:** No
- **Default:** By default ur file will be stored with the same name as original file.
- **Description:**  
  It is an array of file names . If you want to store your file with newName. Please provide names with extension and it allows only alphanumeric character and hyphen and underscore.

---

### Notes

- If a file already exists with the same name and path (if provided):
  - If overwriteFileOnDuplicate is true, then files will be overwritten.
  - Else, the service will throw a 422 (Unprocessable Entity) status code.
  - Number of new filenames should match with total files provided for upload and array order should be same as input files order.

---

### Sample cURL Request And Responses

```bash
curl --location --request POST 'http://staging-document-service-api.privatecargoes.com/bulk-file-storage' \
--header 'X-DPW-ApplicationId: datachain' \
--header 'x-api-key: 9e0b7bc7bd666a8ac0d7f5c70d3460e0' \
--header 'X-Api-Version: v2' \
--form 'overwriteFileOnDuplicateAllowed="true"' \
--form 'files=@"/Users/deepali/Downloads/2.pdf"' \
--form 'files=@"/Users/deepali/Downloads/3.pdf"' \
--form 'storagePath="12345/test/1"'

```

---

### Sample JSON Request Bodies and Responses

**Case 1: Using `storagePath` and `overwriteFileOnDuplicateAllowed`**

```json
{
        "overwriteFileOnDuplicateAllowed": true,
        "storagePath": "12345/test",
        "files":<files to be uploaded>,
        "linkExpiryDuration": 8,
        "enableDownloadLink": true
      }
```

**Case 2: Using `fileIdentifier`**
Here, the user need not explicitly pass "overwriteFileOnDuplicateAllowed". In this case if "fileIdentifier" is provided then by default "overwriteFileOnDuplicateAllowed" is considered to be "true".

```json
{
  "fileIdentifier": "< UUID of length 32>",
  "files": "<files to be uploaded>",
  "linkExpiryDuration": 8,
  "enableDownloadLink": true
}
```

---

**Sample Responses**

**With SDL Per Folder**
Here, there will be no change in the response. In this case, the user is just interested in the secure downloadable link and doesn't even require paths/locations.So in DB, there will be no entry for the bulk upload file request where the user opted for "enableDownloadLinkForBulkDownload": true.

```json
{
  "path": "testFile/test.pdf",
  "secureDownloadLink": "<LINK>"
}
```

---

**With SDL Created Per File**
In this case, a new DB row will be created for each file uploaded and a unique file identifier will be associated with each uploaded file.

```json
[
  {
    "fileIdentifier": "<UUID of length 32>",
    "currentVersion": 1,
    "key": "0",
    "fileName": "Before-US-vietnameseCharsTemplate-af4976c330b582db-uejdtq.pdf",
    "path": "12345/test/Before-US-vietnameseCharsTemplate-af4976c330b582db-uejdtq.pdf",
    "location": "https://docserstagingblobs.blob.core.windows.net/dtlp-file-storage-staging/runner/12345/test/Before-US-vietnameseCharsTemplate-af4976c330b582db-uejdtq.pdf",
    "secureDownloadLink": "<LINK>"
  },
  {
    "fileIdentifier": "<UUID of length 32>",
    "currentVersion": 1,
    "key": "1",
    "fileName": "OCEANorCOMBINEDTRANSPORTBOL_V3.1.docx-001b2630dfd95697.docx",
    "path": "12345/test/OCEANorCOMBINEDTRANSPORTBOL_V3.1.docx-001b2630dfd95697.docx",
    "location": "https://docserstagingblobs.blob.core.windows.net/dtlp-file-storage-staging/runner/12345/test/OCEANorCOMBINEDTRANSPORTBOL_V3.1.docx-001b2630dfd95697.docx",
    "secureDownloadLink": "<LINK>"
  }
]
```

---

**Without SDL**
In this case, a new DB row will be created for each file uploaded and a unique fileIdentifier will be associated with each uploaded file.

```json
[
  {
    "fileIdentifier": "<UUID of length 32>",
    "currentVersion": 1,
    "key": "0",
    "fileName": "Before-US-vietnameseCharsTemplate-af4976c330b582db-uejdtq.pdf",
    "path": "12345/test/Before-US-vietnameseCharsTemplate-af4976c330b582db-uejdtq.pdf",
    "location": "https://docserstagingblobs.blob.core.windows.net/dtlp-file-storage-staging/runner/12345/test/Before-US-vietnameseCharsTemplate-af4976c330b582db-uejdtq.pdf"
  },
  {
    "fileIdentifier": "<UUID of length 32>",
    "currentVersion": 1,
    "key": "1",
    "fileName": "OCEANorCOMBINEDTRANSPORTBOL_V3.1.docx-001b2630dfd95697.docx",
    "path": "12345/test/OCEANorCOMBINEDTRANSPORTBOL_V3.1.docx-001b2630dfd95697.docx",
    "location": "https://docserstagingblobs.blob.core.windows.net/dtlp-file-storage-staging/runner/12345/test/OCEANorCOMBINEDTRANSPORTBOL_V3.1.docx-001b2630dfd95697.docx"
  }
]
```

## If enableDownloadLinkForBulkDownload is true, the response will contain a secure download link to a ZIP folder containing all files.

```json
{
  "filename": "response.zip",
  "secureDownloadLink": "https://docserstagingblobs.blob.core.windows.net/dtlp-file-storage-staging/runner/bulkUploadZipFiles/<UUID>.zip?st=<start-time>&se=<expiry-time>&sp=r&spr=https&sv=2018-03-28&sr=b&sig=<signature>"
}
```

**With Bulk Download SDL**

```json
{
  "filename": "response.zip",
  "secureDownloadLink": "<ZIP DOWNLOAD LINK>"
}
```

---

### Error Codes

- `40030`: Argument Error – Invalid input parameters
- `50090`: API Error – Internal Server Error
- `42210`: FileUpload Error – Unable to upload file

---

# Download File API

## Endpoint

```http
GET /file-storage/file`
```

Retrieve a file using one of two approaches: using the file `path` and `organizationId`, or using the `fileIdentifier`.

---

## Meta Data

**Purpose**
The `Download File API` allows users to retrieve files stored in Azure Blob Storage either by specifying a storage path or a unique `fileIdentifier`. It supports downloading the latest or a specific version of the file, with optional renaming and absolute path support.

**Key Features**

- Downloads files by `path + organizationId` or using `fileIdentifier`.
- Supports output file renaming via `outputFileName`.
- Enables absolute path-based access using `isAbsolutePath`.
- Allows retrieval of specific file versions via `version` query param.
- Flexible identification method using either file path or UUID.
- Default behavior retrieves the latest version of the file.

**Typical Use Cases**

- Download a report, invoice, or user document from its known path.
- Retrieve a previous version of a file for audit or rollback.
- Share a file with a custom filename for better clarity.
- Fetch files uploaded via presigned URLs using their `fileIdentifier`.
- Access content using absolute Azure storage paths when needed.

## Query Parameters

**`organizationId`**

- **Type:** `int`
- **Required:** Yes (only if path
  is provided)
- **Description:** Organization Id with whom the file is associated.

**`path`**

- **Type:** `String`
- **Required:** No
- **Description:** Path of the file in azure storage account, which was provided by uploadFile.

**`outputFileName`**

- **Type:** `String`
- **Required:** No
- **Description:** Desired output name (with extension), if the file name should be changed.Also extension should match with the source file extension and filename should not contain any invalid characters like controlled charaters or &.

**` version`**

- **Type:** `integer`
- **Required:** No
- **Description:** If user wants to retrieve a particular version for a file, same can be done by providing version number. To get how many versions have been created, user can use getAllVersions api.

**` isAbsolutePath`**

- **Type:** `Boolean`
- **Required:** No
- **Description:** if user wants to send Absolute file path then this variable is to be set true. In this case organization Id will not be a required paramter. Example Path- applicationId/organizationId/uploadPath.

**`fileIdentifier`**

- **Type:** `UUID`
- **Required:** No
- **Description:** The system supports file identifiers for uploaded files, whether the files are uploaded using pre-signed URLs or other methods.

## Notes For DownLoad File API

- If `fileIdentifier` is passed, `organizationId` and `path` are not needed
- By default, the **latest version** is downloaded

## Sample Request Bodies and Responses

**Example Using Path**

```json
{
  "organizationId": 12345,
  "path": "testFile/3.pdf",
  "outputFileName": "testfile"
}
```

**Example Using fileIdentifier**

```json
{
  "fileIdentifier": "<file_identifier>",
  "outputFileName": "testfile"
}
```

**Sample Response For Download File API**
A file stream is returned.

## Error Codes

- `40030`: Argument Error – Invalid input parameters
- `50090`: API Error – Internal Server Error

---

# Bulk Download Files API

## Endpoint

```http
POST /file-storage/bulkDownload
```

Downloads multiple files stored in Azure by zipping them into a single archive. Users can optionally receive a secure download link or a presigned URL.

## Meta Data

**Purpose**
The `Bulk Download File API` enables downloading multiple files at once by accepting a list of storage paths or file identifiers. It packages the files into a single ZIP file, with options for secure sharing using presigned or direct download links.

**Key Features**

- Accepts multiple file paths via `storagePaths` or file IDs via `fileIdentifiers`.
- Combines all selected files into a `.zip` archive for a single download.
- Supports both secure direct download links (`enableDownloadLink`) and presigned links (`enablePresignedDownloadUrl`).
- Allows setting expiration and access limits using `options` like `readCount` and `readExpiryDuration`.
- Optional `organizationId` can be provided or embedded in paths.
- Control storage hierarchy using `storeFilesAtRootLocation`.
- Custom output filename via `outputFileName`.

**Typical Use Cases**

- Share multiple client reports or documents in one downloadable ZIP.
- Automate periodic document backups or exports as ZIP archives.
- Provide secure time-limited download access to multiple files.
- Enable bulk access to archived or versioned content based on IDs.
- Deliver a set of generated PDFs or attachments for a transaction or case.

## Request Body Parameters

**`storagePaths`**

- **Type:** `Array`
- **Required:** No
- **Default:** None
- **Description:** Array of paths of all the files in azure storage account

**`outputFileName`**

- **Type:** `String (.zip)`
- **Required:** No
- **Default:** None
- **Description:** Desired output name (with extension), if the file name should be changed. It allows .zip extension only.

**`organizationId`**

- **Type:** `int`
- **Required:** No
- **Default:** None
- **Description:** Organization Id with whom the file is associated.

**`storeFilesAtRootLocation`**

- **Type:** `Boolean
- **Required:** No
- **Default:** False
- **Description:** Flag to store all the files at the root location.

**`linkExpiryDuration`**

- **Type:** `int`
- **Required:** No
- **Default:** 7
- **Description:** User is allowed to set expiry duration for the SAS token, default value is 7 days.

**`enableDownloadLink`**

- **Type:** `Boolean`
- **Required:** No
- **Default:** false
- **Description:** If a secured download link is required for this file , this flag can be set to true. Currently the download link would expire in 7 days from the time of creation of the link.

**`fileIdentifiers`**

- **Type:** `Array of <UUID>`
- **Required:** No
- **Default:** None
- **Description:** The system supports file identifiers for uploaded files, whether the files are uploaded using presigned URLs or other methods.

**`enablePresignedDownloadUrl`**

- **Type:** `Boolean`
- **Required:** No
- **Default:** false
- **Description:** Creates a presignedDo wnload link for this file. This link will be valid for max 60 mins.

**`options`**

- **Type:** `JSON`
- **Required:** No
- **Default:** readCount is 1000 and readExpiryDuration is 60 mins
- **Description:** It has metadata for presignurl data like readCount(no. if time file can be read from this link) and readExpiry Duration(du ration for which this link is valid). Sample curl is written below. If this is not present then presigned will be created for default values that 60 mins and 1000 readCount. Value more than 60 and 1000 are not allowed unless explicitly set to greater value in client config for ur client.

## Notes

**We need security approval for extending the expiry duration in case of enablePresignedDownloadUrl.**

- Bulk download function simply downloads all the files at the given paths and does not depend on organizationId , analogous to bulk upload function, allowing the application to download from specific paths, not depending an organization.

- To support some customer's requests , we are allowing an optional parameter : organizationId. By default we don't append organizationId in the storagePaths[ which will be used to fetch the desired files].

-By default, it is expected for the user to send the storagePaths containing the organizationId. {E.g: storagePath: organizationId/<FILEPATH>} , if they have uploaded using the single file upload function.

- In Scenario2, we will add the organizationId to the storagePaths from our end itself.

- IMPORTANT:
  - By default all the files are stored at the storagePath provided [i,e. following a    folder hierarchy based on the filePath]. If user wants to store all the files at the root location then in that case, the user must send the optional parameter "storeFilesAtRootLocation" : true in the request body.

  - By sending the optional param "storeFilesAtRootLocation", all the files will be stored at the root location with their respective fileNames.The files will be stored with their fileNames regardless of their filePaths. In case, if two/ more files share the same fileName then the file will get overridden.

## Sample JSON Request Bodies And Responses

**Scenario 1 – where optional param organizationId is not sent in req.body but rather organizationId is added in the storagePaths itself by the user**

```json
{
    "storagePaths": [
        "24680/ZMS/SCO/a9034bb6-404b-497c-a95e-e533e379c825/DELIVERY_PACKING_INVOICE/lcl-1666784922849-ab8bd818-0cb0-4a9d-a7f7-46d4848d4db4.webp",
        "24680/ZMS/SCO/a9034bb6-404b-497c-a95e-e533e379c825/SHIPPING_BILL/55aab945-9d45-4ceb-99c1-9e21046b78a3-1666784928284-21474c8e-52a2-45ce-bc96-33f840c0834b.pdf"
    ],
    "outputFileName": "folder.zip"
}
Here, organizationId === 24680 and rest is the relative file path
```

**Scenario 2 - where optional param organizationId is sent in req.body by the user**

```json
{
  "storagePaths": [
    "ZMS/SCO/a9034bb6-404b-497c-a95e-e533e379c825/DELIVERY_PACKING_INVOICE/lcl-1666784922849-ab8bd818-0cb0-4a9d-a7f7-46d4848d4db4.webp",
    "ZMS/SCO/a9034bb6-404b-497c-a95e-e533e379c825/SHIPPING_BILL/55aab945-9d45-4ceb-99c1-9e21046b78a3-1666784928284-21474c8e-52a2-45ce-bc96-33f840c0834b.pdf"
  ],
  "outputFileName": "folder.zip",
  "organizationId": 24680
}
```

**Scenario 3 – using fileIdentifiers:**

```json
{
  "fileIdentifiers": ["file_id1", "file_id2", "file_id3"],
  "outputFileName": "folder.zip"
}
```


**The sample JSON response looks like this:**
A zip of all the requested files If enableDownloadLink is true :

```json
{
    "filename": "folder.zip",
    "secureDownloadLink": "https://docserdevblobs.blob.core.windows.net/dtlp-file-storage-development/datachain/downloadedZipFiles/31ab0199dbdc-4044-b1c4-2cf9ad94519d.zip?st=2022-11-03T05%3A06%3A02Z&se=2022-11-11T05%3A06%3A02Z&sp=r&spr=https&sv=2018-03-28&sr=b&sig=dnCiYagLINk4mGcKSowz42brw9xjWejGZ5SxC%2BDXis4%3D"
}
```


## Sample curl Request and Responses using enablepresigneddownloadlink

**curl Request Body**

```bash
curl --location 'http://qa-document-service-api.private-cargoes.com/file-storage/bulkDownload' \
--header 'X-DPW-ApplicationId: datachain' \
--header 'x-api-key: iklk20yoaimob2mci6uammsgi4542o' \
--header 'Content-Type: application/json' \
--data '{
    "storagePaths": [
        "12345/testname/new10_10.pdf",
        "12345/testname/CREDIT_NOTE_CANADA-50593c0266d2ae28c6j8ok.docx"
    ],
    "outputFileName": "folder12.zip",
    "enablePresignedDownloadUrl": "true",
    "options": {
        "preSignedUrlMetadata": {
            "readCount": 1000,
            "readExpiryDuration": 50
        }
    }
}'

```

**Sample curl Response**

```json
{
  "filename": "folder12.zip",
  "fileIdentifier": "a432ad14-bc47-4d23-81b7-f6bef8c42a0e",
  "presignedDownloadUrl": "https://qa-document-service-api.cargoes.com/file-storage/file/presignedurl? signature=8814eb2b8039e82ee8b6ad0ca4ff64661d89c08cc488faef538d517 a4db11ed77dde3895e51fe878122e5f3f55d331c3| 76fb177629df893f795a35655206eb12"
}
```

---

### Error Codes

- `40030`: Argument Error – Invalid input parameters
- `50090`: API Error – Internal Server Error

# Delete File API

## Endpoint

```http
DELETE /file-storage/file
```

deletes a file from Azure storage either by its `path` or `fileIdentifier`

## Meta Data

**Purpose**
The `Delete File API` allows users to remove files from Azure Blob Storage using either the file path (with `organizationId`) or a unique `fileIdentifier`. Deleted files are retained for a 30-day recovery period.

**Key Features**

- Supports deletion using either:
  - `organizationId` + `path`
  - Or `fileIdentifier` directly.
- Performs soft deletion — files are retained for 30 days.
- Returns a success message with the file path or identifier.
- Handles missing file errors gracefully.

**Typical Use Cases**

- Remove outdated or redundant documents from storage.
- Allow users to undo deletions within a 30-day retention window.
- Delete files uploaded in error via `fileIdentifier`.
- Automate cleanup of files based on retention policies.

---

## Query Parameters

**`organizationId`**
- **Type:** `int`
- **Required:** Yes (only if `path` is provided)
- **Description:** Organization ID with whom the file is associated


**`path`**
- **Type:** `String`
- **Required:** Yes _(when deleting via path)_
- **Description:** Path of the file in Azure storage, as returned by `uploadFile`

**`fileIdentifier`**
- **Type:** `UUID`
- **Required:** No
- **Description:** Unique file identifier — can be used instead of `path` for deletion

## Notes
- User can also perform DELETE using only the `fileIdentifier` (in that case `organizationId` and `path` are not required).
- The deleted files will be retained for a period of 30 days, from the point of deletion time.

---

## Sample Successful Response

```json
{
  "message": "Successfully deleted the file with filePath=${filePath}"
}
```
---

## Error Codes

- `40030`: Argument Error – Invalid arguments (`organizationId`, `path`, `applicationId` header)
- `50090`: API Error – Internal Server Error
- `40410` : Not Found Erro - File not found at the specified path or with the given fileIdentifier.
---

# Move Files API

## Endpoint

```http
POST /file-storage/moveFiles
```

Move files or folders from a source path to a destination path.

## Meta Data

**Purpose**
The `Move Files API` allows relocating one or more files or folders within Azure Blob Storage by specifying their source and destination paths. It supports both file-level and folder-level operations, ensuring structure consistency during the move.

**Key Features**

- Accepts an array of source-destination file path pairs.
- Supports moving:
  - Single files (e.g., `.pdf`, `.docx`)
  - Entire folders (all files within will be moved).
- Ensures source and destination types match (file-to-file or folder-to-folder).
- Allows moving up to 20 entries in a single request.
- Returns a success message and optionally lists invalid paths.

**Typical Use Cases**

- Reorganize uploaded documents into updated folder structures.
- Move departmental reports or files between organization-specific folders.
- Archive old project files to a new location.
- Automate migration of files within the storage account.

## Request Body Parameters

**`filePaths`**

- **Type:** `Array`
- **Required:** Yes
- **Description:** Array of JSON objects containing the `source` and `destination` paths.

## Notes for Move File API

This API moves files from the source location to the destination location, the input should be an array of source and destination file paths. If the source path is a folder, all files present in that folder will be moved to the destination path. The destination file path type and source file path type should be the same i.e., if the source path is a folder then the destination path must be a folder and if the source path is a pdf file then the destination path must be a pdf file. Maximum number of file paths allowed for moving to new destinations is 20.

## Sample JSON Request Body And Responses

**Request Body**
```json
{
  "filePaths": [
    {
      "source": "77323/testFile/test1.docx",
      "destination": "7307/4.docx"
    },
    {
      "source": "9088/final",
      "destination": "9293"
    }
  ]
}
```

**Response Body**

```json
{
  "message": "All files have been successfully moved to new destinations."
}
```

 If any of the file paths are invalid then only valid paths will be moved to their destination and invalid paths will be returned in the response.

**Sample request body with invalid paths:**
```json
{
    "filePaths": [
        {
            "source": "77323/testFile/test1.docx",
            "destination": "7307/4.docx"
        },
        {
            "source": "9088/testFiles",
            "destination": "9293"
        },
        {
            "source": "8466",
            "destination": "12349"
        }
    ]
}

```

**The sample response looks like this With invalid path**

```json
{
 "message": "All files except invalid file paths are successfully moved to new destinations.",
 "invalidPaths": [
        "9088/testFiles",
        "8466"
  ]
 }
 ```

## Error Codes

- `40030`: Argument Error – Invalid input parameters
- `50090`: API Error – Internal Server Error

---

# Copy Files API

## Endpoint

```http
POST /file-storage/copyFiles
```

Copy files or folders from a source path to a destination path.

## Meta Data

**Purpose**
The `Copy Files API` allows users to copy individual files or entire folders from one path to another within Azure Blob Storage. It supports secure download link generation for copied files and enforces type consistency between source and destination paths.

**Key Features**

- Accepts an array of objects each containing:
  - `source` path
  - `destination` path
- Supports both:
  - File-to-file copying
  - Folder-to-folder copying (copies all files within).
- Optional generation of secure download links for copied **files only** via `enableDownloadLink`.
- Configurable expiry for secure links using `linkExpiryDuration` (default: 7 days, max: 3650 days).
- Supports up to 20 file/folder copy operations in one request.
- Returns a list of successfully copied items and reports any invalid paths.

**Typical Use Cases**

- Duplicate a file across different department folders.
- Maintain backup copies of reports in a separate storage area.
- Enable secure download sharing immediately after copying.
- Organize files into a new structure while retaining originals.
- Clone folder contents for versioned archive purposes.

## Request Body Parameters

**`filePaths`**

- **Type:** `Array`
- **Required:** Yes
- **Description:** Array of JSON objects should containing the `source` and `destination` paths.

**`enableDownloadLink`**
- **Type:** `Boolean`
- **Required:** No
- **Description:**  If a secured download link is required for all the files, this flag can be set to true.

**`linkExpiryDuration`**

- **Type:** `int`
- **Required:** No
- **Description:** User is allowed to set the expiry duration for the downloadLink, the default value is 7 days. Max expiry duration is 3650 days.

## Notes
 This API copies files from the source location to the destination location, the input should be an array of source and destination file paths. If the source path is a folder, all files present in that folder will be copied to the destination path. The destination file path type and source file path type should be the same i.e. if the source path is a folder then the destination path must be a folder and if the source path is a pdf file then the destination path must be a pdf file. The maximum number of file paths allowed for copying to new destinations is 20.

## Sample Request & Responses Body

**Sample Request Body**

```json
{
  "filePaths": [
    {
      "source": "77323/testFile/test1.docx",
      "destination": "7307/4.docx"
    },
    {
      "source": "9088/final",
      "destination": "9293"
    }
  ]
}
```

**Sample Response**

```json
[
  {
    "message": "All files have been successfully copied to new destinations."
  }
]
```

 If any of the file paths are invalid then only valid paths will be copied to their destination and invalid paths will be returned in the response.

**Sample request body with invalid paths:**
 Invalid paths are the file paths which doesn't exist or folders that are empty.
```json
 {
    "filePaths": [
        {
            "source": "77323/testFile/test1.docx",
            "destination": "7307/4.docx"
        },
        {
            "source": "9088/testFiles",
            "destination": "9293"
        },
        {
            "source": "8466",
            "destination": "12349"
        }
    ]
 }
```
**The sample response looks like this with invalid Paths**
```json
[
  {
    "message": "All files except invalid file paths are successfully copied to new 
destinations.",
    "invalidPaths": [
         "9088/testFiles",
         "8466"
    ]
  }
]
```

**Sample Request with `enableDownloadLink`**
 Secure download link will be given only for individual files. Secure download link is not supported for folders in this API

```json
{
  "filePaths": [
    {
      "source": "7307/4.zip",
      "destination": "4366/sr.zip"
    },
    {
      "source": "85731/test/testFile/test.pdf",
      "destination": "45747/test.pdf"
    }
  ],
  "enableDownloadLink": "true",
  "linkExpiryDuration": 8
}
```

**Sample Response enableDownoadLink is true**

```json
 [
    {
        "message": "All files have been successfully copied to new destinations."
    },
    [
       {
         "filePath": "4366/sr.zip",
         "secureDownloadLink": "https://docserdevblobs.blob.core.windows.net/dtlp-file-storage-development/datachain/4366/sr.zip? st=2023-04-04T23%3A31%3A02Z&se=2023-04-12T23%3A31%3A02Z&sp=r &spr=https&sv=2018-03-28&sr=b&sig=MNPZ0mVPdQoUhdmNBZ3i1qoqkyLv6vf3kzZmKpojNSs%3D"
       },
       {
         "filePath": "45747/test.pdf",
         "secureDownloadLink": "https://docserdevblobs.blob.core.windows.net/ dtlp-file-storage-development/datachain/45747/test.pdf? st=2023-04-04T23%3A31%3A02Z&se=2023-04-12T23%3A31%3A02Z&sp=r &spr=https&sv=2018-03-28&sr=b&sig=yA9MqtWOOfWo8ifwoSnfdVdI0grtYi8X8ZmNVsDJhk8%3D"
       }
    ]
 ]
```

## Error Codes

- `40030`: Argument Error – Invalid input parameters
- `50090`: API Error – Internal Server Error

# Convert File API

## Endpoint

```http
POST /file-utilities/convert
```

This API converts files of one format to other formats.

## Meta Data

**Purpose**
The `Convert File API` transforms files from one format to another — such as converting `.docx` to `.pdf`, `.xlsx` to `.pdf`, or `.html` to Excel. It offers optional secure or presigned download links, supports splitting Excel files, and provides control over file accessibility.

**Key Features**

- Supports input formats: `.docx`, `.xlsx`, `.xls`, `.html`, `.jpg`, `.jpeg`, `.png`.
- Output formats: `.pdf`, `.html`, `.xlsx`, `.xls` (based on compatibility).
- Max file size: 10 MB for documents,
  5 MB for images.
- Optional Excel splitting using `noOfRecordsInOneSheet`.
- Option to generate:
  - Direct download links (`enableDownloadLink`)
  - Presigned secure URLs (`enablePresignedDownloadUrl`)
- Link expiration is configurable using `linkExpiryDuration` (default 7 days).
- Advanced access control using `options` like `readCount` and `readExpiryDuration`.

**Typical Use Cases**

- Convert Word or Excel files to PDF for secure sharing or compliance.
- Transform HTML templates into Excel spreadsheets.
- Generate downloadable invoices or reports in PDF format.
- Split large Excel sheets into multiple smaller ones before conversion.
- Provide temporary, secure access to converted files using presigned URLs.

## Query Parameters

**`file`**

- **Type:** File
- **Required:** Yes
- **Description:** File to be converted to destinationFileType. Max file size allowed is 10 MB.  Currently, we accept .xlsx [for PDF conversion  ], .docx [for PDF, HTML, Excel conversion  ],  .html [for Excel conversion ] files as input.

**`destinationFileType`**

- **Type:** String
- **Required:** Yes
- **Description:** We support destinationType as 'pdf' or 'xlsx'.

**`enableDownloadLink`**

- **Type:** boolean
- **Required:** No
- **Description:** Creates a shareable download link for converted file, if set true. By default, response would be stream.

**`linkExpiryDuration`**

- **Type:** Integer
- **Required:** No
- **Description:** Sets expiry duration for above link.

**`noOfRecordsInOneSheet`**

- **Type:** Integer
- **Required:** No
- **Description:**  If the value is available, the input excel file is split to multiple sheets, containing fixed number of records as per value provided. if not provided, it will simply convert given excel file to destinationType format.

**`enablePresignedDownloadUrl`**

- **Type:** Boolean
- **Required:** No
- **Description:** Creates a presignedDownload link for this file. This link will be valid for max 60 mins.

**`options`**

- **Type:** Json
- **Required:** No
- **Description:**  It has metadat for presignurl data like readCount(no. if time file can be read from this link) and readExpiryDura tion(duration for which this link is valid). Sample curl is written below. If this is not present then presigned will be created for default values that 60 mins and 1000 readCount. Value more than 60 and 1000 are notallowed unless explicitly set to greater value in client config for ur client.

## Notes
We need security approval for extending the expiry duration in case of enablePresignedDownloadUrl. Only one response type should be true while sendong the request

## File Formats Supported

**Input: `docx`**

- **Output File Types**: `html`, `pdf`, `xlsx`, `xls`
- **Note**:  Input file should contain <html> </html> tags

---

**Input: `xlsx`, `xls`**

- **Output File Types**: `pdf`
- **Note**: null

---

**Input: `html`**

- **Output File Types**: `xlsx`, `xls`
- **Note**: null

---
**Input: `jpg`, `jpeg`, `png`**
- **Output File Types**: `pdf`
- **Note**: Max size: 5 MB

### Sample Curl Request & Responses

**Sample Curl Request**

```bash
 curl --location --request POST 'http://staging-document-service-api.privatecargoes.com/file-utilites/convert'\
 --header 'X-DPW-ApplicationId: datachain'\
 --header'x-api-key:0fec68342d502b603f7bd43b66ad2ee9' \
 --form 'files=@"/Users/rajatbhardwaj/Downloads/Tax_Detail.xlsx"'\
 --form 'destinationFileType="pdf"' \
 --form 'enableDownloadLink="false"'\
 --form 'linkExpiryDuration="8"'\
 --form 'noOfRecordsInOneSheet="100"'
```

**Sample curl Response**
 The sample response would include the respective file after conversion

A file stream is returned. If `enableDownloadLink` is true:

```json
{
  "filename": "test.pdf",
  "secureDownloadLink":  "https://docserdevblobs.blob.core.windows.net/dtlpfile-utility-development/datachain/convertedFiles/31ab0199-dbdc-4044b1c4-2cf9ad94519d-test.pdf? st=2022-11-03T05%3A06%3A02Z&se=2022-11-11T05%3A06%3A02Z&sp=r& spr=https&sv=2018-03-28&sr=b&sig=dnCiYagLINk4mGcKSowz42brw9xjWejG Z5SxC%2BDXis4%3D"
}
```

**Sample Curl with  presigneddownloadlink**

```bash
curl --location 'http: //qa-document-service-api.private-cargoes.com/fileutilites/convert' --header 'X-DPW-ApplicationId: datachain' --header 'x-api-key: iklk20y6toaimob2mci6uammsgi4542o' --form 'files=@"/Users/deepali/Downloads/logisticsnew_CONVERTED.cleaned.xlsx"' --form 'destinationFileType="pdf"' --form 'enablePresignedDownloadUrl="true"' --form 'options="{ \"preSignedUrlMetadata\": {\"readCount\": 1000, \"readExpiryDuration\": 50}}"'
```

**Sample curl Response for PresignedDownloadLink**

```json
{
  "filename": "logisticsnew_CONVERTED_CONVERTED.pdf",
  "fileIdentifier": "da2e3a3f-8f82-4bc0-95e7-ab56e760391b",
  "presignedDownloadUrl":  "https://qa-document-service-api.cargoes.com/file-storage/file/presignedurl? signature=81b6b52623a483e4422fc285f56d83cde9f87228fffae45d28b8988 3f7eed7c50e1fe074dfa35705920ebaefc6f26a81| ca16e15503123990c0248eb0070a8cb2"
}
```

## Error Codes

- `40030`: Argument Error – For invalid arguments [file, destinationType
  ]
- `50090`: API Error – Internal Server Error

---

# Barcode generation

**Document Service Barcode generation: ** https://dev.azure.com/dpwhotfsonline/DTLP/_wiki/wikis/DTLP.wiki/7276/Document-Service-Barcode-generation


# Split File API

## Endpoint

```http
POST /file-utilities/split
```

**Description:** Generic endpoint to handle different split operations based on parameters.

## Meta Data

**Purpose**
The `Split File API` provides flexible mechanisms to split a PDF file based on specific criteria, such as selecting particular pages. It supports file uploads from multiple sources and allows storing or securely sharing the resulting split files.

**Key Features**

- Accepts PDF files from:
  - Direct file upload (`file`)
  - File identifier (`fileIdentifier`)
  - File path (`filePath` with `organizationId`)
- Multiple split strategies supported via `method`, such as:
  - `get_specific_pages`: extract specific pages from a PDF.
- Optional flags:
  - `upload`: uploads the result back to document storage.
  - `enablePresignedDownloadUrl`: returns a secure temporary link.
- Returns either direct file streams, presigned URLs, or file identifiers.
- Supports files up to 400MB in size.
- Custom `options` JSON enables method-specific behavior.

**Typical Use Cases**

- Extract only the required page(s) from a contract or invoice PDF.
- Allow users to download specific sections of a large document.
- Store and share trimmed or partial versions of a document.
- Enable clients to preview only selected pages via secure link.
- Automate splitting logic based on dynamic user selection.

## Request Body Parameters

**`file`**

- **Type:** File (pdf)
- **Required:** Yes
- **Description:**  PDF file that need to be split.

**`fileIdentifier`**

- **Type:** UUID
- **Required:** No
- **Description:** fileIdentifier mapped to the uploaded file. This is used to fetch the file mapped to this fileIdentifier..

**`filePath`**

- **Type:** String
- **Required:** No
- **Description:** filepath mapped to the uploaded file , example : testFile/test.pdf .

**`organizationId`**

- **Type:** int
- **Required:** Yes (if using filePath)
- **Description:** 
  Default is false. If this flag is enabled, file be uploaded and stored at document service end, and response will have file identifier.

**`enablePresignedDownloadUrl`**

- **Type:** Boolean
- **Required:** No
- **Default:** false
- **Description:**
   Default is false. If this flag is enabled, file be uploaded and stored at document service end, and response will have file identifier as well as download URL. The download link would expire in 60 minutes by default(or the client's read expiry limit, if available). A new download URL can always be generated using generatePre signedUrl API

**`upload`**

- **Type:** Boolean
- **Required:** No
- **Default:** false
- **Description:**
   Default is false. If this flag is enabled, file be uploaded and stored at document service end, and response will have file identifier

**`method`**

- **Type:** String
- **Required:** Yes
- **Description:**  
  Specify the split method to be applied.

**`options`**

- **Type:** JSON
- **Required:** Yes
- **Description:** Additional options based on the method.

## Notes

- Max file size allowed: 400MB.
-  Exactly one source is required in case of file input among file , fileIdentifier and filePath.

## Sample Request & Responses Body


**Sample JSON Request**

- Get specific page:
    Method: get_specific_page
    Options: pageNumber (integer): Page Number which you want to retrieve.
```json
{
  
  "file": "<PDF>",
  "fileIdentifier": "<uuid>",
  "filepath": "<path>",
  "organizationId": "<org-id>",
  "method": "get_specific_page",
  "options": {
    "pageNumber": 2
  },
  "enablePresignedDownloadUrl": true,
  "upload" : true
}
```
**Sample Response 
- Responses can be in different ways based on input parameters.
  - If no specific flag is enabled. In response split file will come.

  - If enablePresignedDownloadUrl is enabled, then response will look like this.
  e.g :

  ```json
  {
     "filename": "xbouh9-TestFile1-4.pdf",
    "fileIdentifier": "3bc028de-ce5a-4823-83da-c45342c7aaed", 
    "presignedDownloadUrl": "https://qa-document-service-api.cargoes.com/ file-storage/file/presignedurl? signature=565744507653ffcd56b95823bf7f9789d615e7755b120b7dca2f2600 b047dc1b3cfeb9563805d7c3dd607e4a21b63ac9|18598788e8354f23e2dfd04078ebfbc5"
  }
  ```

**Sample Response If only upload flag is enabled**

```json
{
  "filename": "9k1gx6-TestFile1-4.pdf",
 "fileIdentifier": "9cfa4732-aa3e-477c-a00c-35c480730885"
}
```

**If neither flag is enabled**

The split file stream will be returned in the response.

## Benchmark Latency

This section provides the benchmark latency statistics for PDF processing tasks such as split, merge, and compress.

- **File Size: 1.4 MB**

  - Server Side Latency: 220 ms
  - End-to-End Latency: 3.06 s

- **File Size: 3.5 MB**

  - Server Side Latency: 570 ms
  - End-to-End Latency: 3.6 s

- **File Size: 5 MB**

  - Server Side Latency: 587 ms
  - End-to-End Latency: 4.63 s

- **File Size: 10 MB**

  - Server Side Latency: 833 ms
  - End-to-End Latency: 5.3 s

- **File Size: 20 MB**

  - Server Side Latency: 857 ms
  - End-to-End Latency: 5.7 s

- **File Size: 40 MB**

  - Server Side Latency: 1255 ms
  - End-to-End Latency: 15 s

- **File Size: 50 MB**
  - Server Side Latency: 1300 ms
  - End-to-End Latency: 15 s

## Error Codes

- `40030`: Argument Error – Invalid input parameters
- `50090`: API Error – Internal Server Error

---

# Merge File API

## Endpoint

```http
POST /file-utilities/merge
```
 This API merges files more than one into a single file. Currently, we are only supporting pdf files for merging.

## Meta Data

**Purpose**
The `Merge File API` combines multiple PDF files into a single PDF document. It supports various input types like uploaded files, file identifiers, file paths, or URLs. Users can optionally store or generate secure download links for the merged result.

**Key Features**

- Accepts up to 50 PDF files per merge operation.
- Input sources supported:
  - Direct file uploads (`file1`, `file2`, ..., using sequence numbers).
  - `fileIdentifiers` generated via upload API.
  - `filePaths` or file URLs.
- Sequence-based merging: input file names must follow `file<sequenceNumber>` convention.
- Result file can be renamed using `finalFileName`.
- Optional behaviors controlled via flags:
  - `enableDownloadLink` – secure shareable link.
  - `enablePresignedDownloadUrl` – presigned expiring download link (default: 60 mins).
  - `upload` – store the merged file and return `fileIdentifier`.
- Only one of the above flags should be `true` at a time.
- Maximum individual file size allowed: 5 MB.
- Download link expiry configurable using `linkExpiryDuration` (default: 7 days).

**Typical Use Cases**

- Combine multiple pages of a report or contract into a single document.
- Merge scanned PDFs into one for archival or sharing.
- Allow users to download combined invoices or certificates securely.
- Automate back-office merging workflows using file IDs or URLs.
- Enable frontend upload + merge + download experience via a single API call.

## Request Body Parameters

**`file1`, `file2`**

- **Type:** `File`
- **Required:** Optional
- **Description:**  File to be merged. Max file size allowed is 5 MB. Currently, we only accept .pdf file extensions for the input file.

**`fileUrls`**

- **Type:** `Array`
- **Required:** Optional
- **Description:** List of PDF file links that need to merged.

**`fileIdentifiers`**

- **Type:** `Array`
- **Required:** Optional
- **Description:** List of fileIdentifiers that are generated on uploading a file use upload api.

**`filePaths`**

- **Type:** `Array`
- **Required:** Optional
- **Description:**  List of filepaths that are generated on uploading a file using upload api.

**`filesMetadata`**

- **Type:** `Array`
- **Required:** Optional
- **Description:**  List of fileIdentifiers and fileUrls. Only fileIdentifiers and fileUrls are allowed.

**`enableDownloadLink`**

- **Type:** `Boolean`
- **Required:** Optional
- **Description:** Returns secureDownloadable link.

**`linkExpiryDuration`**

- **Type:** `Integer`
- **Required:** Optional
- **Description:** Default is 7days. Only valid if enableDownload link is set as true.

**`upload`**

- **Type:** `Boolean`
- **Required:** Optional
- **Description:** Default is false. If this flag is enabled, file be uploaded and stored at document service end, and response will have file identifier.

**`finalFileName`**

- **Type:** `String`
- **Required:** Optional
- **Description:**  This is final file name of resulting merged file. Default is 'response.pdf' (uuid in case of secure download link).

**`enablePresignedDownloadUrl`**

- **Type:** `Boolean`
- **Required:** Optional
- **Description:**  Default is false. If this flag is enabled, file be uploaded and stored at document service end, and response will have file identifier as well as download URL. The download link would expire in 60 minutes by default(or the client's read expiry limit, if available). A new download URL can always be generated using generatePresignedUrl API as given in this same documentation.

## Notes

-  Maximum 50 PDFs can be merged at once.
- FieldName of file attribute must be in the following format:
    - file<sequenceNumber>: keyword file followed by the sequence number.

    -  sequenceNumber: Must be an integer. The final merged document will be based on the ascending order of the sequenceNumber.

    - If file1, file11, and file2 are provided, then the final merged document will be in this order file1->file2->file11 .
- Max file size allowed is 5 MB.
- API support either files ,fileIdentifier or fileUrls, it does not support both at once.

-  If fileIdentifiers are provided, then minimum 2 fileIdentifiers are expected to merge files.

- Out of flags (enablePresignedDownloadUrl, enableDownloadlink, upload), only one of them should be true .

## Sample Curl Request & Responses

**Sample Curl Request (Using Files)**

```bash
curl --location --request POST 'http://staging-document-service-api.privatecargoes.com/file-utilities/merge' \
--header 'X-DPW-ApplicationId: datachain' \
--header 'x-api-key: 0fec68342d502b603f7bd43b66ad2ee9' \
--form 'file1=@"/Users/pavanipalvai/Downloads/test1.pdf"' \
--form 'file2=@"/Users/pavanipalvai/Downloads/test2.pdf"'

```

**Sample Curl request (Using FileIdentifiers)**

```bash
curl --location 'http://localhost:3300/file-utilities/merge' \
--header 'X-DPW-ApplicationId: datachain' \
--header 'x-api-key: KCaxy3xxxxxxxxxxxxxxxnNOrKugfn' \
--form 'enableDownloadLink=true' \
--form 'linkExpiryDuration=8' \
--form 'fileIdentifiers=["d1e89775-6f81-4f8f-91ea-a01f17b991d1","e259a877-21ec-4af3-a6dc-c18c600e5a35"]'

```

**Sample Curl request (Using URLs)**

```bash
curl --location 'http://localhost:3300/file-utilities/merge' \
  --header 'X-DPW-ApplicationId: datachain' \
  --header 'x-api-key: KCaxy3nqxxxxxxxxxrKugfn' \
  --form 'enableDownloadLink="true"' \
  --form 'linkExpiryDuration="8"' \
  --form 'fileURLs=["https://s29.q4cdn.com/175625835/files/doc_downloads/test.pdf","https://www.clickdimensions.com/links/TestPDFfile.pdf"]'

```

**Sample Response if enableDownloadLink is true**

```json
{
  "filename": "randomstr.pdf",
  "secureDownloadLink":  "https://docserdevblobs.blob.core.windows.net/dtlp-file-utility-development/datachain/mergedFiles/31ab0199-dbdc-4044b1c4-2cf9ad94519d.pdf?st=2022-11-03T05%3A06%3A02Z&se=2022-11-11T05%3A06%3A02Z&sp=r&spr=https&sv=2018-03-28&sr=b&sig=dnCiYagLINk4mGcKSowz42brw9xjWejGZ5SxC%2BDXis4%3D"
}
```

**Sample Response if upload flag is true**

```json
{
  "filename": "response.pdf",
  "fileIdentifier": "b1e158b8-5a38-48f5-b03d-e4c8173efccb"

}
```

**Sample Response if enablePresignedDownloadUrl flag is true**

```json
{
  "filename": "response.pdf",
  "fileIdentifier":  "b1e158b8-5a38-48f5-b03d-e4c8173efccb",
  "presignedDownloadUrl":  "https://qa-document-service-api.cargoes.com/file-storage/file/presignedurl?signature=fe70cfb9f22430632811ec45cab4cba91c2e0438de4dd9fcead75cedfd69f6f2da6609ee67124d9ea51021e99da5c915|3f3c7e320fb269f749a6cba7fd65baf0"
}
```

## Error Codes

- `40030`: Argument Error – Invalid input parameters
- `50090`: API Error – Internal Server Error

---

# Encrypt File API

## Endpoint

```http
POST /file-utilities/encrypt
```

This API encrypts the given file. Currently, we are only supporting pdf files for encryption.
## Meta Data

**Purpose**
The `Encrypt File API` allows you to secure a PDF file by applying password protection. It ensures that only users with the correct password can open and view the encrypted file, making it suitable for secure document sharing.

**Key Features**

- Accepts `.pdf` files only; maximum file size: 10 MB.
- Files are encrypted using a user-defined password (`userPassword`).
- Supports different response types:
  - Direct file stream (default).
  - Secure download link (`enableDownloadLink`).
  - Presigned download link with time and read-limit control (`enablePresignedDownloadUrl`).
- Configurable link expiration via `linkExpiryDuration` (default: 7 days).
- Presigned URL options:
  - `readCount`: how many times the file can be accessed.
  - `readExpiryDuration`: how long the link remains valid (max: 60 mins).
- Only one response flag should be enabled at a time.

**Typical Use Cases**

- Protect confidential financial or legal PDFs before sharing.
- Encrypt user-generated reports before download.
- Automate encryption workflows for uploaded documents.
- Provide clients a one-time downloadable secure PDF.
- Integrate into document management systems for compliance and data protection.

## Request Body Parameters

**`file`**

- **Type:** File
- **Required:** Yes
- **Description:**  File to be encrypted. Max file size allowed is 10 MB. Currently, we only accept .pdf file extensions for the input file.

**`userPassword`**

- **Type:** Text
- **Required:** Yes
- **Description:**  File will be encrypted with this password.

**`enableDownloadLink`**

- **Type:** Boolean
- **Required:** No
- **Description:**  Creates a shareable download link for the converted file, if set to true.

**`linkExpiryDuration`**

- **Type:** Integer
- **Required:** No
- **Description:** Sets expiry duration (in minutes) for the secure link. Default is 60 mins.

**`enablePresignedDownloadUrl`**

- **Type:** Boolean
- **Required:** No
- **Description:**  Creates a presignedDownload link for this file. This link will be valid for max 60 mins.

**`options`**

- **Type:** JSON
- **Required:** No
- **Description:**  It has metadata for presignurl data like readCount(no. if time file can be read from this link) and readExpiryDuration(duration for which this link is valid). Sample curl is written below. If this is not present then presigned will be created for default values that 60 mins and 1000 readCount. Value more than 60 and 1000 are not allowed unless explicitly set to greater value in client config for ur client.

## Notes
 -  We need security approval for extending the expiry duration in case of enablePresignedDownloadUrl. Only one response type should be true while sendong the request

## Sample Curl Requests & Responses

**curl Request With File and Password**

```bash
curl --location 'http: //staging-document-service-api.private-cargoes.com/file-utilities/encrypt' \
--header 'x-api-key: your-api-key' \
--form 'userPassword="password1"' \
--form 'file=@"/path/to/your/file.pdf"'
```

**curl Response if Succesful With File and Password**

The sample response would be a file encrypted with the user password.

**If enableDownloadLink is set to true, the sample response would be:**

```json
{
  "filename": "randomstr.pdf",
  "secureDownloadLink": "https://docserdevblobs.blob.core.windows.net/dtlpfile-utility-development/datachain/encryptedFiles/31ab0199-dbdc-4044b1c4-2cf9ad94519d.pdf?st=2022-11-03T05%3A06%3A02Z&se=2022-11-11T05%3A06%3A02Z&sp=r&spr=https&sv=2018-03-28&sr=b&sig=dnCiYagLINk4mGcKSowz42brw9xjWejGZ5SxC%2BDXis4%3D"
}
```

**Sample curl with presigneddownload link as response type**

```bash
curl --location 'http://qa-document-service-api.private-cargoes.com/file-utilities/encrypt' \
  --header 'x-api-key: iklk20y6toaimobmci6uammsgi4542o' \
  --form 'userPassword=password1' \
  --form 'file=@/Users/deepali/Downloads/test.pdf' \
  --form 'enablePresignedDownloadUrl=true' \
  --form 'options={"preSignedUrlMetadata":{"readCount":1000,"readExpiryDuration":50}}'
```

**Sample response for curl request presigneddownload link**

```json
{"filename":"test.pdf","fileIdentifier":"63807312-6982-48b5-8e2d-8319a789fffd","presignedDownloadUrl":"https://qa-document-service-api.cargoes.com/filestorage/file/presignedurl?signature=17ced74a86e90c132aab22ad8de9f74431bda06f29ed27bd3d7fa6a2670482fbc653e5d33a3d6806daeeafe62feedb14|d8acf4a59484acc1f33bfeec1f12081b"}

```

## Error Codes

- `40030`: Argument Error – Invalid input parameters
- `50090`: API Error – Internal Server Error

---

# Get All Versions for a File API

## Endpoint

```http
GET /file-storage/file/versions
```

Retrieve all available versions of a file stored in the system.

## Meta Data

**Purpose**
The `Get All Versions for a File API` retrieves the complete version history of a file stored in Azure Blob Storage. Each version entry provides a timestamp indicating when the version was created, allowing clients to track changes and restore specific versions.

**Key Features**

- Requires `organizationId` and the file `path` as input.
- Returns a chronological list of all versions for the specified file.
- Each version includes a timestamp in ISO format.
- Enables version-aware operations like viewing or downloading older versions.
- Helps track file update history for compliance or auditing.

**Typical Use Cases**

- Display file version history in a document management dashboard.
- Allow users to download previous versions of an uploaded document.
- Perform audit checks based on version change timestamps.
- Restore or verify changes made to important legal, technical, or project files.

## Query Parameters

**`organizationId`**

- **Type:** `int`
- **Required:** Yes
- **Description:** Organization ID with which the file is associated.

**`path`**

- **Type:** `String`
- **Required:** Yes
- **Description:** Path of the file in storage.

## Sample JSON Response

```json
[
  {
    "version 1": "2023-06-22T11:47:49.4700754Z"
  },
  {
    "version 2": "2023-06-22T11:48:49.4700754Z"
  }
]
```

## Error Codes

- `40030`: Argument Error – Invalid input parameters
- `50090`: API Error – Internal Server Error

---

# Generate Pre-signed File Upload URL API

## Endpoint

```http
POST /file-storage/presignedurl
```

**Description:**  Pre-signed url refers to the url with read and write access(being able to write within an expiry duration or fixed number of attempts) generated by Document Service. Users can use the api (discussed below), to write a file to a location mapped to pre-signed url in azure storage account.

**Headers:**
x-api-key: <API_KEY> x-document-service-integration-token: <ACCESS_TOKEN> // Only required in case of public endpoint.

Client can provide us with below parameters in order to generate a pre-signed url shows in query parameters :

## Meta Data

**Purpose**
The `Generate Pre-signed File Upload URL API` creates a time-bound, access-controlled URL for securely uploading files directly to Azure Blob Storage. This link grants temporary write access and can be customized based on usage limits and expiration settings.

**Key Features**

- Generates a secure pre-signed URL that supports file uploads via HTTP PUT/POST.
- Configurable usage controls:
  - `writeCount`: number of allowed uploads (default: 1).
  - `writeExpiryDurationInMinutes`: validity window (default: 30 mins, max: 60 mins).
- Requires `clientIdentifier` to associate the URL with client-specific tracking.
- Optional support for routing uploads through Azure Service Bus subscriptions using `subscriptionName`.
- Useful for client-side uploads without exposing storage credentials.

**Typical Use Cases**

- Allow end users or external clients to upload documents via a limited-access URL.
- Use pre-signed URLs for secure, direct uploads from frontend/mobile apps.
- Enable controlled one-time uploads without full API integration.
- Track upload operations using `clientIdentifier`.
- Integrate with Azure Service Bus for asynchronous processing post-upload.

## Request Headers

- `x-api-key`: <API_KEY>
- `x-document-service-integration-token`: <ACCESS*TOKEN> *(Only required for public endpoints)\_

## Request Body Parameters

**`writeCount`**

- **Type:** `integer`
- **Required:** No
- **Description:** The maximum number of times a user can use this url to upload files. Default count would be 1. 

**`writeExpiryDurationInMinutes`**

- **Type:** `integer`
- **Required:** No
- **Description:** The duration, in minutes, after which the presigned URL is no longer valid. The default value is set to 30 minutes and max value is 60 minutes.

**`clientIdentifier`**

- **Type:** `string`
- **Required:** Yes
- **Description:**  Alphanumeric string with allowed underscores and hyphens. Maximum length of this string could be 255. This will be used by clients to map the generated presigned url in their system.

**`subscriptionName`**

- **Type:** `string`
- **Required:** No
- **Description:**  If a client wants to ensure that the data for uploading a file using a generated presigned URL is passed to a particular subscription, they can include the subscriptionName attribute while generating the pre-signed URL. The specified subscription must be created in the Azure Service Bus topic by coordinating with the foundational services team. Subscription would look like: <client_name>-<subscription_name> .

## Sample curl Request & Responses

**Sample curl Request**

```bash
curl --location 'https://qa-document-service-api.cargoes.com/file-storage/presignedurl' --header 'x-api-key: <<API_KEY>>' --header 'Content-Type: application/json' --data '{"clientIdentifier":"test_us","writeCount":10,"writeExpiryDurationInMinutes":50}'

```

**Sample Response**

```json
{
  "preSignedUrl": "https://qa-document-service-api.cargoes.com/file-storage/file/presignedurl?signature=<< SIGNATURE >>"
}
```

## Notes

-  If subscriptionName is not provided, then data would be forwarded to subscription with name <client_name>. Example: If client is 'tms' then subscription name is 'tms'
- Subscription must be created in Azure Service Bus topic via Foundational Services Team.

## Error Codes

- `40030`: Argument Error – Invalid input parameters
- `50090`: API Error – Internal Server Error

# Upload File Using Pre-signed URL API

## Endpoint

```http
POST /file-storage/file/presignedurl
```

Upload files to Azure using a generated pre-signed URL.

## Meta Data

**Purpose**
The `Upload File Using Pre-signed URL API` enables clients to securely upload up to 5 files directly to Azure Blob Storage using a pre-signed URL. This approach allows file uploads without exposing backend credentials or managing upload sessions directly.

**Key Features**

- Allows uploading **up to 5 files** with a **combined size ≤ 10 MB**.
- Each file must be referenced using a unique UUID key (`fileKey1`, `fileKey2`, etc.).
- Clients may optionally provide `filesMetadata` for selected files.
- Pre-signed URL used in the request is generated using the `Generate Pre-signed Upload URL API`.
- Upon successful upload, the client receives:
  - A success message
  - Optionally, an **Azure Service Bus (ASB)** topic event with metadata and download URL.
- ASB Payload includes:
  - `clientIdentifier`
  - `fileName`, `fileSize`, `fileType`
  - `fileIdentifier`, `presignedUploadUrl`, and `presignedDownloadUrl`
- Each uploaded file triggers a separate ASB event notification.

**Typical Use Cases**

- Enable secure, credential-less file uploads from frontend or mobile applications.
- Allow end-users to upload KYC documents or forms directly via email links.
- Integrate into workflows where uploads are tracked asynchronously via ASB.
- Collect form submissions or attachments into a secure cloud bucket with automatic notifications.
- Streamline client-side uploads with minimal server-side interaction.

## Request Parameters

**`signature`**

- **Type:** `string`
- **Required:** Yes
- **Description:**  The signature, provided during the generation of the presigned URL, must be sent along with the URL for uploading a file.

**`fileKey1` to `fileKey5`**

- **Type:** `File`
- **Required:** fileKey1 must be in UUID format. File to be uploaded to Azure storage account. At least one file must be provided.

**`filesMetadata`**

- **Type:** `Text (JSON String)`
- **Required:** No
- **Description:**  filesMetadata JSON in the form of string. It should contain fileKeys as keys and the value of that fileKeys must be JSON.

## Notes

- **Description:**
    -  The client can upload upto 5 files whose total size <= 10MB using the pre-signed URL simply by making a post request for it with the required files. Pre-signed URL can be obtained from API above.

  - Following the completion of the upload process, clients have the option to subscribe to an Azure subscription topic to receive events containing success messages. These events will include the client identifier, which was provided by the client during the generation of the pre-signed URL.
  - Please check out the link to know the allowed file types : Allowed file link : https://login.microsoftonline.com/2bd16c9b-7e21-4274-9c06-7919f7647bbb/oauth2/authorize?client_id=499b84ac-1321-427f-aa17-267ca6975798&site_id=501454&response_mode=form_post&response_type=code+id_token&redirect_uri=https%3a%2f%2fspsprodcus1.vssps.visualstudio.com%2f_signedin&nonce=fbf60908-b561-4ad8-83bd-e619b5e53956&state=realm%3ddpwhotfsonline.visualstudio.com%26reply_to%3dhttps%253A%252F%252Fdpwhotfsonline.visualstudio.com%252FDTLP%252F_wiki%252Fwikis%252FDTLP.wiki%252F6415%252FFile-Validation-Protocol-for-Document-Service-APIs%26ht%3d2%26hid%3ddf1db899-bd64-4260-8a16-170c40ac830f%26nonce%3dfbf60908-b561-4ad8-83bd-e619b5e53956%26protocol%3dwsfederation&resource=https%3a%2f%2fmanagement.core.windows.net%2f&cid=fbf60908-b561-4ad8-83bd-e619b5e53956&wsucxt=1&instance_aware=true&sso_nonce=AwABEgEAAAADAOz_BQD0__W7scE-cWqVVOgUHx0Tmbx66G4R9q9TJWOAwQaTBqNyUHtZLtBIWZ9qclicZ0Bc-6EY1KPsrl6xY8UPLPKT01ggAA&client-request-id=fbf60908-b561-4ad8-83bd-e619b5e53956&mscrid=fbf60908-b561-4ad8-83bd-e619b5e53956 
  - Additionally, the client can provide unique keys in the format fileKey1, fileKey2, and so on, proportional to the number of files provided.

-  Maximum up to 5 files are allowed with total file size up to 10 MB.
- fileKey must be a UUID.
- Not compulsory to add metadata for all the files, we can add metadata for partial files too.

## Sample CURL Request And Responses

**Sample CURL Request**

```bash
curl --location 'http://qa-document-service-api.private-cargoes.com/file-storage/file/presignedurl?<<SIGNATURE>>' \
--header 'x-api-key: <<API-KEY>>' \
--form '1ab85307-3456-4608-81c2-f8fe2a3ed3c2=@"postman-cloud:///1eec9a32-1732-42f0-a08b-2e177057aaf5"' \
--form '2ab85307-3456-4608-81c2-f8fe2a3ed3c2=@"/Users/uzairsayeed/Downloads/Anshita Goel - Resume.cleaned.pdf"' \
--form '3ab85307-3456-4608-81c2-f8fe2a3ed3c2=@"/Users/uzairsayeed/Downloads/ARInvoiceMain_Jeddah 1.docx-4e4d3915f59fb282.docx"' \
--form '4ab85307-3456-4608-81c2-f8fe2a3ed3c2=@"/Users/uzairsayeed/Downloads/TOU2_MAIL 1.pdf"' \
--form '5ab85307-3456-4608-81c2-f8fe2a3ed3c2=@"/Users/uzairsayeed/Downloads/Before-US-vietnameseCharsTemplate-af4976c330b582db-uejdtq.pdf"'

```

**Sample Response**

```json
{
  "message": "file/files have been uploaded successfully."
}
```

## Sample JSON ASB Topic Payload (If Subscribed)

```json
{
  "client": "<< CLIENT NAME >>",
  "fileName": "<< FILE_NAME >>",
  "writeExpiryTimeStamp": "<< TIMESTAMP >>",
  "remainingWriteOperations": "<< INT VALUE >>",
  "clientIdentifier": "<< CLIENT IDENTIFIER PROVIDED BY CLIENT >>",
  "fileIdentifier": "<< FILE IDENTIFIER CREATED BY DOCUMENT SERVICE >>",
  "presignedUploadUrl": "<< UPLOAD URL >>",
  "presignedDownloadUrl": "<< DOWNLOAD URL >>",
  "fileSize": "<< FILE SIZE IN BYTES >>",
  "fileType": "<< FILE TYPE >>",
  "fileKey": "<< IF ANY, PROVIDED BY THE CLIENT >>"
}
```

## Notes

- It is important to remember that the client will receive an ASB topic payload for each file uploaded.
- For each file uploaded, the client will receive a unique <<downloadURL>> as part of the ASB Topic payload, which can be used for downloading the specific file. Please note that default readCount and readExpiryDuration are 1000 and 60 minutes respectively.

## Error Codes

- `40030`: Argument Error – Invalid input parameters
- `50090`: API Error – Internal Server Error

---

# Download File Using Pre-signed URL

## Endpoint

```http
GET /file-storage/file/presignedurl
```

Clients can download the file using a pre-signed URL. The most recently uploaded file will be made available for download.

## Meta Data

**Purpose**
The `Download File Using Pre-signed URL API` allows clients to securely download a file that was previously uploaded, using a time-bound, signed URL. This approach ensures secure access without requiring direct access to storage credentials.

**Key Features**

- Accepts a pre-signed `signature` as a query parameter to authenticate the download.
- Returns the latest version of the requested file as a binary file stream.
- Supports file preview in browser by appending `preview=true` in the query.
- Allows customizing the downloaded filename using the `fileName` query parameter.
- Ensures MIME type validation when using a custom filename.
- URL validity and access can be tightly controlled via expiry settings when the pre-signed URL was generated.

**Typical Use Cases**

- Securely downloading user-uploaded documents such as invoices, reports, or certificates.
- Sharing temporary access links to files with third-party users or partners.
- Displaying file previews directly in a browser tab (e.g., PDF viewer).
- Allowing downloadable content in mobile or desktop applications using secure links.
- Generating download links for audit logs or archived documents with traceability.

---

## Query Parameters

**`signature`**

- **Type:** string
- **Required:** Yes
- **Description:** The signature, which was provided during the generation of the pre-signed URL, needs to be sent along with the URL for downloading a file.

---

## Sample curl Request & Responses

**Sample curl Request**

```bash
curl --location 'https://qa-document-service-api.cargoes.com/file-storage/file/presignedurl?signature=3b08052c8a5193a69cce9752778a1cb01643c9886eea88246ced7d064250243950e4bb66e9cc429a5e002cf6e36e042c%7C355f4d85bfbfa76aacc5556ef328fae2'

```

**Sample Succesful Response**

The sample response will be a file stream.

---

## Preview of Document

Downloading file using a pre-signed URL also supports the preview of a file in a new tab in browser. For doing that, client can send additional query parameter `preview` flag as true in query params.

**Sample URL with preview query param:**

```
https: //qa-document-service-api.cargoes.com/file-storage/file/presignedurl?signature=4860dba00c7f8b569b7fd8bdf876df12ce6c7519c42285aac75c01c34ef001a9aba4eed28b8b042b6afd63a53e6fefcd%7C42abcc171bc17308dd37284ecb498801&preview=true
```

---

## Supporting Custom File Name for Downloaded File

To support downloading a file with a custom name using a pre-signed URL, the client can include an additional query parameter, `fileName`, in the URL. The value of this parameter will be used as the final file name for the download.

**Details:**

- If `fileName` is empty or null, the file will be downloaded with the default name specified at the time of upload.
- If `fileName` is provided and non-null, it must contain only valid characters, which include [alphanumeric characters, '.', '-', '_', '/'
  ]
- File type validation will be performed if `fileName` is provided. The MIME type of the file must match the MIME type inferred from the file extension.

For more information, refer to the detailed guidelines on valid file names and MIME type matching.

**Sample URL with file name query param:**

```
https: //staging-document-service-api.cargoes.com/file-storage/file/presignedurl?signature=4860dba00c7f8b569b7fd8bdf876df12ce6c7519c42285aac75c01c34ef001a9aba4eed28b8b042b6afd63a53e6fefcd%7C42abcc171bc17308dd37284ecb498801&fileName=POD_1.pdf
```

---

## Error Codes

- `40030`: Argument Error – Invalid input parameters
- `50090`: Internal Server Error – Unexpected API failure

---

# Generate Pre-signed Download URL for Given File Identifiers

## Endpoint

```http
POST /file-storage/presignedurl
```

To generate a pre-signed URL for the given fileIdentifiers, the API endpoint accepts a comma-separated list of fileIdentifiers as a parameter and returns the corresponding pre-signed URLs.

## Meta Data

**Purpose**
The `Generate Pre-signed Download URL API` enables clients to securely download files stored in the system using their unique `fileIdentifiers`. This API returns a time-bound, signature-authenticated URL for each requested file, allowing temporary and restricted access without exposing storage credentials.

**Key Features**

- Accepts an array of `fileIdentifiers` to generate download links.
- Supports optional configuration of `readCount` and `readExpiryDurationInMinutes` for each file.
- Returns pre-signed URLs that are secure and expire after the specified duration or access count.
- Supports appending query metadata (`metaData`) to the final URL for client-specific needs.
- Provides two request formats:
  1. Simple list of `fileIdentifiers`
  2. Extended JSON array of objects including `readCount`, `readExpiryDuration`, and `metaData`.

**Typical Use Cases**

- Secure file sharing in external applications without exposing storage credentials.
- Temporary access links for end-users to download confidential documents.
- Generating downloadable links for document dashboards or file history versions.
- Building automated workflows where temporary secure access to files is required.
- Supporting audit-compliant traceable access to stored documents.

---

## Headers

- `x-api-key`: <API_KEY>
- `x-document-service-integration-token`: <ACCESS_TOKEN> // Only required in case of public endpoint.

---

## Input 1: Array of File Identifiers

Clients can provide the below parameters to generate a pre-signed URL for download:

**Fields:**

- `readCount` (integer, Optional): The maximum number of times a user can download a file using the pre-signed URL. The default count is 1.
- `readExpiryDurationInMinutes` (integer, Optional): The duration, in minutes, after which file upload using the pre-signed URL is no longer possible. Default: 30, Max: 60.
- `fileIdentifiers` (Array, Required): Comma separated list of fileIdentifiers. Max allowed fileIdentifiers are 10.

---

## Sample cURL Request and Responses For input 1

**Sample curl Request**

```bash
curl --location 'https://qa-document-service-api.cargoes.com/file-storage/presignedurl' \
--header 'x-api-key: <<API_KEY>>' \
--header 'Content-Type: application/json' \
--data '{
    "fileIdentifiers": [
        "35639f8b-bc7d-430d-9c39-547f9ebb3d88",
        "4ba412e7-4581-4e91-9074-e8bc859d6a6d",
        "834b0319-4931-45db-88b1-af237d94bd5c",
        "d93e3adf-fa14-4f99-bf3e-0c56c622bc99",
        "a512a42b-f57d-48f4-9070-b1f64a7cff85"
    ],
    "readCount": 10,
    "readExpiryDurationInMinutes": 60
}'

```

---

**The sample response looks like this:**

```json
[
    {
        "fileIdentifier": "35639f8b-bc7d-430d-9c39-547f9ebb3d88",
        "preSignedUrl": "https://qa-document-service-api.cargoes.com/filestorage/file/presignedurl?signature=<< SIGNATURE >>"
    },
    {
        "fileIdentifier": "4ba412e7-4581-4e91-9074-e8bc859d6a6d",
        "preSignedUrl": "https://qa-document-service-api.cargoes.com/filestorage/file/presignedurl?signature=<< SIGNATURE >>"
    },
    {
        "fileIdentifier": "834b0319-4931-45db-88b1-af237d94bd5c",
        "preSignedUrl": "https://qa-document-service-api.cargoes.com/filestorage/file/presignedurl?signature=<< SIGNATURE >>"
    },
    {
        "fileIdentifier": "d93e3adf-fa14-4f99-bf3e-0c56c622bc99",
        "preSignedUrl": "https://qa-document-service-api.cargoes.com/filestorage/file/presignedurl?signature=<< SIGNATURE >>"
    },
    {
        "fileIdentifier": "a512a42b-f57d-48f4-9070-b1f64a7cff85",
        "preSignedUrl": "https://qa-document-service-api.cargoes.com/filestorage/file/presignedurl?signature=<< SIGNATURE >>"
    }
]

```

---

## Input 2: Array of Objects Containing File Information

**Attributes for the `fileInfoArray` object:**

- `readCount` (integer, Optional): The maximum number of times a user can download a file using the pre-signed URL. Default: 1.
- `readExpiryDurationInMinutes` (integer, Optional): The duration, in minutes, after which file upload using the pre-signed URL is no longer possible. Default: 30, Max: 60.
- `fileIdentifier` (UUID, Required): UUID mapped to a file.
- `metaData` (Array, Optional): Array of JSON objects as key-value pairs. These will be sent as query params in final response URL.

---

## Notes

- Browser allows maximum of 2000 characters in a URL. Final URL generated using the key values should not exceed this number.
- Maximum allowed URLs to be generated is 10. No duplicate file identifiers are allowed.
- Keys and values should be strings containing alphanumeric characters, with allowed special characters: ['-', '_', '.'
  ]
- `readCount` and `readExpiryDuration` are expected to be sent for each file unless the client wants to use the default values.
- By default, `readExpiryDuration` is 60 minutes and `readCount` is 1000.

---

## Sample curl Request and Responses For input 2

**Sample cURL Request**

```bash
curl --location 'https://qa-document-service-api.cargoes.com/file-storage/presignedurl' \
--header 'x-api-key:<< API_KEY >>' \
--header 'Content-Type: application/json' \
--data '{
  "fileInfoArray": [
    {
      "fileIdentifier": "99ea61e0-281f-4e79-83b0-3b50f8f0e75e",
      "readCount": 1,
      "readExpiryDurationInMinutes": 30,
      "metaData": {
        "key": "value"
      }
    }
  ]
}'

```

---

**JSON Request Body**

```json
{
  "fileInfoArray": [
    {
      "fileIdentifier": "99ea61e0-281f-4e79-83b0-3b50f8f0e75e",
      "readCount": 1,
      "readExpiryDurationInMinutes": 30,
      "metaData": {
        "key": "value"
      }
    }
  ]
}
```

---

**Response**

```json
[
  {
    "fileIdentifier": "99ea61e0-281f-4e79-83b0-3b50f8f0e75e",
    "preSignedUrl": "https://qa-document-service-api.cargoes.com/file-storage/file/presignedurl?key=value&signature=1616cda61cdada631223874bd69a86975a9be7c922b5de18eaf178216a0615d76a7f3a5e533fb7080bf07e3e0993725f%7C44bb3b4c21046bdfe6fd912f8d30815b"
  }
]
```

---

## Error Codes

- `40030`: Argument Error – For invalid arguments
- `50090`: API Error

---

# Compress File

## Endpoint

```http
POST /file-utilities/compress
```

This API compresses the PDF file.

## Meta Data

**Purpose**
The `Compress File API` is designed to reduce the file size of PDF documents by optimizing embedded images and content. This is especially useful for minimizing storage costs, improving upload/download performance, and sharing large files over networks with size constraints.

**Key Features**

- Compresses uploaded or previously stored PDF files up to 400MB.
- Supports three input types: direct file, `filePath`, or `fileIdentifier`.
- Offers flexible response options including file stream, upload with identifier, or secure download link.
- Supports image quality adjustment via the `imageQuality` parameter (range: 0–100).
- Optionally compresses only scanned images using the `scannedImages` flag.
- Allows renaming of the output file with `.pdf` extension via `outputFileName`.
- Only one flag among `upload`, `downloadUrl`, or `secureDownloadLink` should be enabled.

**Typical Use Cases**

- Reduce the size of high-resolution PDF invoices before emailing.
- Compress scanned documents while preserving text readability.
- Prepare large legal or research files for archival or public distribution.
- Optimize PDF storage for mobile applications or low-bandwidth access.
- Automate PDF compression in document workflows using file path or file identifier.

---

## Query Parameters

**`file`**

- **Type:** File
- **Required:** Optional
- **Description:** Maximum allowed file size is 400MB.

**`filepath`**

- **Type:** string
- **Required:** Optional
- **Description:** Already uploaded filepath can be passed here.

**`fileIdentifier`**

- **Type:** UUID
- **Required:** Optional
- **Description:** Already uploaded fileIdentifier can be passed here.

**`enableDownloadLink`**

- **Type:** Boolean
- **Required:** Optional
- **Description:** Returns secureDownloadable link.

**`linkExpiryDuration`**

- **Type:** Integer
- **Required:** Optional
- **Description:** Default is 7 days. Only valid if `enableDownloadLink` is true.

**`imageQuality`**

- **Type:** Integer
- **Required:** Optional
- **Description:**  The default value is 10. This parameter specifies the quality of images to be compressed within the PDF, ranging from 0 to 100. A value of 100 represents the highest quality, while 0 represents the lowest quality.

**`upload`**

- **Type:** Boolean
- **Required:** Optional
- **Description:** Default is false. If enabled, file will be uploaded and stored at document service, and response will contain file identifier.

**`downloadUrl`**

- **Type:** Boolean
- **Required:** Optional
- **Description:** Default is false. If this flag is enabled, file be uploaded and stored at document service end, and response will have file identifier as well as download URL. Expiry duration of this URL will be 60 minutes. A new download URL can always be generated using generatePresignedUrl API as given in this same documentation.

**`outputFileName`**

- **Type:** String
- **Required:** Optional
- **Description:**  If OutputFilename is provided then output filename will be renamed to this file. It should have .pdf as extension.

**`scannedImages`**

- **Type:** Boolean
- **Required:**  By default it is false. If your document contains scanned images then set this flag as true. If this flag is set then only Images will be compressed. So if your document contains more images and less data then also this flag can help.

---

## Notes

- At least one of `file`, `filepath`, or `fileIdentifier` should be present. Do not use multiple together.
- In case of `filepath` or `fileIdentifier`, `X-DPW-ApplicationId` header is mandatory.
- Max file size allowed: **20MB**.
- At most one of `upload`, `downloadUrl`, and `enableDownloadLink` should be true.

---

## Sample cURL Requests And Responses

**Sample curl request For file input:**

```bash
curl --location 'http: //localhost:3300/file-utilities/compress' --header 'x-api-key: KCaxy3nqcfXXK8HEj2D3wEsnNOrKugfn' --form 'files=@"/Users/deepali/Downloads/kkjsanjs.pdf"'
```

**Sample curl request For file path**

```bash
curl --location 'http: //localhost:3300/file-utilities/compress' --header 'x-api-key: KCaxy3nqcfXXK8HEj2D3wEsnNOrKugfn' --form 'filePath="12345/testFile/test.pdf"'
```

**Sample curl request For file Identifier:**

```bash
curl --location 'http: //localhost:3300/file-utilities/compress' --header 'x-api-key: KCaxy3nqcfXXK8HEj2D3wEsnNOrKugfn' --form 'fileIdentifier="d1e89775-6f81-4f8f-91ea-a01f17b991d1"' --form 'enableDownloadLink="true"' --form 'linkExpiryDuration="8"'
```

**The sample successful response looks like this:**

The sample response would be a compressed pdf

---

**Sample Response when `enableDownloadLink` is true**

```json
{
  "filename": "randomstr.pdf",
  "secureDownloadLink": "https://docserdevblobs.blob.core.windows.net/dtlpfile-utility-development/datachain/mergedFiles/31ab0199-dbdc-4044b1c4-2cf9ad94519d.pdf?st=2022-11-03T05%3A06%3A02Z&se=2022-11-11T05%3A06%3A02Z&sp=r&spr=https&sv=2018-03-28&sr=b&sig=dnCiYagLINk4mGcKSowz42brw9xjWejGZ5SxC%2BDXis4%3D"
}
```

---

## Error Codes

- `40030`: Argument Error – Invalid input parameters
- `5009`: Internal Server Error – Unexpected failure

---

# Watermark Settings

## Endpoint

```http
POST /file-utilities/watermark
```

This endpoint allows adding a watermark to a PDF and retrieving watermark properties.

## Meta Data

**Purpose**
The `Watermark Addition API` allows clients to add custom watermarks to PDF files. It supports text-based watermarking with customizable appearance such as font, size, color, opacity, rotation angle, and positioning.

**Key Features**

- Supports direct PDF file upload or uses the `fils`/`filss` field.
- Watermark settings include:
  - Text content
  - Font style and size
  - Opacity (0.0 to 1.0)
  - Color (e.g., black, red, green, blue)
  - Placement angle and coordinates (xIndent, yIndent)
  - Zoom factor for scaling
- Optional `getWatermarkProperties` flag returns a JSON of default or effective properties used for watermarking.
- Ideal for marking documents with "CONFIDENTIAL",
  "DRAFT", or branding stamps.

**Typical Use Cases**

- Add DRAFT/CONFIDENTIAL stamp to legal or financial documents.
- Place organization branding or watermarks on shared reports.
- Preview watermark properties before actually applying to files.
- Automate watermarking of uploaded PDF documents in enterprise workflows.

---

## Watermark Settings
 These settings can alter the watermark and they should be included in the watermark object.

## Sample watermark object 

```json
"watermark": {
  "text": "NOTORIGINAL",
  "zoomFactor": 1,
  "opacity": 0.2,
  "fontStyle": "regular",
  "fontSize": 120,
  "color": "blue",
  "angle": 0,
  "xIndent": 60,
  "yIndent": 100
}
```


## Query Parameters

**`text`**
**Type:** string  
 **Required:** Yes  
 **Description:** The text to be added as a watermark.

**`angle`**  
 **Type:** int  
 **Required:** No  
 **Description:** Angle at which the text should be placed, rotating around the lower-left point of the watermark. Default is the page diagonal angle.

**`fontSize`**  
 **Type:** int  
 **Required:** No  
 **Description:** Font size of the watermark text. Default is 120.

**`fontStyle`**  
 **Type:** string  
 **Required:** No  
 **Description:** Font style for the watermark. Supported values: `regular`, `bold`, `italic`, `bold italic`. Default is `regular`.

**`opacity`**  
 **Type:** float  
 **Required:** No  
 **Description:** Watermark opacity ranging from 0.0 to 1.0. Default is 0.2.

**`color`**  
 **Type:** string  
 **Required:** No  
 **Description:** Color of the watermark. Supported: `green`, `red`, `blue`, `black`. Default is `black`.

**`zoomFactor`**  
 **Type:** float  
 **Required:** No  
 **Description:** Scale factor for the watermark (0.0 to 1.0). Default is 1.

**`xIndent`**  
 **Type:** int  
 **Required:** No  
 **Description:** X-coordinate of the watermark’s lower-left corner, starting from the left.

**`yIndent`**  
 **Type:** int  
 **Required:** No  
 **Description:** Y-coordinate of the watermark’s lower-left corner, starting from the bottom.

**`getWatermarkProperties`**  
 **Type:** boolean  
 **Required:** No  
 **Description:** If true, returns JSON with the watermark properties that will be applied.

---

## Notes 

**Opacity:**
   Sets a value to indicate the stamp opacity. The value ranges from 0.0 to 1.0. By default, the value is 0.2.
**Color:**
 This represents the color of the font. Colors which are supported in this API are green, red, blue, and black. By default, black color is used.
**Font Style:**
 Specifies style information applied to text. Available font styles are regular, bold, italic, and bold italic. By default, the 'regular' font style is used.
**Font Size:**
 Gets or sets the font size of the text. The default value is 120.
**Angle of placement:**
 Gets or sets the angle of the stamp in degrees. This property allows setting arbitrary rotation angles. It rotates on the left lower point of the stamp. The default value for the angle will be the diagonal angle of the page.
**Location:**
 The X and Y coordinates of stamp can be changed manually to adjust the location of the stamp as we want. xIndent is the horizontal stamp coordinate, starting from the left of watermark. yIndent is the vertical stamp coordinate, starting from the bottom of watermark. Coordinates of the lower left point of the stamp are (xIndent, yIndent).
**Zoom:**
 It is the zooming factor of the stamp. The value ranges from 0.0 to 1.0. By default, the value is 1.
**getWatermarkProperties:**
 If this is true then the response will be a JSON with the properties of the watermark that will be used to create the watermark on pdf. With this information, you can easily set properties as you intend.

**Response if getWatermarkProperties is true:**
 ```json
 {
  "zoomFactor": 1,
  "color": "black",
  "fontSize": 120,
  "fontStyle": "regular",
  "opacity": 0.2,
  "angle": 52.035740131923134,
  "xIndent": 160.222081235121,
  "yIndent": 205.33879969955692,
  "pageWidth": 612,
  "pageHeight": 792
}
```


## Sample cURL Request And Responses

**Sample cURL Request**

```bash
curl --location --request POST 'http: //staging-document-service-api.private-cargoes.com/file-utilities/addWatermark' \
--header 'X-DPW-ApplicationId: datachain' \
--header 'x-api-key: 0fec68342d502b603f7bd43b66ad2ee9' \
--form 'files=@"/Users/pavanipalvai/Downloads/sample.pdf"' \
--form 'watermark="{
  \"text\" : \"DRAFT\",
  \"zoomFactor\" : 1,
  \"opacity\" : 0.2,
  \"fontStyle\" : \"regular\",
  \"fontSize\" : 120,
  \"angle\" : 45,
  \"color\" : \"black\"
  }"'
```
---

**Sample Response (watermarked PDF)**

The response will be a PDF file with the watermark applied.

---

## Error Codes

- `40030`: Argument Error – Invalid input parameters
- `50090`: API Error – Internal Server Error

---

# Set File Content Types

## Endpoint

```http
POST admin/file-storage/file/content-type
```

 Adds the contentType for the fileType in the global client_settings in both db and cache.

---

## Meta Data

**Purpose**

The `Set File Content Type API` allows registering a MIME content type (`contentType`) associated with a file extension (`fileType`) in the system. This registration updates both the database and the runtime cache.

**Key Features**

- Registers a new file extension and MIME type mapping for consistent file validation.
- Updates both persistent (database) and in-memory (cache) configurations.
- Used to define accepted file types across the system.
- Prevents uploads of unsupported or invalid file formats.

**Typical Use Cases**

- Add new MIME types during onboarding of new document formats.
- Ensure consistency across systems that rely on MIME-type detection.
- Dynamically configure platform behavior for new file extensions.
- Enable safe and predictable file handling for uploads and downloads.

---

## Query Paramaters

**`fileType`**  
 **Type:** string  
 **Required:** Yes  
 **Description:** Extension of the file type (e.g. `pdf`, `docx`, `xls`).

**`contentType`**  
 **Type:** string  
 **Required:** Yes  
 **Description:** MIME type to associate with the extension (e.g. `application/pdf`, `application/vnd.ms-excel`).

---

## Sample cURL Request And Responses

**Sample cURL Request**

```bash
curl --location --request POST 'https: //api.example.com/admin/file-storage/file/content-type' --header 'x-api-key: <<API_KEY>>' --header 'Content-Type: application/json' --data '{
  "fileType": "pdf",
  "contentType": "application/pdf"
}'
```

---

**Sample cURL Response**

```json
{
  "success": true
}
```

---

## Error Codes

- `40030`: Argument Error – Invalid input parameters
- `42220`: Validation Error – Payload validation failed
- `50090`: API Error – Internal Server Error

# Delete File Content Types

## Endpoint

```http
POST admin/file-storage/file/content-type
```

Adds a content type mapping for a file extension in the global client settings (DB and cache).

## Meta Data

**Purpose**
The `Delete File Content Type API` removes a specified MIME content type associated with a file extension (`filsTyps`) from the global client settings. This deletion is reflected both in the database and the in-memory cache.

**Key Features**

- Used for unregistering or cleaning up invalid/unused MIME types for specific file extensions.
- Affects global `client_settings`, ensuring the change is consistently enforced across the platform.
- Accepts only valid combinations of `filsTyps` (file extension) and `contsntTyps` (MIME type).
- Synchronizes removal across both the persistent storage (DB) and runtime memory (cache).

**Typical Use Cases**

- Remove obsolete or misconfigured MIME types associated with a file extension.
- Prevent clients from uploading or associating files with deprecated content types.
- Maintain consistent content-type mappings for secure and controlled file handling.
- Cleanup global configuration after bulk MIME type corrections or schema updates.

---

## Query Parametrs

**`fileType`**  
 **Type:** string  
 **Required:** Yes  
 **Description:** File extension to configure (e.g. `pdf`, `docx`).

**`contentType`**  
 **Type:** string  
 **Required:** Yes  
 **Description:** MIME type to associate with the extension (e.g. `application/pdf`).

---

## Sample cURL Request And Responses

**Sample cURL Request**

```bash
curl --location --request POST 'https: //api.example.com/admin/file-storage/file/content-type' \
--header 'x-api-key: <<API_KEY>>' \
--header 'Content-Type: application/json' \
--data '{
  "fileType": "pdf",
  "contentType": "application/pdf"
}'
```

---

**Sample Response**

```json
{
  "success": true
}
```

---

## Error Codes

- `40030`: Argument Error – Invalid input parameters
- `42220`: Validation Error – Unprocessable Entity
- `50090`: API Error – Internal Server Error


##syllabus  pdf download link

https://docs.uoc.ac.in/website/syllabus/2024-06-22%2017:03:40_syl1852.pdf
