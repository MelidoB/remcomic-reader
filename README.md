# 🗨️ RemComic Reader

This is the lightweight web app for reading pre-processed comics with accessibility in mind.  
It fetches comic assets (JSON, images, audio) from your cloud storage and presents them in a browser-friendly interface.

---

## 🌐 Deploy Your Own

You can easily deploy this project to **Vercel** or **Netlify**.

### 1. Deploy to Vercel/Netlify
- Sign up for a free account on [Vercel](https://vercel.com/) or [Netlify](https://www.netlify.com/).
- Create a **New Project/Site** and import this repository.
- The framework should be detected as **Vite**. The default build settings are correct.

### 2. Set Environment Variable
In your project settings → **Environment Variables**, add:

Key: VITE_ASSETS_URL
Value: https://your-bucket-url.example.com

yaml
Copy code

(Use the public root URL of your S3/R2 bucket where your comic assets are hosted.  
Example: `https://pub-12345.r2.dev`)

### 3. Deploy
Trigger a new deployment.  
Your comic reader will now be live and fetching content directly from your cloud storage.

---

## 📂 Comic Assets

This reader expects your assets to already be uploaded and publicly accessible.  
The bucket should have a structure similar to:

public/
├── chapters.json
└── chapter-1/
	├── 01.json
	├── 02.json
	├── 01.jpg
	├── 02.jpg
	└── audio/
		├── chapter-1_01_bubble_1_speed_1_0.mp3

yaml
Copy code

(How you generate or upload these files is up to you and is **not included** in this repository.)

---

✅ That’s it! Once deployed, you’ll have your own hosted comic reader that loads content straight from your bucket.