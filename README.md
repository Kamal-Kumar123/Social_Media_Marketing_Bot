# AdBot - AI-Powered Social Media Marketing Bot

AdBot is a comprehensive Streamlit application that automates social media marketing campaigns across multiple platforms using AI-generated content. This tool helps businesses manage, schedule, and optimize their social media advertising efforts with ease.

## Features

- **AI Content Generation**: Create platform-specific ad copy and images using OpenAI's GPT and DALL-E
- **Multi-Platform Management**: Post to Facebook, Twitter, Instagram, LinkedIn, TikTok, Pinterest, and Snapchat
- **Automated Scheduling**: Schedule posts at optimal times or set custom schedules
- **Performance Analytics**: Track engagement metrics and identify top-performing platforms
- **Product Management**: Organize your products and their marketing details
- **User-Friendly Interface**: Streamlit dashboard with intuitive navigation

## Installation

1. Clone the repository:
```
git clone https://github.com/yourusername/AdBot.git
cd AdBot
```

2. Install the required dependencies:
```
pip install -r requirements.txt
```

3. Create a `.env` file with your API credentials (copy from .env.template):
```
cp .env.template .env
```

4. Edit the `.env` file with your API keys and credentials

## Running the Application

Run the Streamlit application:
```
streamlit run streamlit_app.py
```

The application will be accessible at http://localhost:8501

## Project Structure

```
AdBot/
├── data/                  # Data storage
│   ├── analytics/         # Analytics data
│   └── images/            # Generated images
├── models/                # Core models
│   ├── __init__.py
│   ├── config.py          # Configuration management
│   ├── content_generator.py # Content generation
│   ├── social_media_handler.py # Platform integrations
│   └── analytics_manager.py # Analytics and reporting
├── utils/                 # Utility modules
│   ├── __init__.py
│   ├── product_manager.py # Product management
│   └── scheduler.py       # Post scheduling
├── app.py                 # Original application code
├── streamlit_app.py       # Streamlit web application
├── requirements.txt       # Dependencies
└── .env.template          # Template for API credentials
```

## Usage Guide

### 1. Platform Setup
First, configure your social media API credentials in the "Platform Setup" page. You'll need API keys for each platform you want to use.

### 2. Product Management
Add your products with detailed descriptions, features, and target audience information in the "Products" page.

### 3. Content Creation
Generate and preview ad content before posting in the "Create Ad" page. Customize tone, length, and format to suit your marketing needs.

### 4. Post Scheduling
Schedule posts for optimal times or create recurring posting schedules in the "Schedule Posts" page. Use the auto-scheduling feature for efficient planning.

### 5. Analytics
Track performance metrics across platforms and products to optimize your marketing strategy in the "Analytics" page.

## API Requirements

To use all features, you'll need API credentials for:

- OpenAI (for content generation)
- Facebook/Meta Marketing API
- Twitter/X API
- Instagram API
- LinkedIn Marketing API
- TikTok Marketing API
- Pinterest API
- Snapchat Marketing API

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This application is for demonstration purposes. Ensure you comply with each platform's terms of service and API usage policies when deploying for commercial use. 