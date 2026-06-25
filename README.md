# 🚀 Industry Radar (科技产业情报雷达)

An automated, dual-track intelligence gathering system that acts as your personal Silicon Valley VC analyst. It continuously monitors top-tier global tech media and hacker communities, using advanced LLMs to strictly filter out the noise and deliver only world-changing tech breakthroughs and major industry focal points straight to your inbox.

## ✨ Features

- **Dual-Track VC Scoring System**: Articles are rigorously evaluated on two dimensions (0-10 scale) using OpenAI models:
  - **🔬 Hardcore Innovation (硬核创新)**: Measures underlying technological breakthroughs, long-term commercial value, and disruptive potential.
  - **📈 Traffic & Hype (流量舆情)**: Measures short-term market sentiment, consumer frenzy, and social media buzz.
- **Top-Tier Global Sources**: Pulls raw intelligence from extremely high-signal sources including *The Information, Hacker News (Top 100), MIT Technology Review, TechCrunch, 36Kr, VentureBeat, SiliconANGLE*, and more.
- **Strict "Needle in a Haystack" Filtering**: Only articles scoring 8+ on either dimension pass the threshold, ensuring a "quality over quantity" approach. Out of 150+ articles daily, you only see the 2-3 that actually matter.
- **Beautiful HTML Newsletter**: Generates a sleek, premium-formatted HTML email newsletter and delivers it automatically.
- **Anti-Hang Armor**: Robust timeout and retry mechanisms designed to gracefully handle API rate limits and proxy server instability.

## 🛠️ Setup & Installation

### 1. Clone the repository
```bash
git clone https://github.com/edgerzou-stack/industry-radar.git
cd industry-radar
```

### 2. Install dependencies
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configuration
Copy the `.env.example` file to `.env`:
```bash
cp .env.example .env
```
Fill in your credentials in `.env`:
- `OPENAI_API_KEY`: Your OpenAI or proxy API key.
- `OPENAI_BASE_URL`: Base URL for the OpenAI API (defaults to `https://api.openai.com/v1`, change if using a proxy).
- `ICLOUD_APP_PASSWORD`: An App-Specific Password for your iCloud email (used for SMTP).

Adjust scoring thresholds, AI models (e.g. `gpt-5.4`, `gpt-4o-mini`), and target industries in `config.yaml`.

### 4. Run the Radar
```bash
python main.py
```

### 5. Automation
To run the radar automatically every day at 2:00 PM, add a cron job:
```bash
crontab -e
# Add the following line:
0 14 * * * cd /absolute/path/to/industry-radar && source venv/bin/activate && python main.py >> run.log 2>&1
```

## 📄 License
MIT
