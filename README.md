# pythonsponge-server
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

This is an example server implementation for tracking student progress for [PythonSponge](https://github.com/gdenes355/python-frontend). Stack: nginx, uvicorn, FastAPI, websockets.

### High-level principles

* The main Python server is more or less stateless
* The WebSocket server is stateless and when disabled, the FastAPI server should be able to replace all its functionality (albeit slower due to the many API requests)
* Data is stored via the database class. This reference implementation uses Firestore, but it is easy to add other providers (SQLite, etc.)
* The server can be deployed on a VM (instructions below).
* The server(s) can be debugged locally (instructions below).

### Server infrastructure

* [nginx](https://nginx.org/): reverse proxy as the first point of contact on the server
* [uvicorn](https://www.uvicorn.org/): ASGI Python server container
* [FastAPI](https://fastapi.tiangolo.com/): API web framework
* WebSocket: low-latency high-throughput communication (alternative to FastAPI when available)

### Authentication and Authorization

For authentication, you can use MSAL (Sign in with Microsoft) or Google (Sign in with Google). The front end app needs to present a valid MSAL/Google token, which this backend API verifies.

The MSAL/Google token is not stored by the server. We instead return a JWT token, which contains the user's email `encrypted` using the server's private key. Protected endpoints (such as books) check for the presence of the JWT token. Admin endpoints also check whether the user's email is in the admin list.

### Firestore Database

By default we store all data in Google Firestore, which is a NoSQL database. There are 3 collections:

* `classes`: each document is a class with a unique name, such as `9A GXD 2022-23`. Expected fields: `active: boolean`, `books: str[]`, `students: str[]`. For students, this is just their username (first half of email without @....)
* `results`: every result document stores an individual student's progress in a book. The name of the document is `<book_path>&<username>`, URL-encoded. E.g. `books/y9/y9u3/book.json&gdenes355` will turn into `books%2Fy9%2Fy9u3%2Fbook.json%26gdenes355`. Each result document has the following fields: `user: str`, and a field for every attempted challenge

  * The challenge field name is the challenge id. E.g. `013be4e3-583d-f47c-8efc-56b0f5589e73`
  * The challenge field is a map with the following entries:

    * `correct: boolean`
    * `correct-code?: str`
    * `correct-date?: Date`
    * `wrong-code?: str`
    * `wrong-date: Date`

## FAQ:

**How do I add a new `admin/teacher`?**

> Teachers are currently hard-coded in `shared/admin_list.py`. Edit this locally on the deployment server.

**How do I add a new book?**

> New books can be pushed to `/books/*`, keeping a logical structure (e.g. `y5/u1` for Year 5's Unit 1). Note that results are stored using the book path, so if you move a book, it will stop existing books from working and it might invalidate progress reports.

**How do I author a new book?**
See [https://github.com/gdenes355/python-frontend](https://github.com/gdenes355/python-frontend)

# Setting up your own server

There are numerous options out there to host your own server. In practice, a cheap / free tier server hosted on AWS / Google Cloud / Azure can work perfectly well.

### Google Cloud

Create a new instance on [https://console.cloud.google.com/compute/instances](https://console.cloud.google.com/compute/instances)

Select a location close to where you plan to use PythonSponge.

Pick a machine size appropriate for your needs. A free tier e2-micro is likely to work (note that the cloud console will quote the VM price around 10 USD per month, but if this is your only VM, the free tier machine cost will be deducted later).

Hit `Create`, and wait for the creation to finish.

`Stop` the machine for now using the controls on the top, then hit `edit` using the pencil icon.

Edit the VM name to something friendlier if you wish to. E.g. `my-school-pythonsponge-vm`.

In the `Firewalls` section, tick `Allow HTTPS traffic`. Then `Save`, and once complete, `Start/Resume` the VM.

Use the SSH button to open the VM terminal in the browser.

## Server installation on Linux

Create a machine and log in via SSH. Your machine could be an AWS/Google Cloud/Azure VM, or any similar Linux box.

1. Make sure that curl is installed

```bash
sudo apt install curl
```

2. Download and run the machine setup script from this repository. This can be done automatically by running

```bash
curl -fsSL https://raw.githubusercontent.com/gdenes355/pythonsponge-server/main/tools/install.sh -o install.sh
chmod +x install.sh
sudo ./install.sh
```

During installation, you will be prompted for additional information (e.g. authentication method, API keys for authentication etc.). These all get stored in the deployed `.env` file to be accessed by the web server.

## Server scripts

After setting up your server, the following will be available:

#### Redeploy server

Run `pythonsponge redeploy` to refetch the git repository, install requirements and to (re)launch the servers.

#### Restart nginx

This should only be necessary if the nginx config files were altered. In this case, run `pythonsponge restart-nginx`.

#### Rerun installation

The installation script is idempotent and can be rerun at any point to retrigger all setup steps

```bash
curl -fsSL https://raw.githubusercontent.com/gdenes355/pythonsponge-server/main/tools/install.sh -o install.sh
chmod +x install.sh
sudo ./install.sh
```

## Database
The repo is structured such that you could plug in a variety of db solutions. The current public implementation supports **Google Firesfore / Firebase**.

### Google Firestore / Firebase
First, create a new Firebase project at https://console.firebase.google.com/. Enable the Firestore database.

Then on https://console.cloud.google.com/iam-admin/serviceaccounts you need to create a service account with the relevant permissions (`Cloud Datastore User`, `Datastream Service Agent`, `Firebase Realtime Database Service Agent`, `Firebase Rules Firestore Service Agent`, `Firestore Service Agent`).

Configure your Google VM to use this service account (this will propagate roles and permissions automatically). For non-Google servers and local development, go to Keys, create a new key (json), and copy-paste its content into `pythonsponge-google-creds.json`

# Local debugging

The server can be run on localhost, which alongside a local instance of `python-frontend` allows end-to-end testing.

## Initial steps

After cloning the repository, it is best practice to create a new virtual Python environment for development, typically in a subfolder named `.venv`. This can be done e.g. using VSCode's `Python: Create Environment`.

Once the environment is active, run `pip install -r requirements.txt` from the terminal.

Create a local `.env` file with the following contents. The keys here are dummies (and should not match the prod keys). Fill in the relevant fields. E.g. `GOOGLE_AUTH_CLIENT_ID`, `GOOGLE_AUTH_CLIENT_SECRET`. Or for MSAL, update `AUTH_PROVIDER`, and fill in `MSAL_CLIENT_ID`, `MSAL_TENANT_ID`.

```
JWT_SECRET_KEY=please-change-me
ENC_KEY=qN0MrQd968LRVNffCVP6EAtQ539gJWZRBYntQKexQhU=
GOOGLE_APPLICATION_CREDENTIALS=pythonsponge-google-creds.json
GOOGLE_AUTH_CLIENT_ID=
GOOGLE_AUTH_CLIENT_SECRET=
AUTH_PROVIDER=GOOGLE
MSAL_CLIENT_ID=
MSAL_TENANT_ID=
DEBUG=True
CAN_EDIT_BOOKS_FOLDER=True
```

The project contains launch configurations for VSCode. Simply go to the `Run and Debug` panel and launch both FastAPI and Websockets (using the dropdown).

# Credentials, secrets, environment variables

This GitHub repository does not (and should not) contain any secret keys. The server stores its own secrets in `~/deployed/enc/.env`. We currently use:

* `DEBUG`: "TRUE" locally; "FALSE" on the server
* `JWT_SECRET_KEY`: placeholder, feel free to replace
* `ENC_KEY`: placeholder Fernet key, feel free to replace with any other valid Fernet key
* `GOOGLE_APPLICATION_CREDENTIALS`: locally `pythonsponge-google-creds.json`, auto-populated by Google on the server.
* `AUTH_PROVIDER`: `MSAL` or `GOOGLE`
* `MSAL_CLIENT_ID`, `MSAL_TENANT_ID`: non-sensitive information for Microsoft login
* `GOOGLE_AUTH_CLIENT_ID`, `GOOGLE_AUTH_CLIENT_SECRET`: information for Google login (**`GOOGLE_AUTH_CLIENT_SECRET` is sensitive**)
* `RESULTS_PROTOCOL`: locally `ws` at the moment, but can be updated if needed. This determines whether the Flask server will try to promote the WebSocket endpoint.
* `UTILS_PW`: locally `debugPassword`; this is the strong password that protects the `/api/utils/ip` endpoint (which reveals the server IP) — WIP
* `CAN_EDIT_SERVER_BOOKS_FOLDER`: `True` or `False`; specifies whether the `/books/` folder can be edited on the server from the teacher portal. This should be false if you set up some git-based version control system, otherwise `True` makes most sense.

Note that `pythonsponge-google-creds.json` is not committed to the repo. You will need to download the test service account's credentials from [https://console.cloud.google.com/iam-admin/iam](https://console.cloud.google.com/iam-admin/iam).

# Contributing to the project

We welcome code additions to this GitHub repo via PRs as long as they are in-line with the original design intentions of the project:

* lightweight
* enabling Python learners and educators
* serving as a platform to facilitate learning
* maintain open-source MIT license

## Contributors

<a href = "https://github.com/gdenes355/python-frontend/graphs/contributors">
<img src = "https://contrib.rocks/image?repo=gdenes355/pythonsponge-server"/>
</a>

# License

MIT License

Copyright (c) 2022 Gyorgy Denes, Paul Baker

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

