# 🗨️ RemComic Reader

A fast, modern, and hostable web application for reading comics with AI-powered features. This repository contains the **public frontend application**.

The comic processing (AI detection, OCR, TTS) is handled by a separate, private tool: `remcomic-processor`. The static output of that tool is placed in the `/public` directory of this repository and then deployed.

---

## ✨ Features

*   **🚀 Blazing Fast:** A fully static architecture means instant load times with zero backend processing delays for the user.
*   **🗣️ Text-to-Speech:** Pre-generated audio for all speech bubbles allows for an audiobook-like experience.
*   **✨ Modern & Responsive UI:** A clean Vue.js frontend that works on any device.
*   **🌐 Host Anywhere:** Easily deploy the entire reader to any modern static hosting provider like Vercel, Netlify, or GitHub Pages.

---

## 🚀 How to Deploy Your Own Reader

1.  **Generate Your Content:**
    *   Use the private `remcomic-processor` tool to process your comic book library. This will generate a folder of static assets (images, audio files, and JSON data).

2.  **Populate the `public` Directory:**
    *   Fork this repository.
    *   Copy the generated assets from your processor's output into the `/public` directory of your forked repository. For example, your `public` directory will now contain `chapters.json`, a `chapter-1` folder, etc.

3.  **Deploy to Vercel/Netlify:**
    *   Sign up for a free account on [Vercel](https://vercel.com) or [Netlify](https://www.netlify.com).
    *   Create a "New Project/Site" and import your forked repository.
    *   The framework should be detected as **Vite**. The default build settings are correct. Set the "Output Directory" to `dist`.
    *   You do **not** need to set any special environment variables for this simple static setup.
    *   Click **Deploy**.

Your comic reader is now live and serving the content you generated.