# Resume Flow

Resume handling is backend-driven.

Frontend responsibilities:

* validate basic file shape for UX
* send the file to backend API placeholders only
* render resume state returned by backend APIs

Backend responsibilities:

* issue upload contracts
* persist metadata
* coordinate storage and processing
* keep file storage and database access out of the browser

Current placeholder API contracts:

* `POST /v1/resumes`
* `GET /v1/resumes/{user_id}`

The previous client-side storage and direct persistence shortcut has been removed.
