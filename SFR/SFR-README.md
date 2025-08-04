# Selective Frame Renderer (SFR) for Blender

**Version:** 3.4  
**Author:** Edwin Wagha & Gemini 2.5 Pro  
**Compatible Blender Version:** 4.0 and higher  

---

## 1. Introduction

The **Selective Frame Renderer (SFR)** is a powerful utility addon for Blender designed to save you valuable rendering time. It allows you to **specify and exclude certain frame ranges** from your final animation render.

Instead of rendering an entire timeline and deleting unwanted frames later, SFR intelligently skips over the ranges you define, rendering only the frames you need. This is perfect for re-rendering corrected sections of an animation, skipping finished parts, or troubleshooting glitches without having to render everything from scratch.

---

## 2. Key Features

- **Exclude Frame Ranges**: The core feature. Add as many frame ranges to the exclusion list as you need.
- **Stable Modal Operation**: The addon runs as a non-freezing background process, so Blender’s interface remains responsive while rendering. Cancel anytime with **ESC**.
- **Robust File Saving**: A custom file-saving algorithm constructs the full path manually, ensuring no files are missed or overwritten.
---

## 3. Installation

1. Download the Python script (`SFR.py`).
2. In Blender, go to **Edit > Preferences > Add-ons**.
3. Click the **Install...** button at the top-right.
4. Navigate to where you saved the `.py` file and select it.
5. Find **Selective Frame Renderer** in the list and enable it.
6. The addon’s panel will now appear in the **Output Properties** tab (printer icon).

---

## 4. How to Use

### 1. Set Main Timeline
Set your scene’s Start and End frames as usual.

### 2. Set Output Path
In **Output Properties > Output**, set your output path.

> ⚠️ **CRITICAL:** You must include a filename prefix at the end of the path.  
> - ✅ Correct: `C:\renders\my_animation_`  
> - ❌ Incorrect: `C:\renders\`

### 3. Locate the Panel
Go to the **Selective Frame Renderer** panel just below the Output settings.

### 4. Add Exclusion Ranges
- Click the `+` button to add a range.
- Set the Start and End frames you want to skip.
- Add more ranges as needed. Use `-` to remove a range.

### 5. Set Up Live View (Recommended)
- Select the render Tab.
- In the header, choose **Render Result**.

### 6. Start Rendering
- Click the **Render with Live View** button in the SFR panel.
- The progress will show up on the cursor and the Image Editor will update per frame.

---

### Example Scenario

Your animation runs from **frame 1 to 300**.  
You want to skip:

- Frames **50–65** (contains a mistake)
- Frames **150–220** (already rendered and approved)

Add two exclusion ranges:
- `Start: 50, End: 65`
- `Start: 150, End: 220`

SFR will render:
- Frames **1–49**
- Frames **66–149**
- Frames **221–300**

---