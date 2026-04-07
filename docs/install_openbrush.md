# Installing Open Brush for AI Sculptor

This guide covers installing Open Brush with API and Monoscopic mode enabled on all supported platforms.

## Step 1: Install Open Brush

### macOS (Steam)

1. Install [Steam](https://store.steampowered.com/about/) if you don't have it
2. Search for **"Open Brush"** in the Steam Store, or go to:
   https://store.steampowered.com/app/1634870/Open_Brush/
3. Click **Install**
4. Once installed, **don't launch yet** — configure it first (Step 2)

### Windows (Steam)

Same as macOS — install via Steam Store.

### Windows (Standalone)

1. Go to the [Open Brush Releases](https://github.com/icosa-foundation/open-brush/releases)
2. Download the latest `.zip` for Windows
3. Extract to a folder (e.g., `C:\OpenBrush`)

### Linux (Build from Source)

1. Clone the repository:
   ```bash
   git clone https://github.com/icosa-foundation/open-brush.git
   ```
2. Open in Unity (requires Unity 2022.3 LTS or the version specified in the repo)
3. Build for your platform

### Oculus Quest (SideQuest / Meta Store)

Open Brush is available on the Meta Quest Store. However, the **API features may have limitations on Quest**. For the AI Sculptor agent, a desktop version (Steam) is recommended.

---

## Step 2: Enable Monoscopic Mode (No VR Headset Required)

You can run Open Brush **without a VR headset** using Monoscopic Mode.

### Find the Config File

| Platform | Config Location |
|----------|----------------|
| **Windows (Steam)** | `%USERPROFILE%\Documents\Open Brush\Open Brush.cfg` |
| **macOS (Steam)** | `~/Documents/Open Brush/Open Brush.cfg` |
| **Linux** | `~/Documents/Open Brush/Open Brush.cfg` |

> **Note:** If the file doesn't exist, launch Open Brush once and close it — the file will be created automatically.

### Edit the Config File

Open `Open Brush.cfg` in a text editor. Find or add the `"Flags"` section and set:

```json
{
  "Flags": {
    "EnableMonoscopicMode": true
  }
}
```

> If there's already a `"Flags"` section, add the setting inside it.

---

## Step 3: Enable the API

Add these additional flags to enable the HTTP API:

```json
{
  "Flags": {
    "EnableMonoscopicMode": true,
    "EnableApiRemoteCalls": true,
    "EnableApiCorsHeaders": true
  }
}
```

| Flag | Purpose |
|------|---------|
| `EnableMonoscopicMode` | Run without VR headset |
| `EnableApiRemoteCalls` | Accept API commands from other apps on the same machine |
| `EnableApiCorsHeaders` | Allow browser-based API access (needed for web tools) |

---

## Step 4: Launch Open Brush

1. Start Open Brush (from Steam or standalone)
2. It will open in **Monoscopic Mode** (a flat window, no VR)
3. The API server will start on port **40074**

### Verify the API is Working

Open your browser and visit:

```
http://localhost:40074/help
```

You should see the Open Brush API help page. If so, the API is ready!

### Test a Simple Command

Try this in your browser address bar:

```
http://localhost:40074/api/v1?brush.type=ink&color.set.html=crimson&draw.polygon=5,2,0
```

You should see a red pentagon appear in Open Brush!

---

## Step 5: Configure the AI Sculptor

1. Copy `config.example.yaml` to `config.yaml`:
   ```bash
   cp config.example.yaml config.yaml
   ```

2. Edit `config.yaml` with your LLM API key:
   ```yaml
   llm:
     api_key: "sk-your-key-here"
     base_url: "https://api.openai.com/v1"  # or your custom endpoint
     model: "gpt-4o"
   ```

   Or set environment variables:
   ```bash
   export OPENAI_API_KEY="sk-your-key-here"
   export OPENAI_BASE_URL="https://api.openai.com/v1"  # optional
   ```

3. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run the sculptor:
   ```bash
   python -m sculptor.cli
   ```

---

## Monoscopic Mode Controls

When using Open Brush without VR:

| Control | Action |
|---------|--------|
| Alt (⌘ on Mac) + Mouse Drag | Rotate camera view |
| Left Click + Drag | Draw on the drawing plane |
| Right Click + Drag | Move drawing plane near/far |
| Ctrl + Mouse Drag | Rotate the drawing plane |
| Click in viewport | Capture mouse cursor |
| Esc | Release mouse cursor and show game menu |

---

## Running in Windowed Mode (macOS / Windows)

By default, Open Brush launches in fullscreen. To use it side-by-side with the CLI, you can force it into windowed mode using Unity command line arguments:

### If using Steam (Recommended)
1. Right-click **Open Brush** in your Steam library and select **Properties**.
2. In the **General** tab, scroll down to **Launch Options**.
3. Paste the following line to run in a 1280x720 window:
   ```text
   -screen-fullscreen 0 -screen-width 1280 -screen-height 720
   ```
4. Launch the game from Steam.

### If running from terminal (macOS)
```bash
/Applications/OpenBrush.app/Contents/MacOS/Open\ Brush -screen-fullscreen 0 -screen-width 1280 -screen-height 720
```

### If running from Command Prompt (Windows standalone)
```cmd
OpenBrush.exe -screen-fullscreen 0 -screen-width 1280 -screen-height 720
```

```cmd
OpenBrush.exe -screen-fullscreen 0 -screen-width 2560 -screen-height 1440
```

---

## Troubleshooting

### "Cannot connect to Open Brush"
- Make sure Open Brush is running
- Check that `EnableApiRemoteCalls` is set to `true` in the config
- Try visiting `http://localhost:40074/help` in your browser

### "Open Brush won't start in Monoscopic Mode"
- Double-check the config file syntax is valid JSON
- Make sure `EnableMonoscopicMode` is inside the `"Flags"` object
- On Steam, make sure you're using the right Open Brush version (main, not beta)

### API commands work but nothing appears
- Check the Open Brush viewport — you may need to rotate the camera (Alt + drag)
- The drawing might be at the origin (0,0,0) which may not be in view
- Try `http://localhost:40074/api/v1?user.move.to=0,0,-5` to move the camera back
