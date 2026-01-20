# Step-by-Step Guide: Creating a Service Account for GEE Code + Creating a Bucket, Permissions, and 24-Hour Auto-Deletion Rule

This guide explains, step by step, how to:

1. Create a **Google Cloud project**
2. Create a **service account** for running Google Earth Engine (GEE) code
3. Generate a **JSON key** for the service account
4. Create a **Cloud Storage bucket**
5. Assign the required **write permissions** to the service account
6. **Create an auto-deletion rule** that removes files older than 24 hours

> Note: This guide assumes you already have a Google account with access to Google Cloud and Google Earth Engine.

---

## 1. Create (or choose) a Google Cloud Project

1. Go to https://console.cloud.google.com/
2. Open the project selector at the top.
3. Select an existing project or click **New Project**.
4. Give it a name, e.g., `wildfire-assessment-geospatial`.
5. Click **Create**.

---

## 2. Enable Required APIs

Inside the selected project:

1. Go to **APIs & Services → Library**
2. Enable:
   - **Earth Engine API**
   - **Cloud Storage JSON API**

---

## 3. Create the Service Account

1. Go to **IAM & Admin → Service Accounts**
2. Click **Create Service Account**
3. Enter:
   - Name: `gee-service-account`
   - Description: “Service account for Google Earth Engine scripts”
4. Click **Create and Continue**
5. Assign at least the `Viewer` role
6. Click **Done**

Service account email example:
