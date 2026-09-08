# KinderCare Media Downloader — Setup Guide

This guide gets the `kindercare_download.py` script running from a completely
fresh computer — no prior setup assumed. Follow the section for your
operating system, then skip to **Both platforms** at the end.

---

## macOS

### 1. Install Python
1. Go to [python.org/downloads](https://www.python.org/downloads/) and click
   the yellow "Download Python" button.
2. Open the downloaded `.pkg` file and click through the installer
   (default options are fine).
3. Open the **Terminal** app (press `Cmd + Space`, type "Terminal", hit Enter).
4. Type `python3 --version` and press Enter. You should see something like
   `Python 3.12.x`. If you see an error, restart your Mac and try again.

### 2. Install exiftool
1. Go to [exiftool.org](https://exiftool.org) and download the **macOS
   Package** (the `.dmg` file).
2. Open the `.dmg`, then double-click the `.pkg` installer inside it and
   click through it.
3. In Terminal, type `exiftool -ver` and press Enter — it should print a
   version number.

### 3. Set up the project folder
1. In Terminal, run these lines one at a time (each followed by Enter):
   ```
   cd ~/Desktop
   mkdir kindercare-project
   cd kindercare-project
   ```
2. Move (drag and drop) the `kindercare_download.py` file into this new
   `kindercare-project` folder on your Desktop.

### 4. Create a virtual environment and install packages
Copy-paste each line into Terminal, pressing Enter after each:
```
python3 -m venv env
source env/bin/activate
pip install requests beautifulsoup4 python-dateutil
```
You'll know it worked if your Terminal prompt now starts with `(env)`.

---

## Windows

### 1. Install Python
1. Go to [python.org/downloads](https://www.python.org/downloads/) and click
   the yellow "Download Python" button.
2. Run the downloaded installer. **Important:** on the very first screen,
   check the box at the bottom that says **"Add python.exe to PATH"** before
   clicking Install.
3. Open **PowerShell** (press the Windows key, type "PowerShell", hit
   Enter).
4. Type `python --version` and press Enter. You should see something like
   `Python 3.12.x`. If it says "not recognized," restart your computer and
   try again (this fixes it almost every time).

### 2. Install exiftool
1. Go to [exiftool.org](https://exiftool.org) and download the **Windows
   Executable** (a `.zip` file).
2. Right-click the downloaded `.zip` and choose "Extract All."
3. Inside the extracted folder you'll find a file named
   `exiftool(-k).exe`. Rename it to just `exiftool.exe`.
4. Move `exiftool.exe` into `C:\Windows\` (this makes it runnable from
   anywhere — you'll be asked to confirm as an administrator, which is fine).
5. In PowerShell, type `exiftool -ver` and press Enter — it should print a
   version number.

### 3. Set up the project folder
1. In PowerShell, run these lines one at a time:
   ```
   cd ~\Desktop
   mkdir kindercare-project
   cd kindercare-project
   ```
2. Move (drag and drop) the `kindercare_download.py` file into this new
   `kindercare-project` folder on your Desktop.

### 4. Create a virtual environment and install packages
Copy-paste each line into PowerShell, pressing Enter after each:
```
python -m venv env
.\env\Scripts\Activate.ps1
pip install requests beautifulsoup4 python-dateutil
```
You'll know it worked if your prompt now starts with `(env)`.

> If you get an error about "running scripts is disabled," run this line
> once, type `Y` when asked, then try the activate line again:
> ```
> Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
> ```

---

## Both platforms — running the script

### 1. Get your login cookie
The script needs to "log in" as you, using a code your browser already has.
1. Open **Chrome** (or Edge) and log into
   `classroom.kindercare.com` normally.
2. Once you're on the activities page, press `F12` to open Developer Tools.
3. Click the **Network** tab near the top of the panel that opens.
4. Press `Cmd+R` (Mac) or `Ctrl+R` (Windows) to reload the page.
5. A list of requests will appear on the left side of that panel. Click the
   very first one (it should be named `activities?page=1` or similar).
6. On the right, find the **Headers** section, scroll to find a line that
   starts with `Cookie:`. Click on the value and copy the entire long line
   of text after `Cookie:` (it'll be a wall of text — that's normal).

### 2. Add the cookie to the script
1. Open `kindercare_download.py` in a plain text editor:
   - **Mac:** right-click the file → Open With → TextEdit
   - **Windows:** right-click the file → Open with → Notepad
2. Find the line near the top that says:
   ```
   COOKIE_HEADER = "PASTE_YOUR_COOKIE_HEADER_HERE"
   ```
3. Replace the text between the quotes with the cookie you copied, so it
   looks like:
   ```
   COOKIE_HEADER = "the_long_string_you_copied_goes_here"
   ```
4. Save the file (`Cmd+S` / `Ctrl+S`) and close the editor.

### 3. Find your account number
Look at the web address while you're on the activities page — it looks like:
```
https://classroom.kindercare.com/accounts/504906/activities?page=1
```
The number after `/accounts/` (here, `504906`) is your account number.

### 4. Run it — test first, then the real thing
Back in your Terminal/PowerShell window (make sure it still shows `(env)`
at the start of the prompt — if not, redo the "activate" line from step 4
above), run:
```
python3 kindercare_download.py --account 504906 --pages 1 --out ./kindercare_media
```
(On Windows, use `python` instead of `python3`.)

This downloads just page 1 as a test. Open the new `kindercare_media`
folder that appears and check the photos/videos are there and look right.

Once that looks good, download everything (this will take a while — let it
run):
```
python3 kindercare_download.py --account 504906 --pages 142 --out ./kindercare_media
```

### Notes
- If it stops partway through (e.g. your cookie expires after a while),
  just repeat steps 1–2 to get a fresh cookie, then re-run the same command
  — it automatically skips files it already downloaded.
- Every time you come back in a new Terminal/PowerShell window, you need to
  `cd` back into the `kindercare-project` folder and re-run the "activate"
  command before running the script again.
