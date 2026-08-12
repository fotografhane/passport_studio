# Passport Studio

A desktop app for photo studios to generate print-ready passport photo sheets, batch multi-customer sheets, ID card front/back layouts, and cropped/straightened document scans — all on standard A4 paper.

**Created by Sandeep Chahal** ([@noob-214](https://github.com/noob-214))

---

## ✨ Features

- **Single Customer** — upload one photo, choose size & photo count (6/12/18/24), auto face-crop, white background removal, auto enhance, generate print-ready A4 sheet, print directly.
- **Batch (Multiple Customers)** — add unlimited customers in one session, each with their own photo, copy count, and processing options. All customers are placed sequentially on one A4 sheet (e.g. 6 photos for Customer A, then 12 for Customer B right below).
- **ID Card Layout** — auto-detect or manually select front & back of a government ID (Aadhaar, PAN, etc.), rotate, crop/straighten each side individually with a draggable corner editor, then place both sides on one A4 sheet with labels.
- **Single Page Crop** — detect and straighten any photographed document (certificates, forms, handwritten slips) shot at an angle on a phone camera, with manual corner-adjustment fallback when auto-detection isn't confident.
- **Rotate** — quick 90° rotation available for single customer photos, ID card front/back, and document crop images.
- **Auto Enhance** — sharpens and boosts contrast for print clarity.
- **White Background Removal** — swaps busy/uneven backgrounds for a clean white background.
- **Direct Printing** — send generated sheets straight to your configured printer.

---

## 🛠 Installation

```bash
git clone https://github.com/noob-214/Passport_Studio.git
cd Passport_Studio
pip install -r requirements.txt
python app.py
```

## ⚙ Configuration

Edit `settings.json` to adjust DPI, photo size, grid layout, and printer name:

---

## 📦 Building an .exe (Windows)

```bash
pip install pyinstaller
pyinstaller PassportStudio.spec
```

The built executable will be in `dist/PassportStudio.exe`. Copy `settings.json` next to the exe before running it.

---

## 🚧 Upcoming

- [ ] Customer history / saved records
- [ ] Multiple ID card layouts per A4 (batch ID printing)
- [ ] PDF export option alongside JPG
- [ ] Custom paper sizes (Letter, 4x6, etc.)
- [ ] Template presets for common document types (PAN, Aadhaar, Voter ID)
- [ ] Dark/Light theme toggle
- [ ] Auto-update checker

---

## 🤝 Contributing

Pull requests welcome. For major changes, open an issue first to discuss what you'd like to change.

## 📄 License

This project is licensed under the [MIT License](LICENSE) — free to use, modify, and distribute, including for commercial studio work, as long as the original copyright notice is kept.
