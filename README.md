# GHOST-Aurora Labeling GUI

<img src="labelling_app.png" alt="Aurora Labeling App" width="220" />

Desktop application to manually label all-sky camera images as either:
- `GHOST-aurora`
- `non-GHOST-aurora`
- `Unknown`

The app supports:
- one folder per day directly under `data_root`, or
- nested folders where leaf folders contain images (for example `year/month/day`).

Example:

```text
data_root/
  2025-01-03/
    image_0001.jpg
  2025-01-07/
    image_0001.jpg
```

```text
data_root/
  2024/
    12/
      14/
        LYR-Sony-20241214_000000.jpg
      15/
        LYR-Sony-20241215_000000.jpg
```

## 1) Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2) Run

```bash
python app.py --data-root "/path/to/data_root"
```

If your source is an SMB URL (example: `smb://birkeland.unis.no/KHO/Sony/2024/12/14/...`), first mount it in Finder, then use the mounted local path (usually under `/Volumes/...`), e.g.:

```bash
python app.py --data-root "/Volumes/KHO/Sony/2024/12"
```

Optional arguments:
- `--output-csv "/path/to/ghost_aurora_labels.csv"` (default: `ghost_aurora_labels.csv`)

## 3) Labeling workflow

- Select a day in the left panel.
- Use the file list in the left panel to jump directly to any specific image/time.
- Bulk labeling: use `Shift` or `Cmd/Ctrl` in the file list to select multiple images, then press `1`, `2`, or `3` to apply one label to all selected files.
- Bulk unlabel: select multiple files and press `U` (or click **Unlabel**) to remove labels for all selected files.
- If any selected images are already labeled, the app asks for confirmation before overwriting.
- Navigate images with:
  - `Left` / `Right` arrows
- Apply labels with:
  - `1` -> `non-GHOST-aurora`
  - `2` -> `GHOST-aurora`
  - `3` -> `Unknown`
  - `U` -> remove label
- Use filters on the left to show only the categories you want:
  - **Show Unlabeled**
  - **Show Non-GHOST**
  - **Show GHOST**
  - **Show Unknown**

Labels are saved automatically after each action to the session file.

## 4) Export CSV

Click **Export CSV** and choose where to save.

Output format:

```csv
filepath,label
/abs/path/image_0001.jpg,non-GHOST-aurora
/abs/path/image_0002.jpg,GHOST-aurora
```

Only labeled images are exported.
If your session contains old labels from a different dataset root, those rows are skipped automatically.

## Notes

- Supported image extensions: `.jpg`, `.jpeg`, `.png`
- By default, each opened `data_root` keeps its own session file. The app uses `<data_root>/.ghost_label_session.json` when writable, otherwise it uses a writable per-folder fallback under `~/.ghost_label_sessions/`.
- The app prints the exact resolved session path at startup as `Session file: ...`.
- If you close the app, you can resume later by reopening the same folder/date.
- The app uses `labelling_app.png` as logo/icon with rounded corners (falls back to built-in logo if file is missing).
