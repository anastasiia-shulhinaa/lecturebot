# LectureBot — step-by-step setup and run guide

Every step is written as a path: **open → press → type/add → result**.
Do the parts in order. ✅ shows what you should see when a step worked.

> Keys and tokens only ever go into the local `.env` file. Never paste them into chats,
> screenshots, slides or commits.

## Contents
- [Part 1. Install the tools](#part-1-install-the-tools)
- [Part 2. Google Cloud free trial and project](#part-2-google-cloud-free-trial-and-project)
- [Part 3. Turn on the APIs](#part-3-turn-on-the-apis)
- [Part 4. Log in to Google Cloud from your computer](#part-4-log-in-to-google-cloud-from-your-computer)
- [Part 5. Storage bucket](#part-5-storage-bucket)
- [Part 6. YouTube API key](#part-6-youtube-api-key)
- [Part 7. Gemini model](#part-7-gemini-model)
- [Part 8. Telegram bot](#part-8-telegram-bot)
- [Part 9. Fill in .env](#part-9-fill-in-env)
- [Part 10. Check everything](#part-10-check-everything)
- [Part 11. Run the bot](#part-11-run-the-bot)
- [Part 12. Use the bot in Telegram](#part-12-use-the-bot-in-telegram)
- [Part 13. Optional: run in Docker](#part-13-optional-run-in-docker)
- [Part 14. Test every scenario](#part-14-test-every-scenario)
- [Part 15. Publish to GitHub](#part-15-publish-to-github)
- [Part 16. Optional: deploy to Cloud Run](#part-16-optional-deploy-to-cloud-run)
- [Part 17. Demo video, presentation, defence](#part-17-demo-video-presentation-defence)
- [Part 18. Troubleshooting](#part-18-troubleshooting)

### What access you will end up with

| What | Why the bot needs it | Part |
|---|---|---|
| Google Cloud project where you are **Owner** | You can enable APIs; the bot uses them as you | 2 |
| Your Google login saved on the computer (ADC) | Bot → Speech-to-Text, Storage, Gemini (no key files) | 4 |
| YouTube API key | Bot → YouTube video info | 6 |
| Telegram bot token | Code acts as your bot | 8 |
| GitHub repo | Code for the assignment | 15 |
| Service account + Secret Manager (Cloud Run only) | Identity and keys for the bot in the cloud | 16 |

Use a **personal Gmail** everywhere. University accounts (`@knu.ua`) are often blocked from Google Cloud.

---

## Part 1. Install the tools

**1.1 FFmpeg and gcloud**
1. Press **Start** → type `PowerShell` → press **Enter**.
2. Type `winget install --id Gyan.FFmpeg -e` → press **Enter** → if Windows asks "allow changes?" press **Yes** → wait for "Successfully installed".
3. Type `winget install --id Google.CloudSDK -e` → press **Enter** → **Yes** → wait for "Successfully installed".
4. Close **all** PowerShell windows **and VS Code** (File → Exit).

**1.2 Check**
1. Open VS Code → **File → Open Folder** → choose `D:\Uni\Cloud Computing\LectureBot` → press **Select Folder**.
2. Menu **Terminal → New Terminal** (it opens at the bottom; it must say `powershell`).
3. Type `ffmpeg -version` → **Enter**; then `gcloud --version` → **Enter**.

✅ Both print versions. ❌ "not recognized" → you didn't fully close VS Code; restart the computer.

**1.3 Optional: Telegram Desktop** (for recording the demo)
- Open https://desktop.telegram.org → press **Get Telegram for Windows** → run the installer → log in by scanning the QR code with your phone (Telegram → Settings → Devices → **Link Desktop Device**).

---

## Part 2. Google Cloud free trial and project

**2.1 Start the free trial**
1. Open https://cloud.google.com/free → press **Get started for free**.
2. Choose your **personal Gmail** → sign in.
3. Country: **Ukraine** → tick the Terms of Service → press **Agree & continue**.
4. Account type: **Individual** → fill in name and address → add your **card** → press **Start free**.
   - The card only proves you're a real person. A temporary ~$1 hold may appear and disappears.
   - You are never charged unless you press **Upgrade / Activate full account** yourself.
5. Close any welcome survey.

✅ Open ☰ (top-left) → **Billing** → **Overview**. It shows "Free trial credit $300" and the days left.

**2.2 Create the project**
1. Open https://console.cloud.google.com → press the **project picker** in the top bar (next to the "Google Cloud" logo) → press **New project**.
2. Project name: type `lecturebot` → Billing account: your trial account → Location: **No organization** → press **Create**.
3. Wait ~30 s → press the bell icon → **Select project** (or project picker → `lecturebot`).
4. ☰ → **Cloud overview → Dashboard** → in the "Project info" card, copy the **Project ID** (e.g. `lecturebot-471203`) → paste it into a private note as `GOOGLE_CLOUD_PROJECT`.

⚠️ The Project ID can differ from the name. Always check the top bar shows **lecturebot** before changing anything.

**2.3 Budget alert**
1. ☰ → **Billing** → **Budgets & alerts** → press **+ Create budget**.
2. Name: `lecturebot` → Projects: tick **lecturebot** → press **Next**.
3. Budget type: **Specified amount** → Target amount: `10` (use `25` if you'll do Part 16) → press **Next**.
4. Leave thresholds 50 %, 90 %, 100 % → tick **Email alerts to billing admins and users** → press **Finish**.

✅ The budget appears in the list. It only sends emails; it doesn't stop anything.

---

## Part 3. Turn on the APIs

Repeat for each API in the table:
1. ☰ → **APIs & Services** → **Library**.
2. In the search box type the API name → press **Enter** → press the result with exactly that name.
3. Press **Enable** → wait until the API's page opens.

| Type in search | Press the result | Used for |
|---|---|---|
| `Speech-to-Text` | **Cloud Speech-to-Text API** | speech → text |
| `Vertex AI` | **Vertex AI API** (product may be called "Agent Platform") | Gemini |
| `YouTube Data` | **YouTube Data API v3** | video info |
| `Cloud Storage` | **Cloud Storage API** (often shows **Manage** = already on) | temporary audio |

✅ ☰ → **APIs & Services → Enabled APIs & services** lists all four.

---

## Part 4. Log in to Google Cloud from your computer

**4.1 Connect gcloud**
1. VS Code → **Terminal → New Terminal**.
2. Type `gcloud init` → **Enter**.
3. If asked "Pick configuration to use" → type the number of **Re-initialize this configuration** → **Enter**.
4. "Choose the account" → type the number of **Sign in with a new Google Account** → **Enter** → a browser opens → choose your Gmail → press **Continue** → **Allow**.
5. Back in the terminal: "Pick cloud project to use" → type the number of `lecturebot-…` → **Enter**.
6. "Do you want to configure a default Compute Region and Zone?" → type `n` → **Enter**.

**4.2 Give the code access (ADC)**
1. Type `gcloud auth application-default login` → **Enter**.
2. Browser opens → choose the same Gmail → tick **all** checkboxes → press **Continue**.
   ✅ Terminal: `Credentials saved to file: [...application_default_credentials.json]`.
3. Type `gcloud auth application-default set-quota-project <PROJECT_ID>` (your ID from 2.2) → **Enter**.
   ✅ `Quota project "<PROJECT_ID>" was added to ADC`.
   ❌ "Cannot add the project as a quota project" → finish Part 3 first, check the ID for typos.

**4.3 Check**
- Type `gcloud config list` → **Enter**. ✅ Shows your `account` and `project = <PROJECT_ID>`.

---

## Part 5. Storage bucket

**5.1 Create**
1. ☰ → **Cloud Storage** → **Buckets** → press **+ Create**.
2. Name: type `lecturebot-audio-<PROJECT_ID>` → copy it into your note as `GCS_BUCKET` → press **Continue**.
3. Location type: **Region** → choose **us-central1 (Iowa)** → **Continue**.
4. Storage class: **Standard** → **Continue**.
5. Tick **Enforce public access prevention on this bucket** → Access control: **Uniform** → **Continue**.
6. Data protection → Soft delete policy: choose **None** (or leave default) → press **Create**.
7. If a pop-up "Public access will be prevented" appears → press **Confirm**.

**5.2 Auto-delete rule**
1. In the bucket → open tab **Lifecycle** → press **+ Add a rule**.
2. Action: **Delete object** → **Continue**.
3. Condition: tick **Age** → type `1` → **Continue** → press **Create**.

✅ Lifecycle tab shows "Delete object — Age: 1 day".

---

## Part 6. YouTube API key

1. ☰ → **APIs & Services** → **Credentials** → press **+ Create credentials** → **API key**.
2. If a form opens: Name `youtube-key` → **API restrictions: Restrict key** → in the dropdown tick only **YouTube Data API v3** → press **OK** → **Create**.
   If the key is created immediately: press **Edit API key** → **Restrict key** → tick **YouTube Data API v3** → **OK** → **Save**.
3. Press **Show key** (or the copy icon) → copy `AIza…` into your note as `YOUTUBE_API_KEY`.
4. Test: open a new browser tab → paste
   `https://www.googleapis.com/youtube/v3/videos?part=snippet&id=dQw4w9WgXcQ&key=YOUR_KEY` (your key at the end) → **Enter**.

✅ You see JSON text containing `"title"`. A new key can take up to 5 minutes to start working.

---

## Part 7. Gemini model

1. ☰ → **Vertex AI** (or **Agent Platform**) → if asked, press **Enable all recommended APIs**.
2. Left menu → **Model Garden** → search box: type `Gemini` → press the newest **Gemini … Flash** card.
3. On the model page find the **model ID** (e.g. `gemini-3.5-flash`) → copy it into your note as `GEMINI_MODEL`.
4. Test: press **Open in Vertex AI Studio** (or left menu **Vertex AI Studio → Create prompt**) → choose that model → type `Привіт` → press **Submit/Run**.

✅ The model answers. Note `GOOGLE_CLOUD_LOCATION=global` (change to `us-central1` only if Part 10 shows NOT_FOUND).

**Option B: Google AI Studio with an API key**

You need this key **for YouTube links** even when you use Vertex AI for everything else:
Vertex AI answers `401 UNAUTHENTICATED` to YouTube URLs. Keep `GEMINI_BACKEND=vertex` and
just add `GEMINI_API_KEY`; the bot then sends only YouTube videos through AI Studio.

AI Studio and Agent Platform are two different doors to Gemini:

| | Agent Platform (Vertex AI) | Google AI Studio |
|---|---|---|
| Where | console.cloud.google.com | aistudio.google.com |
| Access | your gcloud login (Part 4), **no key** | **API key** |
| `.env` | `GEMINI_BACKEND=vertex` | `GEMINI_BACKEND=aistudio` + `GEMINI_API_KEY` |

1. Open https://aistudio.google.com → sign in with the **same Gmail** → accept the terms if asked.
2. Left menu (bottom) → press **Get API key** (or **Dashboard → API keys**) → press **Create API key**.
3. In "Choose a project" press **Create API key in new project** (or **Create project** → name `lecturebot-youtube`).
   ⚠️ **Don't pick `lecturebot-…`.** It has billing (the free trial), so AI Studio treats it as a
   prepaid tier with a $0 balance and answers `402 Your prepayment credits are depleted`.
   Free-trial credits don't apply to AI Studio. A project **without billing** uses the free tier,
   which includes YouTube videos (up to 8 hours a day).
4. Press **Create key** → press the copy icon next to the key (`AIza…`) → put it into your note as `GEMINI_API_KEY`.
5. Choose a **text** model: left menu → **Playground/Chat** → model dropdown (top right) → pick the newest **Gemini … Flash** → press **Get code** → copy the ID from `model="…"` (e.g. `gemini-3.5-flash`) → this is `GEMINI_MODEL`.
   ⚠️ Don't pick IDs ending in `-tts`, `-image`, `-live` or `-embedding`; they don't generate text answers.
6. Optional, list every text model your key can use (VS Code terminal, after `.venv\Scripts\Activate.ps1`):
   ```powershell
   python -c "import os; from dotenv import load_dotenv; load_dotenv(); from google import genai; c = genai.Client(api_key=os.environ['GEMINI_API_KEY']); [print(m.name) for m in c.models.list() if 'generateContent' in (m.supported_actions or [])]"
   ```
7. In Part 9 set `GEMINI_BACKEND=aistudio`, `GEMINI_API_KEY=<key>`, `GEMINI_MODEL=<model ID without "models/">`.

---

## Part 8. Telegram bot

1. Phone → open **Telegram** → search `@BotFather` → open the one with the **blue checkmark** → press **Start**.
2. Type `/newbot` → send.
3. Bot name: type `LectureBot` → send.
4. Username: type e.g. `lecturebot_uni2026_bot` (must end with `bot`) → send. If taken → try another.
5. ✅ "Done! Congratulations…" → long-press the token (`7123456789:AAH…`) → **Copy** → put it into your note as `TELEGRAM_BOT_TOKEN`.
6. Optional polish:
   - Type `/setdescription` → choose your bot → send `Створюю конспекти й тести з аудіо, відео та YouTube-лекцій.`
   - Type `/setabouttext` → choose the bot → send `Конспекти й тести з лекцій. Google Cloud + Gemini.`
   - Type `/setuserpic` → choose the bot → send a square picture.

You don't need `/setcommands`; the bot sets its menu itself. If the token ever leaks: `/revoke` → choose the bot → update `.env`.

---

## Part 9. Fill in .env

1. VS Code → **Terminal → New Terminal** → type `copy .env.example .env` → **Enter**.
2. Left sidebar (Explorer) → press `.env` to open it.
   ⚠️ Put your values in **`.env`**, never in `.env.example`. `.env.example` is uploaded to GitHub and must keep empty values.
3. Paste the values from your note after the `=` signs (no quotes, no spaces):

| Line in `.env` | What to put |
|---|---|
| `TELEGRAM_BOT_TOKEN=` | token from Part 8 |
| `GOOGLE_CLOUD_PROJECT=` | Project ID from Part 2.2 |
| `GOOGLE_CLOUD_LOCATION=` | `global` |
| `GCS_BUCKET=` | bucket name from Part 5 (without `gs://`) |
| `GEMINI_BACKEND=` | `vertex` (or `aistudio` for the fallback) |
| `GEMINI_MODEL=` | model ID from Part 7 |
| `GEMINI_API_KEY=` | leave empty (only for `aistudio`) |
| `YOUTUBE_API_KEY=` | key from Part 6 |

4. Leave all other lines as they are (`WEBHOOK_URL` must stay **empty** locally) → press **Ctrl+S**.

`.env` is in `.gitignore`, so Git never uploads it.

---

## Part 10. Check everything

1. VS Code terminal → type `.venv\Scripts\Activate.ps1` → **Enter**.
   - ❌ "running scripts is disabled" → type `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` → **Enter** → type `Y` → **Enter** → repeat the activation.
   - ✅ The prompt now starts with `(.venv)`.
2. Type `python -m bot.check_setup` → **Enter**.

✅ Every line starts with `[OK]` and the last line says `All checks passed`:
```
[OK] .env settings - project=lecturebot-471203, gemini=vertex/gemini-3.5-flash
[OK] FFmpeg - ffmpeg and ffprobe found
[OK] Telegram bot token - bot @lecturebot_uni2026_bot
[OK] Google credentials - default project=..., quota project=lecturebot-471203
[OK] Cloud Storage bucket - uploaded and deleted gs://...
[OK] Speech-to-Text API - API reachable (0 results for silence, as expected)
[OK] Gemini - model answered: ...
[OK] YouTube Data API v3 - test video: ...
```
❌ A `[FAIL]` line → read its **Hint** → fix → run the command again. See also [Part 18](#part-18-troubleshooting).
Right after enabling an API, errors often just mean "wait 2–5 minutes".

3. Type `pytest` → **Enter**. ✅ `29 passed`.

---

## Part 11. Run the bot

1. VS Code terminal (prompt starts with `(.venv)`; if not, run `.venv\Scripts\Activate.ps1`).
2. Type `python -m bot.main` → **Enter**.

✅ The terminal shows `Starting in polling mode. Press Ctrl+C to stop.` and `Application started`.

- The bot works **only while this terminal is open** and the computer is awake and online.
- **Stop:** press inside the terminal → **Ctrl+C**.
- **After changing code or `.env`:** **Ctrl+C** → `python -m bot.main` again.
- **Only one copy at a time** (otherwise: `Conflict: terminated by other getUpdates request`).
- Errors appear in this terminal. Copy them if something goes wrong.

---

## Part 12. Use the bot in Telegram

1. Telegram (phone or desktop) → search your bot's username (e.g. `@lecturebot_uni2026_bot`) → open it → press **Start**.
   ✅ Welcome message with the **📚 Обробити лекцію** button.
2. Press **📚 Обробити лекцію** → the bot lists what you can send.
3. Send a lecture, one of:
   - hold the 🎤 button → record → release → **voice message**;
   - press 📎 → **File** → choose an MP3/M4A/OGG/WAV up to **20 MB**;
   - press 📎 → **Gallery** → choose a short video up to 20 MB;
   - paste a **YouTube link** to a public video → send.
4. Watch the status message change: `📥 Файл отримано` → `🎧 Готую аудіо` → `📝 Розпізнаю мовлення`.
5. When you see `✅ Текст лекції готовий` → press one button:
   - **📝 Конспект** → summary message + `summary.md` file;
   - **❓ Тест** → 5 quiz polls → press an answer → see right/wrong + explanation;
   - **📚 Обидва** → both;
   - **📄 Транскрипт** → `transcript.txt`.
6. Ask a question: type e.g. `Що таке IaaS?` → send → the answer comes from this lecture only.
7. YouTube: after the link → card with title/channel/length → press **▶️ Обробити** → wait → same buttons as in step 5.
8. New lecture: press **Menu** → `/new` (or just send the next file).

To let someone else try it: send them `https://t.me/<your-bot-username>` while the bot runs.

---

## Part 13. Optional: run in Docker

1. Stop the Python bot (**Ctrl+C**).
2. Start → open **Docker Desktop** → wait until the bottom-left says **Engine running**.
3. VS Code terminal → type `docker build -t lecturebot .` → **Enter** → wait (first time 3–5 min).
4. Type:
   ```powershell
   docker run --rm --name lecturebot --env-file .env -v "$env:APPDATA\gcloud:/root/.config/gcloud:ro" lecturebot
   ```
   → **Enter**. ✅ Same `Starting in polling mode` as in Part 11.
5. Stop: **Ctrl+C** (or `docker stop lecturebot` in another terminal).

---

## Part 14. Test every scenario

Bot running → in Telegram do each action → tick it:

- [ ] Send `/start` → welcome + button; send `/help` → instructions
- [ ] Record a 30 s voice message → **📚 Обидва** → summary, `summary.md`, quiz polls
- [ ] Send an 8–15 min MP3 → works (long path through Cloud Storage)
- [ ] Send a short MP4 → works
- [ ] Send a file over 20 MB → "Файл більший за 20 МБ…"
- [ ] Record 10 s of silence → "Мовлення не розпізнано…"
- [ ] Send a public YouTube link → card → **▶️ Обробити** → summary
- [ ] Send a private/deleted video link → refusal message
- [ ] Type a question → answer from the lecture
- [ ] Press **📄 Транскрипт** → `transcript.txt`
- [ ] Send a sticker → "Такий тип повідомлення я не обробляю"

Then in the Console:
- [ ] ☰ → **Cloud Storage → Buckets** → your bucket → no audio files left.
- [ ] ☰ → **Billing → Reports** → filter project `lecturebot` → only cents, covered by credits.

Demo material: your own 2–5 min recording; an 8–15 min MP3; a short MP4; a YouTube lecture found via YouTube search → **Filters** → **Creative Commons** (5–15 min).

---

## Part 15. Publish to GitHub

**15.1 Create the repository**
1. Open https://github.com/new.
2. Repository name: `lecturebot` → choose **Public**.
3. Don't tick README, .gitignore or license → press **Create repository**.
4. Copy the HTTPS URL shown (`https://github.com/<you>/lecturebot.git`).

**15.2 Push**
1. VS Code terminal → type `git status` → **Enter** → make sure `.env` is **not** listed.
2. Type `git add -A` → **Enter**.
3. Type `git commit -m "Add setup checker and step-by-step guide"` → **Enter** (skip if it says "nothing to commit").
4. Type `git remote add origin https://github.com/<you>/lecturebot.git` → **Enter**.
5. Type `git push -u origin main` → **Enter** → a window "Connect to GitHub" opens → press **Sign in with your browser** → **Authorize git-ecosystem** → back in the terminal the push finishes.
6. Browser → refresh the repo page.

✅ README with diagrams is shown and `.env` is **not** in the file list.

Later changes: `git add -A` → `git commit -m "what changed"` → `git push`.

---

## Part 16. Optional: deploy to Cloud Run

Do this only in the **last week**: the bot then runs in Google Cloud and your computer can be
off. It costs about **$10/week** of credit, so delete it after the defence (16.7).
In all commands replace `<PROJECT_ID>`, `<BUCKET>` and `<MODEL>` with your values.

**16.1 Enable extra APIs**
- VS Code terminal → type:
  ```powershell
  gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com
  ```
  → **Enter** → wait for "finished successfully".

**16.2 Create the bot's cloud identity and give it access**
1. Type `gcloud iam service-accounts create lecturebot-sa --display-name "LectureBot"` → **Enter**.
2. Type `$SA = "lecturebot-sa@<PROJECT_ID>.iam.gserviceaccount.com"` → **Enter**.
3. Type (one block) → **Enter**:
   ```powershell
   foreach ($role in "roles/speech.client", "roles/aiplatform.user", "roles/storage.objectAdmin", "roles/secretmanager.secretAccessor") {
     gcloud projects add-iam-policy-binding <PROJECT_ID> --member "serviceAccount:$SA" --role $role --condition None
   }
   ```
4. Give the build step its permission:
   ```powershell
   $NUM = gcloud projects describe <PROJECT_ID> --format "value(projectNumber)"
   gcloud projects add-iam-policy-binding <PROJECT_ID> --member "serviceAccount:$NUM-compute@developer.gserviceaccount.com" --role roles/run.builder --condition None
   ```

✅ Console → ☰ → **IAM & Admin → IAM** shows `lecturebot-sa` with 4 roles.

**16.3 Store the secrets**
1. ☰ → **Security** → **Secret Manager** → if asked press **Enable**.
2. Press **+ Create secret** → Name: `telegram-bot-token` → Secret value: paste the bot token → press **Create secret**.
3. Back → **+ Create secret** → Name: `youtube-api-key` → Secret value: paste the YouTube key → **Create secret**.

**16.4 Deploy**
1. Stop the local bot (**Ctrl+C**) and Docker if running.
2. Type → **Enter**:
   ```powershell
   gcloud run deploy lecturebot --source . --region us-central1 `
     --service-account $SA --allow-unauthenticated `
     --no-cpu-throttling --min-instances 1 --max-instances 1 --cpu 1 --memory 1Gi --timeout 3600 `
     --set-env-vars "GOOGLE_CLOUD_PROJECT=<PROJECT_ID>,GCS_BUCKET=<BUCKET>,GEMINI_MODEL=<MODEL>,GOOGLE_CLOUD_LOCATION=global" `
     --set-secrets "TELEGRAM_BOT_TOKEN=telegram-bot-token:latest,YOUTUBE_API_KEY=youtube-api-key:latest"
   ```
3. "…Artifact Registry Docker repository… will be created. Do you want to continue?" → type `Y` → **Enter**.
4. Wait 3–6 minutes. ✅ Ends with `Service URL: https://lecturebot-….run.app`.

**16.5 Switch to webhook mode**
- Type these three lines → **Enter** after each:
  ```powershell
  $URL = gcloud run services describe lecturebot --region us-central1 --format "value(status.url)"
  $SECRET = [guid]::NewGuid().ToString("N")
  gcloud run services update lecturebot --region us-central1 --update-env-vars "WEBHOOK_URL=$URL,WEBHOOK_SECRET=$SECRET"
  ```
- Telegram → send `/start` to the bot. ✅ It answers while nothing runs on your computer.
- Logs: ☰ → **Cloud Run** → press **lecturebot** → tab **Logs**.

**16.6 After code changes**
- Run the same `gcloud run deploy …` command from 16.4 again (webhook settings are kept).

**16.7 Turn it off after the defence**
- Type `gcloud run services delete lecturebot --region us-central1` → **Enter** → `Y`.
- To use the bot locally again: `python -m bot.main` (it removes the webhook itself).

---

## Part 17. Demo video, presentation, defence

**17.1 Record the demo (2–4 min)**
1. Open Telegram Desktop → open the bot chat → turn off notifications (Settings → Notifications).
2. Press **Win+G** → Capture widget → press **● Record** (or use OBS Studio).
3. In the bot (full script with exact buttons and spoken lines: [DEMO.md](DEMO.md)):
   1. `/start`
   2. send a prepared 2–5 min audio → show the progress
   3. press **📚 Обидва** → scroll through the summary → answer 1–2 quiz questions
   4. ask one question
   5. send a YouTube link → card → **▶️ Обробити** → summary
4. Press **Win+Alt+R** to stop. The video is saved in `Videos\Captures`.
5. YouTube → **Create → Upload video** → choose the file → Visibility **Unlisted** → copy the link.
6. VS Code → open `README.md` → replace `_посилання буде додано_` with the link → **Ctrl+S** → `git add -A` → `git commit -m "Add demo link"` → `git push`.

**17.2 Presentation (7 slides)**
1. Title + problem.
2. Solution and use cases (students, teachers, self-learners, course authors).
3. APIs used: Telegram Bot API, Speech-to-Text, Cloud Storage, Gemini, YouTube Data API v3 (copy the table from README).
4. How the services interact: diagrams from README (screenshot them on GitHub) plus the access table at the top of this file.
5. Demo: **Insert → Video → This device** → the MP4 from 17.1, then a live demo.
6. Limitations and next steps (20 MB limit, public YouTube only, Cloud Run, history in Firestore).
7. GitHub link + QR code (Chrome → open the repo → address bar → **Share → Create QR code**).

**17.3 Defence day**
- [ ] One hour before: start the bot (or check Cloud Run) → send a short voice message → it works.
- [ ] Demo video saved offline as a backup.
- [ ] Phone hotspot ready in case the classroom Wi-Fi blocks Telegram.
- [ ] Use a 1–2 min recording for the live demo.

**17.4 After the course**
- [ ] Delete Cloud Run (16.7) if you deployed.
- [ ] ☰ → **IAM & Admin → Settings** → press **Shut down** → type the project ID → **Shut down**.
- [ ] Telegram → @BotFather → `/revoke` → choose the bot.

---

## Part 18. Troubleshooting

| You see | Do this |
|---|---|
| `ffmpeg … not recognized` / `[FAIL] FFmpeg` | Close all terminals and VS Code → reopen (or restart the PC) |
| `running scripts is disabled on this system` | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` → `Y` |
| `Configuration error: Missing … TELEGRAM_BOT_TOKEN` | Part 9: file must be named exactly `.env` and saved |
| `InvalidToken` | @BotFather → `/mybots` → bot → **API Token** → copy again into `.env` |
| `DefaultCredentialsError` | `gcloud auth application-default login` (Part 4.2) |
| `requires a quota project` / `USER_PROJECT_DENIED` | `gcloud auth application-default set-quota-project <PROJECT_ID>` |
| `403 … API has not been used in project … or it is disabled` | Part 3 → enable that API → wait 2–5 min |
| `404 … bucket does not exist` | `.env` → `GCS_BUCKET` = exact name, no `gs://` |
| Gemini `404 NOT_FOUND … model` | Part 7 → copy another model ID, or set `GOOGLE_CLOUD_LOCATION=us-central1` |
| Gemini `429` / "Вичерпано квоту Gemini" | Wait a minute and try again |
| `403 PERMISSION_DENIED` on Gemini right after the trial started | Wait 10–15 min; check Billing → Overview shows the credit |
| `Conflict: terminated by other getUpdates request` | Stop the other copy (another terminal, Docker or Cloud Run) |
| Bot doesn't answer at all | Is `python -m bot.main` running? If Cloud Run was used, starting locally removes its webhook |
| "Файл більший за 20 МБ" | Telegram limit for bots → send MP3 audio or a shorter clip |
| "Мовлення не розпізнано" for real speech | `.env` → `SPEECH_LANGUAGE=en-US` for English lectures → restart the bot |
| YouTube `keyInvalid` / `accessNotConfigured` | Part 6 (copy the key again) / Part 3 (enable the API) |
| Cloud Run build `PERMISSION_DENIED` | Run the `roles/run.builder` command from 16.2 step 4 |
| `git push` asks for a password | Run `git push` again → **Sign in with your browser** |

Still stuck: copy the error from the terminal (make sure it contains no keys) and send it to
Claude together with what you did.
