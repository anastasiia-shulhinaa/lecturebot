# LectureBot — setup checklist

Your step-by-step guide. **Part A** gets every key and service ready; **Part B** runs, tests
and presents the bot.

Never paste keys into chats or commit them. They only go into your local `.env` file.

---

# Part A — prepare services and keys

## A1. Telegram bot (≈5 min)
- [ ] In Telegram, search for **@BotFather** (blue checkmark) and press Start.
- [ ] Send `/newbot`.
  - Name: `LectureBot`
  - Username: must be unique and end in `bot`, e.g. `lecturebot_uni2026_bot`
- [ ] Copy the token (`123456789:AAH...`) → **TELEGRAM_BOT_TOKEN**. If it ever leaks: `/revoke`.
- [ ] Optional: `/setdescription`, `/setabouttext`, `/setuserpic`.
  The command menu (`/start`, `/help`, `/new`) is set automatically when the bot starts.

## A2. Tools on your computer (≈15 min)
Python 3.13 and Git are already installed. Still needed:
```powershell
winget install Gyan.FFmpeg
winget install Google.CloudSDK
```
- [ ] **Restart VS Code** so the new commands are found.
- [ ] Check: `ffmpeg -version` and `gcloud --version`.
- [ ] Set your Git identity if you haven't yet:
  ```powershell
  git config --global user.name "Your Name"
  git config --global user.email "you@example.com"
  ```

## A3. GitHub (≈3 min)
- [ ] https://github.com/new → name `lecturebot` → **Public**.
- [ ] Do **not** add a README, .gitignore or licence (the repo must be empty).
- [ ] Copy the URL: `https://github.com/<you>/lecturebot.git`.

## A4. Google Cloud free trial (≈10 min, do this early)
- [ ] https://cloud.google.com/free → **Get started for free**.
- [ ] Sign in with a **personal Gmail** (university accounts often block Cloud).
- [ ] Account type **Individual**, enter card details.
  The card is only for verification; a small temporary hold may appear and is released.
  You are not charged unless you click "Upgrade" yourself.
- [ ] Check: **Billing → Overview** shows the $300 credit and days left.

## A5. Project and budget (≈5 min)
- [ ] https://console.cloud.google.com → project picker (top bar) → **New project** → `lecturebot`.
- [ ] Copy the **Project ID** (may differ from the name, e.g. `lecturebot-471203`)
  → **GOOGLE_CLOUD_PROJECT**.
- [ ] Make sure this project is selected in the top bar from now on.
- [ ] **Billing → Budgets & alerts → Create budget**: scope = lecturebot, amount $10,
  alerts at 50 / 90 / 100 %. (A budget only sends emails; it doesn't stop spending.
  For this project you'll spend cents.)

## A6. Turn on the APIs (≈3 min)
**APIs & Services → Library**, search for each and click **Enable**:
- [ ] Cloud Speech-to-Text API
- [ ] Vertex AI API (Gemini; the console may call it **Agent Platform**)
- [ ] YouTube Data API v3
- [ ] Cloud Storage API (usually already on)

Or in one command (after A7's `gcloud init`):
```powershell
gcloud services enable speech.googleapis.com aiplatform.googleapis.com youtube.googleapis.com storage.googleapis.com
```

## A7. Connect gcloud to your account (≈5 min)
```powershell
gcloud init
gcloud auth application-default login
gcloud auth application-default set-quota-project <PROJECT_ID>
```
- [ ] `gcloud init`: choose your account and the `lecturebot` project.
- [ ] Both login commands open a browser; allow access.
- [ ] The bot uses this login for Speech-to-Text, Storage and Gemini, so no key file is needed.

## A8. Storage bucket (≈5 min)
- [ ] **Cloud Storage → Buckets → Create**:
  - Name: `lecturebot-audio-<project-id>` (globally unique) → **GCS_BUCKET**
  - Location: **Region → us-central1**
  - Storage class: Standard
  - Access: tick **Enforce public access prevention**, keep **Uniform**
  - Data protection: soft delete **off** (or leave default; it costs almost nothing)
- [ ] Open the bucket → **Lifecycle** → **Add a rule** → *Delete object*, condition *Age = 1 day* → Create.

## A9. YouTube API key (≈3 min)
- [ ] **APIs & Services → Credentials → Create credentials → API key**.
- [ ] Edit the key → **API restrictions → Restrict key** → only **YouTube Data API v3** → Save.
- [ ] Copy it → **YOUTUBE_API_KEY**.
- [ ] Test in a browser (your key at the end):
  `https://www.googleapis.com/youtube/v3/videos?part=snippet&id=dQw4w9WgXcQ&key=YOUR_KEY`
  You should see JSON with the video title.

## A10. Check Gemini (≈5 min)
- [ ] Console → **Vertex AI / Agent Platform → Model Garden** → search "Gemini" → open the
  newest **Flash** model → copy its model ID (e.g. `gemini-3.5-flash`) → **GEMINI_MODEL**.
- [ ] Quick test: open **Vertex AI Studio** (prompt playground) → type "Привіт" → run.
  If you get an answer, Gemini works with your trial.
- [ ] **GOOGLE_CLOUD_LOCATION** = `global` (if the model isn't available there, use `us-central1`).
- [ ] Only if Vertex doesn't work: https://aistudio.google.com → **Get API key** → your project
  → **GEMINI_API_KEY**, and set `GEMINI_BACKEND=aistudio`.

## A11. Demo material (≈15 min)
- [ ] **Short lecture, 2–5 min:** record yourself on your phone explaining a topic
  (e.g. "what cloud computing is"). You own it and the audio is clear.
  Also send it to yourself as a Telegram voice message.
- [ ] **Longer audio, 8–15 min** as MP3 (tests the Cloud Storage path).
- [ ] **Short MP4 video** under 20 MB.
- [ ] **YouTube lecture:** YouTube search → **Filters → Creative Commons**, 5–15 min long.

## Values you should have after Part A
```
TELEGRAM_BOT_TOKEN=
GOOGLE_CLOUD_PROJECT=
GOOGLE_CLOUD_LOCATION=global
GCS_BUCKET=
YOUTUBE_API_KEY=
GEMINI_MODEL=
GEMINI_API_KEY=        # only for the AI Studio fallback
```

---

# Part B — run, test, publish, present

## B1. Install and set up (≈5 min)
In the VS Code terminal, in the project folder:
```powershell
.venv\Scripts\Activate.ps1          # .venv already exists; if not: python -m venv .venv
pip install -r requirements.txt
copy .env.example .env
```
- [ ] If activation is blocked: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, then retry.
- [ ] Open `.env` and paste the values from Part A.

## B2. Tests and start
```powershell
pytest
python -m bot.main
```
- [ ] All tests pass (the FFmpeg tests run once FFmpeg is installed).
- [ ] The terminal says `Starting in polling mode`. Keep it open; the bot runs only while it's open.

## B3. Try every scenario in Telegram
- [ ] `/start` shows the welcome text and button
- [ ] 30-second voice message → "text ready" → **Обидва** → summary + `summary.md` + quiz polls
- [ ] 8–15 min MP3 (Cloud Storage path) → works
- [ ] Short MP4 → works
- [ ] File over 20 MB → clear refusal
- [ ] Silent recording → "speech not recognized"
- [ ] Public YouTube link → info card → **Обробити** → buttons → summary
- [ ] Private or unavailable YouTube link → refusal
- [ ] Question as a normal message → answer based on the lecture
- [ ] **Транскрипт** button → `transcript.txt`

If something fails, copy the **full error text from the terminal** (check it has no keys)
and send it to Claude.

## B4. Check the cloud side
- [ ] **Cloud Storage → your bucket** is empty after processing.
- [ ] **Billing → Reports** shows only cents, paid from the credit.

## B5. Push to GitHub
```powershell
git status                       # .env must NOT be listed
git remote add origin https://github.com/<you>/lecturebot.git
git push -u origin main
```
- [ ] Open the repo in the browser and check `.env` isn't there.

## B6. Demo video (≈30 min)
- [ ] Record Telegram Desktop for 2–4 min with **Win+G** (Xbox Game Bar) or OBS.
  Follow §13 of `lecturebot_updated_instructions.md`.
- [ ] Upload it to YouTube as **Unlisted** (or Google Drive) and put the link in README.md.
- [ ] Keep the MP4 to put directly into the presentation.

## B7. Presentation
- [ ] Screenshots: menu, summary, a quiz poll, YouTube card.
- [ ] Slides (follow §15 of the instructions):
  1. title + problem
  2. solution and use cases
  3. APIs used (role, limits, price)
  4. architecture diagram (from README)
  5. demo video
  6. limitations and next steps
  7. GitHub link + QR code

## B8. Optional: Cloud Run (last week only)
See "Розгортання на Cloud Run" in README.md. It uses credit while running, so delete the
service after your defence.

## B9. Defence day
- [ ] Start the bot and run one test **an hour before**.
- [ ] Have the demo video ready as a backup, plus a phone hotspot.
- [ ] After the course: **IAM & Admin → Settings → Shut down** the project, and `/revoke` the
  bot token in BotFather.
