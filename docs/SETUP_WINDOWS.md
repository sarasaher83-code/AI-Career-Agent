# Setting Up Career Intelligence on Windows

This guide assumes no programming experience. Follow the steps in order. Steps 1–4 are done only once.

---

## Step 1: Install Python (one time, about 5 minutes)

1. Open **https://www.python.org/downloads/** and click the yellow **Download Python 3.12** (or newer) button.
2. Run the downloaded installer.
3. **Important:** on the first screen, tick **"Add python.exe to PATH"**, then click **Install Now**.
4. When it says *Setup was successful*, click **Close**.

## Step 2: Download the application (one time)

1. Open the project page on GitHub: **https://github.com/sarasaher83-code/AI-Career-Agent**
2. Click the branch selector (it shows `main`) and choose the branch named in the latest update message.
3. Click the green **Code** button, then **Download ZIP**.
4. Right-click the downloaded ZIP, choose **Extract All…**, and extract to `Documents\AI-Career-Agent`.

## Step 3: Add your private profile (one time)

1. Inside the `AI-Career-Agent` folder, create a folder named **`private`** if it doesn't already exist.
2. Save the file **`master_profile.json`** (sent to you separately) into that `private` folder.

The `private` folder never leaves your computer. It is excluded from GitHub.

## Step 4: Get your Claude API key (one time, about 10 minutes)

The system uses the Claude API for matching jobs and drafting documents. The API is billed separately from a
Claude.ai subscription: even if you pay for Claude.ai, the API needs its own prepaid credit.

1. Go to **https://console.anthropic.com** and sign up or log in.
2. Open **Settings → Billing**:
   - add a payment card and **buy credits** (USD 10–20 is enough to start; the estimated running cost is about $20–45 a month);
   - optionally set a **monthly spend limit** as a second safety cap.
3. Open **Settings → API keys** (it may be labelled **API Keys** in the left menu) and click **Create key**.
   Name it `Career Intelligence`.
4. **Copy the key immediately.** It starts with `sk-ant-` and is shown only once.
5. Paste it into the `.env` file (Step 5). **Never paste the key into a chat, email, WhatsApp or screenshot.** If it is
   ever exposed, delete it in the console and create a new one.

## Step 5: Put the key into the `.env` file

1. Double-click **`start.bat`** once. The first start prepares the application and creates a file named **`.env`**.
   Close the black window afterwards.
2. In the `AI-Career-Agent` folder, right-click **`.env`** → **Open with** → **Notepad**.
   (If you can't see `.env`: in File Explorer choose **View → Show → File name extensions** and **Hidden items**.)
3. Find the line `ANTHROPIC_API_KEY=` and paste your key straight after the `=` sign, with no spaces or quotes:
   ```
   ANTHROPIC_API_KEY=sk-ant-...(your key)
   ```
4. Leave `MONTHLY_BUDGET_USD=50` (the system stops using the API after USD 50 in a month) or change the number.
5. Save (**Ctrl + S**) and close Notepad.

## Step 6: Start the application (every time)

1. Double-click **`start.bat`**.
2. A black window opens and your browser shows the dashboard at **http://127.0.0.1:8000**.
3. Check **System readiness** on the first page. *Master profile loaded* and *Claude API key configured* should show a gold dot.
4. To stop the application, close the black window.

The dashboard is only reachable from your own computer, never from the internet.

---

## Coming in stage S1: Gmail app password (you don't need to do this yet)

The system will read job-alert emails from one Gmail label. You will:
1. turn on **2-Step Verification** in your Google Account (Security);
2. create an **App password** (Google Account → Security → App passwords) named `Career Intelligence`;
3. paste it into `.env` after `GMAIL_APP_PASSWORD=` and your address after `GMAIL_ADDRESS=`.

A separate guide will cover creating the job alerts on LinkedIn, Bayt, GulfTalent, Naukrigulf and Indeed.

---

## Troubleshooting

| Message | Fix |
|---|---|
| *Python is not installed* | Repeat Step 1 and make sure "Add python.exe to PATH" is ticked |
| *Could not install the required packages* | Check your internet connection and run `start.bat` again |
| *master profile not found* | Check that `master_profile.json` is inside the `private` folder (Step 3) |
| Browser shows "can't reach this page" | Wait 5 seconds and refresh; keep the black window open |
| Claude API key shows "not set" | Recheck Step 5: no spaces, no quotes, and the file saved as `.env` (not `.env.txt`) |
