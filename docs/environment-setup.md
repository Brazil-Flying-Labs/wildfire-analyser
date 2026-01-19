# Step-by-Step Guide: Creating a Service Account for GEE Code + Creating a Bucket and Assigning Required Permissions

This guide explains, step by step, how to:

1. Create a **Google Cloud project** (if you don’t already have one).
2. Create a **service account** to authenticate Python/Node code that uses Google Earth Engine (GEE).
3. Generate a **JSON key** for the service account.
4. Create a **Google Cloud Storage (GCS) bucket**.
5. Assign the **required permissions** so the service account can **write to the bucket** using GEE export tasks (e.g., `Export.image.toCloudStorage`).

> Note: This guide assumes you already have a Google account with access to Google Cloud and Google Earth Engine.

---

## 1. Create (or choose) a Google Cloud Project

1. Go to:  
   https://console.cloud.google.com/

2. At the top of the page, open the project selector.

3. You may:
   - **Use an existing project**, or  
   - Click **“New Project”** and create one:
     - Name example: `wildfire-assessment-geospatial`
     - Choose the appropriate organization (if applicable)
     - Click **Create**

4. Make sure the project is selected (visible in the top bar).

---

## 2. Enable the Required APIs

Inside your selected project:

1. Go to **APIs & Services** → **Library**
2. Enable the following APIs:
   - **Earth Engine API**
   - **Cloud Storage JSON API**

Both are required for scripts that use GEE and export data to Cloud Storage.

---

## 3. Create the Service Account (for your GEE code)

1. Navigate to:  
   **IAM & Admin** → **Service Accounts**

2. Click **“Create Service Account”**

3. Fill out the form:
   - **Service account name**: e.g., `gee-service-account`
   - **Description**: “Service account for Google Earth Engine scripts”
   - The service account email will look like:  
     `gee-service-account@wildfire-assessment.iam.gserviceaccount.com`

4. Click **Create and Continue**

5. Assign basic roles such as:
   - `Viewer` (or `Project Viewer`)

6. Click **Continue** → **Done**

Keep the service account email handy—we will use it to assign bucket permissions.

---

## 4. Create a JSON Key for the Service Account

1. In **IAM & Admin** → **Service Accounts**, click on the service account you created.

2. Open the **Keys** tab.

3. Click **“Add Key”** → **“Create new key”**

4. Choose:
   - **JSON**

5. Click **Create**  
   A `.json` key file will be downloaded, e.g.:
   `wildfire-assessment-gee-service-account.json`

> **Important:**  
> - Keep this file secure.  
> - **Never** upload it to a public repository.

---

## 5. Create a Cloud Storage Bucket

1. Go to:  
   https://console.cloud.google.com/storage/browser

2. Click **“Create Bucket”**

3. Configure:
   - **Bucket name**: e.g., `post-fire-assessment-data`  
     (must be globally unique)
   - **Region**: choose as appropriate (e.g., `us-central1`)
   - **Storage class**: Nearline (default)

4. Leave other settings as default unless you have specific requirements.

5. Click **Create**

---

## 6. Grant the Service Account Permission to Write to the Bucket

To allow GEE export tasks (and Python scripts using GEE) to write into the bucket, assign write permissions.

1. Open the bucket you created (e.g., `post-fire-assessment-data`)
2. Go to the **Permissions** tab
3. Click **“Grant Access”**
4. In **New principals**, add:

gee-service-account@wildfire-assessment.iam.gserviceaccount.com


5. Assign one of the following roles:

### Recommended (production)
- **Storage Object Creator** (`roles/storage.objectCreator`)  
Allows creating/uploading files, but not deleting or listing everything.

### If also reading/listing/deleting objects via code:
- **Storage Object Admin** (`roles/storage.objectAdmin`)

6. Click **Save**

At this point, your service account can write to the bucket.

## 7. LifeCycle
1. In the left menu, click Lifecycle
(Sometimes under “Lifecycle rules” or “Object lifecycle”)
2. Click “Add a rule”
3. Choose “Delete object” as the action
4. Choose the condition:
5. Select “Age”
   Set Age = 1 day
   (This means GCS will delete any object older than 24 hours.)
   Leave the other conditions empty unless needed.
6. Click Create to save the rule.
