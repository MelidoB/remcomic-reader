# remcomic-reader: Self-Hosted with Free Frontend

This project is set up to run a powerful Python backend on your local PC while hosting the user interface for free on a service like Vercel or Netlify.

## How It Works

1.  **Frontend (Vercel/Netlify):** A static site (HTML, CSS, JS) that provides the user interface. It's fast and globally accessible.
2.  **Backend (Your PC):** A Python/Flask server that processes comics, runs AI models, and generates audio.
3.  **Tunnel (`ngrok`):** A free tool that creates a secure public URL for your local backend, allowing the public frontend to find and communicate with it.

## Step-by-Step Deployment Guide    

### Step 1: Set Up the Backend

1.  Navigate to the `backend` directory: `cd backend`
2.  Create and activate a Python virtual environment:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```
3.  Install dependencies: `pip install -r requirements.txt`
4.  Place your comic folders inside `backend/chapters/`.

### Step 2: Set Up the Frontend on GitHub

1.  Create a new, public repository on GitHub (e.g., `my-comic-reader-ui`).
2.  Copy the entire `frontend` folder's contents into this new repository.
3.  Commit and push the files to GitHub.

### Step 3: Run the Full System

You will need **two separate terminal windows** running on your PC.

**Terminal 1: Start the Backend Server**

1.  Navigate to the `backend` directory.
2.  Activate the virtual environment: `source venv/bin/activate`
3.  Run the server:
    ```bash
    bash start_backend.sh
    ```
4.  Leave this terminal running. It is now serving your AI backend on `localhost:5000`.

**Terminal 2: Start the `ngrok` Tunnel**

1.  [Download and install `ngrok`](https://ngrok.com/download).
2.  Authenticate your `ngrok` client (a one-time setup command they provide).
3.  Start the tunnel pointing to your backend's port (5000):
    ```bash
    ngrok http 5000
    ```
4.  `ngrok` will display a public URL (e.g., `https://random-words-123.ngrok.io`). **Copy this `https` URL.**
5.  Leave this terminal running.

### Step 4: Configure and Deploy the Frontend

1.  **Configure:** Open the `frontend/js/config.js` file in your code editor.
2.  **Paste the `ngrok` URL** you copied into the `BACKEND_URL` variable.
    ```javascript
    // Example:
    const BACKEND_URL = 'https://random-words-123.ngrok.io';
    ```
3.  **Commit and push** this change to your GitHub repository.
4.  **Deploy:**
    *   Sign up for a free account on [Vercel](https://vercel.com) or [Netlify](https://www.netlify.com) using your GitHub account.
    *   Create a "New Project/Site" and import your `my-comic-reader-ui` repository from GitHub.
    *   The default settings should be correct. Click "Deploy".
5.  After a minute, your site will be live on a public URL (e.g., `https://my-comic-reader-ui.vercel.app`).

You can now access this Vercel/Netlify URL from any device, anywhere, and it will connect to the backend running on your PC.

**IMPORTANT:** If you restart your PC or the `ngrok` tunnel, you will get a new random `ngrok` URL. You must update `frontend/js/config.js` and push the change to GitHub again to update the live site.